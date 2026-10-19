#!/usr/bin/env bash
# Full build: brand assets -> documents (DOCX + PDF via LibreOffice) -> HTML -> checks.
# Usage: ./build.sh [BASE_URL]
set -euo pipefail
cd "$(dirname "$0")"
if [ -n "${1:-}" ]; then
  python3 - "$1" <<'PY'
import json, sys
p = "data/site.json"; s = json.load(open(p)); s["base_url"] = sys.argv[1].rstrip("/") + "/"
json.dump(s, open(p, "w"), indent=2, ensure_ascii=False); open(p, "a").write("\n")
PY
fi
python3 scripts/make_assets.py
python3 scripts/build_docs.py
python3 scripts/build_site.py
python3 scripts/check_site.py
