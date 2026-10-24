"""Public website API: content, every lead form, survey booking, calculators, downloads, careers, vendor registration,
QR codes, equipment QR service requests, lead-source webhooks and the (optional) website assistant."""
import os
import re
import secrets
import hashlib
from datetime import datetime, timedelta, date
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Query, Depends
from fastapi.responses import Response, RedirectResponse
from pydantic import BaseModel

import engine as ENG
from calc import engine as CALC
from catalog import OPTIONS, label_of
from core import (db, now, now_iso, new_id, today_ist, normalize_phone, normalize_email, rate_limit, client_ip, audit, notify_roles,
                  get_settings, save_upload, sign_file, send_whatsapp, send_email, IST, SITE_URL, D)
from pdf import Letterhead, ind

router = APIRouter()
TURNSTILE_SECRET = os.environ.get("TURNSTILE_SECRET", "")
WEBHOOK_KEY = os.environ.get("LEAD_WEBHOOK_KEY", "")
PUBLIC_PROJECT_FIELDS = ("id", "slug", "public_title", "name", "public_summary", "challenge", "solution", "results", "highlights", "sector",
                         "service", "supply", "voltage", "capacity_kva", "capacity_kw", "town", "year", "cover", "photos", "featured", "status",
                         "account_id", "start_date", "actual_end", "percent_complete")


async def site_settings():
    s = await get_settings()
    keep = ("company_name", "short_name", "tagline", "phone", "whatsapp", "email", "emergency_phone", "address", "gstin", "elb_licence",
            "licences", "website", "socials", "trust", "hero", "about", "process", "announcement", "home_sections", "survey_slots",
            "map_url", "gbp_url", "founded_year", "leadership", "values", "timeline", "safety", "group_companies", "seo", "assistant_enabled",
            "turnstile_site_key", "ga4_id", "brochure_file", "amc_plans", "certifications", "town_list")
    out = {k: s.get(k) for k in keep if s.get(k) is not None}
    out["turnstile_site_key"] = os.environ.get("TURNSTILE_SITE_KEY") or s.get("turnstile_site_key")
    out["ga4_id"] = os.environ.get("GA4_ID") or s.get("ga4_id")
    return out


async def calc_constants():
    s = await get_settings()
    return CALC.merged_constants((s.get("calc_constants") or {}).get("values"))


# ------------------------------------------------------------------ content
@router.get("/public/site")
async def public_site():
    branches = await db.branches.find({"active": {"$ne": False}, "deleted": {"$ne": True}}, {"_id": 0}).sort("order", 1).to_list(50)
    services = await db.services.find({"published": True, "deleted": {"$ne": True}}, {"_id": 0, "body": 0, "faqs": 0}).sort("order", 1).to_list(50)
    return {"settings": await site_settings(), "branches": branches, "services": services,
            "options": {k: OPTIONS[k] for k in ("services", "sectors", "supply", "voltages", "timeline", "product_cats", "gallery_cats", "lead_sources")},
            "tool_groups": CALC.TOOLS["groups"], "tools": [{k: t[k] for k in ("slug", "group", "icon", "title", "summary")} for t in CALC.TOOLS["tools"]]}


def pub(q=None):
    return {"published": True, "deleted": {"$ne": True}, **(q or {})}


@router.get("/public/services/{slug}")
async def public_service(slug: str):
    s = await db.services.find_one(pub({"slug": slug}), {"_id": 0})
    if not s:
        raise HTTPException(404, "Not found")
    projects = await public_projects(service=s.get("service_key"), limit=6)
    return {"service": s, "projects": projects["items"]}


@router.get("/public/products")
async def public_products():
    return await db.products.find(pub(), {"_id": 0}).sort("order", 1).to_list(200)


@router.get("/public/industries")
async def public_industries():
    return await db.industries.find(pub(), {"_id": 0, "body": 0}).sort("order", 1).to_list(50)


@router.get("/public/industries/{slug}")
async def public_industry(slug: str):
    s = await db.industries.find_one(pub({"slug": slug}), {"_id": 0})
    if not s:
        raise HTTPException(404, "Not found")
    projects = await public_projects(sector=s.get("sector"), limit=6)
    return {"industry": s, "projects": projects["items"]}


async def _client_names(ids):
    rows = await db.accounts.find({"id": {"$in": list(ids)}}, {"_id": 0, "id": 1, "name": 1, "show_logo": 1, "logo": 1}).to_list(len(ids) or 1)
    return {r["id"]: r for r in rows}


def _pub_project(p, clients):
    out = {k: p.get(k) for k in PUBLIC_PROJECT_FIELDS if p.get(k) is not None}
    acc = clients.get(p.get("account_id")) or {}
    out["client"] = acc.get("name") if acc.get("show_logo") else None
    out.pop("account_id", None)
    out["title"] = p.get("public_title") or p.get("name")
    out["ongoing"] = p.get("status") not in ("handed_over", "closed")
    return out


