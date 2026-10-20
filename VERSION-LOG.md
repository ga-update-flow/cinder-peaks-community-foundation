# Version Log

## Updated Version — Eligibility Policy Revision

| Item | Detail |
|------|--------|
| Version label | Updated Version — Eligibility Policy Revision |
| Branch | `update-eligibility-policies` |
| Base branch | `main` (commit `a5b0342`) |
| Change summary | Moved “Fundraising events, sponsorships, and advertising” from “What We Do Not Fund” to “Who May Apply.” |
| Pages changed | `grants/eligibility-policies/` |
| Documents changed | None |
| Status | Updated version — pending review |
| Date of change | 2026-10-20 |
| Original production URL | https://hufsa-stack.github.io/cinder-peaks-community-foundation/ |

This is the only intended change in this version. The bullet was relocated, not
duplicated: it now appears once, as the fifth item under “Who May Apply,” and no
longer appears under “What We Do Not Fund.” No other text, documents, layout, or
configuration was changed.

Files changed:

- `templates/eligibility.html`: source template for the page
- `site/grants/eligibility-policies/index.html`: generated page, rebuilt with `scripts/build_site.py`
- `VERSION-LOG.md`: this record

The original `main` branch and the production website must remain unchanged.
Production is served by GitHub Pages from the `gh-pages` branch, which this
update does not modify. Do not merge this branch into `main` or publish it to
`gh-pages` unless that is explicitly approved after review.
