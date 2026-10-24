"""Entity registry: every record type the company keeps, defined once.

The server (engine.py) uses it to check, compute, number, scope and store records; the staff app draws lists, forms
and detail pages from it (served at /api/meta); the hosted preview runs the same definitions in the browser.

Field keys:  k key · t type · l label · req required · opts option list (catalog.OPTIONS key or inline) · ref entity ·
             calc formula (expr.py) · ro read-only · hide tag (cost / salary / bank / internal) · unit · help · group ·
             fields (for t="lines") · default · show {field: value} · multi (refs) · child (lists this record under the
             referenced record's page)
"""
from catalog import OPTIONS

TONES = ("gray", "blue", "amber", "green", "red", "violet", "teal")


def F(k, t="text", l=None, **kw):
    return {"k": k, "t": t, "l": l or k.replace("_id", "").replace("_", " ").capitalize(), **kw}


def T(k, l=None, **kw):
    return F(k, "text", l, **kw)


def TA(k, l=None, **kw):
    return F(k, "textarea", l, **kw)


def MD(k, l=None, **kw):
    return F(k, "markdown", l, **kw)


def N(k, l=None, unit=None, **kw):
    return F(k, "number", l, unit=unit, **kw)


def M(k, l=None, **kw):
    return F(k, "money", l, **kw)


def P(k, l=None, **kw):
    return F(k, "percent", l, **kw)


def DT(k, l=None, **kw):
    return F(k, "date", l, **kw)


def DTM(k, l=None, **kw):
    return F(k, "datetime", l, **kw)


def S(k, l=None, opts=None, **kw):
    return F(k, "select", l, opts=opts or k, **kw)


def MS(k, l=None, opts=None, **kw):
    return F(k, "multiselect", l, opts=opts or k, **kw)


def R(k, l=None, ref=None, **kw):
    return F(k, "ref", l, ref=ref, **kw)


def RS(k, l=None, ref=None, **kw):
    return F(k, "refs", l, ref=ref, **kw)


def B(k, l=None, **kw):
    return F(k, "bool", l, **kw)


def PH(k="phone", l="Phone", **kw):
    return F(k, "phone", l, **kw)


def EM(k="email", l="Email", **kw):
    return F(k, "email", l, **kw)


def FILE(k, l=None, **kw):
    return F(k, "file", l, **kw)


def FILES(k, l=None, **kw):
    return F(k, "files", l, **kw)


def GEO(k="gps", l="Location (GPS)", **kw):
    return F(k, "geo", l, **kw)


def L(k, l, fields, **kw):
    return F(k, "lines", l, fields=fields, **kw)


def st(*states):
    """st(("draft", "Draft", "gray"), ...)"""
    return [{"value": v, "label": lab, "tone": tone} for v, lab, tone in states]


PROJECT = lambda **kw: R("project_id", "Project", "projects", child=True, **kw)  # noqa: E731
ACCOUNT = lambda **kw: R("account_id", "Client", "accounts", **kw)  # noqa: E731
GST_LINE = [S("gst_rate", "GST %", "gst_rates", default="18", w=1)]

E = {}


def entity(key, module, label, plural, fields, **kw):
    d = {"key": key, "module": module, "label": label, "plural": plural, "fields": fields, **kw}
    d.setdefault("nav", MODULE_NAV.get(module, "Other"))
    d.setdefault("title", "name" if any(f["k"] == "name" for f in fields) else "code")
    d.setdefault("sort", "-created_at")
    d.setdefault("list", [f["k"] for f in fields if f["t"] not in ("lines", "textarea", "markdown", "files", "file", "json", "geo")][:7])
    E[key] = d
    return d


MODULE_NAV = {"crm": "Sales", "marketing": "Sales", "estimation": "Estimation", "proposals": "Estimation",
              "tenders": "Tenders", "projects": "Projects", "site": "Projects", "quality": "Quality & testing",
              "testing": "Quality & testing", "liaison": "Liaison", "procurement": "Procurement", "stores": "Stores",
              "plant": "Tools & vehicles", "subcon": "Subcontractors & labour", "hse": "Safety",
              "service": "Service & AMC", "finance": "Finance", "hr": "HR & payroll", "documents": "Documents",
              "compliance": "Documents", "cms": "Website", "tasks": "Home", "settings": "Settings", "approvals": "Home"}

DRAFT_APPROVAL = st(("draft", "Draft", "gray"), ("pending_approval", "Waiting for approval", "amber"),
                    ("approved", "Approved", "green"), ("rejected", "Rejected", "red"))

# =========================================================================== settings-level masters
entity("branches", "settings", "Branch", "Branches", [
    T("name", req=True), T("code", "Short code", req=True, help="Used in document numbers, e.g. ERD"), T("city", "Town", req=True),
    TA("address"), PH(), PH("whatsapp", "WhatsApp"), EM(), T("hours", "Opening hours", default="Mon–Sat 9:30 am – 6:30 pm"),
    N("lat", "Latitude"), N("lng", "Longitude"), T("map_url", "Google Maps link"), T("gbp_url", "Google Business Profile link"),
    B("is_head_office", "Head office"), B("active", default=True), N("order", default=10),
], icon="building-2", nav="Settings", title="name", sort="order", list=["name", "code", "city", "phone", "is_head_office", "active"])

# =========================================================================== CRM
entity("accounts", "crm", "Client", "Clients", [
    T("name", "Company / client name", req=True, search=True), S("type", "Type", "account_types", filter=True),
    S("sector", "Sector", "sectors", filter=True), T("gstin", "GSTIN"), T("pan", "PAN"), PH(search=True), EM(search=True),
    T("website"), TA("address"), T("town", filter=True), T("district"), T("pincode", "PIN code"),
    R("owner_id", "Account manager", "users", filter=True), S("source", "Source", "lead_sources"),
    N("credit_days", "Credit days", default=30), M("credit_limit", "Credit limit"),
    L("connections", "Electricity service connections", [T("number", "Service no."), S("supply", "Supply", "supply"),
      T("tariff", "Tariff category"), N("sanctioned_kva", "Sanctioned / contract demand", "kVA"), T("site", "Site")]),
    L("sites", "Sites", [T("name", "Site"), T("address"), T("town")]),
    B("show_logo", "Show logo on website", help="Only with the client's permission"), FILE("logo", "Logo"),
    TA("notes"),
], icon="briefcase", number={"prefix": "AC", "kind": "plain"}, branch=True, search=["name", "phone", "email", "gstin", "code"],
    list=["code", "name", "type", "sector", "town", "owner_id", "phone"],
    portal={"client": "id"})

entity("contacts", "crm", "Contact", "Contacts", [
    T("name", req=True, search=True), R("account_id", "Client", "accounts", child=True, filter=True), T("designation"),
    S("role", "Role", [{"value": v, "label": l} for v, l in (("owner", "Owner / MD"), ("accounts", "Accounts"),
      ("facility", "Facility / maintenance"), ("purchase", "Purchase"), ("project", "Project in-charge"),
      ("consultant", "Consultant / architect"), ("other", "Other"))]),
    PH(search=True), PH("whatsapp", "WhatsApp"), EM(search=True), B("is_primary", "Primary contact"),
    B("consent_marketing", "Agreed to updates"), TA("notes"),
], icon="contact", list=["name", "account_id", "designation", "role", "phone", "email"], branch=False)

LEAD_STATES = st(("new", "New", "blue"), ("contacted", "Contacted", "teal"), ("survey_scheduled", "Survey scheduled", "violet"),
                 ("survey_done", "Survey done", "violet"), ("estimating", "Estimating", "amber"), ("quoted", "Quoted", "amber"),
                 ("negotiation", "Negotiation", "amber"), ("won", "Won", "green"), ("lost", "Lost", "red"),
                 ("on_hold", "On hold", "gray"))
entity("leads", "crm", "Lead", "Leads", [
    T("name", "Name", req=True, search=True, group="Contact"), PH(req=True, search=True, group="Contact"), EM(search=True, group="Contact"),
    T("company", search=True, group="Contact"), T("designation", group="Contact"),
    S("service", "Service", "services", filter=True, group="Requirement"), S("supply", "Supply", "supply", filter=True, group="Requirement"),
    N("load_kva", "Load", "kVA", group="Requirement"), S("site_type", "Site type", "sectors", group="Requirement"),
    T("town", filter=True, group="Requirement"), T("district", group="Requirement"), S("timeline", "Timeline", "timeline", group="Requirement"),
    TA("message", "Message / requirement", group="Requirement"), FILES("attachments", "Drawings, load list, bills or photos", group="Requirement"),
    S("stage", "Stage", "lead_stages", default="new", filter=True, group="Pipeline"),
    R("owner_id", "Owner", "users", filter=True, group="Pipeline"), M("value", "Expected value", group="Pipeline"),
    P("probability", "Probability", ro=True, group="Pipeline"), N("score", "Lead score", ro=True, group="Pipeline", help="0–100 from load, LT/HT, timeline, source and engagement"),
    DTM("next_follow_up", "Next follow-up", group="Pipeline"), DTM("response_due_at", "Respond by", ro=True, group="Pipeline"),
    DTM("first_response_at", "First response", ro=True, group="Pipeline"), B("escalated", ro=True, group="Pipeline"),
    S("lost_reason", "Lost reason", "lost_reasons", show={"stage": "lost"}, group="Pipeline"), TA("lost_note", "Lost note", show={"stage": "lost"}, group="Pipeline"),
    DT("hold_until", "Re-engage on", show={"stage": "on_hold"}, group="Pipeline"),
    S("source", "Source", "lead_sources", filter=True, group="Source"), T("source_detail", "Source detail", group="Source"),
    R("partner_id", "Referral partner", "partners", group="Source"), R("campaign_id", "Campaign", "campaigns", group="Source"),
    T("utm_source", group="Source"), T("utm_medium", group="Source"), T("utm_campaign", group="Source"), T("utm_term", group="Source"),
    T("utm_content", group="Source"), T("referrer", group="Source"), T("landing_page", group="Source"), T("gclid", group="Source"),
    T("fbclid", group="Source"), T("qr_code", "QR code", group="Source"), T("first_touch", group="Source"), T("last_touch", group="Source"),
    F("calculator", "json", "Calculator result", ro=True, group="Source"),
    B("consent", "Consent given", group="Source"), T("consent_text", group="Source", ro=True), DTM("consent_at", group="Source", ro=True),
    R("account_id", "Client", "accounts", ro=True, group="Converted"), R("project_id", "Project", "projects", ro=True, group="Converted"),
    R("duplicate_of", "Merged into", "leads", ro=True, group="Converted"),
], icon="inbox", number={"prefix": "LEAD", "kind": "year"}, branch=True, title="name", subtitle="company",
    status={"field": "stage", "states": LEAD_STATES},
    search=["name", "phone", "email", "company", "code"],
    list=["code", "name", "company", "service", "supply", "town", "source", "stage", "owner_id", "score", "created_at"])

entity("activities", "crm", "Activity", "Activities", [
    S("kind", "Type", [{"value": v, "label": l} for v, l in (("call", "Call"), ("whatsapp", "WhatsApp"), ("email", "Email"),
      ("meeting", "Meeting"), ("site_visit", "Site visit"), ("note", "Note"), ("follow_up", "Follow-up"))], req=True),
    T("subject", req=True), TA("notes"), R("lead_id", "Lead", "leads", child=True), R("account_id", "Client", "accounts", child=True),
    R("project_id", "Project", "projects"), R("liaison_id", "Approval", "liaisons", child=True),
    DTM("due_at", "Due"), B("done"), DTM("done_at", ro=True), T("outcome"), R("owner_id", "Owner", "users"),
], icon="phone-call", title="subject", list=["kind", "subject", "lead_id", "account_id", "due_at", "done", "owner_id"])

entity("surveys", "crm", "Site survey", "Site surveys", [
    S("survey_type", "Type", [{"value": "site_survey", "label": "Site survey"}, {"value": "energy_audit", "label": "Energy audit"},
      {"value": "bill_review", "label": "Bill review"}], default="site_survey"),
    R("lead_id", "Lead", "leads", child=True), R("account_id", "Client", "accounts", child=True),
    DTM("scheduled_at", "Scheduled for", req=True), R("engineer_id", "Engineer", "users", filter=True),
    TA("address", "Site address"), GEO(), FILE("existing_sld", "Existing single-line diagram"),
    L("load_list", "Load list", [T("description", "Load"), N("qty", "Qty"), N("kw", "kW each", "kW"), N("pf", "PF", default=0.9),
      N("df", "Demand factor", default=0.8), N("total_kw", "Total kW", calc="round(qty * kw, 2)", ro=True),
      N("demand_kw", "Demand kW", calc="round(qty * kw * df, 2)", ro=True)]),
    N("connected_kw", "Connected load", "kW", calc="round(sum(load_list.total_kw), 2)", ro=True),
    N("demand_kw", "Maximum demand", "kW", calc="round(sum(load_list.demand_kw), 2)", ro=True),
    TA("measurements"), FILES("photos"), TA("findings"), S("recommended_supply", "Recommended supply", "supply"),
    N("recommended_kva", "Recommended transformer / CD", "kVA"),
], icon="clipboard-list", number={"prefix": "SRV", "kind": "year"}, branch=True, title="code",
    status={"field": "status", "states": st(("scheduled", "Scheduled", "blue"), ("done", "Done", "green"), ("cancelled", "Cancelled", "gray"))},
    list=["code", "survey_type", "lead_id", "account_id", "scheduled_at", "engineer_id", "status"])

