"""Roles, modules and what each role may do (section 9 of the build brief).

Letters: r = read, w = write (add / change), a = approve, e = export, d = delete, p = publish (website).
The server checks these on every request; the menu only hides what a person may not open.
"""

ROLES = {
    "super_admin": "Super admin",
    "director": "Director / CEO",
    "branch_manager": "Branch manager",
    "sales": "Sales / BD",
    "estimator": "Estimation engineer",
    "tender_exec": "Tender executive",
    "project_manager": "Project manager",
    "site_engineer": "Site engineer / supervisor",
    "liaison": "Liaison officer",
    "qaqc": "QA/QC & testing engineer",
    "safety": "Safety officer",
    "purchase": "Purchase",
    "store": "Store keeper",
    "accounts": "Accounts",
    "hr": "HR",
    "service_manager": "Service manager",
    "technician": "Service technician",
    "marketing": "Marketing",
    "auditor": "Auditor (read-only)",
    "employee": "Employee",
    # customer and partner sign-ins (their own portal only)
    "client": "Client (portal)",
    "consultant": "Consultant / architect (portal)",
    "vendor": "Vendor (portal)",
    "subcontractor": "Subcontractor (portal)",
    "partner": "Referral partner (portal)",
}
PORTAL_ROLES = ("client", "consultant", "vendor", "subcontractor", "partner")
STAFF_ROLES = [r for r in ROLES if r not in PORTAL_ROLES]
ALL_BRANCH_ROLES = ("super_admin", "director", "auditor")

MODULES = {
    "dashboard": "Dashboard", "ceo": "CEO dashboard", "crm": "Sales & CRM", "marketing": "Marketing",
    "estimation": "Estimation", "proposals": "Proposals", "tenders": "Tenders", "projects": "Projects",
    "site": "Site work", "liaison": "Liaison & approvals", "quality": "Quality", "testing": "Testing & commissioning",
    "procurement": "Procurement", "stores": "Stores", "plant": "Tools, plant & vehicles", "subcon": "Subcontractors & labour",
    "hse": "Safety (HSE)", "service": "Service & AMC", "finance": "Finance", "hr": "HR & payroll",
    "documents": "Documents", "compliance": "Compliance", "cms": "Website", "reports": "Reports",
    "approvals": "Approvals", "tasks": "Tasks", "users": "Users & roles", "settings": "Settings", "audit": "Activity log",
    "vault": "Password vault", "calculators": "Calculators",
}
ALL = "rwaedp"


def _all(p, **over):
    out = {m: p for m in MODULES}
    out.update(over)
    return out


BASE = {"dashboard": "r", "tasks": "rw", "calculators": "r", "approvals": "r"}

PERMS = {
    "super_admin": _all(ALL),
    "director": _all("rwaedp", users="rw", settings="rw", audit="re"),
    "branch_manager": {**BASE, "crm": "rwae", "marketing": "r", "estimation": "rw", "proposals": "rwa", "tenders": "rw",
                       "projects": "rwae", "site": "rwa", "liaison": "rw", "quality": "rw", "testing": "r",
                       "procurement": "rwa", "stores": "rw", "plant": "rw", "subcon": "rwa", "hse": "rw",
                       "service": "rwa", "finance": "r", "hr": "ra", "documents": "rw", "compliance": "rw",
                       "reports": "re", "approvals": "ra", "users": "r", "vault": "rw", "ceo": "r"},
    "sales": {**BASE, "crm": "rwe", "marketing": "r", "proposals": "rw", "estimation": "r", "documents": "rw",
              "service": "r", "projects": "r"},
    "estimator": {**BASE, "crm": "r", "estimation": "rwe", "proposals": "rw", "tenders": "rw", "documents": "rw",
                  "procurement": "r", "projects": "r"},
    "tender_exec": {**BASE, "crm": "r", "tenders": "rwe", "estimation": "r", "proposals": "r", "documents": "rw",
                    "compliance": "r", "vault": "r"},
    "project_manager": {**BASE, "crm": "r", "estimation": "r", "proposals": "r", "projects": "rwe", "site": "rwa",
                        "liaison": "rw", "quality": "rw", "testing": "r", "procurement": "rw", "stores": "r",
                        "plant": "rw", "subcon": "rwa", "hse": "rw", "service": "r", "documents": "rw",
                        "reports": "re", "approvals": "ra"},
    "site_engineer": {**BASE, "projects": "r", "site": "rw", "quality": "rw", "hse": "rw", "procurement": "w",
                      "stores": "r", "plant": "r", "subcon": "r", "documents": "r", "testing": "r"},
    "liaison": {**BASE, "liaison": "rwe", "projects": "r", "crm": "r", "documents": "rw", "vault": "r"},
    "qaqc": {**BASE, "quality": "rwa", "testing": "rwa", "projects": "r", "site": "r", "plant": "r", "documents": "rw"},
    "safety": {**BASE, "hse": "rwa", "projects": "r", "subcon": "r", "plant": "r", "documents": "rw", "hr": "r"},
    "purchase": {**BASE, "procurement": "rwe", "stores": "r", "plant": "r", "subcon": "rw", "documents": "rw",
                 "estimation": "r", "projects": "r", "finance": "r"},
    "store": {**BASE, "stores": "rwe", "procurement": "r", "plant": "rw", "projects": "r"},
    "accounts": {**BASE, "ceo": "r", "finance": "rwaep", "procurement": "r", "projects": "r", "crm": "r",
                 "tenders": "r", "hr": "r", "subcon": "r", "service": "r", "reports": "re", "documents": "rw",
                 "compliance": "rw", "vault": "rw", "approvals": "ra"},
    "hr": {**BASE, "hr": "rwae", "documents": "rw", "compliance": "r", "hse": "r", "subcon": "r", "users": "r"},
    "service_manager": {**BASE, "service": "rwae", "crm": "r", "stores": "r", "plant": "r", "testing": "rw",
                        "documents": "rw", "reports": "re", "projects": "r"},
    "technician": {**BASE, "service": "rw", "testing": "w"},
    "marketing": {**BASE, "cms": "rwp", "marketing": "rwe", "crm": "r", "reports": "r", "vault": "rw"},
    "auditor": {**_all("r"), "reports": "re", "audit": "re", "vault": "", "users": "r", "settings": "r"},
    "employee": {**BASE},
    "client": {}, "consultant": {}, "vendor": {}, "subcontractor": {}, "partner": {},
}