@router.get("/public/projects")
async def public_projects(sector: str = "", service: str = "", supply: str = "", voltage: str = "", town: str = "", year: str = "",
                          state: str = "", limit: int = 60, featured: bool = False):
    q = {"publish": True, "deleted": {"$ne": True}}
    for k, v in (("sector", sector), ("service", service), ("supply", supply), ("voltage", voltage), ("year", year)):
        if v:
            q[k] = v
    if town:
        q["town"] = {"$regex": f"^{re.escape(town)}$", "$options": "i"}
    if featured:
        q["featured"] = True
    if state == "ongoing":
        q["status"] = {"$nin": ["handed_over", "closed"]}
    elif state == "completed":
        q["status"] = {"$in": ["handed_over", "closed"]}
    rows = await db.projects.find(q, {"_id": 0}).sort([("featured", -1), ("year", -1), ("created_at", -1)]).to_list(min(limit, 200))
    clients = await _client_names({r.get("account_id") for r in rows if r.get("account_id")})
    items = [_pub_project(r, clients) for r in rows]
    facets = {}
    allp = await db.projects.find({"publish": True, "deleted": {"$ne": True}}, {"_id": 0, "sector": 1, "service": 1, "town": 1, "year": 1, "voltage": 1}).to_list(1000)
    for k in ("sector", "service", "town", "year", "voltage"):
        facets[k] = sorted({r.get(k) for r in allp if r.get(k)})
    return {"items": items, "facets": facets}