entity("partners", "crm", "Referral partner", "Referral partners", [
    T("name", req=True, search=True), S("type", "Type", [{"value": v, "label": v.capitalize()} for v in ("electrician", "architect", "consultant", "builder", "other")]),
    PH(search=True), EM(), T("town"), P("commission_pct", "Commission", default=2), B("active", default=True), TA("notes"),
], icon="handshake", list=["name", "type", "phone", "town", "commission_pct", "active"])

entity("campaigns", "marketing", "Campaign", "Campaigns", [
    T("name", req=True), S("channel", "Channel", "channels", filter=True), DT("start"), DT("end"), M("spend", "Spend"),
    T("utm_campaign", "UTM campaign tag"), TA("notes"),
], icon="megaphone", list=["name", "channel", "start", "end", "spend"])

entity("qr_codes", "marketing", "QR code", "QR codes", [
    T("label", req=True), S("kind", "Placed on", [{"value": v, "label": l} for v, l in (("site_board", "Site board"), ("van", "Vehicle"),
      ("brochure", "Brochure"), ("equipment", "Installed equipment"), ("other", "Other"))]),
    T("target", "Opens", default="/get-quote"), T("token", "Code", ro=True), N("scans", ro=True), N("leads", ro=True),
], icon="qr-code", title="label", list=["label", "kind", "target", "token", "scans", "leads"])

# =========================================================================== Estimation
entity("items", "estimation", "Item", "Item master", [
    T("name", req=True, search=True), S("category", "Category", "item_categories", default="material", filter=True),
    S("group", "Group", "item_groups", filter=True), T("make", search=True), TA("spec", "Specification"), S("unit", "Unit", "units", default="nos"),
    M("std_rate", "Selling rate"), M("cost_rate", "Cost rate", hide="cost"), S("gst_rate", "GST %", "gst_rates", default="18"),
    T("hsn", "HSN / SAC"), N("min_stock", "Reorder level"), N("reorder_qty", "Reorder qty"),
    B("serial_tracked", "Track serial numbers"), B("drum_tracked", "Track cable drums"), B("active", default=True),
], icon="package", number={"prefix": "IT", "kind": "plain", "width": 5}, search=["name", "code", "make", "spec"],
    list=["code", "name", "group", "make", "unit", "std_rate", "cost_rate", "active"])

entity("rate_analyses", "estimation", "Rate analysis", "Rate analyses", [
    T("name", "Work item", req=True), R("item_id", "Item it prices", "items"), S("unit", "Unit", "units"),
    L("lines", "Build-up", [S("kind", "Type", "item_categories", default="material"), R("item_id", "Item", "items"),
      T("description"), N("qty", "Qty"), S("unit", "Unit", "units"), M("rate", "Rate", hide="cost"),
      M("amount", "Amount", calc="round(qty * rate, 2)", ro=True, hide="cost")]),
    P("overhead_pct", "Overhead", default=8), P("profit_pct", "Profit", default=10),
    M("direct", "Direct cost", calc="round(sum(lines.amount), 2)", ro=True, hide="cost"),
    M("overhead", calc="round(direct * overhead_pct / 100, 2)", ro=True, hide="cost"),
    M("profit", calc="round((direct + overhead) * profit_pct / 100, 2)", ro=True, hide="cost"),
    M("rate", "Rate per unit", calc="round(direct + overhead + profit, 2)", ro=True),
], icon="calculator", list=["name", "unit", "direct", "rate"])

entity("sor_items", "estimation", "Schedule-of-rates item", "Schedules of rates", [
    S("library", "Library", [{"value": v, "label": l} for v, l in (("tnpdcl", "TNPDCL"), ("pwd", "TN PWD"), ("cpwd", "CPWD DSR"),
      ("client", "Client SOR"), ("own", "Our standard"))], filter=True), T("year", filter=True), T("sor_code", "SOR code", search=True),
    TA("description", req=True, search=True), S("unit", "Unit", "units"), M("rate", "Rate"),
], icon="book-open", title="sor_code", list=["library", "year", "sor_code", "description", "unit", "rate"], search=["sor_code", "description"])

BOQ_LINE = [T("section", "Section"), R("item_id", "Item", "items"), TA("description", req=True), T("make"),
            S("unit", "Unit", "units", default="nos"), N("qty", "Qty"), M("rate", "Rate"), M("cost", "Cost rate", hide="cost"),
            S("gst_rate", "GST %", "gst_rates", default="18"),
            M("amount", "Amount", calc="round(qty * rate, 2)", ro=True),
            M("gst_amt", "GST", calc="round(qty * rate * gst_rate / 100, 2)", ro=True),
            M("cost_amount", "Cost", calc="round(qty * cost, 2)", ro=True, hide="cost")]
entity("boqs", "estimation", "Estimate (BOQ)", "Estimates (BOQ)", [
    T("title", req=True, search=True), R("lead_id", "Lead", "leads", child=True), R("account_id", "Client", "accounts", child=True),
    R("tender_id", "Tender", "tenders", child=True), R("project_id", "Project", "projects"), N("version", default=1),
    L("lines", "Bill of quantities", BOQ_LINE),
    M("subtotal", calc="round(sum(lines.amount), 2)", ro=True), P("discount_pct", "Discount"),
    M("discount", calc="round(subtotal * discount_pct / 100, 2)", ro=True),
    M("taxable", calc="round(subtotal - discount, 2)", ro=True),
    M("gst", "GST", calc="round(sum(lines.gst_amt) * (1 - discount_pct / 100), 2)", ro=True),
    M("total", calc="round(taxable + gst, 2)", ro=True),
    M("cost_total", "Cost total", calc="round(sum(lines.cost_amount), 2)", ro=True, hide="cost"),
    M("margin", "Margin (without GST)", calc="round(taxable - cost_total, 2)", ro=True, hide="cost"),
    P("margin_pct", "Margin %", calc="if(taxable, round((taxable - cost_total) / taxable * 100, 2), 0)", ro=True, hide="cost"),
    TA("alternate_makes", "Alternate makes"), TA("notes", hide="internal"),
], icon="list-checks", number={"doc": "EST"}, branch=True, title="title",
    status={"field": "status", "states": DRAFT_APPROVAL}, approval={"amount": "total"},
    list=["code", "title", "account_id", "lead_id", "total", "margin_pct", "status", "created_at"])

PROPOSAL_STATES = st(("draft", "Draft", "gray"), ("pending_approval", "Waiting for approval", "amber"), ("approved", "Approved", "teal"),
                     ("rejected", "Rejected internally", "red"), ("sent", "Sent", "blue"), ("accepted", "Accepted", "green"),
                     ("declined", "Declined by client", "red"), ("expired", "Expired", "gray"), ("revised", "Revised", "gray"))
entity("proposals", "proposals", "Proposal", "Proposals", [
    T("title", req=True, search=True), R("account_id", "Client", "accounts", child=True, filter=True), R("contact_id", "Contact", "contacts"),
    R("lead_id", "Lead", "leads", child=True), R("boq_id", "Estimate (BOQ)", "boqs", child=True),
    MD("cover_letter", "Cover letter"), MD("scope", "Scope of work"), MD("exclusions"), MD("deviations"),
    MD("payment_terms", "Payment terms", default="40% advance with order, 50% against delivery and erection pro rata, 10% after testing and commissioning."),
    N("validity_days", "Valid for", "days", default=30), S("terms_set", "Terms & conditions", [{"value": "standard", "label": "Standard"},
      {"value": "government", "label": "Government / tender"}, {"value": "amc", "label": "AMC"}], default="standard"),
    MD("compliance", "Compliance statement"),
    M("subtotal", ro=True), P("discount_pct", "Discount", ro=True), M("taxable", ro=True), M("gst", "GST", ro=True), M("total", ro=True),
    P("margin_pct", "Margin %", ro=True, hide="cost"), DT("valid_until", ro=True), DTM("sent_at", ro=True),
    DTM("accepted_at", ro=True), T("accepted_by", ro=True), T("decline_reason", ro=True),
], icon="file-pen-line", number={"doc": "QT"}, branch=True, title="title",
    status={"field": "status", "states": PROPOSAL_STATES}, approval={"amount": "total"},
    actions={"send": {"label": "Mark as sent", "from": ["approved", "draft"], "to": "sent", "perm": "w", "needs_approval_clear": True},
             "accept": {"label": "Client accepted", "from": ["sent"], "to": "accepted", "perm": "w"},
             "decline": {"label": "Client declined", "from": ["sent"], "to": "declined", "perm": "w", "reason": True},
             "revise": {"label": "Mark revised", "from": ["sent", "declined", "approved"], "to": "revised", "perm": "w"}},
    portal={"client": "account_id"},
    list=["code", "title", "account_id", "total", "margin_pct", "status", "valid_until"])

# =========================================================================== Tenders
entity("tenders", "tenders", "Tender", "Tenders", [
    T("title", req=True, search=True), T("authority", "Authority / client", search=True), S("portal", "Portal", "tender_portals", filter=True),
    T("tender_no", "Tender no.", search=True), M("value_estimate", "Estimated value"), M("emd_amount", "EMD"), M("tender_fee", "Tender fee"),
    S("emd_mode", "EMD mode", [{"value": v, "label": l} for v, l in (("online", "Online"), ("bg", "Bank guarantee"), ("dd", "DD"), ("exempt", "Exempt (MSE)"))]),
    DT("published_on"), DTM("prebid_on", "Pre-bid meeting"), DTM("due_on", "Bid due", req=True), DTM("opening_on", "Opening"),
    M("our_quote", "Our quote"), M("l1_amount", "L1 amount"), T("l1_bidder", "L1 bidder"), N("rank", "Our rank"),
    L("competitors", "Competitor rates", [T("bidder"), M("amount"), N("rank")]),
    L("checklist", "Submission checklist", [T("item"), B("done")], default=[{"item": "Tender fee & EMD paid", "done": False},
      {"item": "Technical bid documents", "done": False}, {"item": "Pre-qualification documents", "done": False},
      {"item": "Financial bid (BOQ)", "done": False}, {"item": "Digital signature uploaded", "done": False}]),
    TA("prebid_queries", "Pre-bid queries"), S("loss_reason", "Loss reason", "lost_reasons"), R("owner_id", "Owner", "users"), B("emd_refunded", "EMD refunded"),
], icon="landmark", number={"prefix": "TND", "kind": "year"}, branch=True, title="title",
    status={"field": "status", "states": st(("identified", "Identified", "gray"), ("preparing", "Preparing", "blue"),
            ("submitted", "Submitted", "violet"), ("tech_qualified", "Technically qualified", "teal"), ("tech_rejected", "Technically rejected", "red"),
            ("financial_opened", "Financial opened", "amber"), ("won", "Won", "green"), ("lost", "Lost", "red"), ("cancelled", "Cancelled", "gray"))},
    list=["code", "title", "authority", "portal", "due_on", "value_estimate", "our_quote", "status"])

entity("bank_guarantees", "tenders", "Bank guarantee", "Bank guarantees", [
    S("kind", "Type", [{"value": v, "label": l} for v, l in (("emd", "EMD"), ("pbg", "Performance BG"), ("advance", "Advance BG"), ("retention", "Retention BG"))], req=True),
    R("tender_id", "Tender", "tenders", child=True), R("project_id", "Project", "projects", child=True), T("bank", req=True), T("bg_no", "BG no.", req=True),
    M("amount", req=True), DT("issued_on"), DT("valid_until", req=True), DT("claim_until", "Claim period ends"), T("beneficiary"),
    M("margin_money", "Margin money", hide="cost"), M("commission", "Bank commission", hide="cost"),
], icon="shield-check", title="bg_no", number={"prefix": "BG", "kind": "year"},
    status={"field": "status", "states": st(("active", "Active", "green"), ("released", "Released", "gray"), ("claimed", "Claimed", "red"), ("expired", "Expired", "amber"))},
    list=["kind", "bg_no", "bank", "amount", "valid_until", "claim_until", "status"])

entity("prequal_docs", "tenders", "Pre-qualification document", "Pre-qualification library", [
    T("name", req=True), S("category", "Category", [{"value": v, "label": l} for v, l in (("financials", "Financials"), ("experience", "Work experience"),
      ("licences", "Licences"), ("certificates", "Certificates"), ("profiles", "Company profile"), ("other", "Other"))]),
    FILE("file", req=True), DT("valid_until"), TA("notes"),
], icon="folder-check", list=["name", "category", "valid_until"])

# =========================================================================== Projects
PROJECT_STATES = st(("planned", "Planned", "gray"), ("mobilising", "Mobilising", "blue"), ("in_progress", "In progress", "blue"),
                    ("on_hold", "On hold", "amber"), ("testing", "Testing", "violet"), ("handed_over", "Handed over", "green"),
                    ("closed", "Closed", "gray"), ("cancelled", "Cancelled", "red"))
