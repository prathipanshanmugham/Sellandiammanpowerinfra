"""CRM: pipeline board, converting a won lead, merging duplicates, lead timeline, routing rules, marketing numbers."""
import re
from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException

import engine as ENG
from catalog import OPTIONS, label_of
from core import db, require, staff_user, now_iso, now, new_id, audit, get_settings, clear_settings_cache, today_ist, can, IST

router = APIRouter(prefix="/crm")
STAGES = [s["value"] for s in OPTIONS["lead_stages"]]


@router.get("/pipeline")
async def pipeline(user=Depends(require("crm", "r")), owner: str = "", service: str = "", source: str = "", q: str = ""):
    params = {"size": "500", "sort": "-score"}
    if owner:
        params["owner_id"] = owner
    if service:
        params["service"] = service
    if source:
        params["source"] = source
    if q:
        params["q"] = q
    data = await ENG.list_records("leads", user, params)
    cols = {s: {"stage": s, "label": label_of("lead_stages", s), "items": [], "count": 0, "value": 0.0} for s in STAGES}
    cutoff = (now() - timedelta(days=60)).isoformat()
    for d in data["items"]:
        if d.get("stage") in ("won", "lost") and (d.get("updated_at") or "") < cutoff:
            continue
        c = cols.get(d.get("stage") or "new")
        if not c:
            continue
        c["count"] += 1
        c["value"] += float(d.get("value") or 0)
        c["items"].append({k: d.get(k) for k in ("id", "code", "name", "company", "service", "supply", "load_kva", "town", "value", "score",
                                                 "owner_id", "next_follow_up", "response_due_at", "first_response_at", "source", "created_at")})
    weighted = sum(c["value"] * (ENG.REG.E and 1) * {"new": .05, "contacted": .1, "survey_scheduled": .2, "survey_done": .3, "estimating": .4,
                                                      "quoted": .5, "negotiation": .7, "won": 1, "lost": 0, "on_hold": .05}[c["stage"]] for c in cols.values())
    return {"columns": list(cols.values()), "refs": data["refs"], "weighted_value": round(weighted, 2)}


@router.post("/leads/{lid}/move")
async def move(lid: str, body: dict, user=Depends(require("crm", "w"))):
    upd = {"stage": body.get("stage")}
    for k in ("lost_reason", "lost_note", "hold_until"):
        if body.get(k):
            upd[k] = body[k]
    if upd["stage"] not in STAGES:
        raise HTTPException(422, "Unknown stage")
    return await ENG.update_record("leads", user, lid, upd)


@router.post("/leads/{lid}/convert")
async def convert(lid: str, body: dict, user=Depends(require("crm", "w"))):
    """Won lead -> client (new or existing) + contact + project, carrying everything over."""
    lead = await ENG.get_record("leads", user, lid, raw=True)
    if lead.get("project_id"):
        raise HTTPException(409, "This lead was already converted")
    acc_id = body.get("account_id") or lead.get("account_id")
    if not acc_id:
        acc = await ENG.create_record("accounts", user, {"name": body.get("account_name") or lead.get("company") or lead["name"], "phone": lead.get("phone"),
                                                         "email": lead.get("email"), "town": lead.get("town"), "sector": lead.get("site_type"),
                                                         "source": lead.get("source"), "owner_id": lead.get("owner_id"), "branch_id": lead.get("branch_id")})
        acc_id = acc["id"]
    contact = await db.contacts.find_one({"account_id": acc_id, "phone": lead.get("phone"), "deleted": {"$ne": True}}, {"_id": 0})
    if not contact:
        contact = await ENG.create_record("contacts", user, {"name": lead["name"], "account_id": acc_id, "designation": lead.get("designation"),
                                                             "phone": lead.get("phone"), "email": lead.get("email"), "is_primary": True,
                                                             "consent_marketing": bool(lead.get("consent"))})
    project = None
    if body.get("create_project", True):
        prop = await db.proposals.find_one({"lead_id": lid, "status": "accepted", "deleted": {"$ne": True}}, {"_id": 0})
        project = await ENG.create_record("projects", user, {
            "name": body.get("project_name") or f"{lead.get('company') or lead['name']} — {label_of('services', lead.get('service'))}",
            "account_id": acc_id, "contact_id": contact["id"], "lead_id": lid, "proposal_id": (prop or {}).get("id"),
            "service": lead.get("service"), "sector": lead.get("site_type"), "supply": lead.get("supply") if lead.get("supply") in ("LT", "HT") else None,
            "capacity_kva": lead.get("load_kva"), "town": lead.get("town"), "contract_value": (prop or {}).get("taxable") or lead.get("value"),
            "manager_id": body.get("manager_id"), "branch_id": lead.get("branch_id"), "start_date": body.get("start_date")})
        for coll in ("activities", "surveys", "boqs", "proposals"):
            await db[coll].update_many({"lead_id": lid}, {"$set": {"account_id": acc_id}})
    await db.leads.update_one({"id": lid}, {"$set": {"stage": "won", "probability": 100, "account_id": acc_id, "project_id": (project or {}).get("id"),
                                                     "updated_at": now_iso()}})
    await audit(user, "lead_converted", "leads", lid, {"account_id": acc_id, "project_id": (project or {}).get("id")})
    return {"account_id": acc_id, "contact_id": contact["id"], "project_id": (project or {}).get("id")}