@router.get("/public/projects/{slug}")
async def public_project(slug: str):
    p = await db.projects.find_one({"slug": slug, "publish": True, "deleted": {"$ne": True}}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Not found")
    clients = await _client_names({p.get("account_id")})
    t = await db.testimonials.find_one(pub({"project_id": p["id"], "permission": True}), {"_id": 0})
    gallery = await db.gallery.find(pub({"project_id": p["id"]}), {"_id": 0}).sort("order", 1).to_list(50)
    related = await public_projects(sector=p.get("sector") or "", limit=4)
    return {"project": _pub_project(p, clients), "testimonial": t, "gallery": gallery,
            "related": [r for r in related["items"] if r.get("slug") != slug][:3]}


@router.get("/public/clients")
async def public_clients():
    accs = await db.accounts.find({"show_logo": True, "deleted": {"$ne": True}}, {"_id": 0, "id": 1, "name": 1, "sector": 1, "logo": 1, "town": 1}).sort("name", 1).to_list(300)
    tm = await db.testimonials.find(pub({"permission": True}), {"_id": 0}).to_list(100)
    return {"clients": accs, "testimonials": tm}


@router.get("/public/gallery")
async def public_gallery(category: str = ""):
    q = pub({"category": category} if category else {})
    rows = await db.gallery.find(q, {"_id": 0}).sort([("order", 1), ("taken_on", -1)]).to_list(500)
    return rows


@router.get("/public/insights")
async def public_insights(tag: str = ""):
    nowi = now_ist_min()
    q = {"status": {"$in": ["published", "scheduled"]}, "publish_at": {"$lte": nowi}, "deleted": {"$ne": True}}
    if tag:
        q["tags"] = tag
    return await db.insights.find(q, {"_id": 0, "body": 0}).sort("publish_at", -1).to_list(100)


def now_ist_min():
    return datetime.now(IST).strftime("%Y-%m-%dT%H:%M")


@router.get("/public/insights/{slug}")
async def public_insight(slug: str):
    p = await db.insights.find_one({"slug": slug, "status": {"$in": ["published", "scheduled"]}, "publish_at": {"$lte": now_ist_min()}, "deleted": {"$ne": True}}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Not found")
    more = await db.insights.find({"slug": {"$ne": slug}, "status": {"$in": ["published", "scheduled"]}, "publish_at": {"$lte": now_ist_min()}, "deleted": {"$ne": True}},
                                  {"_id": 0, "body": 0}).sort("publish_at", -1).to_list(3)
    return {"post": p, "more": more}


@router.get("/public/faqs")
async def public_faqs():
    return await db.faqs.find(pub(), {"_id": 0}).sort("order", 1).to_list(200)


@router.get("/public/downloads")
async def public_downloads():
    rows = await db.downloads.find(pub(), {"_id": 0}).sort("order", 1).to_list(100)
    for r in rows:
        if r.get("gated") and r.get("file"):
            r["file"] = {"name": r["file"].get("name")}
    return rows


@router.get("/public/guides/{slug}")
async def public_guide(slug: str):
    g = await db.downloads.find_one(pub({"slug": slug}), {"_id": 0})
    if not g:
        raise HTTPException(404, "Not found")
    if g.get("gated") and g.get("file"):
        g["file"] = {"name": g["file"].get("name")}
    return g


@router.get("/public/jobs")
async def public_jobs():
    t = today_ist().isoformat()
    rows = await db.jobs.find(pub(), {"_id": 0}).to_list(50)
    return [r for r in rows if not r.get("closes_on") or r["closes_on"] >= t]


@router.get("/public/towns/{slug}")
async def public_town(slug: str):
    t = await db.town_pages.find_one(pub({"slug": slug}), {"_id": 0})
    if not t:
        raise HTTPException(404, "Not found")
    projects = await public_projects(town=t["town"], limit=12)
    if not projects["items"]:
        raise HTTPException(404, "Not found")
    return {"town": t, "projects": projects["items"]}


@router.get("/public/towns")
async def public_towns():
    return await db.town_pages.find(pub(), {"_id": 0, "town": 1, "slug": 1}).to_list(100)


@router.get("/public/amc-plans")
async def amc_plans():
    s = await get_settings()
    return s.get("amc_plans") or []


# ------------------------------------------------------------------ lead intake
class LeadIn(BaseModel):
    form: str = "contact_form"
    name: str
    phone: str
    email: str | None = None
    company: str | None = None
    designation: str | None = None
    service: str | None = None
    supply: str | None = None
    load_kva: float | None = None
    site_type: str | None = None
    town: str | None = None
    timeline: str | None = None
    budget: str | None = None
    message: str | None = None
    attachments: list[dict] = []
    consent: bool = False
    tracking: dict = {}
    calculator: dict | None = None
    product: str | None = None
    website: str | None = None  # honeypot
    captcha: str | None = None
    extra: dict = {}


FORM_SOURCE = {"quote_wizard": "quote_wizard", "survey_booking": "survey_booking", "calculator": "calculator", "bill_review": "bill_review",
               "tender_invite": "tender_invite", "callback": "callback", "emergency": "emergency", "amc_enquiry": "amc_enquiry",
               "download": "download", "contact_form": "contact_form", "product_enquiry": "product_enquiry", "service_enquiry": "quote_wizard",
               "sector_enquiry": "contact_form", "similar_project": "quote_wizard", "assistant": "assistant", "referral": "referral",
               "existing_client": "existing_client", "whatsapp": "whatsapp"}
CONSENT_TEXT = ("I agree that Sellandiamman Power Infra may contact me by phone, WhatsApp or email about this enquiry and keep these "
                "details for that purpose, as explained in the privacy notice.")


async def check_captcha(token, request):
    if not TURNSTILE_SECRET:
        return
    import httpx
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.post("https://challenges.cloudflare.com/turnstile/v0/siteverify",
                             data={"secret": TURNSTILE_SECRET, "response": token or "", "remoteip": client_ip(request)})
        if not r.json().get("success"):
            raise HTTPException(400, "Please complete the check above the button")
    except HTTPException:
        raise
    except Exception:
        return  # fail open if the check service is unreachable; rate limits still apply


def clean_tracking(t):
    keep = ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "referrer", "landing_page", "first_touch", "last_touch", "gclid", "fbclid", "qr")
    return {k: str(t.get(k))[:300] for k in keep if t.get(k)}


async def intake(body: LeadIn, request: Request | None, source=None, partner_id=None, user=None):
    """Creates or updates a lead from any channel. Matching phone / email within 90 days updates the open lead instead of
    making a duplicate; a phone belonging to a client contact links the lead to that client."""
    if body.website:
        return {"ok": True, "reference": "LEAD-OK"}  # honeypot filled: quietly accept and drop
    if request is not None and not body.consent and body.form not in ("emergency",):
        raise HTTPException(422, "Please tick the consent box so we can contact you")
    phone = normalize_phone(body.phone)
    email = normalize_email(body.email) if body.email else None
    src = source or FORM_SOURCE.get(body.form, "contact_form")
    tr = clean_tracking(body.tracking or {})
    if tr.get("qr"):
        src = "qr" if src in ("contact_form", "quote_wizard") else src
    contact = await db.contacts.find_one({"phone": phone, "deleted": {"$ne": True}}, {"_id": 0})
    acc_id = contact.get("account_id") if contact else None
    if acc_id and src in ("contact_form", "quote_wizard", "callback"):
        src = "existing_client"
    since = (now() - timedelta(days=90)).isoformat()
    or_ = [{"phone": phone}] + ([{"email": email}] if email else [])
    existing = await db.leads.find_one({"$or": or_, "deleted": {"$ne": True}, "stage": {"$nin": ["won", "lost"]}, "created_at": {"$gte": since}}, {"_id": 0})
    vals = {k: v for k, v in {"name": body.name.strip()[:80], "phone": phone, "email": email, "company": (body.company or "").strip()[:120] or None,
                               "designation": body.designation, "service": body.service if body.service in [o["value"] for o in OPTIONS["services"]] else None,
                               "supply": body.supply if body.supply in ("LT", "HT", "not_sure") else None, "load_kva": body.load_kva,
                               "site_type": body.site_type if body.site_type in [o["value"] for o in OPTIONS["sectors"]] else None,
                               "town": (body.town or "").strip()[:60] or None, "timeline": body.timeline if body.timeline in [o["value"] for o in OPTIONS["timeline"]] else None,
                               "message": "\n".join(x for x in [(body.message or "").strip()[:4000], f"Product: {body.product}" if body.product else "",
                                                              f"Budget: {body.budget}" if body.budget else ""] + [f"{k}: {v}" for k, v in (body.extra or {}).items()][:12] if x) or None}.items() if v not in (None, "")}
    files = [{"id": f["id"], "name": f.get("name"), "type": f.get("type"), "size": f.get("size")} for f in (body.attachments or [])[:10]
             if isinstance(f, dict) and f.get("id") and await db.files.find_one({"id": f["id"]})]
    if existing:
        upd = {k: v for k, v in vals.items() if not existing.get(k)}
        if files:
            upd["attachments"] = (existing.get("attachments") or []) + files
        if body.calculator:
            upd["calculator"] = body.calculator
        upd["last_touch"] = tr.get("last_touch") or src
        upd["updated_at"] = now_iso()
        await db.leads.update_one({"id": existing["id"]}, {"$set": upd})
        await db.activities.insert_one({"id": new_id(), "kind": "note", "subject": f"New enquiry via {label_of('lead_sources', src)}",
                                        "notes": vals.get("message") or "", "lead_id": existing["id"], "done": True, "done_at": now_iso(),
                                        "created_at": now_iso(), "created_by": None, "deleted": False, "owner_id": existing.get("owner_id")})
        lead = await db.leads.find_one({"id": existing["id"]}, {"_id": 0})
        if lead.get("owner_id"):
            from core import notify
            await notify([lead["owner_id"]], f"Repeat enquiry: {lead['name']}", label_of("lead_sources", src), f"/erp/e/leads/{lead['id']}", kind="assigned")
    else:
        data = {**vals, **tr, "source": src, "attachments": files, "consent": bool(body.consent), "consent_text": CONSENT_TEXT if body.consent else None,
                "account_id": acc_id, "partner_id": partner_id, "calculator": body.calculator, "first_touch": tr.get("first_touch") or src,
                "qr_code": tr.get("qr")}
        if tr.get("utm_campaign"):
            camp = await db.campaigns.find_one({"utm_campaign": tr["utm_campaign"], "deleted": {"$ne": True}}, {"_id": 0, "id": 1})
            if camp:
                data["campaign_id"] = camp["id"]
        lead = await ENG.create_record("leads", user, data, system=True)
        if tr.get("qr"):
            await db.qr_codes.update_one({"token": tr["qr"]}, {"$inc": {"leads": 1}})
    s = await get_settings()
    msg = (f"Thank you {vals['name'].split()[0]} — we've received your enquiry ({lead['code']}). "
           f"Our engineer will call you within {s.get('first_response_text') or '30 working minutes'}. — {s.get('short_name') or 'SA Power Infra'}")
    if body.form != "emergency":
        await send_whatsapp(phone, msg)
        if email:
            await send_email(email, f"We've received your enquiry ({lead['code']})", msg)
    if request is not None:
        await audit(None, "public_lead", "leads", lead["id"], {"source": src, "code": lead.get("code")}, client_ip(request))
    return {"ok": True, "reference": lead["code"], "lead_id": lead["id"], "merged": bool(existing)}


@router.post("/public/leads")
async def public_lead(body: LeadIn, request: Request):
    rate_limit(request, "lead", 8, 600)
    await check_captcha(body.captcha, request)
    out = await intake(body, request)
    out.pop("lead_id", None)
    return out


@router.post("/public/upload")
async def public_upload(request: Request, file: UploadFile = File(...)):
    """Drawings, load lists, bills or photos attached to a website form (stored privately)."""
    rate_limit(request, "pubupload", 12, 600)
    rec = await save_upload(file, max_bytes=15 * 1024 * 1024)
    return {"id": rec["id"], "name": rec["original_name"], "type": rec["content_type"], "size": rec["size"]}


# ------------------------------------------------------------------ site survey booking
DEFAULT_SLOTS = ["10:00", "12:00", "15:00", "17:00"]


@router.get("/public/survey-slots")
async def survey_slots(days: int = 14):
    s = await get_settings()
    slots = s.get("survey_slots") or DEFAULT_SLOTS
    engineers = await db.users.find({"role": {"$in": ["sales", "estimator", "project_manager"]}, "active": True, "takes_surveys": {"$ne": False}}, {"_id": 0, "id": 1}).to_list(50)
    cap = max(1, len(engineers))
    start = today_ist() + timedelta(days=1)
    end = start + timedelta(days=min(days, 30))
    booked = await db.surveys.find({"scheduled_at": {"$gte": start.isoformat(), "$lt": end.isoformat()}, "status": "scheduled", "deleted": {"$ne": True}},
                                   {"_id": 0, "scheduled_at": 1}).to_list(2000)
    taken = {}
    for b in booked:
        taken[b["scheduled_at"][:16]] = taken.get(b["scheduled_at"][:16], 0) + 1
    out = []
    dday = start
    while dday < end:
        if dday.weekday() != 6:  # no Sundays
            free = [t for t in slots if taken.get(f"{dday.isoformat()}T{t}", 0) < cap]
            out.append({"date": dday.isoformat(), "slots": free})
        dday += timedelta(days=1)
    return out


class BookingIn(LeadIn):
    slot: str
    survey_type: str = "site_survey"
    address: str | None = None


@router.post("/public/survey-booking")
async def survey_booking(body: BookingIn, request: Request):
    rate_limit(request, "booking", 5, 600)
    await check_captcha(body.captcha, request)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", body.slot or ""):
        raise HTTPException(422, "Pick a date and time")
    avail = await survey_slots(30)
    d_, t_ = body.slot.split("T")
    if not any(x["date"] == d_ and t_ in x["slots"] for x in avail):
        raise HTTPException(409, "That slot was just taken — please pick another")
    body.form = "survey_booking"
    res = await intake(body, request)
    # pick the engineer with the fewest surveys that day
    engineers = await db.users.find({"role": {"$in": ["sales", "estimator", "project_manager"]}, "active": True, "takes_surveys": {"$ne": False}}, {"_id": 0, "id": 1, "name": 1}).to_list(50)
    load = {}
    for e in engineers:
        load[e["id"]] = await db.surveys.count_documents({"engineer_id": e["id"], "scheduled_at": {"$regex": f"^{d_}"}, "deleted": {"$ne": True}})
    eng = min(engineers, key=lambda e: load[e["id"]]) if engineers else None
    stype = body.survey_type if body.survey_type in ("site_survey", "energy_audit", "bill_review") else "site_survey"
    sv = await ENG.create_record("surveys", None, {"survey_type": stype, "lead_id": res["lead_id"], "scheduled_at": body.slot,
                                                   "engineer_id": eng["id"] if eng else None, "address": body.address or body.town}, system=True)
    token = sign_file(f"ics:{sv['id']}", minutes=60 * 24 * 60)
    when = datetime.fromisoformat(body.slot).strftime("%a %d %b, %I:%M %p")
    await send_whatsapp(normalize_phone(body.phone), f"Your site survey is booked for {when} ({res['reference']}). We'll call before we come.")
    return {"ok": True, "reference": res["reference"], "when": body.slot, "engineer": (eng or {}).get("name"), "ics": f"/api/public/ics/{token}"}


@router.get("/public/ics/{token}")
async def ics(token: str):
    from core import check_file_token
    ref = check_file_token(token)
    if not ref.startswith("ics:"):
        raise HTTPException(404, "Not found")
    sv = await db.surveys.find_one({"id": ref[4:]}, {"_id": 0})
    if not sv:
        raise HTTPException(404, "Not found")
    start = datetime.fromisoformat(sv["scheduled_at"]).replace(tzinfo=IST)
    fmt = lambda x: x.astimezone().strftime("%Y%m%dT%H%M%SZ") if False else x.astimezone(tz=None).strftime("%Y%m%dT%H%M%S")  # noqa: E731
    utc = lambda x: x.astimezone(tz=__import__("datetime").timezone.utc).strftime("%Y%m%dT%H%M%SZ")  # noqa: E731
    body = "\r\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Sellandiamman Power Infra//Survey//EN", "BEGIN:VEVENT",
                        f"UID:{sv['id']}@sellandiammanpowerinfra", f"DTSTAMP:{utc(now())}", f"DTSTART:{utc(start)}", f"DTEND:{utc(start + timedelta(hours=1))}",
                        f"SUMMARY:Site survey — Sellandiamman Power Infra ({sv.get('code')})", f"LOCATION:{(sv.get('address') or '').replace(',', ' ')}",
                        "END:VEVENT", "END:VCALENDAR", ""])
    return Response(body, media_type="text/calendar", headers={"Content-Disposition": 'attachment; filename="site-survey.ics"'})