# Field tags hidden from roles (cost prices, margins, salaries, bank details, personal details).
HIDDEN_FIELD_TAGS = {
    "sales": ["cost", "salary"],
    "site_engineer": ["cost", "salary"],
    "technician": ["cost", "salary"],
    "liaison": ["cost", "salary"],
    "qaqc": ["cost", "salary"],
    "safety": ["cost", "salary"],
    "store": ["salary"],
    "purchase": ["salary"],
    "estimator": ["salary"],
    "tender_exec": ["salary"],
    "project_manager": ["salary"],
    "branch_manager": ["salary"],
    "service_manager": ["cost", "salary"],
    "marketing": ["cost", "salary"],
    "employee": ["cost", "salary"],
    "auditor": [],
    "accounts": [],
    "hr": ["cost"],
    "client": ["cost", "salary", "internal"],
    "consultant": ["cost", "salary", "internal"],
    "vendor": ["cost", "salary", "internal"],
    "subcontractor": ["cost", "salary", "internal"],
    "partner": ["cost", "salary", "internal"],
}

# These roles only see the projects they are on (as manager or team member), and the records of those projects.
PROJECT_SCOPED_ROLES = ("project_manager", "site_engineer")

# These roles only see records where the field equals their own user id.
OWN_SCOPE = {
    "sales": {"leads": "owner_id", "surveys": "engineer_id"},
    "technician": {"tickets": "assigned_to", "pm_jobs": "technician_id"},
    "employee": {"tasks": "assigned_to"},
}

# Who may approve what, and up to which amount (default rules; editable in Settings -> Approval limits).
DEFAULT_APPROVAL_RULES = [
    {"doc": "purchase_orders", "up_to": 100000, "roles": ["branch_manager", "director"]},
    {"doc": "purchase_orders", "up_to": None, "roles": ["director"]},
    {"doc": "vendor_payments", "up_to": 50000, "roles": ["accounts", "branch_manager", "director"]},
    {"doc": "vendor_payments", "up_to": None, "roles": ["director"]},
    {"doc": "proposals", "up_to": None, "roles": ["branch_manager", "director"], "when": "discount_pct > 5 or margin_pct < 12"},
    {"doc": "boqs", "up_to": None, "roles": ["branch_manager", "director"], "when": "margin_pct < 12"},
    {"doc": "variations", "up_to": None, "roles": ["project_manager", "branch_manager", "director"]},
    {"doc": "work_orders", "up_to": 200000, "roles": ["project_manager", "branch_manager", "director"]},
    {"doc": "work_orders", "up_to": None, "roles": ["director"]},
    {"doc": "sc_bills", "up_to": None, "roles": ["project_manager", "branch_manager", "director"]},
    {"doc": "expenses", "up_to": 10000, "roles": ["branch_manager", "accounts", "director"]},
    {"doc": "expenses", "up_to": None, "roles": ["director"]},
    {"doc": "leaves", "up_to": None, "roles": ["hr", "branch_manager", "director"]},
    {"doc": "purchase_requests", "up_to": None, "roles": ["project_manager", "branch_manager", "director"]},
    {"doc": "ra_bills", "up_to": None, "roles": ["project_manager", "branch_manager", "director"]},
    {"doc": "payroll_runs", "up_to": None, "roles": ["director"]},
    {"doc": "advances", "up_to": None, "roles": ["hr", "director"]},
]