@router.post("/leads/{lid}/merge")
async def merge(lid: str, body: dict, user=Depends(require("crm", "w"))):
    into = body.get("into_id")
    if not into or into == lid:
        raise HTTPException(422, "Pick the lead to keep")
    a = await ENG.get_record("leads", user, lid, raw=True)
    b = await ENG.get_record("leads", user, into, raw=True)
    upd = {k: v for k, v in a.items() if k in ("email", "company", "designation", "service", "supply", "load_kva", "town", "message") and v and not b.get(k)}
    upd["attachments"] = (b.get("attachments") or []) + (a.get("attachments") or [])
    await db.leads.update_one({"id": into}, {"$set": upd})
    for coll in ("activities", "surveys", "boqs", "proposals"):
        await db[coll].update_many({"lead_id": lid}, {"$set": {"lead_id": into}})
    await db.leads.update_one({"id": lid}, {"$set": {"stage": "lost", "lost_reason": "duplicate", "duplicate_of": into, "updated_at": now_iso()}})
    await audit(user, "lead_merged", "leads", lid, {"into": into})
    return {"ok": True, "into": into}


@router.get("/duplicates")
async def duplicates(user=Depends(require("crm", "r"))):
    rows = await db.leads.find({"deleted": {"$ne": True}, "stage": {"$nin": ["won", "lost"]}}, {"_id": 0, "id": 1, "code": 1, "name": 1, "phone": 1, "email": 1,
                                                                                               "company": 1, "created_at": 1, "stage": 1}).to_list(5000)
    groups = {}
    for r in rows:
        for k in ("phone", "email"):
            if r.get(k):
                groups.setdefault(f"{k}:{r[k]}", []).append(r)
    out, seen = [], set()
    for key, g in groups.items():
        ids = tuple(sorted(x["id"] for x in g))
        if len(g) > 1 and ids not in seen:
            seen.add(ids)
            out.append({"match": key.split(":", 1)[0], "value": key.split(":", 1)[1], "leads": sorted(g, key=lambda x: x["created_at"])})
    return out


@router.get("/leads/{lid}/timeline")
async def timeline(lid: str, user=Depends(require("crm", "r"))):
    lead = await ENG.get_record("leads", user, lid, raw=True)
    items = []
    for a in await db.activities.find({"lead_id": lid, "deleted": {"$ne": True}}, {"_id": 0}).to_list(500):
        items.append({"at": a.get("done_at") or a.get("due_at") or a["created_at"], "kind": a["kind"], "title": a["subject"], "text": a.get("notes"),
                      "done": a.get("done"), "id": a["id"], "entity": "activities"})
    for s in await db.surveys.find({"lead_id": lid, "deleted": {"$ne": True}}, {"_id": 0}).to_list(50):
        items.append({"at": s["scheduled_at"], "kind": "survey", "title": f"{label_of('lead_sources', 'survey_booking')} {s.get('code')}", "text": s.get("findings"),
                      "id": s["id"], "entity": "surveys"})
    for p in await db.proposals.find({"lead_id": lid, "deleted": {"$ne": True}}, {"_id": 0}).to_list(50):
        items.append({"at": p.get("sent_at") or p["created_at"], "kind": "proposal", "title": f"Proposal {p.get('code')} — {p.get('status')}", "id": p["id"], "entity": "proposals"})
    for a in await db.audit_logs.find({"entity": "leads", "entity_id": lid}, {"_id": 0}).to_list(200):
        ch = (a.get("details") or {}).get("changes") or {}
        if "stage" in ch:
            items.append({"at": a["at"], "kind": "stage", "title": f"Stage: {label_of('lead_stages', ch['stage'][0])} → {label_of('lead_stages', ch['stage'][1])}", "by": a.get("user_name")})
        elif a["action"] in ("create", "public_lead"):
            items.append({"at": a["at"], "kind": "created", "title": f"Lead created ({label_of('lead_sources', lead.get('source'))})", "by": a.get("user_name")})
    items.sort(key=lambda x: x["at"] or "", reverse=True)
    return items


