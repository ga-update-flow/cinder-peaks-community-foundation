# Creating future versions

Version 1 is the baseline. Keep it unchanged, both its repository and its public URL,
so later versions can be compared against it.

## Steps

1. **Copy the project** to a new folder. The original stays untouched:
   ```bash
   python3 scripts/new_version.py ../cinder-peaks-community-foundation-v2 2
   cd ../cinder-peaks-community-foundation-v2
   ```
2. **Edit only the fields under test** in `data/grants/<id>.json`, for example:
   - Eligibility: `eligibility`, `not_eligible`, `geography`
   - How to Apply: `how_to_apply.intro`, `how_to_apply.steps`
   - Focus and impact areas: `focus_areas`, `impact_areas`
   - Population served: `populations_served`
   - Funding: `funding.summary`, `funding.min`, `funding.max`, `funding.tiers`
   - LOI date: `dates.loi_deadline` (add, change, or remove the key)
   - Full application date: `dates.application_deadline`
   - Contact: `contact`
   Leave all other files alone so unchanged content stays identical.
3. **Documents.** Guidelines/RFPs and the grants calendar are generated from the grant
   JSON, so they update automatically. To replace a template or add a document:
   - Add an entry to `data/documents.json`, using a **new filename** (for example
     `...-2027-rfp-rev1`), and reference its id in the grant's `documents` list.
   - If a template's content must change, edit its generator in `scripts/build_docs.py`.
   New filenames keep the old document paths valid in earlier versions.
4. **Build and check:**
   ```bash
   ./build.sh https://<user>.github.io/cinder-peaks-community-foundation-v2/
   ```
5. **Publish** the copy to its own repository (for example `cinder-peaks-community-foundation-v2`)
   and its own GitHub Pages URL. Record the changes in a `CHANGES.md` inside that copy.

Grant ids in `data/grants/` act as URL slugs. Keep them the same across versions so each
opportunity's URL matches between versions.
