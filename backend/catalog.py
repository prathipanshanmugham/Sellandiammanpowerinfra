"""Option lists shared by the server, the staff app and the website (served in /api/meta and /api/public/meta)."""


def o(*pairs):
    """o(("value", "Label"), ...) or o("value", ...) -> [{"value", "label"}]"""
    out = []
    for p in pairs:
        if isinstance(p, tuple):
            out.append({"value": p[0], "label": p[1]})
        else:
            out.append({"value": p, "label": p.replace("_", " ").capitalize()})
    return out


SERVICES = o(
    ("ht_substation", "HT substations (11/22/33 kV)"),
    ("lt_electrification", "LT electrification"),
    ("ht_lt_panels", "HT & LT panels"),
    ("transformers", "Transformer supply & erection"),
    ("cabling", "HT & LT cabling"),
    ("earthing_lps", "Earthing & lightning protection"),
    ("dg_ups", "DG sets & UPS"),
    ("street_lighting", "Street & area lighting"),
    ("solar_epc", "Solar EPC"),
    ("ev_charging", "EV charging"),
    ("liaison", "TNPDCL & CEIG liaison"),
    ("testing", "Testing & commissioning"),
    ("amc", "AMC and O&M"),
    ("energy_audit", "Energy audit"),
    ("other", "Something else"),
)
SECTORS = o(("factory", "Factories & industry"), ("commercial", "Commercial buildings"),
            ("residential", "Residential towers & apartments"), ("hospital", "Hospitals"),
            ("education", "Schools & colleges"), ("infrastructure", "Infrastructure & utilities"),
            ("government", "Government"), ("warehouse", "Warehouses & logistics"), ("home", "Homes & villas"),
            ("other", "Other"))
SUPPLY = o(("LT", "LT (low tension)"), ("HT", "HT (high tension)"), ("not_sure", "Not sure"))
VOLTAGES = o(("415V", "415 V (LT)"), ("11kV", "11 kV"), ("22kV", "22 kV"), ("33kV", "33 kV"), ("110kV", "110 kV"))
TIMELINE = o(("now", "Immediately"), ("1_3m", "Within 1–3 months"), ("3_6m", "3–6 months"), ("later", "Later / planning"))
LEAD_SOURCES = o(
    ("quote_wizard", "Website quote"), ("survey_booking", "Survey booking"), ("calculator", "Calculator result"),
    ("bill_review", "Bill review"), ("tender_invite", "Tender / BOQ invite"), ("callback", "Call-back request"),
    ("whatsapp", "WhatsApp"), ("phone", "Phone call"), ("emergency", "Emergency breakdown"), ("amc_enquiry", "AMC enquiry"),
    ("download", "Gated download"), ("newsletter", "Newsletter"), ("referral", "Referral partner"),
    ("existing_client", "Existing client"), ("google_ads", "Google Ads"), ("meta_ads", "Meta (Facebook/Instagram)"),
    ("indiamart", "IndiaMART"), ("justdial", "JustDial"), ("email", "Email (enquiries@)"), ("qr", "QR code"),
    ("missed_call", "Missed call"), ("walk_in", "Walk-in"), ("exhibition", "Exhibition / event"), ("contact_form", "Contact form"),
    ("product_enquiry", "Product enquiry"), ("assistant", "Website assistant"), ("other", "Other"))
LEAD_STAGES = o(("new", "New"), ("contacted", "Contacted"), ("survey_scheduled", "Survey scheduled"),
                ("survey_done", "Survey done"), ("estimating", "Estimating"), ("quoted", "Quoted"),
                ("negotiation", "Negotiation"), ("won", "Won"), ("lost", "Lost"), ("on_hold", "On hold"))
LOST_REASONS = o(("price", "Price too high"), ("competitor", "Went with competitor"), ("timeline", "Timeline didn't suit"),
                 ("no_budget", "No budget / project dropped"), ("no_response", "No response"), ("scope", "Out of our scope"),
                 ("duplicate", "Duplicate / spam"), ("other", "Other"))