entity("projects", "projects", "Project", "Projects", [
    T("name", "Project name", req=True, search=True, group="Contract"), R("account_id", "Client", "accounts", child=True, filter=True, group="Contract"),
    R("contact_id", "Client contact", "contacts", group="Contract"), R("lead_id", "Lead", "leads", group="Contract"), R("proposal_id", "Proposal", "proposals", group="Contract"),
    T("wo_no", "Work order / LOA no.", group="Contract"), DT("wo_date", "Work order date", group="Contract"),
    M("contract_value", "Contract value (without GST)", group="Contract"),
    S("service", "Main service", "services", filter=True, group="Scope"), S("sector", "Sector", "sectors", filter=True, group="Scope"),
    S("supply", "Supply", "supply", filter=True, group="Scope"), S("voltage", "Voltage", "voltages", group="Scope"),
    N("capacity_kva", "Capacity", "kVA", group="Scope"), N("capacity_kw", "Solar / load", "kW", group="Scope"),
    TA("site_address", "Site address", group="Scope"), T("town", filter=True, group="Scope"), GEO(group="Scope"),
    R("manager_id", "Project manager", "users", filter=True, group="Team"), RS("team_ids", "Site team", "users", group="Team"),
    RS("consultant_ids", "Consultants / architects", "contacts", group="Team"),
    DT("start_date", "Start", group="Schedule"), DT("end_date", "Planned finish", group="Schedule"), DT("actual_end", "Actual finish", group="Schedule"),
    P("percent_complete", "% complete", ro=True, group="Schedule"),
    P("retention_pct", "Retention", default=5, group="Commercial"), M("mobilisation_advance", "Mobilisation advance", group="Commercial"),
    P("advance_recovery_pct", "Advance recovery per bill", default=10, group="Commercial"),
    P("ld_pct_per_week", "LD per week of delay", default=0.5, group="Commercial"), P("ld_cap_pct", "LD cap", default=5, group="Commercial"),
    N("dlp_months", "Defects liability period", "months", default=12, group="Commercial"), DT("dlp_until", "DLP ends", ro=True, group="Commercial"),
    TA("payment_terms", group="Commercial"),
    L("budget", "Budget (cost)", [S("head", "Cost head", [{"value": v, "label": l} for v, l in (("material", "Material"), ("labour", "Own labour"),
      ("subcon", "Subcontract"), ("tp", "Tools & plant"), ("liaison", "Liaison & fees"), ("overhead", "Site overheads"), ("other", "Other"))]),
      M("amount", "Budget")], hide="cost", group="Commercial"),
    M("budget_total", "Budget total", calc="round(sum(budget.amount), 2)", ro=True, hide="cost", group="Commercial"),
    B("publish", "Show on website", group="Website", help="Only with the client's permission"), T("slug", "Web address", group="Website"),
    T("public_title", "Public title", group="Website"), TA("public_summary", "Summary", group="Website"), TA("challenge", group="Website"),
    TA("solution", group="Website"), TA("results", group="Website"),
    L("highlights", "Key numbers", [T("label"), T("value")], group="Website"), T("year", group="Website"), B("featured", group="Website"),
    FILE("cover", "Cover photo", group="Website"), FILES("photos", "Photos", group="Website"),
], icon="hard-hat", number={"doc": "PRJ"}, branch=True, title="name", subtitle="account_id",
    status={"field": "status", "states": PROJECT_STATES},
    list=["code", "name", "account_id", "supply", "capacity_kva", "contract_value", "manager_id", "percent_complete", "status"],
    portal={"client": "account_id", "consultant": "consultant_ids"})

entity("milestones", "projects", "Milestone", "Schedule", [
    PROJECT(req=True), T("name", req=True), T("wbs", "WBS"), P("weight_pct", "Weight", default=10), DT("planned_start", req=True),
    DT("planned_end", req=True), DT("actual_start"), DT("actual_end"), P("percent", "% done"), RS("depends_on", "Depends on", "milestones"),
    P("billing_pct", "Payment milestone %"), TA("notes"),
], icon="calendar-range", sort="planned_start", project=True,
    status={"field": "status", "states": st(("not_started", "Not started", "gray"), ("in_progress", "In progress", "blue"), ("done", "Done", "green"), ("delayed", "Delayed", "red"))},
    list=["wbs", "name", "planned_start", "planned_end", "percent", "status"], portal={"client": "project", "consultant": "project"})

entity("dprs", "site", "Daily progress report", "Daily progress reports", [
    PROJECT(req=True), DT("date", req=True), S("weather", "Weather", [{"value": v, "label": v.capitalize()} for v in ("clear", "cloudy", "rain", "heavy_rain", "hot")], default="clear"),
    L("manpower", "Manpower", [S("trade", "Trade", "trades"), N("own", "Own"), N("subcon", "Subcontract")]),
    N("manpower_total", "Total manpower", calc="sum(manpower.own) + sum(manpower.subcon)", ro=True),
    L("work_done", "Work done", [TA("description"), N("qty", "Qty"), S("unit", "Unit", "units"), T("location")]),
    L("materials", "Materials used", [R("item_id", "Item", "items"), N("qty", "Qty"), S("unit", "Unit", "units")]),
    TA("equipment", "Equipment on site"), TA("hindrances", "Hindrances"), TA("safety", "Safety observations"),
    FILES("photos", "Photos (time-stamped)"), GEO(), B("share_with_client", "Share with client", default=True),
], icon="notebook-pen", title="date", sort="-date", project=True,
    list=["date", "project_id", "manpower_total", "weather", "created_by"], portal={"client": "project", "consultant": "project"})

entity("hindrances", "site", "Hindrance", "Hindrance register", [
    PROJECT(req=True), DT("raised_on", req=True), TA("description", req=True),
    S("cause", "Cause", [{"value": v, "label": l} for v, l in (("client", "Client"), ("discom", "TNPDCL / discom"), ("weather", "Weather"),
      ("material", "Material"), ("design", "Design / drawings"), ("other_agency", "Other agency"), ("own", "Our side"))]),
    T("responsibility"), N("impact_days", "Impact", "days"), DT("resolved_on"),
], icon="octagon-alert", title="description", project=True,
    status={"field": "status", "states": st(("open", "Open", "red"), ("resolved", "Resolved", "green"))},
    list=["raised_on", "project_id", "description", "cause", "impact_days", "status"])

entity("rfis", "site", "RFI", "RFIs", [
    PROJECT(req=True), T("subject", req=True), TA("question", req=True), S("to", "To", [{"value": "client", "label": "Client"}, {"value": "consultant", "label": "Consultant"}]),
    DT("due_on"), TA("answer"), DT("answered_on"),
], icon="message-square-reply", number={"prefix": "RFI", "kind": "year"}, title="subject", project=True,
    status={"field": "status", "states": st(("open", "Open", "amber"), ("answered", "Answered", "green"), ("closed", "Closed", "gray"))},
    list=["code", "project_id", "subject", "to", "due_on", "status"], portal={"client": "project", "consultant": "project"})

entity("drawings", "site", "Drawing", "Drawing register", [
    PROJECT(req=True), T("number", "Drawing no.", req=True, search=True), T("title", req=True, search=True),
    S("dtype", "Type", [{"value": v, "label": l} for v, l in (("sld", "Single-line diagram"), ("layout", "Layout"), ("cable_schedule", "Cable schedule"),
      ("earthing", "Earthing layout"), ("panel_ga", "Panel GA"), ("lighting", "Lighting layout"), ("substation", "Substation layout"), ("other", "Other"))]),
    T("revision", default="R0"), FILE("file"), DT("submitted_on"), DT("approved_on"), TA("comments", "Client / consultant comments"),
    B("share_with_client", "Share with client", default=True),
], icon="pencil-ruler", title="number", project=True,
    status={"field": "status", "states": st(("draft", "Draft", "gray"), ("submitted", "Submitted", "blue"), ("approved", "Approved", "green"),
            ("approved_with_comments", "Approved with comments", "teal"), ("rejected", "Rejected", "red"), ("superseded", "Superseded", "gray"), ("as_built", "As-built", "violet"))},
    actions={"submit": {"label": "Submit for approval", "from": ["draft", "rejected", "approved_with_comments"], "to": "submitted", "perm": "w"}},
    list=["number", "title", "dtype", "revision", "status", "submitted_on", "approved_on"], portal={"client": "project", "consultant": "project"})

entity("mb_entries", "site", "Measurement", "Measurement book", [
    PROJECT(req=True), DT("date", req=True), TA("description", "BOQ item", req=True), R("item_id", "Item", "items"), T("location"),
    N("nos", "Nos", default=1), N("length", "L"), N("breadth", "B"), N("height", "H"),
    N("qty", "Quantity", calc="round(nos * if(length, length, 1) * if(breadth, breadth, 1) * if(height, height, 1), 3)", ro=True),
    S("unit", "Unit", "units", default="m"), M("rate", "BOQ rate"), M("amount", calc="round(qty * rate, 2)", ro=True),
    R("ra_bill_id", "RA bill", "ra_bills", ro=True),
], icon="ruler", title="description", sort="-date", project=True,
    status={"field": "status", "states": st(("recorded", "Recorded", "blue"), ("checked", "Checked", "teal"), ("billed", "Billed", "green"))},
    actions={"check": {"label": "Mark checked", "from": ["recorded"], "to": "checked", "perm": "w"}},
    list=["date", "project_id", "description", "location", "qty", "unit", "amount", "status"])

RA_LINE = [TA("description"), S("unit", "Unit", "units"), N("prev_qty", "Previous qty"), N("this_qty", "This bill qty"),
           N("cum_qty", "Up to date", calc="prev_qty + this_qty", ro=True), M("rate"),
           M("this_amount", "This bill", calc="round(this_qty * rate, 2)", ro=True)]
entity("ra_bills", "projects", "RA bill", "RA bills", [
    PROJECT(req=True), N("bill_no", "RA bill no.", ro=True), DT("period_from"), DT("period_to", req=True),
    L("lines", "Abstract", RA_LINE),
    M("gross", "Gross this bill", calc="round(sum(lines.this_amount), 2)", ro=True),
    P("retention_pct", "Retention"), M("retention", calc="round(gross * retention_pct / 100, 2)", ro=True),
    M("advance_recovery", "Advance recovery"), P("tds_pct", "TDS (194C)", default=2),
    M("tds", "TDS", calc="round(gross * tds_pct / 100, 2)", ro=True), M("other_deductions", "Other deductions"),
    S("gst_rate", "GST %", "gst_rates", default="18"), M("gst", "GST", calc="round(gross * gst_rate / 100, 2)", ro=True),
    M("net", "Net payable", calc="round(gross + gst - retention - advance_recovery - tds - other_deductions, 2)", ro=True),
    M("certified_amount", "Certified by client"), DT("certified_on"), R("invoice_id", "Invoice", "invoices", ro=True),
], icon="receipt-indian-rupee", number={"doc": "RA"}, title="code", project=True, branch=True,
    status={"field": "status", "states": st(("draft", "Draft", "gray"), ("pending_approval", "Waiting for approval", "amber"), ("approved", "Approved", "teal"),
            ("rejected", "Rejected", "red"), ("submitted", "Submitted to client", "blue"), ("certified", "Certified", "violet"), ("invoiced", "Invoiced", "green"), ("paid", "Paid", "green"))},
    approval={"amount": "gross"},
    actions={"submit_client": {"label": "Submit to client", "from": ["approved"], "to": "submitted", "perm": "w"},
             "certify": {"label": "Record certification", "from": ["submitted"], "to": "certified", "perm": "w", "need": ["certified_amount", "certified_on"]}},
    list=["code", "project_id", "bill_no", "period_to", "gross", "net", "status"], portal={"client": "project"})

entity("variations", "projects", "Variation", "Variations & extra items", [
    PROJECT(req=True), T("title", req=True), TA("reason"),
    L("lines", "Items", [TA("description"), N("qty"), S("unit", "Unit", "units"), M("rate"), M("amount", calc="round(qty * rate, 2)", ro=True)]),
    M("amount", calc="round(sum(lines.amount), 2)", ro=True), DT("client_approved_on"), T("client_approved_by"),
], icon="git-pull-request-arrow", number={"prefix": "VO", "kind": "year"}, title="title", project=True,
    status={"field": "status", "states": st(("draft", "Draft", "gray"), ("pending_approval", "Waiting for internal approval", "amber"),
            ("approved", "Approved internally", "teal"), ("rejected", "Rejected", "red"), ("sent", "Sent to client", "blue"),
            ("client_approved", "Client approved", "green"), ("client_rejected", "Client rejected", "red"))},
    approval={"amount": "amount"},
    actions={"send": {"label": "Send to client", "from": ["approved"], "to": "sent", "perm": "w"},
             "client_approve": {"label": "Client approved", "from": ["sent"], "to": "client_approved", "perm": "w"},
             "client_reject": {"label": "Client rejected", "from": ["sent"], "to": "client_rejected", "perm": "w"}},
    list=["code", "project_id", "title", "amount", "status"], portal={"client": "project"})

