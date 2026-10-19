"""Create the next site version as a separate copy, leaving this project untouched.

Usage:
  python3 scripts/new_version.py ../cinder-peaks-community-foundation-v2 2

Copies data, scripts, templates, static, documents-src, and docs into the
destination (no git history, no built site/), and sets site_version/version_label
in data/site.json. Then edit only the fields that should change, run ./build.sh,
and publish the copy to its own repository and URL.
"""
import json
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
KEEP = ["data", "scripts", "templates", "static", "documents-src", "build.sh", "README.md", "VERSIONING.md", ".gitignore", ".github"]


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    dest, version = Path(sys.argv[1]).resolve(), sys.argv[2]
    if dest.exists():
        raise SystemExit(f"{dest} already exists; choose a new folder so earlier versions are preserved.")
    dest.mkdir(parents=True)
    for name in KEEP:
        p = SRC / name
        if p.is_dir():
            shutil.copytree(p, dest / name)
        elif p.exists():
            shutil.copy2(p, dest / name)
    site = dest / "data" / "site.json"
    s = json.loads(site.read_text())
    s["site_version"] = f"{version}.0"
    s["version_label"] = f"Version {version}"
    site.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n")
    print(f"Created {dest} as Version {version}. Edit data/grants/*.json, then run ./build.sh <BASE_URL>.")


if __name__ == "__main__":
    main()