ACCOUNT_TYPES = o("factory", "commercial", "builder", ("consultant", "Consultant / architect firm"), "government",
                  "hospital", "education", "residential", "individual", "other")
ITEM_CATEGORIES = o(("material", "Material"), ("labour", "Labour"), ("tp", "Tools & plant"), ("overhead", "Overhead"),
                    ("subcontract", "Subcontract"))
ITEM_GROUPS = o(("cable", "Cables"), ("panel", "Panels"), ("transformer", "Transformers"), ("switchgear", "Switchgear"),
                ("earthing", "Earthing & LPS"), ("lighting", "Lighting"), ("conduit_tray", "Conduit & cable tray"),
                ("accessories", "Lugs, glands & accessories"), ("ev", "EV chargers"), ("solar", "Solar"),
                ("dg_ups", "DG & UPS"), ("apfc", "APFC & capacitors"), ("civil", "Civil works"), ("labour", "Labour"),
                ("tp", "Tools & plant"), ("other", "Other"))
UNITS = o("nos", "m", "km", "set", "lot", "kg", "sqm", "cum", "ls", "day", "hour", "trip", "pair", "box", "roll", "litre", "kVA", "kW", "job")
GST_RATES = o(("0", "0%"), ("5", "5%"), ("12", "12%"), ("18", "18%"), ("28", "28%"))
TENDER_PORTALS = o(("gem", "GeM"), ("tntenders", "Tamil Nadu tenders portal"), ("cppp", "CPPP"),
                   ("private", "Private / client"), ("other", "Other"))
PROJECT_STATUS = o("planned", "mobilising", "in_progress", "on_hold", "testing", "handed_over", "closed", "cancelled")
LIAISON_KINDS = o(("new_lt_service", "New LT service"), ("new_ht_service", "New HT service"), ("load_change", "Load change"),
                  ("tariff_change", "Tariff change"), ("name_transfer", "Name transfer"),
                  ("solar_net_metering", "Solar net metering"), ("ceig_drawing", "CEIG drawing approval"),
                  ("ceig_inspection", "CEIG inspection"), ("energisation", "Energisation"), ("other", "Other"))
LIAISON_STAGES = o(("prepared", "Documents prepared"), ("applied", "Applied"), ("feasibility", "Feasibility / inspection"),
                   ("estimate_paid", "Estimate paid"), ("drawing_approved", "Drawing approved"), ("works_done", "Works done"),
                   ("inspection", "Final inspection"), ("energised", "Energised"), ("closed", "Closed"))
TEST_TYPES = o(("ir", "Insulation resistance"), ("earth", "Earth resistance"), ("continuity", "Continuity"),
               ("polarity", "Polarity"), ("rcd", "RCD trip"), ("tx_ir", "Transformer IR & PI"),
               ("tx_ratio", "Transformer ratio"), ("tx_winding", "Winding resistance"), ("oil_bdv", "Oil BDV"),
               ("magnetic_balance", "Magnetic balance"), ("vector_group", "Vector group"),
               ("ht_cable", "HT cable HV / VLF"), ("ctpt", "CT / PT tests"), ("relay", "Relay tests"),
               ("breaker_timing", "Breaker timing"), ("panel_function", "Panel function check"), ("dg_load", "DG load test"))
ASSET_KINDS = o(("transformer", "Transformer"), ("ht_panel", "HT panel / VCB"), ("lt_panel", "LT panel"),
                ("rmu", "RMU"), ("dg", "DG set"), ("earth_pit", "Earth pit"), ("apfc", "APFC panel"), ("ups", "UPS"),
                ("cable", "Cable / feeder"), ("ev_charger", "EV charger"), ("solar_inverter", "Solar inverter"),
                ("lighting", "Lighting"), ("other", "Other"))
TICKET_PRIORITY = o(("urgent", "Urgent"), ("high", "High"), ("normal", "Normal"), ("low", "Low"))
# reply-by / fix-by targets in hours (editable in Settings)
SLA_DEFAULTS = {"urgent": [4, 24], "high": [8, 48], "normal": [24, 120], "low": [72, 336]}
PERMIT_TYPES = o(("electrical_isolation", "Electrical isolation (LOTO)"), ("ht_work", "HT work"), ("height", "Work at height"),
                 ("hot_work", "Hot work"), ("confined_space", "Confined space"), ("excavation", "Excavation"))