entity("snags", "site", "Snag", "Snag list", [
    PROJECT(req=True), TA("description", req=True), T("location"), S("priority", "Priority", "ticket_priority", default="normal"),
    FILE("photo"), R("assigned_to", "Assigned to", "users"), DT("due_on"), B("client_signoff", "Client signed off"),
], icon="list-todo", title="description", project=True,
    status={"field": "status", "states": st(("open", "Open", "red"), ("fixed", "Fixed", "amber"), ("verified", "Verified", "green"))},
    list=["project_id", "description", "location", "priority", "assigned_to", "status"], portal={"client": "project"})

entity("handovers", "projects", "Handover", "Handovers", [
    PROJECT(req=True), DT("date", req=True), T("client_rep", "Client representative"),
    L("checklist", "Handover pack", [T("document"), B("included")], default=[{"document": d, "included": False} for d in (
        "As-built drawings", "Test reports & certificates", "CEIG approval", "TNPDCL energisation letter", "Warranty cards",
        "O&M manuals", "Spare parts list", "Training record", "Snag list signed off")]),
    B("signed", "Signed by client"), TA("notes"),
], icon="package-check", title="date", project=True, list=["project_id", "date", "client_rep", "signed"], portal={"client": "project"})

# =========================================================================== Quality & testing
entity("inspections", "quality", "Inspection", "Inspections (QA/QC)", [
    PROJECT(req=True), S("itype", "Inspection", [{"value": v, "label": l} for v, l in (("material_receipt", "Material receipt"), ("cable_laying", "Cable laying"),
      ("termination", "Termination"), ("earthing", "Earthing"), ("panel_erection", "Panel erection"), ("transformer_erection", "Transformer erection"),
      ("pre_commissioning", "Pre-commissioning"))], req=True),
    DT("date", req=True), L("checklist", "Checklist", [T("check"), S("result", "Result", [{"value": "ok", "label": "OK"}, {"value": "not_ok", "label": "Not OK"}, {"value": "na", "label": "N/A"}]), T("remarks")]),
    S("result", "Result", [{"value": "pass", "label": "Pass"}, {"value": "fail", "label": "Fail"}]), R("inspected_by", "Inspected by", "users"),
    T("witness", "Client / consultant witness"),
], icon="clipboard-check", number={"prefix": "ITP", "kind": "year"}, title="code", project=True,
    list=["code", "project_id", "itype", "date", "result", "inspected_by"], portal={"client": "project", "consultant": "project"})

entity("ncrs", "quality", "Non-conformance", "Non-conformance reports", [
    PROJECT(req=True), TA("description", req=True), S("severity", "Severity", [{"value": v, "label": v.capitalize()} for v in ("minor", "major", "critical")]),
    DT("raised_on", req=True), TA("root_cause"), TA("corrective_action"), DT("due_on"), DT("closed_on"),
], icon="badge-alert", number={"prefix": "NCR", "kind": "year"}, title="code", project=True,
    status={"field": "status", "states": st(("open", "Open", "red"), ("action_taken", "Action taken", "amber"), ("closed", "Closed", "green"))},
    list=["code", "project_id", "description", "severity", "due_on", "status"])

entity("instruments", "testing", "Test instrument", "Test instruments", [
    T("name", req=True), S("itype", "Type", [{"value": v, "label": v.replace("_", " ").capitalize()} for v in (
        "insulation_tester", "earth_tester", "ctpt_analyser", "relay_test_kit", "hv_tester", "vlf_tester", "bdv_kit",
        "winding_resistance", "multimeter", "clamp_meter", "thermal_camera", "pq_analyser", "other")]),
    T("make"), T("model"), T("serial_no", "Serial no.", req=True), DT("calibration_on", "Calibrated on"), DT("calibration_due", "Calibration due", req=True),
    FILE("certificate", "Calibration certificate"), R("issued_to", "Issued to", "users"),
], icon="gauge", title="name",
    status={"field": "status", "states": st(("available", "Available", "green"), ("issued", "Issued", "blue"), ("calibration", "Out for calibration", "amber"), ("damaged", "Damaged", "red"))},
    list=["name", "itype", "serial_no", "calibration_due", "issued_to", "status"])

entity("test_reports", "testing", "Test report", "Test reports", [
    R("project_id", "Project", "projects", child=True), R("asset_id", "Installed equipment", "installed_assets", child=True),
    R("ticket_id", "Service ticket", "tickets", child=True), S("test_type", "Test", "test_types", req=True, filter=True),
    T("equipment", "Equipment tested", req=True), R("instrument_id", "Instrument used", "instruments", req=True), DT("date", req=True),
    L("readings", "Readings", [T("point", "Point / phase"), T("value"), T("unit"), T("limit", "Acceptance limit"),
      S("result", "Result", [{"value": "pass", "label": "Pass"}, {"value": "fail", "label": "Fail"}])]),
    S("result", "Overall result", [{"value": "pass", "label": "Pass"}, {"value": "fail", "label": "Fail"}]), TA("remarks"),
    R("tested_by", "Tested by", "users"), T("witnessed_by", "Witnessed by"),
], icon="activity", number={"prefix": "TR", "kind": "year"}, title="code",
    status={"field": "status", "states": st(("draft", "Draft", "gray"), ("issued", "Issued", "green"))},
    actions={"issue": {"label": "Issue certificate", "from": ["draft"], "to": "issued", "perm": "w", "need": ["result", "tested_by"]}},
    list=["code", "test_type", "equipment", "project_id", "date", "result", "status"], portal={"client": "project", "consultant": "project"})

# =========================================================================== Liaison
entity("liaisons", "liaison", "Approval / liaison", "Approvals & liaison", [
    S("kind", "Application", "liaison_kinds", req=True, filter=True), R("project_id", "Project", "projects", child=True),
    R("account_id", "Client", "accounts", child=True), S("authority", "Authority", [{"value": v, "label": v} for v in ("TNPDCL", "TANTRANSCO", "CEIG", "Other")], default="TNPDCL"),
    T("application_no", "Application no."), T("office", "Office / section"),
    S("stage", "Stage", "liaison_stages", default="prepared", filter=True),
    L("stages", "Stage tracker", [S("stage", "Stage", "liaison_stages"), DT("expected_on", "Expected"), DT("done_on", "Done"), T("notes")]),
    L("fees", "Fees paid", [T("description"), M("amount"), DT("paid_on"), T("receipt_no", "Receipt no.")]),
    M("fees_total", "Fees total", calc="round(sum(fees.amount), 2)", ro=True),
    T("officer_name", "Officer"), PH("officer_phone", "Officer phone"), DTM("next_follow_up", "Next follow-up"),
    FILES("documents"), B("share_with_client", "Show status to client", default=True), T("status_note", "Status note for client"),
], icon="stamp", number={"prefix": "LIA", "kind": "year"}, title="code", branch=True,
    status={"field": "stage", "states": st(*[(x["value"], x["label"], "green" if x["value"] in ("energised", "closed") else "blue") for x in OPTIONS["liaison_stages"]])},
    list=["code", "kind", "project_id", "authority", "application_no", "stage", "next_follow_up"], portal={"client": "account_id"})

# =========================================================================== Procurement
entity("vendors", "procurement", "Vendor", "Vendors & subcontractors", [
    T("name", req=True, search=True), S("vtype", "Type", [{"value": v, "label": l} for v, l in (("supplier", "Supplier"), ("subcontractor", "Subcontractor"),
      ("labour_contractor", "Labour contractor"), ("transporter", "Transporter / crane hire"), ("service", "Service provider"))], default="supplier", filter=True),
    MS("categories", "Supplies", "item_groups"), T("gstin", "GSTIN"), T("pan", "PAN"), PH(search=True), EM(), T("contact_person"), TA("address"), T("town"),
    N("payment_terms_days", "Payment terms", "days", default=30), T("licence_no", "Electrical licence no."), DT("licence_valid_until", "Licence valid until"),
    T("bank_name", "Bank", hide="bank"), T("bank_account", "Account no.", hide="bank"), T("ifsc", "IFSC", hide="bank"),
    L("compliance", "Compliance documents", [T("document"), DT("valid_until"), FILE("file")]),
    N("rating", "Rating (out of 5)", ro=True), B("active", default=True),
], icon="truck", number={"prefix": "V", "kind": "plain"}, search=["name", "phone", "gstin", "code"],
    list=["code", "name", "vtype", "town", "phone", "rating", "active"], portal={"vendor": "id", "subcontractor": "id"})

ITEM_LINE = [R("item_id", "Item", "items"), TA("description"), N("qty", "Qty"), S("unit", "Unit", "units", default="nos"), T("remarks")]
entity("purchase_requests", "procurement", "Material request", "Material requests", [
    PROJECT(), R("store_id", "Deliver to store", "stores"), DT("required_by", req=True),
    L("lines", "Materials", ITEM_LINE), TA("notes"),
], icon="clipboard-pen", number={"doc": "MR"}, title="code", project=True, branch=True,
    status={"field": "status", "states": st(("draft", "Draft", "gray"), ("pending_approval", "Waiting for approval", "amber"), ("approved", "Approved", "teal"),
            ("rejected", "Rejected", "red"), ("ordered", "Ordered", "blue"), ("closed", "Closed", "green"))},
    approval={"amount": None}, list=["code", "project_id", "required_by", "status", "created_by"])

entity("rfqs", "procurement", "RFQ", "RFQs", [
    R("pr_id", "Material request", "purchase_requests", child=True), PROJECT(), RS("vendor_ids", "Vendors asked", "vendors"),
    L("lines", "Items", ITEM_LINE), DT("due_on", "Quotes due"), TA("terms"),
], icon="mails", number={"doc": "RFQ"}, title="code", branch=True,
    status={"field": "status", "states": st(("draft", "Draft", "gray"), ("sent", "Sent", "blue"), ("compared", "Compared", "violet"), ("closed", "Closed", "green"))},
    actions={"send": {"label": "Mark sent", "from": ["draft"], "to": "sent", "perm": "w"}},
    list=["code", "project_id", "due_on", "status"], portal={"vendor": "vendor_ids"})

entity("vendor_quotes", "procurement", "Vendor quote", "Vendor quotes", [
    R("rfq_id", "RFQ", "rfqs", req=True, child=True), R("vendor_id", "Vendor", "vendors", req=True),
    L("lines", "Rates", [R("item_id", "Item", "items"), TA("description"), N("qty"), M("rate"), S("gst_rate", "GST %", "gst_rates", default="18"),
      T("make"), N("delivery_days", "Delivery", "days"), M("amount", calc="round(qty * rate, 2)", ro=True)]),
    M("freight"), M("subtotal", calc="round(sum(lines.amount), 2)", ro=True), M("total", calc="round(subtotal + freight, 2)", ro=True),
    T("payment_terms"), DT("valid_until"),
], icon="file-spreadsheet", title="vendor_id", list=["rfq_id", "vendor_id", "total", "valid_until"], portal={"vendor": "vendor_id"})

PO_LINE = [R("item_id", "Item", "items"), TA("description"), T("make"), N("qty", "Qty"), S("unit", "Unit", "units", default="nos"),
           M("rate"), S("gst_rate", "GST %", "gst_rates", default="18"), M("amount", calc="round(qty * rate, 2)", ro=True),
           M("gst", "GST", calc="round(qty * rate * gst_rate / 100, 2)", ro=True), N("received_qty", "Received", ro=True)]
entity("purchase_orders", "procurement", "Purchase order", "Purchase orders", [
    R("vendor_id", "Vendor", "vendors", req=True, filter=True, child=True), PROJECT(), R("store_id", "Deliver to store", "stores"),
    R("rfq_id", "RFQ", "rfqs"), R("pr_id", "Material request", "purchase_requests", child=True), DT("date", req=True), DT("delivery_by"),
    L("lines", "Items", PO_LINE), M("freight"),
    M("subtotal", calc="round(sum(lines.amount), 2)", ro=True), M("gst", "GST", calc="round(sum(lines.gst), 2)", ro=True),
    M("total", calc="round(subtotal + gst + freight, 2)", ro=True), TA("terms", default="Delivery to site / store as per schedule. Test certificates and warranty cards to accompany supply. Payment as per agreed terms after receipt and acceptance."),
    L("schedule", "Delivery schedule", [DT("date"), T("note")]),
], icon="shopping-cart", number={"doc": "PO"}, title="code", project=True, branch=True,
    status={"field": "status", "states": st(("draft", "Draft", "gray"), ("pending_approval", "Waiting for approval", "amber"), ("approved", "Approved", "teal"),
            ("rejected", "Rejected", "red"), ("sent", "Sent to vendor", "blue"), ("partly_received", "Partly received", "violet"), ("received", "Received", "green"),
            ("closed", "Closed", "gray"), ("cancelled", "Cancelled", "gray"))},
    approval={"amount": "total"},
    actions={"send": {"label": "Mark sent to vendor", "from": ["approved"], "to": "sent", "perm": "w"},
             "close": {"label": "Close", "from": ["partly_received", "received", "sent"], "to": "closed", "perm": "w"},
             "cancel": {"label": "Cancel", "from": ["draft", "approved", "sent"], "to": "cancelled", "perm": "w", "reason": True}},
    list=["code", "vendor_id", "project_id", "date", "total", "status"], portal={"vendor": "vendor_id"}, locked=["received", "closed", "cancelled"])