# ------------------------------------------------------------------ calculators
@router.get("/public/calc/constants")
async def public_constants():
    C = await calc_constants()
    return {"constants": C, "tools": CALC.TOOLS}


@router.post("/public/calc/{slug}")
async def public_calc(slug: str, body: dict, request: Request):
    rate_limit(request, "calc", 120, 60)
    try:
        s = await get_settings()
        res = CALC.run(slug, body.get("inputs") or {}, (s.get("calc_constants") or {}).get("values"))
    except CALC.CalcError as ex:
        raise HTTPException(422, str(ex))
    await db.calc_runs.insert_one({"id": new_id(), "slug": slug, "at": now_iso(), "lead": False})
    return res


class CalcLeadIn(LeadIn):
    inputs: dict = {}
    want: str = "report"  # report | review


@router.post("/public/calc/{slug}/lead")
async def calc_lead(slug: str, body: CalcLeadIn, request: Request):
    """'Download the PDF report' or 'Get this checked by an engineer': name and phone, then the lead carries the inputs and result."""
    rate_limit(request, "calclead", 10, 600)
    await check_captcha(body.captcha, request)
    s = await get_settings()
    try:
        res = CALC.run(slug, body.inputs, (s.get("calc_constants") or {}).get("values"))
    except CALC.CalcError as ex:
        raise HTTPException(422, str(ex))
    body.form = "calculator"
    body.calculator = {"slug": slug, "title": res["title"], "inputs": res["inputs"], "headline": res["headline"], "verdict": res["verdict"], "want": body.want}
    if not body.message:
        body.message = f"{res['title']}: {res['verdict']}" + (" — wants an engineer to check this." if body.want == "review" else "")
    out = await intake(body, request)
    await db.calc_runs.insert_one({"id": new_id(), "slug": slug, "at": now_iso(), "lead": True})
    token = sign_file(f"calc:{out['lead_id']}", minutes=60 * 24 * 30)
    return {"ok": True, "reference": out["reference"], "pdf": f"/api/public/calc-report/{token}"}


