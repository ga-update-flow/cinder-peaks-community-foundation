"""Generate every downloadable document.

1. Each document in data/documents.json is written as a branded Word file
   (documents-src/<category>/<filename>.docx) by the generator for its "kind".
   Grant-specific documents pull their content from data/grants/<id>.json.
2. LibreOffice converts each .docx to PDF.
3. PDFs (and .docx files for fillable templates) are copied into site/documents/.

Usage: python3 scripts/build_docs.py [document-id ...]
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from common import DOC_SRC, ROOT, SITE_OUT, fmt_date, key_dates, load_all, money
from docx_kit import BOX, BrandedDoc, CINDER, STONE

ASSETS = ROOT / "build-assets"


def page_url(ctx, path):
    return ctx["site"]["base_url"].rstrip("/") + "/" + path.lstrip("/")


def grant_url(ctx, g):
    return page_url(ctx, f"grants/{g['id']}/")


def doc_url(ctx, doc_id):
    d = ctx["docs_by_id"][doc_id]
    return page_url(ctx, d["paths"]["pdf"])


# ---------------------------------------------------------------- guidelines

def gen_guidelines(ctx, doc):
    g = ctx["grants_by_id"][doc["grant"]]
    focus = ctx["focus_by_id"]
    year_sub = f"{g['program_type']}  ·  {g['status']}"
    b = BrandedDoc(ctx, doc["title"], "Grant Guidelines" if "Guidelines" in doc["title"] else "Request for Proposals", year_sub)

    b.callout("At a glance", [
        f"Funding: {g['funding']['summary']}",
        f"Type of support: {g['funding']['type']}",
        *( [f"Term: {g['funding']['term']}"] if g['funding'].get('term') else [] ),
        *( [f"Total available: {g['funding']['total_available']}"] if g['funding'].get('total_available') else [] ),
        f"Geographic eligibility: {g['geography']['summary']}",
        f"Program page: {grant_url(ctx, g)}",
    ])

    b.h1("About the program")
    for p in g["description"]:
        b.para(p)

    b.h1("Focus and impact areas")
    b.para("Focus areas: " + ", ".join(focus[f]["title"] for f in g["focus_areas"]) + ".")
    b.para("We welcome proposals that address one or more of the following impact areas:")
    b.bullets(g["impact_areas"])

    b.h2("Populations served")
    b.bullets(g["populations_served"])

    b.h1("Eligibility")
    b.h2("Geographic eligibility")
    b.para(g["geography"]["summary"])
    b.h2("Who may apply")
    b.bullets(g["eligibility"])
    if g.get("not_eligible"):
        b.h2("What we do not fund")
        b.bullets(g["not_eligible"])

    b.h1("Funding")
    b.para(f"{g['funding']['summary']}. {g['funding']['type']}.")
    if g["funding"].get("tiers"):
        b.para("Award amounts are based on the applicant's most recent board-approved annual operating budget:")
        b.table([(t["budget"], t["award"]) for t in g["funding"]["tiers"]], header=["Annual operating budget", "Grant award"], widths=(3.4, 2.4))

    b.h1("Key dates")
    b.table(key_dates(g), header=["Milestone", "Date"], widths=(2.4, 4.3), label_col=True)

    b.h1("How to apply")
    b.para(g["how_to_apply"]["intro"])
    b.numbered([(s["title"], s["text"]) for s in g["how_to_apply"]["steps"]])
    if doc.get("extra_questions"):
        b.h2("Application questions")
        b.numbered(doc["extra_questions"])

    if g.get("review_criteria"):
        b.h1("Review criteria")
        b.bullets(g["review_criteria"])

    b.h1("Reporting requirements")
    b.para(g["reporting"]["summary"])
    if g["reporting"].get("items"):
        b.bullets(g["reporting"]["items"])
    if g["reporting"].get("due"):
        b.para(g["reporting"]["due"] + ".", bold_lead="Due: ")

    supporting = [d for d in g["documents"] if d != doc["id"]]
    if supporting:
        b.h1("Templates and supporting documents")
        b.bullets([(ctx["docs_by_id"][d]["title"] + ": ", doc_url(ctx, d)) for d in supporting])

    if g.get("faq"):
        b.h1("Frequently asked questions")
        for f in g["faq"]:
            b.para(f["q"], bold_lead="")
            b.doc.paragraphs[-1].runs[-1].bold = True
            b.para(f["a"])

    b.contact_block(g["contact"])
    return b


# ---------------------------------------------------------------- templates

ORG_FIELDS = ["Organization legal name", "Doing business as (if different)", "Mailing address", "Website",
              "Executive director / CEO", "Primary contact name and title", "Primary contact email and phone",
              "Organization type (501(c)(3), public agency, tribe or tribal program, fiscally sponsored)",
              "Year founded", "Current annual operating budget", "Counties served"]


def gen_application_worksheet(ctx, doc):
    b = BrandedDoc(ctx, doc["title"], "Application Template", "Use this worksheet to draft your Community Impact Grant or Prism Fund application before entering answers in the CPCF Grant Portal.")
    b.hint("Each question below appears exactly as it does in the online application. Word limits are enforced in the portal.")
    b.h1("Section 1. Organization information")
    b.form(ORG_FIELDS)
    b.h2("Grant program and field of interest")
    b.checklist([
        "Community Impact Grants: Spring Cycle (Health & Human Services; Civic & Economic Opportunity)",
        "Community Impact Grants: Fall Cycle (Education & Youth; Arts & Culture; Environment & Land Stewardship; Animal Welfare)",
        "Prism Fund for LGBTQ+ Arizonans",
    ])
    b.h1("Section 2. Organization narrative")
    b.answer_box("2.1  Describe your organization's mission and the community you serve.", 6, "250 words")
    b.answer_box("2.2  What need or opportunity does your work address? Include local data or community input where possible.", 7, "300 words")
    b.answer_box("2.3  Describe your main programs and the results you achieved in the past year.", 7, "300 words")
    b.answer_box("2.4  How do the people most affected by your work help shape your programs, staff, or board?", 6, "200 words")
    b.answer_box("2.5  Describe your most important partnerships with other organizations, agencies, or tribal programs.", 5, "200 words")
    b.answer_box("2.6  How would general operating support from the Foundation strengthen your organization this year?", 6, "200 words")
    b.h1("Section 3. People served")
    b.table([("Children (0–17)", ""), ("Adults (18–64)", ""), ("Older adults (65+)", ""), ("Total unduplicated people served", "")],
            header=["Population", "Number served in the past 12 months"], widths=(3.2, 3.5), label_col=True)
    b.table([("Coconino County", ""), ("Yavapai County", ""), ("Navajo County", ""), ("Apache County", ""), ("Other Arizona counties", "")],
            header=["County", "Percent of people served"], widths=(3.2, 3.5), label_col=True)
    b.h1("Section 4. Financial information")
    b.table([("Total revenue", "", ""), ("Total expenses", "", ""), ("Net assets at year end", ""," "), ("Months of operating cash on hand", "", "")],
            header=["", "Last completed fiscal year", "Current fiscal year (budget)"], widths=(2.6, 2.05, 2.05), label_col=True)
    b.answer_box("4.1  Describe any significant changes in your revenue or expenses over the past two years.", 4, "150 words")
    b.h1("Section 5. Required attachments")
    b.checklist(["Current fiscal year operating budget, approved by the board",
                 "Most recent financial statements (audit, review, or board-approved statements)",
                 "List of current board members and their affiliations",
                 "Fiscal Sponsor Letter (fiscally sponsored applicants only)"])
    b.h1("Section 6. Certification")
    b.para("By submitting this application, I certify that the information is accurate, that the organization does not discriminate in hiring or services, and that the board of directors has authorized this request.")
    b.signature_block(["Name and title", "Signature", "Date"])
    return b


def gen_loi_template(ctx, doc):
    b = BrandedDoc(ctx, doc["title"], "Application Template", "For the First Steps Infant & Toddler Fund, Plateau Indigenous Communities Fund, and Stronger Nonprofits Capacity Grants.")
    users = [ctx["grants_by_id"][g] for g in doc["grants"]]
    b.hint("Your letter of inquiry may not exceed two pages, not including the cover information. Save the completed letter as a PDF and email it to the address listed for your program by the LOI deadline.")
    rows = []
    for g in users:
        email = "learning@cinderpeakscf.org" if g["id"] == "stronger-nonprofits-capacity-grants" else "grants@cinderpeakscf.org"
        rows.append((g["title"], fmt_date(g["dates"]["loi_deadline"]) + ", " + g["dates"]["deadline_time"], email))
    b.table(rows, header=["Program", "LOI deadline", "Submit to"], widths=(2.8, 2.2, 1.9))
    b.h1("Cover information")
    b.form(["Program you are applying to", "Organization legal name", "Contact name, title, email, and phone",
            "Amount requested", "Grant term requested (months)", "Project title", "Counties or tribal communities served"])
    b.h1("Letter of inquiry")
    b.h2("1. About your organization")
    b.hint("Briefly describe your mission, history, and the community you serve. (About 150 words.)")
    b.answer_box("Response", 5)
    b.h2("2. The need")
    b.hint("What problem or opportunity will this work address? Why is it important now? (About 150 words.)")
    b.answer_box("Response", 5)
    b.h2("3. The proposed work")
    b.hint("What will you do, who will benefit, and who will lead the work? (About 250 words.)")
    b.answer_box("Response", 7)
    b.h2("4. Expected results")
    b.hint("What will be different at the end of the grant? How will you know? (About 100 words.)")
    b.answer_box("Response", 4)
    b.h2("5. Budget summary")
    b.hint("Total project budget, amount requested, and other confirmed or pending sources of support.")
    b.table([("Total project budget", ""), ("Amount requested from CPCF", ""), ("Other confirmed funding", ""), ("Other pending funding", "")],
            widths=(3.2, 3.5), label_col=True)
    b.para("Plateau Indigenous Communities Fund applicants may call (928) 555-0147 ext. 121 to schedule an oral letter of inquiry instead of using this template.", italic=True, size=9.5, color=STONE)
    return b


def gen_budget_template(ctx, doc):
    b = BrandedDoc(ctx, doc["title"], "Application Template", "Required for project and program grant proposals. Add rows as needed.")
    b.h1("Project information")
    b.form(["Organization name", "Project title", "Grant program", "Grant period (start and end dates)", "Amount requested"])
    b.h1("Project income")
    rows = [(s, "", "") for s in ["Cinder Peaks Community Foundation (this request)", "Other foundation grants", "Government grants or contracts",
                                  "Tribal government support", "Individual contributions", "Earned income and fees", "In-kind contributions"]]
    rows.append(("Total project income", "", ""))
    b.table(rows, header=["Source", "Amount", "Confirmed or pending"], widths=(3.3, 1.6, 1.8), total_row=True)
    b.h1("Project expenses")
    rows = [(s, "", "", "") for s in ["Salaries and wages", "Payroll taxes and benefits", "Contract services and consultants",
                                      "Supplies and materials", "Equipment (under $5,000 per item)", "Travel and mileage",
                                      "Rent and utilities", "Training and professional development", "Participant support (stipends, meals, child care)",
                                      "Indirect costs (up to 15%)"]]
    rows.append(("Total project expenses", "", "", ""))
    b.table(rows, header=["Expense category", "Total project", "CPCF request", "Other sources"], widths=(2.9, 1.3, 1.25, 1.25), total_row=True)
    b.h1("Budget narrative")
    b.hint("Explain each line of the CPCF request, how amounts were calculated, and how the project will be sustained after the grant ends.")
    b.answer_box("Budget narrative", 8, "300 words")
    return b


def gen_eligibility_checklist(ctx, doc):
    b = BrandedDoc(ctx, doc["title"], "Applicant Checklist", "Confirm each item before you begin an application. If you cannot check every box, contact the program officer before applying.")
    b.h1("All competitive programs")
    b.checklist([
        "Our organization is a 501(c)(3) nonprofit, a public or governmental agency, a federally recognized tribe or tribal program, or a project with a qualified fiscal sponsor.",
        "Our organization does not discriminate in hiring, board membership, or delivery of services.",
        "The request is not for individuals, scholarships, religious activities, lobbying, endowments, or fundraising events.",
        "We have read the current guidelines or RFP for the program.",
        "We can submit by 6:00 p.m. MST (Arizona time) on the deadline date.",
    ])
    b.h1("Community Impact Grants (Spring and Fall)")
    b.checklist([
        "We are located in or primarily serve residents of Coconino, Yavapai, Navajo, or Apache counties.",
        "We have operated for at least two years and have a board-approved annual budget.",
        "We did not receive a Community Impact Grant in calendar year 2026.",
        "We are submitting only one Community Impact application this calendar year.",
        "Our work fits a field of interest funded in this cycle.",
    ])
    b.h1("Funds with statewide eligibility")
    b.checklist([
        "Prism Fund: our organization serves LGBTQ+ Arizonans and has a nondiscrimination policy that includes sexual orientation and gender identity.",
        "Rising Roots Fund: our organization or project is Black-led, or we have a documented partnership with a Black-led organization.",
        "Plateau Indigenous Communities Fund: our organization is a tribe, tribal program, Native-led organization, or a documented partner of one.",
    ])
    b.h1("Award tiers for Community Impact Grants")
    g = ctx["grants_by_id"]["community-impact-grants-spring"]
    b.table([(t["budget"], t["award"]) for t in g["funding"]["tiers"]], header=["Annual operating budget", "Grant award"], widths=(3.4, 2.4))
    b.contact_block({"name": "Theo Lindqvist", "title": "Grants Manager", "email": "tlindqvist@cinderpeakscf.org", "phone": "(928) 555-0147 ext. 119"})
    return b


def gen_fiscal_sponsor_letter(ctx, doc):
    b = BrandedDoc(ctx, doc["title"], "Application Template", "Print on the fiscal sponsor's letterhead, complete the bracketed fields, and upload with your application.")
    b.para("[Date]")
    b.para("Grants & Community Impact\nCinder Peaks Community Foundation\nP.O. Box 30419\nFlagstaff, AZ 86003-0419")
    b.para("Re: Fiscal sponsorship of [Project name]")
    b.para("To the Grants Committee:")
    b.para("[Fiscal sponsor legal name], a 501(c)(3) organization (EIN [number]), confirms that it serves as fiscal sponsor for [Project name] under a written agreement dated [date]. The agreement remains in effect through at least [date].")
    b.para("As fiscal sponsor, we will receive and administer any grant awarded by Cinder Peaks Community Foundation for [Project name], maintain records of grant expenditures, ensure that funds are used for the purposes described in the application, and submit any required reports with the project's leadership.")
    b.para("Our administrative fee for this project is [percent] percent. The project's annual operating budget, excluding the sponsor's budget, is [amount].")
    b.para("Please contact me with any questions.")
    b.para("Sincerely,")
    b.signature_block(["Name", "Title", "Signature", "Email and phone"])
    b.h2("Checklist for fiscally sponsored applicants")
    b.checklist(["The sponsor's IRS determination letter is attached.", "The written fiscal sponsorship agreement is available on request.",
                 "The award tier is based on the project's budget, not the sponsor's."])
    return b


def gen_capacity_assessment(ctx, doc):
    b = BrandedDoc(ctx, doc["title"], "Application Template", "Complete with your board chair and attach to your Stronger Nonprofits Capacity Grants letter of inquiry.")
    b.hint("Rate each statement from 1 (not yet in place) to 4 (fully in place). There are no right answers. The assessment helps us understand where a capacity grant would make the biggest difference.")
    areas = {
        "Mission and planning": ["Our mission statement is current and guides decisions.", "We have a written strategic plan updated within the last three years.", "Staff and board share clear annual goals."],
        "Board governance": ["The board meets at least quarterly with a quorum.", "Board members understand their legal and fiduciary duties.", "We have conflict of interest, whistleblower, and document retention policies."],
        "Financial management": ["Monthly financial statements are reviewed by the board treasurer or finance committee.", "We have at least three months of operating reserves.", "Internal controls separate approval and payment of expenses."],
        "Fund development": ["We have a written annual fundraising plan.", "No single funding source provides more than 40% of revenue.", "We track donors and gifts in a database."],
        "Technology and data": ["Staff have the hardware and software they need.", "We back up data and protect it with multifactor authentication.", "We use data to measure program results."],
        "Leadership and staffing": ["Key roles have written job descriptions.", "We have an emergency succession plan for the executive director.", "Staff receive regular professional development."],
    }
    for area, items in areas.items():
        b.h2(area)
        b.table([(s, "1   2   3   4") for s in items], header=["Statement", "Rating (circle one)"], widths=(5.0, 1.7))
    b.h1("Reflection")
    b.answer_box("Which area would most benefit from a capacity-building project, and why?", 5, "200 words")
    b.signature_block(["Executive director name and signature", "Board chair name and signature", "Date"])
    return b


def gen_rapid_request(ctx, doc):
    g = ctx["grants_by_id"]["rapid-response-resilience-fund"]
    b = BrandedDoc(ctx, doc["title"], "Application Form", g["title"])
    b.hint(f"Call {g['contact']['name']} at {g['contact']['phone']} before submitting. Email the completed form to grants@cinderpeakscf.org with the subject line \"Rapid Response – [Organization Name]\".")
    b.h1("Organization")
    b.form(["Organization legal name", "Organization type", "Contact name and title", "Email and phone", "Fiscal sponsor (if applicable)"])
    b.h1("The emergency")
    b.checklist(["Wildfire", "Flooding or post-fire debris flow", "Severe winter storm", "Extreme heat", "Other emergency or preparedness project"])
    b.form(["Date the emergency began", "Communities and counties affected", "Is there a declared emergency? (local, tribal, state, or federal)"])
    b.answer_box("Describe the emergency and the immediate needs of the people you serve.", 5, "200 words")
    b.answer_box("How will you use the grant, and how quickly will you spend it?", 5, "200 words")
    b.answer_box("Which emergency management, tribal, or relief agencies are you coordinating with?", 3, "100 words")
    b.h1("Budget")
    b.table([(s, "") for s in ["Food, water, and supplies", "Temporary shelter or lodging", "Transportation and fuel", "Staff or volunteer costs", "Equipment and cleanup", "Other (describe)", "Total request (up to $10,000)"]],
            header=["Use of funds", "Amount"], widths=(4.4, 2.3), total_row=True)
    b.h1("Payment")
    b.form(["Payee name", "Payment method (direct deposit or check)", "Authorized signer and date"])
    return b


def gen_catalog_profile(ctx, doc):
    g = ctx["grants_by_id"]["shared-giving-catalog"]
    b = BrandedDoc(ctx, doc["title"], "Application Form", f"Profiles due {fmt_date(g['dates']['application_deadline'], weekday=True)}, {g['dates']['deadline_time']}")
    b.h1("Organization profile")
    b.form(["Organization name", "Website", "Contact name, email, and phone", "Counties served", "Annual operating budget", "Primary field of interest"])
    b.answer_box("Organizational summary for fundholders", 6, "150 words")
    b.h1("Funding need")
    b.hint("Describe one specific need between $1,000 and $15,000. Needs that are concrete and easy to picture, such as a van for meal delivery or a season of youth art classes, are most often funded.")
    b.form(["Name of funding need", "Amount needed"])
    b.answer_box("What will the gift make possible?", 5, "120 words")
    b.answer_box("What would a gift of $1,000 accomplish?", 3, "50 words")
    b.h1("Photo")
    b.checklist(["One high-resolution photo (at least 1,600 pixels wide) is attached.", "We have permission from everyone pictured.", "Photo credit to use:"])
    b.h1("Acknowledgment")
    b.para("Organizations listed in the catalog agree to send a thank-you acknowledgment to the Foundation within 30 days of receiving a fundholder grant.")
    b.signature_block(["Name and title", "Signature", "Date"])
    return b


# ---------------------------------------------------------------- reporting

def gen_story_report(ctx, doc):
    users = ", ".join(ctx["grants_by_id"][g]["title"] for g in doc["grants"])
    b = BrandedDoc(ctx, doc["title"], "Grant Reporting Form", f"For grantees of: {users}")
    b.hint("Submit this report in the CPCF Grant Portal, or email it to grants@cinderpeakscf.org, by the due date in your award letter.")
    rows = []
    for gid in doc["grants"]:
        g = ctx["grants_by_id"][gid]
        rows.append((g["title"], g["reporting"]["due"]))
    b.table(rows, header=["Program", "Report due"], widths=(4.0, 2.7))
    b.h1("Grant information")
    b.form(["Organization name", "Grant program and year", "Grant amount", "Report prepared by (name, title, email)"])
    b.h1("Your story")
    b.hint("Tell us one story that shows what this grant made possible. You may write a narrative, submit up to five photos with captions, or share a short video link.")
    b.answer_box("Your story", 10, "300–500 words")
    b.h1("People served")
    b.form(["Total people served during the grant year", "Counties or communities served"])
    b.h1("Permission to share")
    b.checklist(["CPCF may share this story, photos, and our organization's name publicly.",
                 "CPCF may share this story without identifying individuals.",
                 "Please do not share this story publicly."])
    b.signature_block(["Name and title", "Date"])
    return b


def gen_interim_report(ctx, doc):
    b = BrandedDoc(ctx, doc["title"], "Grant Reporting Form", "For First Steps Infant & Toddler Fund and Stronger Nonprofits Capacity Grants grantees")
    rows = [(ctx["grants_by_id"][g]["title"], ctx["grants_by_id"][g]["reporting"]["due"]) for g in doc["grants"]]
    b.table(rows, header=["Program", "Reporting schedule"], widths=(3.0, 3.7))
    b.h1("Grant information")
    b.form(["Organization name", "Grant number", "Grant period", "Report period covered", "Prepared by (name, title, email)"])
    b.h1("Progress")
    b.table([("", "", "") for _ in range(4)], header=["Goal or milestone from proposal", "Progress to date", "On track? (Yes / Partly / No)"], widths=(2.6, 2.6, 1.5))
    b.answer_box("Describe your most important accomplishments so far.", 5, "250 words")
    b.answer_box("What challenges have you encountered, and how are you addressing them?", 5, "200 words")
    b.answer_box("Do you anticipate any changes to the timeline, budget, or outcomes?", 3, "150 words")
    b.h1("Expenses to date")
    b.table([("CPCF grant amount", ""), ("Grant funds spent to date", ""), ("Grant funds remaining", "")], widths=(3.2, 3.5), label_col=True)
    b.signature_block(["Name and title", "Date"])
    return b


def gen_final_report(ctx, doc):
    b = BrandedDoc(ctx, doc["title"], "Grant Reporting Form", "For project and program grants")
    rows = [(ctx["grants_by_id"][g]["title"], ctx["grants_by_id"][g]["reporting"]["due"]) for g in doc["grants"]]
    b.table(rows, header=["Program", "Reporting schedule"], widths=(3.0, 3.7))
    b.para("Plateau Indigenous Communities Fund grantees may submit this report in writing, as an audio or video recording, or in a conversation with the program officer.", italic=True, size=9.5, color=STONE)
    b.h1("Grant information")
    b.form(["Organization name", "Grant number", "Grant program", "Grant amount", "Grant period", "Prepared by (name, title, email)"])
    b.h1("Results")
    b.table([("", "", "") for _ in range(5)], header=["Outcome from proposal", "Result achieved", "How measured"], widths=(2.4, 2.4, 1.9))
    b.answer_box("Summarize what the grant accomplished.", 6, "300 words")
    b.answer_box("Who participated or benefited? Include numbers by county or community where possible.", 4, "150 words")
    b.answer_box("What did you learn, and what would you do differently?", 5, "200 words")
    b.answer_box("How will the work continue after the grant ends?", 4, "150 words")
    b.h1("Financial report")
    b.table([(s, "", "", "") for s in ["Personnel", "Contract services", "Supplies and materials", "Travel", "Participant support", "Other", "Total"]],
            header=["Expense category", "Approved budget", "Actual spent", "Variance explanation"], widths=(2.0, 1.4, 1.4, 1.9), total_row=True)
    b.h1("Permission to share")
    b.checklist(["CPCF may share this report, photos, and our organization's name publicly.", "Please contact us before sharing any part of this report."])
    b.signature_block(["Executive director name and signature", "Date"])
    return b


def gen_rapid_report(ctx, doc):
    b = BrandedDoc(ctx, doc["title"], "Grant Reporting Form", "High Country Rapid Response & Resilience Fund · Due within 60 days after funds are spent")
    b.form(["Organization name", "Grant amount and date received", "Emergency or project name", "Prepared by (name, email)"])
    b.answer_box("How were the funds used?", 5, "150 words")
    b.form(["Number of people or households helped", "Communities served"])
    b.table([(s, "") for s in ["Food, water, and supplies", "Shelter or lodging", "Transportation and fuel", "Staff or volunteer costs", "Equipment and cleanup", "Other", "Total spent"]],
            header=["Use of funds", "Amount spent"], widths=(4.4, 2.3), total_row=True)
    b.answer_box("What needs remain in the community?", 3, "100 words")
    b.checklist(["Photos are attached and CPCF may share them publicly."])
    return b


# ---------------------------------------------------------------- reports

def gen_annual_report(ctx, doc):
    site = ctx["site"]
    b = BrandedDoc(ctx, doc["title"], "Annual Report", "January 1 – December 31, 2025")
    b.h1("A letter from our President and Board Chair")
    b.para("Dear friends,")
    b.para("In 2025, the people of northern Arizona showed again what generosity looks like at elevation. When post-fire floods reached homes in the Timberline area, neighbors arrived with shovels before the water had receded. When federal funding for rural child care faltered, 61 new donors joined the First Steps Infant & Toddler Fund. And when our Plateau Indigenous Communities Fund advisory council asked for more resources for language revitalization, donors answered with the largest single year of gifts in the fund's history.")
    b.para("Across all of our funds, the Foundation granted $7.85 million in 2025 to more than 600 nonprofits, schools, and tribal programs. Our assets grew to $168.4 million, and 22 families and businesses opened new charitable funds. Behind every number in this report is a person who chose to invest in this place for the long term.")
    b.para("Thank you for being part of that choice.")
    b.para("Renata Holloway, President & CEO\nGloria Atcitty, Chair, Board of Directors")
    b.h1("2025 at a glance")
    b.table([("Total grants paid", "$7,846,000"), ("Organizations receiving grants", "614"), ("Competitive grants awarded", "$1,986,000"),
             ("Donor-advised fund grants", "$4,912,000"), ("Designated and agency fund grants", "$948,000"), ("New charitable funds established", "22"),
             ("Total charitable funds", "310"), ("Total assets (December 31, 2025)", "$168.4 million")],
            header=["Measure", "2025"], widths=(4.0, 2.7), label_col=True)
    b.h1("Grantmaking by focus area")
    b.image(ASSETS / "chart-focus-2025.png", 6.4)
    b.para("Grants from all fund types, including donor-advised funds, classified by the primary focus area of the recipient organization.", italic=True, size=9, color=STONE)
    b.h1("Highlights")
    b.bullets([
        ("Community Impact Grants: ", "$1.21 million in unrestricted support to 97 organizations across the Spring and Fall cycles."),
        ("First Steps Infant & Toddler Fund: ", "$455,000 to 14 programs, adding 86 licensed infant and toddler care slots in the region."),
        ("Plateau Indigenous Communities Fund: ", "$221,000 to 29 tribal programs and Native-led organizations, including nine language programs."),
        ("Rapid Response & Resilience: ", "$208,000 to 23 organizations responding to wildfire, flooding, and a January blizzard on the Navajo Nation."),
        ("Nonprofit Learning Hub: ", "412 nonprofit staff and board members attended 38 workshops and cohort sessions."),
    ])
    b.h1("Financial summary")
    b.table([("Contributions received", "$14,200,000"), ("Investment return, net", "$16,800,000"), ("Other income", "$300,000"),
             ("Total revenue", "$31,300,000")], header=["Revenue", "2025"], widths=(4.0, 2.7), total_row=True)
    b.table([("Grants paid", "$7,846,000"), ("Community programs and Learning Hub", "$1,120,000"), ("Management and general", "$940,000"),
             ("Fundraising and donor services", "$610,000"), ("Total expenses", "$10,516,000")], header=["Expenses", "2025"], widths=(4.0, 2.7), total_row=True)
    b.para("Complete figures appear in the Financial Summary, Fiscal Year 2025, available at " + doc_url(ctx, "financial-summary-fy2025"), size=9.5)
    b.h1("Board of directors")
    b.table([(m["name"], m["role"], m["city"]) for m in site["board"]], header=["Name", "Role", "Community"], widths=(2.6, 1.8, 2.3))
    b.h1("Staff")
    b.table([(s["name"], s["title"]) for s in site["staff"]], header=["Name", "Title"], widths=(2.6, 4.1))
    return b


def gen_impact_report(ctx, doc):
    b = BrandedDoc(ctx, doc["title"], "Community Impact Report", "Stories and results from grants made in 2025")
    b.para("Every grant the Foundation makes is an investment in a person, a place, or an idea. This report shares what our grantees accomplished in 2025, in their words and in numbers. All organizations named in this report are fictional and are used for demonstration purposes.", italic=True)
    b.h1("Where our grants went")
    b.image(ASSETS / "chart-county-2025.png", 6.2)
    b.table([("Coconino County", "$3,620,000", "268"), ("Yavapai County", "$2,310,000", "187"), ("Navajo County", "$1,040,000", "86"),
             ("Apache County", "$660,000", "52"), ("Statewide and other Arizona", "$216,000", "21"), ("Total", "$7,846,000", "614")],
            header=["County served", "Grants", "Organizations"], widths=(3.0, 2.0, 1.7), total_row=True)
    stories = [
        ("Health & Human Services", "Juniper Path Recovery House, Prescott", "A $15,000 Community Impact Grant helped Juniper Path keep its doors open while a state contract was delayed. Forty-one women completed residential recovery programs during the grant year, and 33 moved into stable housing."),
        ("Civic & Economic Opportunity", "High Country Worker Center, Flagstaff", "Seasonal workers at Grand Canyon lodges used the center's mobile benefits clinic to file 380 tax returns and claim $412,000 in refunds and credits."),
        ("Education & Youth", "Red Mesa Reading Circle, Teec Nos Pos", "Volunteer elders read with 120 children each week in Diné bizaad and English. Participating second-graders gained an average of 1.4 grade levels in reading."),
        ("Environment & Land Stewardship", "Upper Verde Springs Alliance, Chino Valley", "Volunteers restored fencing and native plantings at nine springs, and monitoring shows flow has returned to two springs that were dry in 2022."),
        ("Arts & Culture", "Little Colorado Youth Orchestra, Winslow", "Seventy-two students received free instruments and weekly lessons, and the orchestra performed at the Navajo County Fair for the first time."),
        ("Animal Welfare", "Mogollon Rim Paws Alliance, Show Low", "Mobile clinics provided 1,640 low-cost spay and neuter surgeries in rural Navajo and Apache county communities."),
        ("Early Childhood", "Painted Desert Family Resource Center, Holbrook", "A First Steps grant funded licensing support for six home-based infant care providers, adding 28 infant slots in a county with fewer than one slot per seven infants."),
        ("Indigenous Communities", "Third Mesa Seed Keepers, Kykotsmovi", "Youth and elders planted and harvested 11 heritage crop varieties and distributed seed to 140 families."),
        ("LGBTQ+ Communities", "Rimrock Pride Center, Sedona", "Peer support groups for LGBTQ+ older adults grew to 85 regular participants across three Verde Valley towns."),
        ("Black Futures", "Southside Heritage Project, Flagstaff", "The project recorded 24 oral histories with descendants of Black families who came to Flagstaff to work in the lumber mills in the 1940s."),
    ]
    b.h1("Grantee stories")
    for area, org, text in stories:
        b.h2(area)
        b.para(org, bold_lead="")
        b.doc.paragraphs[-1].runs[-1].bold = True
        b.para(text)
    b.h1("What grantees told us")
    b.bullets(["94% said unrestricted funding allowed them to respond to unexpected needs.",
               "88% said the story-based report took less than two hours to complete.",
               "71% of rural grantees said CPCF was their only foundation funder."])
    return b


def gen_awards_summary(ctx, doc):
    b = BrandedDoc(ctx, doc["title"], "Grant Awards Summary", "Competitive grants approved by the Board of Directors in calendar year 2026")
    b.para("This summary lists competitive grants approved in 2026. Donor-advised fund grants are not included. All organizations named are fictional and are used for demonstration purposes.", italic=True, size=9.5, color=STONE)
    b.h1("Summary by program")
    b.table([("Community Impact Grants: Spring 2026", "51", "$652,500"), ("Community Impact Grants: Fall 2026", "46", "$612,500"),
             ("First Steps Infant & Toddler Fund", "12", "$398,000"), ("Plateau Indigenous Communities Fund", "31", "$238,000"),
             ("Prism Fund for LGBTQ+ Arizonans", "11", "$121,000"), ("Rising Roots Black Futures Fund", "13", "$84,500"),
             ("Stronger Nonprofits Capacity Grants", "10", "$156,000"), ("High Country Rapid Response & Resilience Fund", "19", "$131,000"),
             ("Total", "193", "$2,393,500")], header=["Program", "Grants", "Amount"], widths=(4.1, 1.1, 1.5), total_row=True)
    b.h1("Community Impact Grants by award tier")
    b.table([("$5,000 (budget up to $75,000)", "29", "24"), ("$10,000 ($75,001 – $200,000)", "13", "12"),
             ("$15,000 ($200,001 – $750,000)", "6", "7"), ("$25,000 ($750,001 and above)", "3", "3"), ("Total grants", "51", "46")],
            header=["Award tier", "Spring 2026", "Fall 2026"], widths=(3.7, 1.5, 1.5), total_row=True)
    b.h1("First Steps Infant & Toddler Fund")
    b.table([("Painted Desert Family Resource Center", "Navajo", "$40,000"), ("Kinship Circle of the Verde Valley", "Yavapai", "$35,000"),
             ("Canyon Country Early Learning Network", "Coconino", "$38,000"), ("Ganado Young Parents Program", "Apache", "$40,000"),
             ("Mountain Cradle Infant Center", "Coconino", "$32,000"), ("Prescott Teen Parent Partners", "Yavapai", "$30,000"),
             ("White Mountain Home Child Care Alliance", "Navajo", "$36,000"), ("Chinle Grandparents Raising Grandchildren", "Apache", "$25,000"),
             ("Northern Arizona Early Educator Fellowship", "Coconino", "$40,000"), ("Page Family Health Outreach", "Coconino", "$27,000"),
             ("Bright Mesa Doula Collective", "Navajo", "$30,000"), ("Camp Verde Infant Care Cooperative", "Yavapai", "$25,000")],
            header=["Organization", "County", "Award"], widths=(3.9, 1.3, 1.5))
    b.h1("Stronger Nonprofits Capacity Grants")
    b.table([("Upper Verde Springs Alliance", "Financial management system", "$15,000"), ("Little Colorado Youth Orchestra", "Strategic plan", "$12,000"),
             ("Mogollon Rim Paws Alliance", "Donor database and fundraising plan", "$18,000"), ("Third Mesa Seed Keepers", "Board development", "$10,000"),
             ("High Country Worker Center", "Executive succession plan", "$20,000"), ("Red Mesa Reading Circle", "Data and evaluation system", "$14,000"),
             ("Sedona Senior Ride Share", "Technology and cybersecurity", "$16,000"), ("Snowflake Food Pantry Network", "Strategic plan", "$15,000"),
             ("Kaibab Trails Youth Corps", "Fund development plan", "$18,000"), ("Rimrock Pride Center", "Board governance policies", "$18,000")],
            header=["Organization", "Capacity project", "Award"], widths=(2.9, 2.5, 1.3))
    return b


def gen_financial_summary(ctx, doc):
    b = BrandedDoc(ctx, doc["title"], "Financial Report", "Fiscal year ended December 31, 2025")
    b.para("This summary is derived from the Foundation's audited financial statements for the year ended December 31, 2025. The complete audited statements are available on request from the Chief Financial Officer.", italic=True, size=9.5, color=STONE)
    b.h1("Statement of financial position")
    b.table([("Cash and cash equivalents", "$4,100,000"), ("Investments, at fair value", "$160,900,000"), ("Split-interest agreements and other assets", "$2,600,000"),
             ("Property and equipment, net", "$800,000"), ("Total assets", "$168,400,000")], header=["Assets", "December 31, 2025"], widths=(4.2, 2.5), total_row=True)
    b.table([("Grants payable", "$1,900,000"), ("Agency endowment funds held for nonprofits", "$9,600,000"), ("Accounts payable and other liabilities", "$400,000"),
             ("Total liabilities", "$11,900,000")], header=["Liabilities", "December 31, 2025"], widths=(4.2, 2.5), total_row=True)
    b.table([("Without donor restrictions", "$121,300,000"), ("With donor restrictions", "$35,200,000"), ("Total net assets", "$156,500,000")],
            header=["Net assets", "December 31, 2025"], widths=(4.2, 2.5), total_row=True)
    b.h1("Statement of activities")
    b.table([("Contributions", "$14,200,000"), ("Investment return, net", "$16,800,000"), ("Fees and other income", "$300,000"), ("Total revenue", "$31,300,000"),
             ("Grants", "$7,846,000"), ("Program services", "$1,120,000"), ("Management and general", "$940,000"), ("Fundraising", "$610,000"),
             ("Total expenses", "$10,516,000"), ("Change in net assets", "$20,784,000")], header=["", "2025"], widths=(4.2, 2.5), label_col=True)
    b.h1("Funds by type")
    b.table([("Donor-advised funds", "142"), ("Designated funds", "51"), ("Scholarship funds", "44"), ("Field-of-interest funds", "38"),
             ("Agency endowment funds", "29"), ("Unrestricted community funds", "6"), ("Total", "310")], header=["Fund type", "Number of funds"], widths=(4.2, 2.5), total_row=True)
    b.h1("Investment and spending policy")
    b.para("Endowed funds are invested in a diversified long-term pool overseen by the Finance & Investment Committee. The annual spending rate is 4.5 percent of each fund's average market value over the previous 16 quarters, which balances current grantmaking with long-term growth. The Foundation's administrative fee ranges from 0.5 to 1.5 percent depending on fund type and size.")
    b.contact_block({"name": "Corinne Abernathy, CPA", "title": "Chief Financial Officer", "email": "cabernathy@cinderpeakscf.org", "phone": "(928) 555-0147 ext. 105"})
    return b


def gen_research_brief(ctx, doc):
    b = BrandedDoc(ctx, doc["title"], "Research Brief", "Commissioned by the First Steps Infant & Toddler Fund · September 2026")
    b.h1("Key findings")
    b.bullets([
        "Northern Arizona has about 16,900 infants and toddlers under age three and about 3,190 licensed infant and toddler care slots: one slot for every 5.3 children.",
        "Apache County has one licensed slot for every 10.8 infants and toddlers, the steepest shortage in the region.",
        "Infant care costs an average of $13,900 per year in Coconino County, about 19 percent of the county's median household income.",
        "Six in ten parents interviewed had turned down a job, cut work hours, or left school because they could not find infant care.",
        "Early childhood educators in the region earn a median wage of $15.40 per hour, and 38 percent of providers reported an open position they could not fill.",
    ])
    b.h1("Supply and demand by county")
    b.image(ASSETS / "chart-infant-ratio.png", 6.0)
    b.table([("Coconino County", "4,300", "1,120", "3.8"), ("Yavapai County", "6,100", "1,310", "4.7"), ("Navajo County", "3,900", "520", "7.5"),
             ("Apache County", "2,600", "240", "10.8"), ("Four-county region", "16,900", "3,190", "5.3")],
            header=["County", "Children under 3 (est.)", "Licensed infant and toddler slots", "Children per slot"], widths=(2.0, 1.6, 1.8, 1.3), total_row=True)
    b.para("Sources: fictional estimates prepared for this demonstration, modeled on public licensing and census data structures.", italic=True, size=9, color=STONE)
    b.h1("What parents and providers told us")
    b.para("Researchers interviewed 64 parents, grandparents, and child care providers in 11 communities. Three themes emerged:")
    b.bullets([("Distance. ", "Families on the Navajo Nation and in rural Yavapai County described driving more than 40 miles each way to the nearest licensed infant program."),
               ("Cost. ", "Even families who found care often could not afford it without a subsidy, and subsidy waiting lists averaged four months."),
               ("Workforce. ", "Providers described losing trained staff to retail and hospitality jobs that pay more and offer predictable hours.")])
    b.h1("Recommendations")
    b.numbered(["Fund licensing support and start-up grants for home-based infant care in Apache and Navajo counties.",
                "Invest in wage supplements and credential pathways for infant and toddler educators.",
                "Support kin caregivers, who provide most infant care in rural and tribal communities.",
                "Coordinate with tribal child care programs to align licensing, training, and funding."])
    b.para("These recommendations shape the First Steps Infant & Toddler Fund 2027 Request for Proposals: " + doc_url(ctx, "rfp-first-steps-2027"))
    return b


def gen_grants_calendar(ctx, doc):
    b = BrandedDoc(ctx, doc["title"], "Grants Calendar", "Deadlines are 6:00 p.m. Mountain Standard Time (Arizona time) unless noted.")
    events = []
    for g in ctx["grants"]:
        d = g["dates"]
        if d.get("opens"):
            events.append((d["opens"], g["title"], "Application period opens"))
        if d.get("loi_deadline"):
            events.append((d["loi_deadline"], g["title"], "Letter of inquiry deadline"))
        if d.get("invitation_date"):
            events.append((d["invitation_date"], g["title"], "Full application invitations sent"))
        if d.get("application_deadline"):
            events.append((d["application_deadline"], g["title"], "Full application deadline" if d.get("loi_deadline") else "Application deadline"))
    events.sort()
    b.table([(fmt_date(e[0], weekday=True), e[1], e[2]) for e in events], header=["Date", "Program", "Milestone"], widths=(2.1, 2.9, 1.8), font_size=9)
    b.h2("Open year-round")
    rolling = [g for g in ctx["grants"] if g["dates"].get("rolling")]
    b.bullets([(g["title"] + ": ", g["dates"]["rolling"]) for g in rolling])
    b.para("Program details and guidelines: " + page_url(ctx, "grants/"))
    return b


def gen_learning_guide(ctx, doc):
    b = BrandedDoc(ctx, doc["title"], "Nonprofit Learning Hub", "A practical guide from the Cinder Peaks Nonprofit Learning Hub")
    sections = [
        ("1. Start with fit", ["Read the full guidelines or RFP before writing anything. Highlight the funder's priorities, geographic limits, and what it does not fund.",
                               "Call the program officer. A ten-minute conversation can save you twenty hours of writing.",
                               "Check the deadline time zone. Arizona does not observe daylight saving time, so Arizona deadlines are always Mountain Standard Time."]),
        ("2. Describe the need clearly", ["Use one or two local statistics, not ten. County-level data is usually more persuasive than national data.",
                                          "Include the voices of the people you serve, with their permission.",
                                          "Explain why your organization is well positioned to respond."]),
        ("3. Describe your approach", ["Say what you will do, who will do it, when, and for whom.",
                                       "Connect each activity to a result you expect to see.",
                                       "Name your partners and describe what each will contribute."]),
        ("4. Build a realistic budget", ["Every number in the narrative should match the budget.",
                                         "Include the full cost of the work, including staff time and a fair share of overhead.",
                                         "Show other sources of support, confirmed and pending."]),
        ("5. Plan to measure results", ["Choose two or three measures you can realistically track.",
                                        "Collect stories as well as numbers.",
                                        "Report honestly on what did not work. Funders value learning."]),
        ("6. After you submit", ["Send a short thank-you note whether or not the grant is awarded.",
                                 "If you are declined, ask for feedback.",
                                 "Put reporting due dates on your calendar as soon as you receive an award letter."]),
    ]
    for title, tips in sections:
        b.h1(title)
        b.bullets(tips)
    b.h1("Common reasons applications are declined")
    b.table([("The request does not fit the program's priorities", "Re-read the guidelines and call the program officer before applying."),
             ("The budget and narrative do not match", "Have a colleague compare the two documents line by line."),
             ("The applicant is outside the eligible geography", "Check the county list carefully, including where participants live."),
             ("The application is incomplete", "Use the attachment checklist in the application worksheet.")],
            header=["Reason", "How to avoid it"], widths=(3.0, 3.7))
    b.contact_block({"name": "Wren Castellano", "title": "Nonprofit Learning Coordinator", "email": "wcastellano@cinderpeakscf.org", "phone": "(928) 555-0147 ext. 124"})
    return b


def gen_board_checklist(ctx, doc):
    b = BrandedDoc(ctx, doc["title"], "Nonprofit Learning Hub", "Review this checklist with your board each year.")
    groups = {
        "Legal and regulatory": ["File the annual report with the Arizona Corporation Commission by the due date.",
                                 "File IRS Form 990, 990-EZ, or 990-N within five months and fifteen days after the fiscal year ends.",
                                 "Confirm that board members, officers, and the statutory agent are current in state records.",
                                 "Review insurance coverage, including directors and officers liability."],
        "Policies": ["Conflict of interest policy signed annually by each board member.", "Whistleblower policy.", "Document retention and destruction policy.",
                     "Gift acceptance policy.", "Executive compensation reviewed and approved by the board."],
        "Financial oversight": ["Board approves the annual budget before the fiscal year begins.", "Board reviews financial statements at least quarterly.",
                                "Audit, review, or compilation completed as required by funders.", "Operating reserve policy adopted."],
        "Board development": ["Each board member makes a personal contribution.", "New members receive an orientation.",
                              "Board completes a self-assessment.", "Term limits and officer elections followed as stated in the bylaws."],
        "Strategy and leadership": ["Board reviews progress on the strategic plan.", "Board completes the executive director's annual evaluation.",
                                    "Emergency succession plan for the executive director is current."],
    }
    for g, items in groups.items():
        b.h1(g)
        b.checklist(items)
    b.para("Questions? Contact the Nonprofit Learning Hub at learning@cinderpeakscf.org or (928) 555-0147 ext. 124.")
    return b


GENERATORS = {
    "guidelines": gen_guidelines, "application_worksheet": gen_application_worksheet, "loi_template": gen_loi_template,
    "budget_template": gen_budget_template, "eligibility_checklist": gen_eligibility_checklist, "fiscal_sponsor_letter": gen_fiscal_sponsor_letter,
    "capacity_assessment": gen_capacity_assessment, "rapid_request": gen_rapid_request, "catalog_profile": gen_catalog_profile,
    "story_report": gen_story_report, "interim_report": gen_interim_report, "final_report": gen_final_report, "rapid_report": gen_rapid_report,
    "annual_report": gen_annual_report, "impact_report": gen_impact_report, "awards_summary": gen_awards_summary,
    "financial_summary": gen_financial_summary, "research_brief": gen_research_brief, "grants_calendar": gen_grants_calendar,
    "learning_guide": gen_learning_guide, "board_checklist": gen_board_checklist,
}


def convert_to_pdf(docx_paths, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as profile:
        cmd = ["soffice", f"-env:UserInstallation=file://{profile}", "--headless", "--convert-to", "pdf", "--outdir", str(outdir)] + [str(p) for p in docx_paths]
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)


def main(only=None):
    ctx = load_all()
    ctx["logo_png"] = ASSETS / "logo-doc.png"
    targets = [d for d in ctx["documents"] if not only or d["id"] in only]
    by_cat = {}
    for d in targets:
        b = GENERATORS[d["kind"]](ctx, d)
        src = DOC_SRC / d["category"] / f"{d['filename']}.docx"
        b.save(src)
        by_cat.setdefault(d["category"], []).append((d, src))
        print("docx", src.relative_to(ROOT))
    for cat, items in by_cat.items():
        out = SITE_OUT / "documents" / cat
        convert_to_pdf([s for _, s in items], out)
        for d, src in items:
            if "docx" in d["formats"]:
                shutil.copy2(src, out / src.name)
            pdf = out / f"{d['filename']}.pdf"
            if not pdf.exists():
                raise SystemExit(f"PDF conversion failed for {d['id']}")
            print("pdf ", pdf.relative_to(ROOT))


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