entity("grns", "stores", "Goods receipt", "Goods receipts (GRN)", [
    R("po_id", "Purchase order", "purchase_orders", child=True), R("vendor_id", "Vendor", "vendors", req=True), R("store_id", "Store", "stores", req=True),
    PROJECT(), DT("date", req=True), T("dc_no", "Delivery challan no."), T("invoice_no", "Vendor invoice no."), T("vehicle_no", "Vehicle no."),
    L("lines", "Received", [R("item_id", "Item", "items", req=True), N("ordered_qty", "Ordered", ro=True), N("received_qty", "Received"),
      N("accepted_qty", "Accepted"), N("rejected_qty", "Rejected", calc="max(received_qty - accepted_qty, 0)", ro=True),
      T("reason", "Shortage / reject reason"), M("rate", hide="cost"), T("drum_no", "Drum no."), N("drum_length", "Drum length", "m"),
      TA("serial_nos", "Serial numbers (one per line)")]),
    FILES("photos"), TA("notes"),
], icon="package-open", number={"doc": "GRN"}, title="code", branch=True,
    status={"field": "status", "states": st(("draft", "Draft", "gray"), ("posted", "Posted to stock", "green"))},
    actions={"post": {"label": "Post to stock", "from": ["draft"], "to": "posted", "perm": "w", "confirm": "Posting adds the accepted quantities to stock. It can't be undone."}},
    list=["code", "po_id", "vendor_id", "store_id", "date", "status"], locked=["posted"])

entity("vendor_bills", "finance", "Vendor bill", "Vendor bills", [
    R("vendor_id", "Vendor", "vendors", req=True, filter=True, child=True), R("po_id", "Purchase order", "purchase_orders", child=True),
    RS("grn_ids", "Goods receipts", "grns"), PROJECT(), T("bill_no", "Bill no.", req=True), DT("bill_date", req=True), DT("due_date"),
    L("lines", "Lines", [TA("description"), N("qty"), M("rate"), S("gst_rate", "GST %", "gst_rates", default="18"),
      M("amount", calc="round(qty * rate, 2)", ro=True), M("gst", "GST", calc="round(qty * rate * gst_rate / 100, 2)", ro=True)]),
    M("subtotal", calc="round(sum(lines.amount), 2)", ro=True), M("gst", "GST", calc="round(sum(lines.gst), 2)", ro=True),
    P("tds_pct", "TDS", default=0), M("tds", "TDS", calc="round(subtotal * tds_pct / 100, 2)", ro=True),
    M("total", "Bill total", calc="round(subtotal + gst, 2)", ro=True), M("payable", calc="round(total - tds, 2)", ro=True),
    M("paid", ro=True), M("balance", calc="round(payable - paid, 2)", ro=True),
    S("match_status", "3-way match", [{"value": v, "label": l} for v, l in (("matched", "Matched"), ("qty_mismatch", "Quantity differs"),
      ("rate_mismatch", "Rate differs"), ("no_grn", "No goods receipt"), ("no_po", "No PO"))], ro=True),
    T("eway_bill_no", "E-way bill no."), FILE("file", "Bill copy"),
], icon="file-text", number={"prefix": "VB", "kind": "year"}, title="bill_no", branch=True,
    status={"field": "status", "states": st(("draft", "Draft", "gray"), ("verified", "Verified", "blue"), ("part_paid", "Part paid", "amber"), ("paid", "Paid", "green"))},
    actions={"verify": {"label": "Mark verified", "from": ["draft"], "to": "verified", "perm": "w"}},
    list=["code", "vendor_id", "bill_no", "bill_date", "total", "balance", "match_status", "status"], portal={"vendor": "vendor_id"})

entity("rate_contracts", "procurement", "Rate contract", "Rate contracts", [
    R("vendor_id", "Vendor", "vendors", req=True, child=True), R("item_id", "Item", "items", req=True), M("rate", req=True),
    DT("valid_from"), DT("valid_to"), TA("notes"),
], icon="file-lock-2", title="item_id", list=["vendor_id", "item_id", "rate", "valid_from", "valid_to"])

entity("vendor_registrations", "procurement", "Vendor registration", "Vendor registrations (website)", [
    T("company", req=True), S("vtype", "Type", [{"value": "supplier", "label": "Supplier"}, {"value": "subcontractor", "label": "Subcontractor"},
      {"value": "labour_contractor", "label": "Labour contractor"}, {"value": "transporter", "label": "Transporter"}]),
    T("trade", "Trade / products"), T("gstin", "GSTIN"), T("contact_person"), PH(), EM(), T("town"), T("licence_no", "Licence no."), FILES("documents"),
    R("vendor_id", "Vendor record", "vendors", ro=True),
], icon="user-plus", title="company",
    status={"field": "status", "states": st(("new", "New", "blue"), ("approved", "Approved", "green"), ("rejected", "Rejected", "red"))},
    list=["company", "vtype", "trade", "town", "phone", "status", "created_at"])

# =========================================================================== Stores
entity("stores", "stores", "Store", "Stores", [
    T("name", req=True), S("stype", "Type", [{"value": "warehouse", "label": "Warehouse"}, {"value": "site_store", "label": "Site store"}], default="warehouse"),
    PROJECT(), TA("address"), R("keeper_id", "Store keeper", "users"), B("active", default=True),
], icon="warehouse", branch=True, list=["name", "stype", "project_id", "keeper_id", "active"])

entity("stock_moves", "stores", "Stock movement", "Stock ledger", [
    DT("date"), R("item_id", "Item", "items"), R("store_id", "Store", "stores"), N("qty"), M("rate", hide="cost"), M("value", hide="cost"),
    S("kind", "Movement", [{"value": v, "label": l} for v, l in (("grn", "Goods receipt"), ("issue", "Issue to project"), ("return", "Return from project"),
      ("transfer_out", "Transfer out"), ("transfer_in", "Transfer in"), ("adjustment", "Adjustment"), ("scrap", "Scrap"))]),
    T("ref_code", "Reference"), R("project_id", "Project", "projects"), T("drum_no"), T("serial_no"), T("note"),
], icon="arrow-left-right", readonly=True, title="ref_code", sort="-created_at", list=["date", "item_id", "store_id", "qty", "kind", "ref_code", "project_id"])

entity("material_moves", "stores", "Material movement", "Issues, returns & transfers", [
    S("mtype", "Type", [{"value": v, "label": l} for v, l in (("issue", "Issue to project"), ("return", "Return from project"),
      ("transfer", "Transfer between stores"), ("adjustment", "Stock adjustment"), ("scrap", "Scrap"))], req=True, filter=True),
    R("from_store_id", "From store", "stores"), R("to_store_id", "To store", "stores"), PROJECT(), DT("date", req=True),
    L("lines", "Items", [R("item_id", "Item", "items", req=True), N("qty", "Qty (+/- for adjustment)"), R("drum_id", "Cable drum", "cable_drums"),
      T("serial_no", "Serial no."), T("remarks")]),
    T("vehicle_no", "Vehicle no."), TA("notes"),
], icon="arrow-left-right", number={"doc": "MM"}, title="code", branch=True,
    status={"field": "status", "states": st(("draft", "Draft", "gray"), ("posted", "Posted", "green"), ("in_transit", "In transit", "amber"), ("received", "Received", "green"))},
    actions={"post": {"label": "Post", "from": ["draft"], "to": "posted", "perm": "w", "confirm": "Posting changes stock. It can't be undone."},
             "receive": {"label": "Receive at store", "from": ["in_transit"], "to": "received", "perm": "w"}},
    list=["code", "mtype", "from_store_id", "to_store_id", "project_id", "date", "status"], locked=["posted", "in_transit", "received"])

entity("cable_drums", "stores", "Cable drum", "Cable drums", [
    T("drum_no", "Drum no.", req=True, search=True), R("item_id", "Cable", "items", req=True), T("make"), T("size", "Size / core"),
    N("initial_length", "Length on receipt", "m", req=True), N("remaining_length", "Remaining", "m", ro=True),
    R("store_id", "Store", "stores"), PROJECT(), B("returnable", "Returnable drum"), M("deposit", "Drum deposit"),
    R("vendor_id", "Vendor", "vendors"),
    L("cuts", "Cuts", [DT("date"), N("length", "Length", "m"), R("project_id", "Project", "projects"), T("circuit", "Feeder / circuit"), T("by", "Cut by")]),
], icon="cylinder", title="drum_no",
    status={"field": "status", "states": st(("in_store", "In store", "blue"), ("at_site", "At site", "violet"), ("empty", "Empty", "gray"), ("returned", "Returned to vendor", "green"))},
    list=["drum_no", "item_id", "size", "initial_length", "remaining_length", "store_id", "project_id", "status"])

entity("serial_items", "stores", "Serial-tracked item", "Serial numbers", [
    R("item_id", "Item", "items", req=True), T("serial_no", "Serial no.", req=True, search=True), T("make"), T("model"), T("rating"),
    R("store_id", "Store", "stores"), PROJECT(), R("asset_id", "Installed as", "installed_assets"), R("grn_id", "GRN", "grns"), DT("warranty_until"),
], icon="scan-barcode", title="serial_no",
    status={"field": "status", "states": st(("in_store", "In store", "blue"), ("issued", "Issued", "violet"), ("installed", "Installed", "green"), ("returned", "Returned", "gray"), ("faulty", "Faulty", "red"))},
    list=["serial_no", "item_id", "make", "store_id", "project_id", "status", "warranty_until"])

# =========================================================================== Tools, plant & vehicles
entity("tools", "plant", "Tool", "Tools & plant", [
    T("name", req=True, search=True), S("tcat", "Category", [{"value": v, "label": v.replace("_", " ").capitalize()} for v in (
        "hand_tool", "power_tool", "crimping", "cable_pulling", "lifting", "ladder_scaffold", "safety_equipment", "other")]),
    T("make"), T("serial_no"), M("value", hide="cost"), R("store_id", "Kept at", "stores"), T("issued_to", "Issued to"), DT("issued_on"),
    DT("expected_return"), PROJECT(),
], icon="wrench", number={"prefix": "T", "kind": "plain"},
    status={"field": "status", "states": st(("available", "Available", "green"), ("issued", "Issued", "blue"), ("repair", "Under repair", "amber"), ("lost", "Lost", "red"), ("scrapped", "Scrapped", "gray"))},
    list=["code", "name", "tcat", "issued_to", "project_id", "expected_return", "status"])

entity("vehicles", "plant", "Vehicle", "Vehicles", [
    T("reg_no", "Registration no.", req=True), S("vtype", "Type", [{"value": v, "label": v.capitalize()} for v in ("truck", "pickup", "car", "two_wheeler", "crane", "hydra", "jcb")]),
    T("make_model", "Make / model"), B("owned", default=True), DT("insurance_until", req=True), DT("fitness_until"), DT("permit_until"), DT("puc_until", "PUC until"),
    T("driver_name", "Driver"), DT("driver_licence_until", "Driver licence until"), N("odometer", "Odometer", "km"),
], icon="truck", title="reg_no",
    status={"field": "status", "states": st(("active", "Active", "green"), ("repair", "Under repair", "amber"), ("sold", "Sold", "gray"))},
    list=["reg_no", "vtype", "insurance_until", "fitness_until", "puc_until", "driver_licence_until", "status"])

entity("trips", "plant", "Trip", "Trips", [
    R("vehicle_id", "Vehicle", "vehicles", req=True, child=True), DT("date", req=True), T("from_place", "From"), T("to_place", "To"), PROJECT(),
    T("purpose"), T("driver"), N("odo_start", "Odometer start"), N("odo_end", "Odometer end"), N("km", calc="max(odo_end - odo_start, 0)", ro=True),
    N("fuel_litres", "Fuel", "litres"), M("fuel_cost", "Fuel cost"),
], icon="route", title="date", list=["date", "vehicle_id", "from_place", "to_place", "project_id", "km"])

entity("hires", "plant", "Equipment hire", "Crane & equipment hire", [
    T("equipment", req=True), R("vendor_id", "Vendor", "vendors"), PROJECT(), DT("from_date", req=True), DT("to_date"),
    S("unit", "Charged per", [{"value": v, "label": v} for v in ("day", "hour", "trip", "month")], default="day"), N("qty"), M("rate"),
    M("amount", calc="round(qty * rate, 2)", ro=True),
], icon="construction", title="equipment", list=["equipment", "vendor_id", "project_id", "from_date", "amount"])

# =========================================================================== Subcontractors & labour
entity("work_orders", "subcon", "Work order", "Subcontract work orders", [
    R("vendor_id", "Subcontractor", "vendors", req=True, child=True), PROJECT(req=True), TA("scope", req=True),
    L("lines", "Rates", [TA("description"), S("unit", "Unit", "units"), N("qty"), M("rate"), M("amount", calc="round(qty * rate, 2)", ro=True)]),
    M("total", calc="round(sum(lines.amount), 2)", ro=True), P("retention_pct", "Retention", default=5), P("tds_pct", "TDS", default=1),
    DT("start"), DT("end"),
], icon="file-badge", number={"doc": "WO"}, title="code", project=True, branch=True,
    status={"field": "status", "states": st(("draft", "Draft", "gray"), ("pending_approval", "Waiting for approval", "amber"), ("approved", "Approved", "teal"),
            ("rejected", "Rejected", "red"), ("active", "Active", "blue"), ("completed", "Completed", "green"), ("closed", "Closed", "gray"))},
    approval={"amount": "total"}, actions={"start": {"label": "Start work", "from": ["approved"], "to": "active", "perm": "w"},
                                            "complete": {"label": "Mark completed", "from": ["active"], "to": "completed", "perm": "w"}},
    list=["code", "vendor_id", "project_id", "total", "status"], portal={"subcontractor": "vendor_id"})