@router.get("/public/calc-report/{token}")
async def calc_report(token: str):
    from core import check_file_token
    ref = check_file_token(token)
    if not ref.startswith("calc:"):
        raise HTTPException(404, "Not found")
    lead = await db.leads.find_one({"id": ref[5:]}, {"_id": 0})
    if not lead or not lead.get("calculator"):
        raise HTTPException(404, "Not found")
    s = await get_settings()
    c = lead["calculator"]
    res = CALC.run(c["slug"], c["inputs"], (s.get("calc_constants") or {}).get("values"))
    return Response(calc_pdf(res, s, lead), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{c["slug"]}-{lead["code"]}.pdf"'})


def fmt_val(it):
    v = it.get("value")
    if isinstance(v, (int, float)):
        f = it.get("fmt")
        if f == "inr":
            v = "Rs. " + ind(v, 0)
        elif f == "int":
            v = ind(v, 0)
        elif f in ("1dp", "2dp", "3dp", "4dp"):
            v = ind(v, int(f[0]))
        else:
            v = ind(v, 2).rstrip("0").rstrip(".")
    return f"{v} {it.get('unit') or ''}".strip().replace("₹", "Rs.")


def calc_pdf(res, s, lead=None):
    L = Letterhead(res["title"], s, subtitle=f"Calculator report, {today_ist().strftime('%d %b %Y')}" + (f", ref {lead['code']}" if lead else ""))
    if lead:
        L.meta([("Prepared for", lead.get("name")), ("Company", lead.get("company")), ("Phone", lead.get("phone")), ("Reference", lead.get("code"))])
    hl = res["headline"]
    L.h(f"{hl.get('label')}: {fmt_val(hl)}" + (f" ({hl['sub']})" if hl.get("sub") else ""))
    L.p(res.get("verdict", "").replace("₹", "Rs. "))
    spec = CALC.SPEC[res["slug"]]
    rows = []
    for f in spec["inputs"]:
        v = res["inputs"].get(f["k"])
        if f["t"] == "lines":
            v = f"{len(v or [])} lines"
        elif f["t"] == "series":
            v = ", ".join(f"{x:g}" for x in v or [])
        elif f["t"] == "select":
            opts = f.get("opts") or CALC.options_from(f.get("opts_from"), CALC.merged_constants())
            v = next((o["label"] for o in opts if o["value"] == v), v)
        elif f["t"] == "bool":
            v = "Yes" if v else "No"
        if v in (None, ""):
            continue
        rows.append([f["l"], f"{v} {f.get('unit') or ''}".strip()])
    L.h("Inputs")
    L.table(["Input", "Value"], rows, widths=[55, 45])
    if res.get("items"):
        L.h("Results")
        L.table(["Result", "Value"], [[it["label"], fmt_val(it)] for it in res["items"]], widths=[55, 45])
    if res.get("table"):
        L.h(res["table"].get("title") or "Details")
        L.table(res["table"]["columns"], [[ind(c, 2).rstrip("0").rstrip(".") if isinstance(c, float) else str(c) for c in r] for r in res["table"]["rows"]])
    if res.get("checklist"):
        L.h("Documents")
        L.table(["#", "Document"], [[n + 1, x] for n, x in enumerate(res["checklist"])], widths=[8, 92])
    if res.get("steps"):
        L.h("How this is worked out")
        L.table(["Step", "Formula", "Value"], [[st["label"], st["formula"], f"{st['value']} {st.get('unit') or ''}"] for st in res["steps"]], widths=[28, 50, 22])
    for n in res.get("notes") or []:
        L.p("• " + n.replace("₹", "Rs. "), "small")
    L.p(f"Basis: {res['basis']}. Rates as of {res.get('rates_as_of')}.", "small")
    L.p("This result is indicative only. Final design must be done and signed by a licensed electrical engineer. "
        "Sellandiamman Power Infra can check this for you — call or WhatsApp us.", "small")
    return L.build()


# ------------------------------------------------------------------ downloads, newsletter, careers, vendors
@router.post("/public/download/{slug}")
async def gated_download(slug: str, body: LeadIn, request: Request):
    rate_limit(request, "dl", 10, 600)
    g = await db.downloads.find_one(pub({"slug": slug}), {"_id": 0})
    if not g or not g.get("file"):
        raise HTTPException(404, "Not found")
    if g.get("gated"):
        await check_captcha(body.captcha, request)
        body.form = "download"
        body.message = body.message or f"Downloaded: {g['title']}"
        await intake(body, request)
    await db.files.update_one({"id": g["file"]["id"]}, {"$inc": {"downloads": 1}})
    return {"url": f"/api/files/get/{sign_file(g['file']['id'], minutes=60)}"}


@router.get("/public/download/{slug}")
async def open_download(slug: str):
    g = await db.downloads.find_one(pub({"slug": slug, "gated": {"$ne": True}}), {"_id": 0})
    if not g or not g.get("file"):
        raise HTTPException(404, "Not found")
    return RedirectResponse(f"/api/files/get/{sign_file(g['file']['id'], minutes=60)}")


class NewsIn(BaseModel):
    email: str
    name: str | None = None
    consent: bool = False
    website: str | None = None


@router.post("/public/newsletter")
async def newsletter(body: NewsIn, request: Request):
    rate_limit(request, "news", 5, 600)
    if body.website:
        return {"ok": True}
    if not body.consent:
        raise HTTPException(422, "Please tick the box to agree to receive updates")
    email = normalize_email(body.email, required=True)
    await db.subscribers.update_one({"email": email}, {"$set": {"email": email, "name": body.name, "consent_at": now_iso(), "active": True}}, upsert=True)
    return {"ok": True}


@router.get("/public/unsubscribe")
async def unsubscribe(email: str, t: str):
    if hashlib.sha256((email + os.environ.get("JWT_SECRET", "")).encode()).hexdigest()[:16] != t:
        raise HTTPException(403, "Invalid link")
    await db.subscribers.update_one({"email": email.lower()}, {"$set": {"active": False, "unsubscribed_at": now_iso()}})
    return {"ok": True}


class ApplyIn(BaseModel):
    name: str
    phone: str
    email: str | None = None
    experience_years: float | None = None
    current_role: str | None = None
    cv: dict | None = None
    message: str | None = None
    consent: bool = False
    website: str | None = None


@router.post("/public/careers/{job_id}/apply")
async def apply_job(job_id: str, body: ApplyIn, request: Request):
    rate_limit(request, "apply", 5, 600)
    if body.website:
        return {"ok": True}
    if not body.consent:
        raise HTTPException(422, "Please tick the consent box")
    job = await db.jobs.find_one(pub({"id": job_id}), {"_id": 0})
    if not job:
        raise HTTPException(404, "This opening is closed")
    await ENG.create_record("job_applications", None, {"job_id": job_id, "name": body.name.strip()[:80], "phone": normalize_phone(body.phone),
                                                       "email": normalize_email(body.email) or None, "experience_years": body.experience_years,
                                                       "current_role": body.current_role, "cv": body.cv, "message": (body.message or "")[:3000]}, system=True)
    await notify_roles(["hr"], f"New application: {job['title']}", body.name, "/erp/e/job_applications", kind="info")
    return {"ok": True}


class VendorRegIn(BaseModel):
    company: str
    vtype: str = "supplier"
    trade: str | None = None
    gstin: str | None = None
    contact_person: str | None = None
    phone: str
    email: str | None = None
    town: str | None = None
    licence_no: str | None = None
    documents: list[dict] = []
    consent: bool = False
    website: str | None = None


@router.post("/public/vendor-registration")
async def vendor_registration(body: VendorRegIn, request: Request):
    rate_limit(request, "vreg", 5, 600)
    if body.website:
        return {"ok": True}
    if not body.consent:
        raise HTTPException(422, "Please tick the consent box")
    if body.gstin and not re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]", body.gstin.strip().upper()):
        raise HTTPException(422, "GSTIN doesn't look right (15 characters)")
    await ENG.create_record("vendor_registrations", None, {"company": body.company.strip()[:120], "vtype": body.vtype if body.vtype in ("supplier", "subcontractor", "labour_contractor", "transporter") else "supplier",
                                                           "trade": body.trade, "gstin": (body.gstin or "").strip().upper() or None, "contact_person": body.contact_person,
                                                           "phone": normalize_phone(body.phone), "email": normalize_email(body.email) or None, "town": body.town,
                                                           "licence_no": body.licence_no, "documents": body.documents[:10]}, system=True)
    await notify_roles(["purchase"], f"Vendor registration: {body.company}", body.trade or "", "/erp/e/vendor_registrations", kind="info")
    return {"ok": True}