INCIDENT_KINDS = o(("near_miss", "Near-miss"), ("first_aid", "First aid"), ("medical", "Medical treatment"),
                   ("lti", "Lost-time injury"), ("property_damage", "Property damage"), ("fatality", "Fatality"))
DEPARTMENTS = o(("f1", "BD & Estimation"), ("f2", "Engineering, Design & T&C"), ("f3", "Projects & Execution"),
                ("f4", "Supply Chain"), ("f5", "Liaison & Approvals"), ("f6", "O&M & Services"), ("f7", "QHSE"),
                ("f8", "Finance, HR & Admin"), ("mgmt", "Management"))
TRADES = o("electrician", "wireman", "helper", "lineman", ("cable_jointer", "Cable jointer"), "welder", "rigger",
           "supervisor", "fabricator", "driver", "civil_mason")
PAY_MODES = o(("upi", "UPI"), ("neft", "NEFT / RTGS"), ("cheque", "Cheque"), ("cash", "Cash"), ("card", "Card"))
EXPENSE_CATS = o("fuel", "travel", "food", ("site_petty", "Site petty"), "tools", "repairs", "rent", "utilities",
                 ("liaison_fees", "Liaison fees"), "printing", "communication", "other")
PRODUCT_CATS = o(("panels", "Panels"), ("transformers", "Transformers"), ("cables", "Cables"),
                 ("switchgear", "Switchgear"), ("lighting", "Lighting"), ("earthing", "Earthing & LPS"),
                 ("ev_chargers", "EV chargers"), ("solar", "Solar"), ("apfc", "APFC & power quality"), ("dg_ups", "DG & UPS"))
GALLERY_CATS = o("substations", "panels", "transformers", "cabling", "solar", "lighting", "earthing", "testing", "team", "safety")
DOC_KINDS = o("guide", "brochure", ("company_profile", "Company profile"), ("prequal_pack", "Pre-qualification pack"),
              "datasheet", "certificate")
CHANNELS = o(("google_ads", "Google Ads"), ("meta", "Meta ads"), ("indiamart", "IndiaMART"), ("justdial", "JustDial"),
             ("print", "Print / boards"), ("event", "Event / exhibition"), ("referral", "Referral"),
             ("website", "Website / SEO"), ("whatsapp", "WhatsApp"), ("other", "Other"))

OPTIONS = {
    "services": SERVICES, "sectors": SECTORS, "supply": SUPPLY, "voltages": VOLTAGES, "timeline": TIMELINE,
    "lead_sources": LEAD_SOURCES, "lead_stages": LEAD_STAGES, "lost_reasons": LOST_REASONS,
    "account_types": ACCOUNT_TYPES, "item_categories": ITEM_CATEGORIES, "item_groups": ITEM_GROUPS, "units": UNITS,
    "gst_rates": GST_RATES, "tender_portals": TENDER_PORTALS, "project_status": PROJECT_STATUS,
    "liaison_kinds": LIAISON_KINDS, "liaison_stages": LIAISON_STAGES, "test_types": TEST_TYPES,
    "asset_kinds": ASSET_KINDS, "ticket_priority": TICKET_PRIORITY, "permit_types": PERMIT_TYPES,
    "incident_kinds": INCIDENT_KINDS, "departments": DEPARTMENTS, "trades": TRADES, "pay_modes": PAY_MODES,
    "expense_cats": EXPENSE_CATS, "product_cats": PRODUCT_CATS, "gallery_cats": GALLERY_CATS, "doc_kinds": DOC_KINDS,
    "channels": CHANNELS,
}


def label_of(options_key, value):
    for x in OPTIONS.get(options_key, []):
        if x["value"] == value:
            return x["label"]
    return (value or "").replace("_", " ").capitalize()