entity("sc_bills", "subcon", "Subcontractor bill", "Subcontractor bills", [
    R("work_order_id", "Work order", "work_orders", req=True, child=True), R("vendor_id", "Subcontractor", "vendors", req=True), PROJECT(),
    DT("period_to", req=True),
    L("lines", "Measurements", [TA("description"), S("unit", "Unit", "units"), N("prev_qty", "Previous"), N("this_qty", "This bill"), M("rate"),
      M("amount", calc="round(this_qty * rate, 2)", ro=True)]),
    M("gross", calc="round(sum(lines.amount), 2)", ro=True), P("retention_pct", "Retention", default=5),
    M("retention", calc="round(gross * retention_pct / 100, 2)", ro=True), P("tds_pct", "TDS", default=1),
    M("tds", "TDS", calc="round(gross * tds_pct / 100, 2)", ro=True), M("advance_recovery"), M("material_recovery", "Material issued (recovery)"),
    M("penalty"), M("net", calc="round(gross - retention - tds - advance_recovery - material_recovery - penalty, 2)", ro=True), M("paid", ro=True),
], icon="file-check-2", number={"prefix": "SB", "kind": "year"}, title="code", project=True,
    status={"field": "status", "states": st(("draft", "Submitted", "blue"), ("pending_approval", "Waiting for approval", "amber"), ("approved", "Approved", "teal"),
            ("rejected", "Rejected", "red"), ("paid", "Paid", "green"))},
    approval={"amount": "net"}, list=["code", "vendor_id", "work_order_id", "period_to", "gross", "net", "status"], portal={"subcontractor": "vendor_id"})

entity("workers", "subcon", "Worker", "Workers", [
    T("name", req=True, search=True), PH(), S("trade", "Trade", "trades"), R("contractor_id", "Labour contractor (blank = own)", "vendors"),
    T("id_type", "ID type", default="Aadhaar"), T("id_last4", "ID last 4 digits", help="Only the last 4 digits are kept"),
    T("permit_no", "Wireman permit / competency no."), DT("permit_valid_until", "Permit valid until"), DT("medical_fit_until", "Medically fit until"),
    DT("induction_on", "Safety induction on"), T("bocw_no", "BOCW no."), T("esi_no", "ESI no."), T("uan", "PF UAN"),
    M("daily_wage", "Daily wage", hide="salary"), FILE("photo"), B("active", default=True),
], icon="users-round", number={"prefix": "W", "kind": "plain"}, list=["code", "name", "trade", "contractor_id", "permit_valid_until", "medical_fit_until", "active"],
    portal={"subcontractor": "contractor_id"})

entity("labour_attendance", "site", "Labour attendance", "Labour attendance", [
    PROJECT(req=True), DT("date", req=True), R("worker_id", "Worker", "workers", req=True),
    S("present", "Attendance", [{"value": "present", "label": "Present"}, {"value": "half_day", "label": "Half day"}, {"value": "absent", "label": "Absent"}], default="present"),
    T("in_time", "In"), T("out_time", "Out"), N("ot_hours", "Overtime", "h"), GEO(), FILE("photo"),
], icon="user-check", title="date", sort="-date", project=True, list=["date", "project_id", "worker_id", "present", "in_time", "out_time"],
    portal={"subcontractor": "worker"})

# =========================================================================== Safety
entity("permits", "hse", "Permit to work", "Permits to work", [
    PROJECT(req=True), S("ptype", "Permit type", "permit_types", req=True, filter=True), T("location", req=True), T("equipment", "Equipment / circuit"),
    TA("description", "Work to be done", req=True),
    MS("hazards", "Hazards", [{"value": v, "label": v.replace("_", " ").capitalize()} for v in ("electric_shock", "arc_flash", "fall", "fire", "toxic_gas", "cave_in", "induced_voltage", "heat")]),
    L("precautions", "Precautions", [T("check"), B("done")], default=[{"check": c, "done": False} for c in (
        "Circuit isolated and locked out", "Tested dead with approved tester", "Earthed on both sides", "Danger boards and barricades",
        "PPE checked (gloves, arc-rated clothing, helmet, shoes)", "Rescue plan and first-aid ready")]),
    L("isolations", "Isolation points (LOTO)", [T("point"), T("lock_no", "Lock no."), T("tag_no", "Tag no."), T("locked_by")]),
    R("authorised_person_id", "Authorised person", "users", req=True), DTM("valid_from", req=True), DTM("valid_to", req=True),
    DTM("closed_at", ro=True), TA("closure_note", "Closure: work done, locks removed, people clear"),
], icon="shield-alert", number={"prefix": "PTW", "kind": "year"}, title="code", project=True,
    status={"field": "status", "states": st(("requested", "Requested", "blue"), ("approved", "Approved", "teal"), ("active", "Active", "amber"),
            ("suspended", "Suspended", "red"), ("closed", "Closed", "green"), ("cancelled", "Cancelled", "gray"))},
    actions={"approve": {"label": "Approve permit", "from": ["requested"], "to": "approved", "perm": "a", "not_self": True},
             "activate": {"label": "Start work", "from": ["approved"], "to": "active", "perm": "w", "need_lines_done": "precautions"},
             "suspend": {"label": "Stop work", "from": ["active"], "to": "suspended", "perm": "w", "reason": True},
             "resume": {"label": "Resume", "from": ["suspended"], "to": "active", "perm": "a"},
             "close": {"label": "Close permit", "from": ["active", "suspended"], "to": "closed", "perm": "w", "need": ["closure_note"]},
             "cancel": {"label": "Cancel", "from": ["requested", "approved"], "to": "cancelled", "perm": "w"}},
    list=["code", "project_id", "ptype", "location", "valid_from", "valid_to", "status"])

entity("authorised_persons", "hse", "Authorised person", "Authorised persons (HT work)", [
    R("user_id", "Staff member", "users"), R("worker_id", "Worker", "workers"), T("name", req=True),
    S("level", "Authorised for", [{"value": v, "label": v} for v in ("LT", "HT 11 kV", "HT 22 kV", "HT 33 kV", "EHV 110 kV")]),
    T("authorised_by"), DT("valid_until", req=True), FILE("certificate"),
], icon="badge-check", list=["name", "level", "authorised_by", "valid_until"])

entity("toolbox_talks", "hse", "Toolbox talk", "Toolbox talks", [
    PROJECT(req=True), DT("date", req=True), T("topic", req=True), T("conducted_by"),
    L("attendees", "Attendees", [T("name"), T("trade")]), N("count", "People", calc="count(attendees)", ro=True), FILES("photos"),
], icon="megaphone", title="topic", sort="-date", project=True, list=["date", "project_id", "topic", "count"])

entity("ppe_issues", "hse", "PPE issue", "PPE issued", [
    R("worker_id", "Worker", "workers", req=True), S("item", "PPE", [{"value": v, "label": l} for v, l in (("helmet", "Helmet"), ("shoes", "Safety shoes"),
      ("gloves_lt", "Electrical gloves (class 0)"), ("gloves_ht", "Electrical gloves (class 2+)"), ("arc_suit", "Arc-flash suit"), ("harness", "Full-body harness"),
      ("goggles", "Goggles / face shield"), ("reflective", "Reflective jacket"))]), N("qty", default=1), DT("date", req=True), PROJECT(),
], icon="hard-hat", title="item", list=["date", "worker_id", "item", "qty", "project_id"])

entity("incidents", "hse", "Incident", "Incidents & near-misses", [
    PROJECT(), DTM("occurred_at", "When", req=True), S("kind", "Type", "incident_kinds", req=True, filter=True), TA("description", req=True),
    T("person", "Person involved"), N("lost_days", "Days lost"), TA("root_cause"),
    L("actions", "Corrective actions", [T("action"), T("owner"), DT("due"), B("done")]),
], icon="siren", number={"prefix": "INC", "kind": "year"}, title="code",
    status={"field": "status", "states": st(("reported", "Reported", "red"), ("investigating", "Investigating", "amber"), ("closed", "Closed", "green"))},
    list=["code", "occurred_at", "kind", "project_id", "lost_days", "status"])

entity("hse_manhours", "hse", "Man-hours", "Man-hours", [
    PROJECT(req=True), T("month", "Month (YYYY-MM)", req=True), N("man_hours", "Man-hours", req=True),
], icon="timer", title="month", list=["project_id", "month", "man_hours"])

entity("trainings", "hse", "Training record", "Training records", [
    T("person", req=True), R("worker_id", "Worker", "workers"), R("user_id", "Staff", "users"),
    S("course", "Course", [{"value": v, "label": l} for v, l in (("electrical_safety", "Electrical safety"), ("first_aid", "First aid & CPR"), ("fire", "Fire safety"),
      ("height", "Work at height"), ("loto", "Lock-out / tag-out"), ("ht_operation", "HT switching operation"), ("induction", "Site induction"))]),
    DT("date", req=True), DT("valid_until"), FILE("certificate"),
], icon="graduation-cap", title="person", list=["person", "course", "date", "valid_until"])

# =========================================================================== Service & AMC
entity("installed_assets", "service", "Installed equipment", "Installed equipment", [
    R("account_id", "Client", "accounts", req=True, child=True, filter=True), T("site"), R("project_id", "Project", "projects", child=True),
    S("kind", "Equipment", "asset_kinds", req=True, filter=True), T("make"), T("model"), T("serial_no", "Serial no.", search=True), T("rating", "Rating"),
    DT("installed_on"), DT("warranty_until"), R("amc_id", "AMC", "amc_contracts"), T("location", "Location at site"),
    DT("last_service_on", ro=True), DT("next_service_on"), T("qr_token", "QR code", ro=True),
], icon="cpu", number={"prefix": "AST", "kind": "plain", "width": 5}, title="code", subtitle="kind",
    list=["code", "kind", "make", "rating", "account_id", "warranty_until", "next_service_on"], portal={"client": "account_id"})

entity("amc_contracts", "service", "AMC contract", "AMC contracts", [
    R("account_id", "Client", "accounts", req=True, child=True, filter=True), T("title", req=True), TA("scope"),
    RS("asset_ids", "Equipment covered", "installed_assets"), N("visits_per_year", "Visits per year", default=4),
    M("price", "Contract price (yearly, without GST)", req=True), S("billing", "Billing", [{"value": v, "label": v.replace("_", "-").capitalize()} for v in ("yearly", "half_yearly", "quarterly", "monthly")], default="quarterly"),
    DT("start", req=True), DT("end", req=True), N("response_hours", "Response within", "h", default=4), N("restore_hours", "Restore within", "h", default=24),
], icon="calendar-check-2", number={"doc": "AMC"}, title="title", branch=True,
    status={"field": "status", "states": st(("draft", "Draft", "gray"), ("active", "Active", "green"), ("expired", "Expired", "red"), ("renewed", "Renewed", "teal"), ("cancelled", "Cancelled", "gray"))},
    actions={"activate": {"label": "Activate (creates visits)", "from": ["draft"], "to": "active", "perm": "w"},
             "renew": {"label": "Mark renewed", "from": ["active", "expired"], "to": "renewed", "perm": "w"}},
    list=["code", "title", "account_id", "price", "start", "end", "status"], portal={"client": "account_id"})

entity("pm_jobs", "service", "Maintenance visit", "Maintenance visits", [
    R("amc_id", "AMC", "amc_contracts", child=True), R("account_id", "Client", "accounts", req=True, child=True), RS("asset_ids", "Equipment", "installed_assets"),
    DT("scheduled_on", req=True), R("technician_id", "Technician", "users", filter=True),
    L("checklist", "Checklist", [T("check"), S("result", "Result", [{"value": "ok", "label": "OK"}, {"value": "attention", "label": "Needs attention"}, {"value": "na", "label": "N/A"}]), T("remarks")],
      default=[{"check": c, "result": "", "remarks": ""} for c in ("Visual inspection & cleaning", "Tightness of terminations", "IR values recorded",
               "Earth pit resistance", "Oil level / BDV (transformer)", "Protection relay & breaker operation", "Thermography of joints")]),
    L("parts", "Parts used", [R("item_id", "Item", "items"), N("qty")]), FILES("photos"), TA("report", "Report"),
    T("signed_by", "Customer signature (name)"), DTM("completed_at", ro=True),
], icon="calendar-clock", number={"prefix": "PM", "kind": "year"}, title="code", sort="scheduled_on",
    status={"field": "status", "states": st(("scheduled", "Scheduled", "blue"), ("in_progress", "In progress", "amber"), ("done", "Done", "green"), ("missed", "Missed", "red"))},
    actions={"start": {"label": "Start visit", "from": ["scheduled"], "to": "in_progress", "perm": "w"},
             "complete": {"label": "Complete visit", "from": ["in_progress", "scheduled"], "to": "done", "perm": "w", "need": ["signed_by"]}},
    list=["code", "account_id", "scheduled_on", "technician_id", "status"], portal={"client": "account_id"})