# ------------------------------------------------------------------ emergency breakdown
class EmergencyIn(LeadIn):
    equipment: str | None = None


@router.post("/public/emergency")
async def emergency(body: EmergencyIn, request: Request):
    rate_limit(request, "emerg", 6, 600)
    body.form = "emergency"
    body.consent = True
    res = await intake(body, request)
    lead = await db.leads.find_one({"id": res["lead_id"]}, {"_id": 0})
    t = await ENG.create_record("tickets", None, {"account_id": lead.get("account_id"), "channel": "website", "category": "breakdown", "priority": "urgent",
                                                  "title": f"Breakdown: {body.equipment or body.service or 'electrical'} at {body.town or body.company or body.name}",
                                                  "description": body.message, "contact_name": body.name, "contact_phone": normalize_phone(body.phone),
                                                  "photos": body.attachments[:5]}, system=True)
    await send_whatsapp(normalize_phone(body.phone), f"We've logged your breakdown call ({t['code']}). Our duty engineer will call you shortly.")
    return {"ok": True, "reference": t["code"]}


# ------------------------------------------------------------------ QR codes
@router.get("/public/qr/{token}")
async def qr_redirect(token: str):
    q = await db.qr_codes.find_one({"token": token, "deleted": {"$ne": True}}, {"_id": 0})
    if not q:
        return RedirectResponse("/")
    await db.qr_codes.update_one({"token": token}, {"$inc": {"scans": 1}})
    target = q.get("target") or "/get-quote"
    sep = "&" if "?" in target else "?"
    return RedirectResponse(f"{target}{sep}qr={token}")