@router.get("/routing")
async def get_routing(user=Depends(require("crm", "r"))):
    s = await get_settings()
    return {"rules": s.get("routing_rules") or [], "first_response_minutes": s.get("first_response_minutes") or 30,
            "working_hours": s.get("working_hours") or {"start": "09:30", "end": "18:30", "days": [0, 1, 2, 3, 4, 5]}}


@router.put("/routing")
async def put_routing(body: dict, user=Depends(require("crm", "a"))):
    rules = []
    for r in (body.get("rules") or [])[:50]:
        rules.append({"name": str(r.get("name") or "")[:60], "service": r.get("service") or None, "supply": r.get("supply") or None,
                      "towns": [str(t)[:40] for t in (r.get("towns") or [])][:40], "branch_id": r.get("branch_id") or None,
                      "team": [str(t) for t in (r.get("team") or [])][:20]})
    upd = {"routing_rules": rules}
    if body.get("first_response_minutes"):
        upd["first_response_minutes"] = max(5, min(1440, int(body["first_response_minutes"])))
    await db.settings.update_one({"id": "company"}, {"$set": upd}, upsert=True)
    clear_settings_cache()
    await audit(user, "routing_updated", "settings", "company", {"rules": len(rules)})
    return await get_routing(user)


def month_key(iso):
    return (iso or "")[:7]


