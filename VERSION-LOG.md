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
| Status | Published to production on 2026-10-20 at the repository owner's request (merged into `main` and deployed to `gh-pages`) |
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

Before publishing, the original Version 1 was preserved in two branches:

- `v1-original`: the original `main` source (commit `a5b0342`)
- `gh-pages-v1-original`: the original published website (commit `842841c`)
