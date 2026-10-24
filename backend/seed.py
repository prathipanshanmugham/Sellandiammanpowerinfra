"""First-run setup and (optional) sample data.

Always: company settings, the two starting branches, website content (services, industries, products, FAQs, guides,
terms) and the first admin login from ADMIN_EMAIL / ADMIN_PASSWORD.
With SEED_DEMO=true (preview and local trials only): logins for every role, and sample clients, leads, projects,
tenders, stock, AMCs, invoices and so on. Sample records are made up; production starts empty.
"""
import os
import random
from datetime import timedelta, datetime

import engine as ENG
from core import db, now_iso, new_id, hash_password, today_ist, logger, clear_settings_cache, IST
from roles import ROLES, DEFAULT_APPROVAL_RULES
import site_content as SC

DEMO_DOMAIN = "demo.sellandiammanpowerinfra.test"


async def ensure_indexes():
    try:
        await db.users.create_index("email", unique=True)
        await db.users.create_index("id", unique=True)
        await db.sessions.create_index("sid", unique=True)
        await db.audit_logs.create_index("seq")
        await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
        for coll in ("leads", "projects", "accounts", "invoices", "tickets", "stock_moves", "approvals"):
            await db[coll].create_index("id")
        await db.stock_moves.create_index([("item_id", 1), ("store_id", 1)])
        await db.leads.create_index("phone")
    except Exception:
        logger.warning("Index creation skipped")


BASE_SETTINGS = {
    "id": "company", "company_name": "Sellandiamman Power Infra", "short_name": "SA Power Infra", "company_code": "SPI",
    "tagline": "LT and HT electrical contracting and consulting, a Sellandiamman Group company",
    "number_format": "{co}/{br}/{doc}/{fy}/{seq}", "fy_start_month": 4, "mfa_required_roles": [], "email_notifications": True,
    "first_response_minutes": 30, "first_response_text": "30 working minutes",
    "working_hours": {"start": "09:30", "end": "18:30", "days": [0, 1, 2, 3, 4, 5]}, "geofence_m": 300,
    "payroll_statutory": {"pf": False, "esi": False, "pt": False, "tds": False},
    "website": "sellandiammanpowerinfra.com", "survey_slots": ["10:00", "12:00", "15:00", "17:00"],
    "hero": {"eyebrow": "LT and HT, up to 33 kV", "title": "Power infrastructure, engineered and energised.",
             "text": "Substations, panels, cabling, earthing, solar and EV charging for factories, buildings and campuses across Tamil Nadu — designed, approved, built, tested and maintained by one accountable team."},
    "trust": [{"value": "11–33 kV", "label": "HT substations designed and built"}, {"value": "24×7", "label": "Breakdown service line"},
              {"value": "24", "label": "Free engineering calculators"}, {"value": "1 team", "label": "Survey to approvals to AMC"}],
    "process": SC.PROCESS,
    "about": {"story": "Sellandiamman Power Infra is the electrical contracting and consulting company of the Sellandiamman Group, which also runs "
                       "Sellandiamman Traders (electrical and construction materials), Sellandiamman Estates (real estate) and Sensoper Controls and "
                       "Renewables (solar). We bring that group's supply chain and local presence to LT and HT power projects: one team that surveys, "
                       "designs, gets approvals, builds, tests and maintains.",
              "mission": "Safe, reliable power for every site we touch — delivered on time, documented properly and supported for its whole life."},
    "values": [{"title": "Safety first", "text": "Permits, lock-out and authorised persons on every HT job. Anyone can stop unsafe work."},
               {"title": "Engineering, not guesswork", "text": "Every size and setting is calculated and recorded."},
               {"title": "Open with clients", "text": "Progress, photos, approvals and bills in the client portal."},
               {"title": "Here for the long run", "text": "AMC and breakdown service for what we build."}],
    "group_companies": [{"name": "Sellandiamman Traders", "text": "Electrical and construction materials", "url": "https://sellandiammantraders.com"},
                        {"name": "Sellandiamman Estates", "text": "Real estate and property management", "url": "https://www.sellandiammanestates.com"},
                        {"name": "Sensoper Controls and Renewables", "text": "Solar EPC", "url": ""}],
    "safety": {"policy": "We plan every job for safety: risk assessment, permit to work, lock-out / tag-out, tested-dead before touch, earthing on both "
                         "sides, and an authorised person for all HT work. Toolbox talks start every shift, PPE is issued and recorded, and near-misses "
                         "are reported and investigated like incidents.",
               "quality": "Inspection and test plans for every project, material inspection on receipt, hold points for client witness, "
                          "calibrated instruments, and non-conformances closed with root cause."},
    "amc_plans": [{"name": "Essential", "for": "Small substations and LT panels", "visits": "2 visits a year", "response": "Next working day",
                   "items": ["Visual inspection and cleaning", "Tightness checks", "IR and earth resistance readings", "Service report"]},
                  {"name": "Standard", "for": "Factories and commercial buildings", "visits": "4 visits a year", "response": "Within 8 hours",
                   "items": ["Everything in Essential", "Transformer oil BDV test", "Relay and breaker operation checks", "Thermography once a year"]},
                  {"name": "Critical", "for": "Hospitals, process plants, data rooms", "visits": "Monthly visits", "response": "Within 4 hours, 24×7",
                   "items": ["Everything in Standard", "Power-quality logging", "Oil filtration as needed", "Priority spares and on-call engineer"]}],
    "home_sections": ["hero", "trust", "services", "sectors", "projects", "clients", "tools", "process", "insights", "cta"],
    "announcement": {"text": "", "link": "", "active": False},
    "assistant_enabled": False,
}


