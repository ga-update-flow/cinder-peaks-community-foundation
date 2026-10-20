"""Shared data loading and helpers for the site and document builders.

All opportunity-level content lives in data/grants/<id>.json. Documents are
registered in data/documents.json. Both builders read from here so that a
change to a single field flows to every page and document that uses it.
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE_OUT = ROOT / "site"
DOC_SRC = ROOT / "documents-src"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_date(value):
    return date.fromisoformat(value) if value else None


def fmt_date(value, weekday=False):
    d = parse_date(value) if isinstance(value, str) else value
    if not d:
        return ""
    s = f"{d.strftime('%B')} {d.day}, {d.year}"
    return f"{d.strftime('%A')}, {s}" if weekday else s


def money(n):
    return f"${n:,.0f}"


def doc_paths(doc):
    """Published paths (relative to site root) for each format of a document."""
    folder = f"documents/{doc['category']}"
    return {fmt: f"{folder}/{doc['filename']}.{fmt}" for fmt in doc["formats"]}


def load_all():
    site = load_json(DATA / "site.json")
    focus = load_json(DATA / "focus_areas.json")
    docs_data = load_json(DATA / "documents.json")

    grants = [load_json(p) for p in sorted((DATA / "grants").glob("*.json"))]
    grants.sort(key=lambda g: g["order"])
    grants_by_id = {g["id"]: g for g in grants}

    documents = docs_data["documents"]
    docs_by_id = {d["id"]: d for d in documents}
    categories = {c["id"]: c for c in docs_data["categories"]}

    for d in documents:
        d["paths"] = doc_paths(d)
        d["grants"] = [g["id"] for g in grants if d["id"] in g.get("documents", [])]

    # Validate cross references so a typo never ships as a broken link.
    for g in grants:
        for ref in g.get("documents", []) + g.get("reporting", {}).get("forms", []):
            if ref not in docs_by_id:
                raise SystemExit(f"Grant {g['id']} references unknown document {ref}")
        for fa in g["focus_areas"]:
            if fa not in {a["id"] for a in focus["areas"]}:
                raise SystemExit(f"Grant {g['id']} references unknown focus area {fa}")
    for a in focus["areas"]:
        for gid in a["grants"]:
            if gid not in grants_by_id:
                raise SystemExit(f"Focus area {a['id']} references unknown grant {gid}")

    return {
        "site": site,
        "focus": focus,
        "focus_by_id": {a["id"]: a for a in focus["areas"]},
        "grants": grants,
        "grants_by_id": grants_by_id,
        "documents": documents,
        "docs_by_id": docs_by_id,
        "categories": categories,
    }


def key_dates(grant):
    """Ordered (label, value) pairs for a grant's dates. Absent fields are skipped."""
    d = grant.get("dates", {})
    t = d.get("deadline_time", "")
    rows = []
    if d.get("rolling"):
        rows.append(("Application review", d["rolling"]))
    if d.get("opens"):
        rows.append(("Application period opens", fmt_date(d["opens"], weekday=True)))
    if d.get("registration_deadline"):
        rows.append(("Registration deadline", f"{fmt_date(d['registration_deadline'], weekday=True)}, {t}".rstrip(", ")))
    if d.get("info_session"):
        label, _, val = d["info_session"].partition(": ")
        rows.append((label, val))
    if d.get("loi_deadline"):
        rows.append(("Letter of inquiry deadline", f"{fmt_date(d['loi_deadline'], weekday=True)}, {t}".rstrip(", ")))
    if d.get("invitation_date"):
        rows.append(("Invitations to submit a full application", f"Sent by {fmt_date(d['invitation_date'])}"))
    if d.get("application_deadline"):
        label = d.get("application_deadline_label") or ("Full application deadline" if d.get("loi_deadline") else "Application deadline")
        rows.append((label, f"{fmt_date(d['application_deadline'], weekday=True)}, {t}".rstrip(", ")))
    if d.get("decision"):
        rows.append(("Decision", d["decision"]))
    if d.get("grant_period"):
        rows.append(("Grant period", d["grant_period"]))
    return rows


def next_deadline(grant):
    """(label, ISO date) of the next deadline, LOI first if present."""
    d = grant.get("dates", {})
    if d.get("loi_deadline"):
        return ("LOI due", d["loi_deadline"])
    if d.get("application_deadline"):
        return ("Application due", d["application_deadline"])
    return None