@router.get("/marketing")
async def marketing(user=Depends(require("marketing", "r")), frm: str = "", to: str = ""):
    t = today_ist()
    frm = frm or (t - timedelta(days=89)).isoformat()
    to = to or t.isoformat()
    leads = await db.leads.find({"deleted": {"$ne": True}, "created_at": {"$gte": frm, "$lte": to + "T23:59:59"}}, {"_id": 0}).to_list(20000)
    camps = await db.campaigns.find({"deleted": {"$ne": True}}, {"_id": 0}).to_list(500)
    chan_src = {"google_ads": ["google_ads"], "meta": ["meta_ads"], "indiamart": ["indiamart"], "justdial": ["justdial"], "website": ["quote_wizard", "contact_form", "calculator", "survey_booking", "download", "bill_review"],
                "referral": ["referral"], "whatsapp": ["whatsapp"], "event": ["exhibition"], "print": ["qr"]}
    spend_by_src = {}
    for c in camps:
        if (c.get("end") or "9999") < frm or (c.get("start") or "0000") > to:
            continue
        srcs = chan_src.get(c.get("channel"), [c.get("channel")])
        for s in srcs:
            spend_by_src[s] = spend_by_src.get(s, 0) + float(c.get("spend") or 0) / len(srcs)
    won_ids = {l["id"] for l in leads if l.get("stage") == "won"}
    projects = await db.projects.find({"lead_id": {"$in": list(won_ids)}}, {"_id": 0, "lead_id": 1, "contract_value": 1}).to_list(5000)
    rev = {p["lead_id"]: float(p.get("contract_value") or 0) for p in projects}
    by = {}
    for l in leads:
        s = l.get("source") or "other"
        r = by.setdefault(s, {"source": s, "label": label_of("lead_sources", s), "leads": 0, "won": 0, "revenue": 0.0, "spend": 0.0, "responded_in_time": 0, "responded": 0})
        r["leads"] += 1
        if l.get("stage") == "won":
            r["won"] += 1
            r["revenue"] += rev.get(l["id"], float(l.get("value") or 0))
        if l.get("first_response_at"):
            r["responded"] += 1
            if l.get("response_due_at") and l["first_response_at"] <= l["response_due_at"]:
                r["responded_in_time"] += 1
    for s, v in spend_by_src.items():
        by.setdefault(s, {"source": s, "label": label_of("lead_sources", s), "leads": 0, "won": 0, "revenue": 0.0, "spend": 0.0, "responded_in_time": 0, "responded": 0})["spend"] = round(v, 2)
    rows = []
    for r in by.values():
        r["conversion_pct"] = round(r["won"] / r["leads"] * 100, 1) if r["leads"] else 0
        r["cost_per_lead"] = round(r["spend"] / r["leads"], 0) if r["leads"] and r["spend"] else None
        r["roi"] = round(r["revenue"] / r["spend"], 1) if r["spend"] else None
        rows.append(r)
    rows.sort(key=lambda r: -r["leads"])
    months = {}
    for l in leads:
        m = months.setdefault(month_key(l["created_at"]), {"month": month_key(l["created_at"]), "leads": 0, "won": 0})
        m["leads"] += 1
        m["won"] += 1 if l.get("stage") == "won" else 0
    runs = await db.calc_runs.find({"at": {"$gte": frm, "$lte": to + "T23:59:59"}}, {"_id": 0}).to_list(100000)
    tools = {}
    for r in runs:
        x = tools.setdefault(r["slug"], {"slug": r["slug"], "runs": 0, "leads": 0})
        x["runs"] += 1
        x["leads"] += 1 if r.get("lead") else 0
    resp = [l for l in leads if l.get("first_response_at") and l.get("created_at")]
    mins = sorted((datetime.fromisoformat(l["first_response_at"]) - datetime.fromisoformat(l["created_at"])).total_seconds() / 60 for l in resp)
    median = round(mins[len(mins) // 2]) if mins else None
    in_time = sum(1 for l in resp if l.get("response_due_at") and l["first_response_at"] <= l["response_due_at"])
    return {"from": frm, "to": to, "total": len(leads), "won": len(won_ids), "by_source": rows, "by_month": sorted(months.values(), key=lambda x: x["month"]),
            "tools": sorted(tools.values(), key=lambda x: -x["runs"]), "median_first_response_min": median,
            "responded_in_time_pct": round(in_time / len(resp) * 100) if resp else None,
            "spend": round(sum(float(c.get("spend") or 0) for c in camps if not ((c.get("end") or "9999") < frm or (c.get("start") or "0000") > to)), 2)}


@router.get("/partners/{pid}/statement")
async def partner_statement(pid: str, user=Depends(require("crm", "r"))):
    p = await ENG.get_record("partners", user, pid, raw=True)
    leads = await db.leads.find({"partner_id": pid, "deleted": {"$ne": True}}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    pids = [l.get("project_id") for l in leads if l.get("project_id")]
    prj = {x["id"]: x for x in await db.projects.find({"id": {"$in": pids}}, {"_id": 0, "id": 1, "contract_value": 1}).to_list(1000)}
    rows, total = [], 0.0
    for l in leads:
        v = float((prj.get(l.get("project_id")) or {}).get("contract_value") or 0) if l.get("stage") == "won" else 0
        c = round(v * float(p.get("commission_pct") or 0) / 100, 2)
        total += c
        rows.append({"code": l["code"], "name": l["name"], "company": l.get("company"), "stage": l.get("stage"), "created_at": l["created_at"][:10],
                     "value": v, "commission": c})
    return {"partner": p, "rows": rows, "commission_total": round(total, 2)}


@router.get("/leads/{lid}/whatsapp")
async def wa_link(lid: str, user=Depends(require("crm", "r"))):
    lead = await ENG.get_record("leads", user, lid, raw=True)
    s = await get_settings()
    text = (f"Hello {lead['name'].split()[0]}, this is {user['name']} from {s.get('short_name') or 'Sellandiamman Power Infra'} about your enquiry "
            f"({lead.get('code')}) for {label_of('services', lead.get('service')).lower()}. When is a good time to talk?")
    digits = re.sub(r"\D", "", lead.get("phone") or "")
    from urllib.parse import quote
    return {"url": f"https://wa.me/{digits}?text={quote(text)}", "text": text}