async def seed_base():
    s = await db.settings.find_one({"id": "company"})
    if not s:
        await db.settings.insert_one(dict(BASE_SETTINGS))
    clear_settings_cache()
    if not await db.branches.count_documents({}):
        await db.branches.insert_many([
            {"id": new_id(), "name": "Head office — Perundurai", "code": "PDR", "city": "Perundurai", "is_head_office": True, "active": True, "order": 1,
             "hours": "Mon–Sat 9:30 am – 6:30 pm", "created_at": now_iso(), "deleted": False},
            {"id": new_id(), "name": "Erode", "code": "ERD", "city": "Erode", "is_head_office": False, "active": True, "order": 2,
             "hours": "Mon–Sat 9:30 am – 6:30 pm", "created_at": now_iso(), "deleted": False}])
    if not await db.services.count_documents({}):
        for x in SC.SERVICES:
            await ENG.create_record("services", None, {**x, "standards": [{"code": a, "title": b} for a, b in x["standards"]],
                                                       "scope": [{"item": i} for i in x["scope"]], "published": True}, system=True)
        for x in SC.INDUSTRIES:
            await ENG.create_record("industries", None, {**x, "needs": [{"item": i} for i in x["needs"]], "published": True}, system=True)
        for x in SC.PRODUCTS:
            await ENG.create_record("products", None, {**x, "specs": [{"label": a, "value": b} for a, b in x["specs"]], "published": True}, system=True)
        for n, (cat, q, a) in enumerate(SC.FAQS, 1):
            await ENG.create_record("faqs", None, {"question": q, "answer": a, "category": cat, "order": n, "published": True}, system=True)
        for g in SC.GUIDES:
            await ENG.create_record("downloads", None, {**g, "published": True, "gated": False}, system=True)
        for t in SC.TERMS:
            await ENG.create_record("templates", None, t, system=True)
    if not await db.users.count_documents({}):
        email = (os.environ.get("ADMIN_EMAIL") or "").strip().lower()
        pw = os.environ.get("ADMIN_PASSWORD") or ""
        if email and pw:
            await db.users.insert_one({"id": new_id(), "name": os.environ.get("ADMIN_NAME") or "Administrator", "email": email, "role": "super_admin",
                                       "password_hash": hash_password(pw), "active": True, "branch_ids": [], "created_at": now_iso(), "mfa_enabled": False})
            logger.warning("Created the first admin login %s — remove ADMIN_PASSWORD from backend/.env after signing in", email)


async def seed():
    await ensure_indexes()
    await seed_base()
    if os.environ.get("SEED_DEMO") == "true" and not await db.users.find_one({"email": f"director@{DEMO_DOMAIN}"}):
        from seed_demo import seed_demo
        await seed_demo()