entity("tickets", "service", "Service request", "Service requests", [
    R("account_id", "Client", "accounts", child=True, filter=True), R("asset_id", "Equipment", "installed_assets", child=True), R("project_id", "Project", "projects"),
    S("channel", "Received via", [{"value": v, "label": l} for v, l in (("portal", "Client portal"), ("phone", "Phone"), ("whatsapp", "WhatsApp"),
      ("website", "Website"), ("qr", "Equipment QR"), ("email", "Email"), ("staff", "Staff"))], default="staff"),
    S("category", "Category", [{"value": v, "label": l} for v, l in (("breakdown", "Breakdown"), ("maintenance", "Maintenance"), ("warranty", "Warranty"),
      ("testing", "Testing"), ("other", "Other"))], default="breakdown", filter=True),
    S("priority", "Priority", "ticket_priority", default="normal", filter=True), T("title", req=True, search=True), TA("description"), FILES("photos"),
    T("contact_name", "Contact"), PH("contact_phone", "Contact phone"), R("assigned_to", "Assigned to", "users", filter=True),
    DTM("respond_by", "Reply by", ro=True), DTM("restore_by", "Fix by", ro=True), DTM("first_response_at", ro=True), DTM("resolved_at", ro=True),
    B("sla_breached", "Past target", ro=True), L("parts", "Parts used", [R("item_id", "Item", "items"), N("qty")]),
    TA("resolution"), N("rating", "Customer rating (1–5)"), TA("feedback"),
], icon="life-buoy", number={"prefix": "TKT", "kind": "year"}, title="title", branch=True,
    status={"field": "status", "states": st(("new", "New", "blue"), ("assigned", "Assigned", "violet"), ("in_progress", "In progress", "amber"),
            ("waiting_customer", "Waiting for customer", "gray"), ("resolved", "Resolved", "green"), ("closed", "Closed", "gray"), ("reopened", "Reopened", "red"))},
    actions={"start": {"label": "Start work", "from": ["new", "assigned", "reopened"], "to": "in_progress", "perm": "w"},
             "wait": {"label": "Waiting for customer", "from": ["in_progress"], "to": "waiting_customer", "perm": "w"},
             "resolve": {"label": "Resolve", "from": ["in_progress", "waiting_customer", "assigned", "new", "reopened"], "to": "resolved", "perm": "w", "need": ["resolution"]},
             "close": {"label": "Close", "from": ["resolved"], "to": "closed", "perm": "w"},
             "reopen": {"label": "Reopen", "from": ["resolved", "closed"], "to": "reopened", "perm": "w"}},
    list=["code", "title", "account_id", "priority", "assigned_to", "restore_by", "status"], portal={"client": "account_id"})

# =========================================================================== Finance
INV_LINE = [TA("description", req=True), T("hsn", "HSN / SAC"), N("qty", default=1), S("unit", "Unit", "units", default="nos"), M("rate"),
            S("gst_rate", "GST %", "gst_rates", default="18"), M("amount", calc="round(qty * rate, 2)", ro=True),
            M("gst", "GST", calc="round(qty * rate * gst_rate / 100, 2)", ro=True)]
entity("invoices", "finance", "Invoice", "Invoices", [
    S("itype", "Type", [{"value": v, "label": l} for v, l in (("tax_invoice", "Tax invoice"), ("proforma", "Proforma"), ("ra_bill", "RA bill invoice"),
      ("amc", "AMC invoice"), ("service", "Service invoice"))], default="tax_invoice", filter=True),
    R("account_id", "Client", "accounts", req=True, filter=True, child=True), PROJECT(), R("ra_bill_id", "RA bill", "ra_bills"), R("amc_id", "AMC", "amc_contracts", child=True),
    DT("date", req=True), DT("due_date"), T("place_of_supply", default="Tamil Nadu (33)"), B("interstate", "Inter-state (IGST)"),
    L("lines", "Lines", INV_LINE),
    M("subtotal", calc="round(sum(lines.amount), 2)", ro=True), M("gst", "GST", calc="round(sum(lines.gst), 2)", ro=True),
    M("cgst", "CGST", calc="if(interstate, 0, round(gst / 2, 2))", ro=True), M("sgst", "SGST", calc="if(interstate, 0, round(gst - cgst, 2))", ro=True),
    M("igst", "IGST", calc="if(interstate, gst, 0)", ro=True), M("total", calc="round(subtotal + gst, 2)", ro=True),
    M("retention", "Retention held"), M("tds_expected", "TDS expected"), M("receivable", calc="round(total - retention - tds_expected, 2)", ro=True),
    M("paid", "Received", ro=True), M("balance", calc="round(receivable - paid, 2)", ro=True),
    T("irn", "IRN (e-invoice)"), T("eway_bill", "E-way bill"),
], icon="receipt", number={"doc": "INV"}, title="code", branch=True,
    status={"field": "status", "states": st(("draft", "Draft", "gray"), ("issued", "Issued", "blue"), ("part_paid", "Part paid", "amber"), ("paid", "Paid", "green"), ("cancelled", "Cancelled", "red"))},
    actions={"issue": {"label": "Issue invoice", "from": ["draft"], "to": "issued", "perm": "w", "confirm": "After issuing, the invoice can't be edited (use a credit note)."},
             "cancel": {"label": "Cancel", "from": ["issued", "draft"], "to": "cancelled", "perm": "a", "reason": True}},
    list=["code", "itype", "account_id", "date", "total", "balance", "due_date", "status"], portal={"client": "account_id"}, locked=["issued", "part_paid", "paid", "cancelled"])

entity("receipts", "finance", "Receipt", "Receipts", [
    R("account_id", "Client", "accounts", req=True, child=True, filter=True), DT("date", req=True), M("amount", req=True),
    S("mode", "Mode", "pay_modes", default="neft"), T("reference", "UTR / cheque no."), R("bank_account_id", "Received into", "bank_accounts"),
    M("tds", "TDS deducted by client"),
    L("allocations", "Against invoices", [R("invoice_id", "Invoice", "invoices"), M("amount")]), TA("notes"), FILE("proof", "Payment proof"),
], icon="badge-indian-rupee", number={"doc": "RCT"}, title="code", branch=True,
    status={"field": "status", "states": st(("pending", "Waiting for confirmation", "amber"), ("confirmed", "Confirmed", "green"), ("rejected", "Not received", "red"))},
    actions={"confirm": {"label": "Confirm received", "from": ["pending"], "to": "confirmed", "perm": "w"},
             "reject": {"label": "Not received", "from": ["pending"], "to": "rejected", "perm": "w", "reason": True}},
    list=["code", "account_id", "date", "amount", "mode", "reference", "status"], portal={"client": "account_id"}, locked=["confirmed"])

entity("vendor_payments", "finance", "Vendor payment", "Vendor payments", [
    R("vendor_id", "Vendor", "vendors", req=True, child=True), R("vendor_bill_id", "Vendor bill", "vendor_bills", child=True),
    R("sc_bill_id", "Subcontractor bill", "sc_bills", child=True), DT("date", req=True), M("amount", req=True), M("tds"),
    S("mode", "Mode", "pay_modes", default="neft"), T("reference", "UTR / cheque no."), R("bank_account_id", "Paid from", "bank_accounts"), TA("notes"),
], icon="banknote", number={"doc": "PAY"}, title="code", branch=True,
    status={"field": "status", "states": st(("draft", "Draft", "gray"), ("pending_approval", "Waiting for approval", "amber"), ("approved", "Approved", "teal"),
            ("rejected", "Rejected", "red"), ("paid", "Paid", "green"))},
    approval={"amount": "amount"}, actions={"pay": {"label": "Mark paid", "from": ["approved"], "to": "paid", "perm": "w", "need": ["reference"]}},
    list=["code", "vendor_id", "date", "amount", "mode", "status"], portal={"vendor": "vendor_id", "subcontractor": "vendor_id"}, locked=["paid"])

entity("expenses", "finance", "Expense", "Expenses", [
    DT("date", req=True), S("category", "Category", "expense_cats", req=True, filter=True), PROJECT(), R("vehicle_id", "Vehicle", "vehicles"),
    R("employee_id", "Spent by", "users"), M("amount", req=True), M("gst"), TA("description", req=True), FILE("bill", "Bill photo"),
    R("paid_from", "Paid from", "bank_accounts"),
], icon="wallet", number={"prefix": "EXP", "kind": "year"}, title="description", project=True, branch=True,
    status={"field": "status", "states": st(("draft", "Draft", "gray"), ("pending_approval", "Waiting for approval", "amber"), ("approved", "Approved", "teal"),
            ("rejected", "Rejected", "red"), ("reimbursed", "Paid / reimbursed", "green"))},
    approval={"amount": "amount"}, actions={"reimburse": {"label": "Mark paid", "from": ["approved"], "to": "reimbursed", "perm": "w"}},
    list=["code", "date", "category", "project_id", "employee_id", "amount", "status"])

entity("bank_accounts", "finance", "Cash / bank account", "Cash & bank accounts", [
    T("name", req=True), S("kind", "Kind", [{"value": v, "label": l} for v, l in (("bank", "Bank account"), ("cash", "Cash"), ("upi", "UPI"), ("petty_cash", "Site petty cash"))], default="bank"),
    T("bank"), T("account_last4", "Account no. (last 4)"), T("ifsc", "IFSC"), T("upi_id", "UPI ID"), M("opening_balance", "Opening balance"),
    DT("opening_date"), PROJECT(), R("custodian_id", "Custodian", "users"), M("balance", ro=True), B("active", default=True),
], icon="landmark", branch=True, list=["name", "kind", "bank", "account_last4", "balance", "active"])

entity("transfers", "finance", "Transfer", "Transfers", [
    R("from_account", "From", "bank_accounts", req=True), R("to_account", "To", "bank_accounts", req=True), M("amount", req=True), DT("date", req=True), T("reference"),
], icon="arrow-right-left", number={"prefix": "TRF", "kind": "year"}, title="code", list=["code", "date", "from_account", "to_account", "amount"])

entity("credit_notes", "finance", "Credit note", "Credit notes", [
    R("invoice_id", "Invoice", "invoices", req=True, child=True), R("account_id", "Client", "accounts"), DT("date", req=True), M("amount", req=True),
    M("gst", "GST portion"), TA("reason", req=True),
], icon="undo-2", number={"doc": "CN"}, title="code", list=["code", "invoice_id", "date", "amount"])

# =========================================================================== HR & payroll
entity("employees", "hr", "Employee", "Employees", [
    T("name", req=True, search=True), R("user_id", "Login", "users"), T("designation"), S("department", "Department", "departments", filter=True),
    PH(), EM(), DT("joined_on"), S("employment", "Employment", [{"value": v, "label": v.replace("_", " ").capitalize()} for v in ("permanent", "probation", "contract", "trainee")], default="permanent"),
    R("reports_to", "Reports to", "employees"), T("shift", default="General 9:30–18:30"), R("work_site", "Usual work site (project)", "projects"),
    M("monthly_ctc", "Monthly CTC", hide="salary"), M("basic", "Basic + DA", hide="salary"), M("hra", "HRA", hide="salary"), M("allowances", "Other allowances", hide="salary"),
    B("pf", "PF applicable"), B("esi", "ESI applicable"), B("pt", "Professional tax"),
    T("bank_account", "Salary account no.", hide="salary"), T("ifsc", "IFSC", hide="salary"),
    MS("skills", "Skills", [{"value": v, "label": v.upper() if len(v) <= 3 else v.replace("_", " ").capitalize()} for v in ("lt", "ht", "substation", "testing", "autocad", "estimation", "liaison", "solar", "plc", "safety")]),
    T("licence_no", "Licence (wireman / supervisor)"), DT("licence_valid_until"), FILES("documents"),
], icon="id-card", number={"prefix": "EMP", "kind": "plain"}, branch=True,
    status={"field": "status", "states": st(("active", "Active", "green"), ("notice", "On notice", "amber"), ("left", "Left", "gray"))},
    list=["code", "name", "designation", "department", "phone", "joined_on", "status"])

entity("attendance", "hr", "Attendance", "Attendance", [
    R("employee_id", "Employee", "employees", req=True, child=True), DT("date", req=True), DTM("check_in"), DTM("check_out"),
    GEO("in_gps", "Check-in location"), GEO("out_gps", "Check-out location"), R("project_id", "At site", "projects"), R("branch_id_at", "At office", "branches"),
    N("distance_m", "Distance from site", "m", ro=True), S("flag", "Flag", [{"value": v, "label": l} for v, l in (("", "—"), ("outside", "Outside the site area"),
      ("late", "Late"), ("no_checkout", "No check-out"))], ro=True, help="Flags are for review only, never penalties"),
    N("hours", calc="if(check_out, round(days(check_out, check_in) * 24, 2), 0)", ro=True),
], icon="map-pin-check", title="date", sort="-date", list=["date", "employee_id", "check_in", "check_out", "flag"])
# hours are set by the server from the timestamps (the formula language works in whole days)
E["attendance"]["fields"] = [f for f in E["attendance"]["fields"] if f["k"] != "hours"] + [N("hours", ro=True)]

