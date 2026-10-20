"""Render the static website into site/.

Every page is written as <path>/index.html so URLs are stable and clean
(e.g. /grants/first-steps-infant-toddler-fund/). All internal links are
relative, so the site works at a domain root or under a sub-path such as a
GitHub Pages project URL.

Usage: python3 scripts/build_site.py [--base-url https://host/path/]
"""
import argparse
import json
import os
import shutil
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from common import ROOT, SITE_OUT, fmt_date, key_dates, load_all, next_deadline, parse_date

TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"


def file_size(path):
    p = SITE_OUT / path
    if not p.exists():
        raise SystemExit(f"Missing document {path}. Run scripts/build_docs.py first.")
    n = p.stat().st_size
    return f"{n/1024:.0f} KB" if n < 1024 * 1024 else f"{n/1024/1024:.1f} MB"


def build_pages(ctx):
    """Return list of (path, template, title, extra_context)."""
    pages = [
        ("", "home.html", None, {}),
        ("about/", "about.html", "About Us", {}),
        ("about/our-people/", "people.html", "Our People", {}),
        ("about/service-area/", "service_area.html", "Our Service Area", {}),
        ("about/news/", "news.html", "News & Stories", {}),
        ("focus-areas/", "focus_index.html", "Focus Areas", {}),
        ("grants/", "grants_index.html", "Grant Opportunities", {}),
        ("grants/how-to-apply/", "how_to_apply.html", "How to Apply", {}),
        ("grants/eligibility-policies/", "eligibility.html", "Eligibility & Grant Policies", {}),
        ("grants/calendar/", "calendar.html", "Grants Calendar", {}),
        ("grants/reporting/", "reporting.html", "Grant Reporting Requirements", {}),
        ("grants/faq/", "faq.html", "Grant Seeker FAQ", {}),
        ("resources/", "resources_index.html", "Resources & Reports", {}),
        ("contact/", "contact.html", "Contact Us", {}),
        ("privacy-policy/", "privacy.html", "Privacy Policy", {}),
        ("terms-of-use/", "terms.html", "Terms of Use", {}),
        ("site-map/", "sitemap_page.html", "Site Map", {}),
    ]
    for a in ctx["focus"]["areas"]:
        pages.append((f"focus-areas/{a['id']}/", "focus_area.html", a["title"], {"area": a}))
    for g in ctx["grants"]:
        pages.append((f"grants/{g['id']}/", "grant.html", g["title"], {"grant": g}))
    for c in ctx["categories"].values():
        pages.append((f"resources/{c['slug']}/", "resource_category.html", c["title"], {"category": c}))
    return pages


def calendar_events(ctx):
    events = []
    for g in ctx["grants"]:
        d = g["dates"]
        for key, label in (("opens", "Application period opens"), ("registration_deadline", "Registration deadline"), ("loi_deadline", "Letter of inquiry deadline"),
                           ("invitation_date", "Full application invitations sent"), ("application_deadline", None)):
            if d.get(key):
                lab = label or d.get("application_deadline_label") or ("Full application deadline" if d.get("loi_deadline") else "Application deadline")
                events.append({"date": d[key], "grant": g, "label": lab, "is_deadline": key in ("registration_deadline", "loi_deadline", "application_deadline")})
    events.sort(key=lambda e: e["date"])
    return events


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url")
    args = ap.parse_args()

    ctx = load_all()
    site = ctx["site"]
    if args.base_url:
        site["base_url"] = args.base_url.rstrip("/") + "/"
    today = parse_date(site["build_date"])

    # Clean previous HTML output but keep generated documents.
    if SITE_OUT.exists():
        for child in SITE_OUT.iterdir():
            if child.name != "documents":
                shutil.rmtree(child) if child.is_dir() else child.unlink()
    SITE_OUT.mkdir(exist_ok=True)
    shutil.copytree(STATIC, SITE_OUT / "assets")

    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html", "xml"]),
                      trim_blocks=True, lstrip_blocks=True)
    env.filters["date"] = fmt_date
    env.filters["initials"] = lambda n: "".join(w[0] for w in n.split(",")[0].split()[::max(1, len(n.split(",")[0].split()) - 1)])
    env.filters["extract"] = lambda key, mapping: mapping[key]
    env.filters["longdate"] = lambda v: fmt_date(v, weekday=True)
    env.globals.update(key_dates=key_dates, next_deadline=next_deadline, file_size=file_size)

    grants_sorted = sorted(ctx["grants"], key=lambda g: (next_deadline(g) or ("", "9999"))[1])
    upcoming = [g for g in grants_sorted if next_deadline(g) and parse_date(next_deadline(g)[1]) >= today]
    rolling = [g for g in ctx["grants"] if g["dates"].get("rolling")]

    pages = build_pages(ctx)
    nav = json.loads((ROOT / "data" / "navigation.json").read_text())
    all_paths = []
    for path, tpl, title, extra in pages:
        depth = path.count("/")
        prefix = "../" * depth

        def url(target, prefix=prefix):
            return (prefix + target) if (prefix + target) else "./"

        def doc_href(doc_id, fmt="pdf", prefix=prefix):
            return prefix + ctx["docs_by_id"][doc_id]["paths"][fmt]

        html = env.get_template(tpl).render(
            **ctx, **extra, nav=nav, page_path=path, page_title=title, url=url, doc_href=doc_href,
            asset=lambda p, prefix=prefix: prefix + "assets/" + p,
            canonical=site["base_url"] + path, upcoming=upcoming, rolling=rolling,
            grants_sorted=grants_sorted, events=calendar_events(ctx), today=today, pages=pages,
        )
        out = SITE_OUT / path / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        all_paths.append(path)

    # 404 page uses absolute-from-base links because it can be served at any depth.
    base_path = "/" + site["base_url"].split("://", 1)[1].split("/", 1)[1] if "://" in site["base_url"] else "/"
    html = env.get_template("404.html").render(
        **ctx, nav=nav, page_path="404", page_title="Page not found", url=lambda t: base_path + t,
        doc_href=lambda d, f="pdf": base_path + ctx["docs_by_id"][d]["paths"][f], asset=lambda p: base_path + "assets/" + p,
        canonical=None, upcoming=upcoming, rolling=rolling, grants_sorted=grants_sorted, today=today, noindex=True)
    (SITE_OUT / "404.html").write_text(html, encoding="utf-8")

    # robots.txt and sitemap.xml
    (SITE_OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {site['base_url']}sitemap.xml\n")
    lastmod = site["build_date"]
    urls = [f"  <url><loc>{site['base_url']}{p}</loc><lastmod>{lastmod}</lastmod></url>" for p in all_paths]
    for d in ctx["documents"]:
        for fmt, p in d["paths"].items():
            urls.append(f"  <url><loc>{site['base_url']}{p}</loc><lastmod>{lastmod}</lastmod></url>")
    (SITE_OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n")
    (SITE_OUT / ".nojekyll").write_text("")
    print(f"Built {len(all_paths)} pages and {sum(len(d['paths']) for d in ctx['documents'])} document files into {SITE_OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