@router.get("/public/asset/{token}")
async def asset_info(token: str):
    a = await db.installed_assets.find_one({"qr_token": token, "deleted": {"$ne": True}}, {"_id": 0})
    if not a:
        raise HTTPException(404, "Equipment not found")
    acc = await db.accounts.find_one({"id": a.get("account_id")}, {"_id": 0, "name": 1})
    amc = await db.amc_contracts.find_one({"id": a.get("amc_id"), "status": "active"}, {"_id": 0, "end": 1}) if a.get("amc_id") else None
    return {"code": a.get("code"), "kind": label_of("asset_kinds", a.get("kind")), "make": a.get("make"), "rating": a.get("rating"), "site": a.get("site"),
            "client": (acc or {}).get("name"), "warranty_until": a.get("warranty_until"), "amc_until": (amc or {}).get("end"),
            "last_service_on": a.get("last_service_on")}


class AssetReqIn(BaseModel):
    name: str
    phone: str
    issue: str
    priority: str = "normal"
    photos: list[dict] = []
    website: str | None = None


@router.post("/public/asset/{token}/request")
async def asset_request(token: str, body: AssetReqIn, request: Request):
    rate_limit(request, "assetreq", 6, 600)
    if body.website:
        return {"ok": True}
    a = await db.installed_assets.find_one({"qr_token": token, "deleted": {"$ne": True}}, {"_id": 0})
    if not a:
        raise HTTPException(404, "Equipment not found")
    t = await ENG.create_record("tickets", None, {"account_id": a.get("account_id"), "asset_id": a["id"], "channel": "qr", "category": "breakdown",
                                                  "priority": body.priority if body.priority in ("urgent", "high", "normal", "low") else "normal",
                                                  "title": f"{label_of('asset_kinds', a.get('kind'))} {a.get('code')}: {body.issue[:80]}", "description": body.issue[:3000],
                                                  "contact_name": body.name, "contact_phone": normalize_phone(body.phone), "photos": body.photos[:5]}, system=True)
    return {"ok": True, "reference": t["code"]}


