# Cinder Peaks Community Foundation — demonstration website (Version 1)

A complete static website for a **fictional** community foundation in Flagstaff,
Coconino County, Arizona, built for testing a grant-opportunity link collector
and crawler. The information architecture follows the general pattern of a
U.S. community foundation website (grantseeker pages, cause-based funds,
document library, financials and reports, contact). All names, programs,
people, figures, addresses, phone numbers (555-01xx), and email addresses are invented.

## What's included

| Area | Pages |
|------|-------|
| Home | Mission, stats, focus areas, upcoming deadlines, reports, news |
| About Us | About, Our People, Service Area, News & Stories |
| Focus Areas | Overview + 10 focus area pages |
| Grants | Overview, 9 opportunity pages, How to Apply, Eligibility & Policies, Calendar, Reporting, FAQ |
| Resources & Reports | Document library + 5 category pages |
| Contact | Addresses, phones, emails, program contacts, office closures |
| Other | Privacy Policy, Terms of Use, Site Map, 404, `sitemap.xml`, `robots.txt` |

29 documents (42 files): 9 PDF guidelines and RFPs, 8 application templates and
4 reporting forms (each as Word `.docx` and PDF), 6 reports, and 2 learning resources.

## Project layout

```
data/
  site.json              organization, contact info, staff, board, stats, news
  navigation.json        main menu and dropdowns
  focus_areas.json       focus areas and their linked grant programs
  documents.json         document registry (title, category, filename, formats)
  grants/<id>.json       ONE FILE PER GRANT OPPORTUNITY  <- edit these for new versions
scripts/
  make_assets.py         logo, favicon, social card, report charts
  build_docs.py          writes branded .docx files, converts to PDF with LibreOffice
  build_site.py          renders HTML pages from templates + data
  check_site.py          link, PDF, placeholder-text, sitemap checks (local or --url)
  new_version.py         copies the project to a new folder for the next version
templates/               Jinja2 page templates (layout only, no grant content)
static/                  CSS, JS, images
documents-src/           generated Word sources for every document
site/                    BUILD OUTPUT — the deployable static website
```

## Build

Requires Python 3 with `jinja2`, `python-docx`, `pypdf`, `Pillow`, and LibreOffice (`soffice`).

```bash
./build.sh https://<user>.github.io/<repo>/   # base URL is used for sitemap, canonical links, and URLs inside PDFs
```

Then publish the `site/` folder to any static host.

## Grant opportunity fields

Each `data/grants/<id>.json` holds every field for one opportunity. The page section
for each field has a stable anchor and `data-field` attribute:

| Field | JSON key | Page anchor | `data-field` |
|-------|----------|-------------|--------------|
| Eligibility criteria | `eligibility`, `not_eligible`, `geography` | `#eligibility` | `eligibility`, `geographic-eligibility` |
| How to Apply | `how_to_apply` | `#how-to-apply` | `how-to-apply` |
| Focus and impact areas | `focus_areas`, `impact_areas` | `#focus-impact` | `focus-impact-areas` |
| Population served | `populations_served` | `#populations` | `population-served` |
| Funding amounts | `funding` | `#funding` | `funding-amount` |
| LOI date | `dates.loi_deadline` | `#key-dates` | `deadlines` |
| Full application date | `dates.application_deadline` | `#key-dates` | `deadlines` |
| RFPs and templates | `documents` (ids in `documents.json`) | `#documents` | `documents` |
| Other documents | `documents`, `reporting.forms` | `#documents`, `#reporting` | `documents`, `reporting` |
| Contact | `contact` | `#contact` | `contact` |

Optional fields (for example `dates.loi_deadline`) are simply omitted from the JSON
when they don't apply, and the page and PDF leave them out with no empty rows.

See [VERSIONING.md](VERSIONING.md) for creating Version 2 and later.
