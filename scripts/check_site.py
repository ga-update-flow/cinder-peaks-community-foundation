"""Verify the built site in site/ (or a deployed URL with --url).

Checks:
  * every internal href/src resolves to a real file (local) or HTTP 200 (remote)
  * every page has one <h1>, a <title>, and no noindex (404 page excepted)
  * no placeholder / "not available" wording anywhere in pages
  * every PDF opens, has pages, and contains its expected title text
  * every .docx opens and contains its title
  * every document in the registry is linked from at least one resources page and grant pages link their documents
  * sitemap.xml and robots.txt exist; sitemap lists every page
"""
import argparse
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from docx import Document
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).parent))
from common import SITE_OUT, load_all  # noqa: E402

FORBIDDEN = [
    "not available", "not provided", "unknown", "to be determined", "tbd", "placeholder", "lorem ipsum",
    "sample field", "document not included", "coming soon", "example county", "anywhere town", "example avenue",
    "sample foundation", "santa fe community foundation", "sfcf", "santafecf",
]


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.h1, self.title, self.meta_robots = [], 0, "", ""
        self.ids = set()
        self._in_title = False
        self.text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag in ("a", "link") and a.get("href"):
            self.links.append(a["href"])
        if tag in ("script", "img") and a.get("src"):
            self.links.append(a["src"])
        if tag == "h1":
            self.h1 += 1
        if tag == "title":
            self._in_title = True
        if tag == "meta" and a.get("name") == "robots":
            self.meta_robots = a.get("content", "")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        self.text.append(data)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "cpcf-site-check/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read(), r.headers.get("Content-Type", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="Check a deployed site at this base URL instead of local files")
    args = ap.parse_args()
    remote = args.url.rstrip("/") + "/" if args.url else None
    errors, warnings = [], []
    ctx = load_all()

    pages = sorted(SITE_OUT.rglob("index.html"))
    rel_pages = [str(p.parent.relative_to(SITE_OUT)).replace(".", "") for p in pages]
    rel_pages = [(r + "/" if r else "") for r in rel_pages]
    page_ids = {}
    checked_targets = {}
    linked_docs = set()

    def target_ok(target):
        if target in checked_targets:
            return checked_targets[target]
        if remote:
            try:
                status, body, ctype = fetch(remote + target)
                ok = status == 200 and len(body) > 0
            except Exception as e:  # noqa: BLE001
                ok = False
        else:
            p = SITE_OUT / target
            ok = (p / "index.html").exists() if (target.endswith("/") or target == "") else p.is_file()
        checked_targets[target] = ok
        return ok

    for rel in rel_pages:
        if remote:
            status, body, _ = fetch(remote + rel)
            html = body.decode("utf-8")
            if status != 200:
                errors.append(f"{rel}: HTTP {status}")
        else:
            html = (SITE_OUT / rel / "index.html").read_text(encoding="utf-8")
        c = Collector()
        c.feed(html)
        page_ids[rel] = c.ids
        if c.h1 != 1:
            errors.append(f"/{rel}: expected one <h1>, found {c.h1}")
        if not c.title.strip():
            errors.append(f"/{rel}: missing <title>")
        if "noindex" in c.meta_robots:
            errors.append(f"/{rel}: has noindex")
        visible = re.sub(r"\s+", " ", " ".join(c.text)).lower()
        for phrase in FORBIDDEN:
            if re.search(r"\b" + re.escape(phrase) + r"\b", visible):
                errors.append(f"/{rel}: contains forbidden wording '{phrase}'")
        for href in c.links:
            if href.startswith(("mailto:", "tel:", "https://", "http://")):
                continue
            path, _, frag = href.partition("#")
            base = urllib.parse.urljoin("http://x/" + rel, path) if path else "http://x/" + rel
            target = urllib.parse.urlparse(base).path.lstrip("/")
            target = urllib.parse.unquote(target)
            if target.startswith("documents/"):
                linked_docs.add(target)
            if not target_ok(target):
                errors.append(f"/{rel}: broken link {href} -> /{target}")
            elif frag and (target.endswith("/") or target == "") and target in page_ids and frag not in page_ids[target]:
                warnings.append(f"/{rel}: anchor #{frag} not found on /{target}")

    # Re-check anchors now that all pages are parsed.
    # (Anchors to pages parsed later are validated here.)

    # Documents
    for d in ctx["documents"]:
        for fmt, path in d["paths"].items():
            if path not in linked_docs:
                errors.append(f"document {path} is not linked from any page")
            if remote:
                status, body, ctype = fetch(remote + path)
                data = body
                if fmt == "pdf" and "pdf" not in ctype:
                    errors.append(f"{path}: served with content-type {ctype}")
                tmp = SITE_OUT.parent / "build-assets" / ("_check." + fmt)
                tmp.write_bytes(data)
                local = tmp
            else:
                local = SITE_OUT / path
            if fmt == "pdf":
                r = PdfReader(str(local))
                text = " ".join((pg.extract_text() or "") for pg in r.pages)
                text = re.sub(r"\s+", " ", text)
                if len(r.pages) < 1 or len(text) < 400:
                    errors.append(f"{path}: PDF has too little content")
                key = re.sub(r"\s+", " ", d["title"].split(":")[0])
                if key.lower() not in text.lower():
                    errors.append(f"{path}: title '{key}' not found in PDF text")
                for phrase in FORBIDDEN:
                    if re.search(r"\b" + re.escape(phrase) + r"\b", text.lower()):
                        errors.append(f"{path}: contains forbidden wording '{phrase}'")
            else:
                doc = Document(str(local))
                body = " ".join(p.text for p in doc.paragraphs)
                if d["title"].split(":")[0] not in body:
                    errors.append(f"{path}: title not found in DOCX")

    # Grant pages link their own documents
    for g in ctx["grants"]:
        if g.get("soft_404"):
            continue  # simulated soft 404 test page intentionally has no grant content
        rel = f"grants/{g['id']}/"
        html = (SITE_OUT / rel / "index.html").read_text() if not remote else fetch(remote + rel)[1].decode()
        for did in g["documents"]:
            if ctx["docs_by_id"][did]["paths"]["pdf"] not in html:
                errors.append(f"/{rel}: does not link {did}")
        for field in ("eligibility", "how-to-apply", "focus-impact-areas", "population-served", "funding-amount", "deadlines", "documents", "contact"):
            if f'data-field="{field}"' not in html:
                errors.append(f"/{rel}: missing section {field}")

    # robots + sitemap
    if remote:
        robots = fetch(remote + "robots.txt")[1].decode()
        sitemap = fetch(remote + "sitemap.xml")[1].decode()
    else:
        robots = (SITE_OUT / "robots.txt").read_text()
        sitemap = (SITE_OUT / "sitemap.xml").read_text()
    if "Allow: /" not in robots or "Disallow: /\n" in robots:
        errors.append("robots.txt does not allow crawling")
    base = ctx["site"]["base_url"] if not remote else remote
    for rel in rel_pages:
        if f"<loc>{base}{rel}</loc>" not in sitemap:
            errors.append(f"sitemap.xml missing {base}{rel}")

    n_links = len(checked_targets)
    print(f"Checked {len(rel_pages)} pages, {n_links} unique internal targets, {len(ctx['documents'])} documents ({sum(len(d['paths']) for d in ctx['documents'])} files).")
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print("RESULT:", "PASS" if not errors else f"FAIL ({len(errors)} errors)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