entity("leaves", "hr", "Leave", "Leave", [
    R("employee_id", "Employee", "employees", req=True, child=True), S("ltype", "Type", [{"value": v, "label": l} for v, l in (("casual", "Casual"), ("sick", "Sick"),
      ("earned", "Earned"), ("comp_off", "Comp-off"), ("unpaid", "Unpaid"))], default="casual"),
    DT("from_date", req=True), DT("to_date", req=True), N("days", calc="days(to_date, from_date) + 1", ro=True), TA("reason"),
], icon="calendar-x", title="employee_id", status={"field": "status", "states": DRAFT_APPROVAL}, approval={"amount": None},
    list=["employee_id", "ltype", "from_date", "to_date", "days", "status"])

entity("payroll_runs", "hr", "Payroll", "Payroll", [
    T("month", "Month (YYYY-MM)", req=True),
    L("lines", "Payslips", [R("employee_id", "Employee", "employees"), N("days_paid", "Days paid"), M("gross", hide="salary"), M("pf", "PF", hide="salary"),
      M("esi", "ESI", hide="salary"), M("pt", "PT", hide="salary"), M("tds", "TDS", hide="salary"), M("advance", "Advance recovery", hide="salary"),
      M("net", calc="round(gross - pf - esi - pt - tds - advance, 2)", ro=True, hide="salary")], hide="salary"),
    M("gross_total", calc="round(sum(lines.gross), 2)", ro=True, hide="salary"), M("net_total", calc="round(sum(lines.net), 2)", ro=True, hide="salary"),
], icon="hand-coins", title="month", branch=True, status={"field": "status", "states": DRAFT_APPROVAL + st(("paid", "Paid", "green"))},
    approval={"amount": "net_total"}, actions={"pay": {"label": "Mark paid", "from": ["approved"], "to": "paid", "perm": "w"}},
    list=["month", "gross_total", "net_total", "status"])

entity("advances", "hr", "Salary advance", "Salary advances", [
    R("employee_id", "Employee", "employees", req=True), DT("date", req=True), M("amount", req=True, hide="salary"), TA("reason"),
    M("monthly_recovery", "Recover per month", hide="salary"), M("recovered", ro=True, hide="salary"),
], icon="piggy-bank", title="employee_id", status={"field": "status", "states": DRAFT_APPROVAL + st(("closed", "Recovered", "gray"))}, approval={"amount": "amount"},
    list=["employee_id", "date", "amount", "recovered", "status"])

entity("job_applications", "hr", "Job application", "Job applications", [
    R("job_id", "Opening", "jobs", child=True), T("name", req=True), PH(), EM(), N("experience_years", "Experience", "years"), T("current_role"),
    FILE("cv", "CV"), TA("message"),
], icon="file-user", status={"field": "status", "states": st(("new", "New", "blue"), ("shortlisted", "Shortlisted", "violet"), ("interview", "Interview", "amber"),
    ("offered", "Offered", "teal"), ("hired", "Hired", "green"), ("rejected", "Not selected", "gray"))},
    list=["name", "job_id", "phone", "experience_years", "status", "created_at"])

# =========================================================================== Documents & compliance
entity("documents", "documents", "Document", "Documents", [
    T("name", req=True, search=True), S("category", "Category", [{"value": v, "label": v.replace("_", " ").capitalize()} for v in (
        "drawing", "approval", "test_certificate", "warranty", "manual", "contract", "correspondence", "photo", "other")]),
    R("project_id", "Project", "projects", child=True), R("account_id", "Client", "accounts", child=True), FILE("file", req=True), T("version", default="1"),
    DT("valid_until"), B("share_with_client", "Show in client portal"), TA("notes"),
], icon="file", list=["name", "category", "project_id", "account_id", "version", "share_with_client", "created_at"],
    portal={"client": "account_id_or_project"})

entity("compliance_items", "compliance", "Compliance item", "Compliance register", [
    T("name", req=True), S("category", "Category", [{"value": v, "label": l} for v, l in (("licence", "Licence"), ("tax", "Tax / statutory"), ("insurance", "Insurance"),
      ("vehicle", "Vehicle"), ("iso", "ISO / audit"), ("other", "Other"))]),
    T("authority"), T("number", "Number / policy no."), DT("valid_from"), DT("valid_until", req=True), N("remind_days", "Remind before", "days", default=30),
    R("owner_id", "Responsible", "users"), FILE("file"), TA("notes"),
], icon="scale", list=["name", "category", "number", "valid_until", "owner_id"])

entity("templates", "documents", "Template", "Templates", [
    T("name", req=True), S("kind", "Kind", [{"value": v, "label": l} for v, l in (("terms", "Proposal terms"), ("letter", "Letter"), ("checklist", "Checklist"), ("test_format", "Test format"))]),
    MD("body", req=True),
], icon="file-cog", list=["name", "kind", "updated_at"])

entity("tasks", "tasks", "Task", "Tasks", [
    T("title", req=True, search=True), TA("description"), R("assigned_to", "Assigned to", "users", filter=True), DT("due_on"),
    S("priority", "Priority", "ticket_priority", default="normal"), R("project_id", "Project", "projects", child=True), T("link", "Link"),
], icon="square-check", title="title", sort="due_on",
    status={"field": "status", "states": st(("open", "Open", "blue"), ("in_progress", "In progress", "amber"), ("done", "Done", "green"))},
    list=["title", "assigned_to", "due_on", "priority", "project_id", "status"])

# =========================================================================== Website content
PUB = dict(nav="Website")
entity("services", "cms", "Service", "Services (website)", [
    T("title", req=True), T("slug", req=True), S("service_key", "Quote form service", "services"), T("icon", "Icon name", default="zap"),
    TA("summary", req=True), MD("body", "Page text"), L("scope", "What we do", [T("item")]), L("standards", "Standards followed", [T("code"), T("title")]),
    L("faqs", "FAQs", [T("q", "Question"), TA("a", "Answer")]), MS("sectors", "Sectors", "sectors"), N("order", default=10), B("published", default=True),
    T("seo_title", "SEO title"), TA("seo_description", "SEO description"), FILE("image"),
], icon="zap", title="title", sort="order", list=["title", "slug", "order", "published"], **PUB)

entity("products", "cms", "Product", "Products (website)", [
    T("name", req=True), T("slug", req=True), S("category", "Category", "product_cats", filter=True), TA("summary"),
    L("specs", "Specifications", [T("label"), T("value")]), T("makes", "Makes we supply"), FILE("image"), FILE("datasheet"),
    N("order", default=10), B("published", default=True),
], icon="boxes", title="name", sort="order", list=["name", "category", "makes", "published"], **PUB)

entity("industries", "cms", "Industry", "Industries (website)", [
    T("name", req=True), T("slug", req=True), S("sector", "Sector", "sectors"), TA("summary"), MD("body"),
    L("needs", "What they need", [T("item")]), N("order", default=10), B("published", default=True), FILE("image"),
], icon="factory", title="name", sort="order", list=["name", "slug", "published"], **PUB)

entity("testimonials", "cms", "Testimonial", "Testimonials", [
    TA("quote", req=True), T("person", req=True), T("designation"), T("company"), R("account_id", "Client", "accounts"), R("project_id", "Project", "projects"),
    T("video_url", "Video link"), N("rating", "Rating (1–5)"), B("permission", "Client gave permission to publish", req=True), B("published"),
], icon="quote", title="person", list=["person", "company", "permission", "published"], **PUB)

entity("gallery", "cms", "Gallery item", "Gallery", [
    T("title", req=True), S("category", "Category", "gallery_cats", filter=True), R("project_id", "Project", "projects"), FILE("image"),
    T("video_url", "Video link"), FILE("before_image", "Before photo"), FILE("after_image", "After photo"), T("series", "Progress series name"),
    DT("taken_on"), N("order", default=10), B("published", default=True),
], icon="images", title="title", sort="order", list=["title", "category", "project_id", "taken_on", "published"], **PUB)

entity("insights", "cms", "Insights post", "Insights", [
    T("title", req=True), T("slug", req=True), TA("excerpt"), MD("body"), FILE("cover"), MS("tags", "Tags", "services"), T("author"),
    DTM("publish_at", "Publish at"), T("seo_title", "SEO title"), TA("seo_description", "SEO description"),
], icon="newspaper", title="title", sort="-publish_at",
    status={"field": "status", "states": st(("draft", "Draft", "gray"), ("scheduled", "Scheduled", "amber"), ("published", "Published", "green"))},
    list=["title", "author", "publish_at", "status"], **PUB)

entity("faqs", "cms", "FAQ", "FAQs", [
    T("question", req=True), TA("answer", req=True), S("category", "Topic", [{"value": v, "label": v.replace("_", " ").capitalize()} for v in ("general", "ht_connection", "lt_connection", "approvals", "amc", "solar", "safety", "billing")]),
    N("order", default=10), B("published", default=True),
], icon="circle-help", title="question", sort="order", list=["question", "category", "published"], **PUB)

entity("downloads", "cms", "Download / guide", "Guides & downloads", [
    T("title", req=True), T("slug", req=True), S("kind", "Kind", "doc_kinds"), TA("summary"), MD("body", "Guide text"), FILE("file"),
    B("gated", "Ask for name and phone before download"), N("order", default=10), B("published", default=True),
], icon="download", title="title", sort="order", list=["title", "kind", "gated", "published"], **PUB)

entity("jobs", "cms", "Job opening", "Careers", [
    T("title", req=True), S("department", "Department", "departments"), T("location", default="Perundurai"), T("jtype", "Type", default="Full-time"),
    MD("description"), MD("requirements"), DT("closes_on"), B("published", default=True),
], icon="briefcase-business", title="title", list=["title", "department", "location", "closes_on", "published"], **PUB)

entity("town_pages", "cms", "Town page", "Town pages", [
    T("town", req=True), T("slug", req=True), TA("intro"), B("published"),
], icon="map", title="town", list=["town", "slug", "published"], help="Publish a town only when there are real projects there.", **PUB)

# =========================================================================== system (not edited through the generic screens)
entity("approvals", "approvals", "Approval", "Approvals", [
    T("doc_entity", "Record type", ro=True), T("doc_id", ro=True), T("doc_code", "Record", ro=True), T("title", ro=True), M("amount", ro=True),
    R("requested_by", "Asked by", "users", ro=True), F("approver_roles", "json", "Approvers", ro=True), T("reason", ro=True),
    R("decided_by", "Decided by", "users", ro=True), DTM("decided_at", ro=True),
], icon="stamp", title="title", readonly=True, nav="Home",
    status={"field": "status", "states": st(("pending", "Waiting", "amber"), ("approved", "Approved", "green"), ("rejected", "Rejected", "red"), ("cancelled", "Cancelled", "gray"))},
    list=["doc_code", "title", "amount", "requested_by", "status", "created_at"])


# --------------------------------------------------------------------------- derived structure
def _finish():
    for key, e in E.items():
        e.setdefault("search", [f["k"] for f in e["fields"] if f.get("search")] or [e.get("title", "name")])
        e.setdefault("filters", [f["k"] for f in e["fields"] if f.get("filter")])
        e["children"] = []
        if e.get("status"):
            e["status"].setdefault("default", e["status"]["states"][0]["value"])
        if e.get("approval"):
            e["approval"] = {"from": ["draft", "rejected"], "pending": "pending_approval", "approved": "approved",
                             "rejected": "rejected", **e["approval"]}
    for key, e in E.items():
        for f in e["fields"]:
            if f.get("child") and f["t"] == "ref" and f["ref"] in E:
                E[f["ref"]]["children"].append({"entity": key, "field": f["k"], "label": e["plural"]})


_finish()

NAV_ORDER = ["Home", "Sales", "Estimation", "Tenders", "Projects", "Liaison", "Quality & testing", "Procurement", "Stores",
             "Tools & vehicles", "Subcontractors & labour", "Safety", "Service & AMC", "Finance", "HR & payroll", "Documents",
             "Website", "Settings"]


def field(entity_key, k):
    for f in E[entity_key]["fields"]:
        if f["k"] == k:
            return f
    return None


def meta_for(role, hidden_tags, perms):
    """Registry as one role sees it: modules they can read, hidden fields removed."""
    out = {}
    for key, e in E.items():
        p = perms.get(e["module"], "")
        if "r" not in p and "w" not in p:
            continue
        d = dict(e)
        d["fields"] = [_strip(f, hidden_tags) for f in e["fields"] if f.get("hide") not in hidden_tags]
        d["list"] = [k for k in e["list"] if any(f["k"] == k for f in d["fields"]) or k in ("code", "created_at", "status", "created_by")]
        d["perm"] = p
        out[key] = d
    return out


def _strip(f, hidden_tags):
    if f["t"] == "lines":
        f = dict(f)
        f["fields"] = [x for x in f["fields"] if x.get("hide") not in hidden_tags]
    return f