# ------------------------------------------------------------------ webhooks from ad platforms and marketplaces
MAP = {
    "indiamart": {"name": ["SENDER_NAME", "sender_name"], "phone": ["SENDER_MOBILE", "sender_mobile"], "email": ["SENDER_EMAIL", "sender_email"],
                  "company": ["SENDER_COMPANY"], "town": ["SENDER_CITY"], "message": ["QUERY_MESSAGE", "SUBJECT", "QUERY_PRODUCT_NAME"]},
    "justdial": {"name": ["name", "Name"], "phone": ["mobile", "phone", "Mobile"], "email": ["email"], "town": ["city", "area"], "message": ["category", "requirement"]},
    "meta_ads": {"name": ["full_name", "name"], "phone": ["phone_number", "phone"], "email": ["email"], "company": ["company_name"], "town": ["city"], "message": ["message", "requirement"]},
    "google_ads": {"name": ["FULL_NAME", "full_name"], "phone": ["PHONE_NUMBER", "phone_number"], "email": ["EMAIL", "email"], "company": ["COMPANY_NAME"], "town": ["CITY"], "message": ["requirement"]},
    "email": {"name": ["from_name"], "phone": ["phone"], "email": ["from"], "message": ["subject", "text"]},
    "missed_call": {"name": ["name"], "phone": ["caller", "from", "phone"]},
}


def _flat(payload):
    out = {}
    if isinstance(payload, dict):
        for k, v in payload.items():
            if isinstance(v, dict):
                out.update(_flat(v))
            elif isinstance(v, list) and v and isinstance(v[0], dict) and {"name", "values"} <= set(v[0]):
                for x in v:
                    out[x["name"]] = (x.get("values") or [""])[0]
            elif isinstance(v, list) and v and isinstance(v[0], dict) and {"column_id", "string_value"} <= set(v[0]):
                for x in v:
                    out[x["column_id"]] = x.get("string_value")
            else:
                out[k] = v
    return out


@router.post("/hooks/leads/{source}")
async def lead_webhook(source: str, request: Request, key: str = Query("")):
    if not WEBHOOK_KEY or not secrets.compare_digest(key, WEBHOOK_KEY):
        raise HTTPException(403, "Bad key")
    if source not in MAP:
        raise HTTPException(404, "Unknown source")
    try:
        payload = await request.json()
    except Exception:
        payload = dict(await request.form())
    rows = payload if isinstance(payload, list) else (payload.get("RESPONSE") if isinstance(payload.get("RESPONSE"), list) else [payload])
    made = []
    for row in rows[:50]:
        f = _flat(row)
        pick = lambda keys: next((str(f[k]) for k in keys if f.get(k)), None)  # noqa: E731
        m = MAP[source]
        phone = pick(m.get("phone", []))
        if not phone:
            continue
        try:
            body = LeadIn(form="contact_form", name=pick(m.get("name", [])) or "Enquiry", phone=phone[-10:], email=pick(m.get("email", [])),
                          company=pick(m.get("company", [])), town=pick(m.get("town", [])), message=pick(m.get("message", [])), consent=False)
            res = await intake(body, None, source=source)
            made.append(res["reference"])
        except HTTPException:
            continue
    return {"ok": True, "leads": made}


VERIFY = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")


@router.get("/hooks/whatsapp")
async def wa_verify(request: Request):
    p = request.query_params
    if VERIFY and p.get("hub.verify_token") == VERIFY:
        return Response(p.get("hub.challenge") or "", media_type="text/plain")
    raise HTTPException(403, "Bad token")


@router.post("/hooks/whatsapp")
async def wa_inbound(request: Request):
    """Inbound WhatsApp Business messages become leads (or notes on an open lead)."""
    if not VERIFY:
        raise HTTPException(404, "Not set up")
    data = await request.json()
    for entry in data.get("entry", []):
        for ch in entry.get("changes", []):
            v = ch.get("value", {})
            names = {c.get("wa_id"): (c.get("profile") or {}).get("name") for c in v.get("contacts", [])}
            for msg in v.get("messages", []):
                wa = msg.get("from", "")
                text = (msg.get("text") or {}).get("body") or f"[{msg.get('type')}]"
                try:
                    await intake(LeadIn(form="whatsapp", name=names.get(wa) or "WhatsApp enquiry", phone=wa[-10:], message=text, consent=False), None, source="whatsapp")
                except HTTPException:
                    pass
    return {"ok": True}


# ------------------------------------------------------------------ website assistant (off by default)
WORDS = re.compile(r"[a-z0-9]+")


@router.post("/public/assistant")
async def assistant(body: dict, request: Request):
    """Answers from the site's own FAQs, services and calculators. Clearly labelled; hands over to a person."""
    rate_limit(request, "assist", 30, 600)
    s = await get_settings()
    if not s.get("assistant_enabled"):
        raise HTTPException(404, "Not enabled")
    q = set(WORDS.findall((body.get("q") or "").lower()[:300])) - {"the", "a", "an", "is", "to", "for", "of", "and", "i", "my", "we", "in", "on", "what", "how", "do", "can", "you"}
    if not q:
        return {"answers": [], "handover": True}
    scored = []
    for f in await db.faqs.find(pub(), {"_id": 0}).to_list(200):
        words = set(WORDS.findall((f["question"] + " " + f["answer"]).lower()))
        scored.append((len(q & words), {"type": "faq", "title": f["question"], "text": f["answer"]}))
    for sv in await db.services.find(pub(), {"_id": 0}).to_list(50):
        words = set(WORDS.findall((sv["title"] + " " + sv.get("summary", "")).lower()))
        scored.append((len(q & words), {"type": "service", "title": sv["title"], "text": sv.get("summary"), "link": f"/services/{sv['slug']}"}))
    for t in CALC.TOOLS["tools"]:
        words = set(WORDS.findall((t["title"] + " " + t["summary"]).lower()))
        scored.append((len(q & words), {"type": "tool", "title": t["title"], "text": t["summary"], "link": f"/tools/{t['slug']}"}))
    best = [x for sc, x in sorted(scored, key=lambda z: -z[0]) if sc > 0][:4]
    return {"answers": best, "handover": True}
