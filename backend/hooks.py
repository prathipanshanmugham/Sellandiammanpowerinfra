"""Business rules that go beyond the generic engine, attached per record type.

before(doc, old, user, creating)   runs before formulas and saving (may change doc)
after(doc, old, user, creating)    runs after saving
action(name, new, old, user)       runs on a workflow button; returns extra fields to save
approved(doc, user)                runs when an approval is granted (or auto-approved)
"""
import math
import secrets
from datetime import date, datetime, timedelta
from fastapi import HTTPException

from core import (db, now, now_iso, new_id, today_ist, money, audit, notify, notify_roles, get_settings, send_whatsapp,
                  IST, branch_filter)
from engine import HOOKS, create_record
from catalog import SLA_DEFAULTS, label_of

STAGE_PROB = {"new": 5, "contacted": 10, "survey_scheduled": 20, "survey_done": 30, "estimating": 40, "quoted": 50,
              "negotiation": 70, "won": 100, "lost": 0, "on_hold": 5}
SOURCE_SCORE = {"tender_invite": 15, "survey_booking": 15, "quote_wizard": 12, "bill_review": 12, "existing_client": 15,
                "referral": 12, "calculator": 8, "emergency": 10, "amc_enquiry": 10, "phone": 8, "whatsapp": 8, "callback": 6,
                "google_ads": 6, "meta_ads": 4, "indiamart": 4, "justdial": 3, "download": 3, "newsletter": 1}


def hook(entity, **fns):
    HOOKS.setdefault(entity, {}).update(fns)


def d(x):
    return date.fromisoformat(str(x)[:10]) if x else None


# ====================================================================== leads
def lead_score(doc):
    s = 0
    kva = float(doc.get("load_kva") or 0)
    s += 30 if kva >= 500 else 22 if kva >= 200 else 14 if kva >= 75 else 6 if kva > 0 else 0
    s += {"HT": 18, "LT": 8, "not_sure": 6}.get(doc.get("supply") or "", 0)
    s += {"now": 20, "1_3m": 14, "3_6m": 7, "later": 2}.get(doc.get("timeline") or "", 4)
    s += SOURCE_SCORE.get(doc.get("source") or "", 3)
    s += 5 if doc.get("company") else 0
    s += 4 if doc.get("email") else 0
    s += 5 if doc.get("attachments") else 0
    s += 3 if doc.get("calculator") else 0
    if doc.get("service") in ("ht_substation", "transformers", "ht_lt_panels", "solar_epc"):
        s += 5
    return min(100, s)


async def working_deadline(start: datetime, minutes: int):
    """Adds working minutes (Mon–Sat 9:30–18:30 IST) to a time."""
    s = await get_settings()
    wh = s.get("working_hours") or {"start": "09:30", "end": "18:30", "days": [0, 1, 2, 3, 4, 5]}
    sh, sm = map(int, wh["start"].split(":"))
    eh, em = map(int, wh["end"].split(":"))
    t = start.astimezone(IST)
    left = minutes
    for _ in range(14 * 24 * 60):
        day_start = t.replace(hour=sh, minute=sm, second=0, microsecond=0)
        day_end = t.replace(hour=eh, minute=em, second=0, microsecond=0)
        if t.weekday() not in wh["days"] or t >= day_end:
            t = (t + timedelta(days=1)).replace(hour=sh, minute=sm, second=0, microsecond=0)
            continue
        if t < day_start:
            t = day_start
        avail = (day_end - t).total_seconds() / 60
        if left <= avail:
            return t + timedelta(minutes=left)
        left -= avail
        t = (t + timedelta(days=1)).replace(hour=sh, minute=sm, second=0, microsecond=0)
    return t


async def route_lead(doc):
    """Owner from the routing rules (service / supply / town -> branch and team), round-robin within the team."""
    s = await get_settings()
    rules = s.get("routing_rules") or []
    town = (doc.get("town") or "").strip().lower()
    team, branch = None, None
    for r in rules:
        if r.get("service") and r["service"] != doc.get("service"):
            continue
        if r.get("supply") and r["supply"] != doc.get("supply"):
            continue
        if r.get("towns") and town not in [t.strip().lower() for t in r["towns"]]:
            continue
        team, branch = r.get("team") or [], r.get("branch_id")
        break
    if not branch and town:
        b = await db.branches.find_one({"city": {"$regex": f"^{town}$", "$options": "i"}}, {"_id": 0, "id": 1})
        branch = b and b["id"]
    if not branch:
        b = await db.branches.find_one({"is_head_office": True}, {"_id": 0, "id": 1})
        branch = b and b["id"]
    if not team:
        q = {"role": "sales", "active": True}
        if branch:
            q["$or"] = [{"branch_ids": branch}, {"branch_ids": []}, {"branch_ids": {"$exists": False}}]
        team = [u["id"] for u in await db.users.find(q, {"_id": 0, "id": 1}).sort("created_at", 1).to_list(50)]
    if not team:
        team = [u["id"] for u in await db.users.find({"role": {"$in": ["branch_manager", "director"]}, "active": True}, {"_id": 0, "id": 1}).to_list(5)]
    owner = None
    if team:
        c = await db.counters.find_one_and_update({"_id": f"rr:{branch}"}, {"$inc": {"seq": 1}}, upsert=True, return_document=True)
        owner = team[(c["seq"] - 1) % len(team)]
    return owner, branch


async def lead_before(doc, old, user, creating):
    if creating:
        if not doc.get("owner_id") or not doc.get("branch_id") or (user and user.get("role") in ("super_admin",) and not doc.get("branch_id")):
            owner, branch = await route_lead(doc)
            doc.setdefault("owner_id", owner) if not doc.get("owner_id") else None
            if not doc.get("branch_id"):
                doc["branch_id"] = branch
        s = await get_settings()
        due = await working_deadline(now(), int(s.get("first_response_minutes") or 30))
        doc["response_due_at"] = due.isoformat()
        if doc.get("consent") and not doc.get("consent_at"):
            doc["consent_at"] = now_iso()
    else:
        if doc.get("stage") == "lost" and not doc.get("lost_reason"):
            raise HTTPException(422, "Pick a lost reason")
        if doc.get("stage") == "on_hold" and not doc.get("hold_until"):
            raise HTTPException(422, "Set a re-engage date for leads on hold")
        if old and old.get("stage") == "new" and doc.get("stage") != "new" and not doc.get("first_response_at"):
            doc["first_response_at"] = now_iso()
    doc["probability"] = STAGE_PROB.get(doc.get("stage") or "new", 5)
    doc["score"] = lead_score(doc)


async def lead_after(doc, old, user, creating):
    if creating and doc.get("owner_id"):
        await notify([doc["owner_id"]], f"New lead: {doc.get('name')}{', ' + doc['company'] if doc.get('company') else ''}",
                     f"{label_of('services', doc.get('service'))} in {doc.get('town') or 'an unknown town'}. Respond by {str(doc.get('response_due_at'))[11:16]}",
                     f"/erp/e/leads/{doc['id']}", kind="assigned")
    if not creating and old and old.get("owner_id") != doc.get("owner_id") and doc.get("owner_id"):
        await notify([doc["owner_id"]], f"Lead assigned to you: {doc.get('name')}", "", f"/erp/e/leads/{doc['id']}", kind="assigned")
    if not creating and old and old.get("stage") != doc.get("stage") and doc.get("stage") == "won":
        await notify_roles(["director", "branch_manager"], f"Won: {doc.get('name')} {doc.get('company') or ''}", "Convert it to a client and project.",
                           f"/erp/e/leads/{doc['id']}", branch_id=doc.get("branch_id"))


hook("leads", before=lead_before, after=lead_after)


async def activity_after(doc, old, user, creating):
    if creating and doc.get("lead_id"):
        lead = await db.leads.find_one({"id": doc["lead_id"]}, {"_id": 0})
        if lead:
            upd = {}
            if not lead.get("first_response_at") and doc.get("kind") in ("call", "whatsapp", "email", "meeting", "site_visit"):
                upd["first_response_at"] = now_iso()
            if lead.get("stage") == "new" and doc.get("kind") in ("call", "whatsapp", "email", "meeting", "site_visit"):
                upd["stage"] = "contacted"
                upd["probability"] = STAGE_PROB["contacted"]
            if doc.get("due_at") and not doc.get("done"):
                upd["next_follow_up"] = doc["due_at"]
            if upd:
                await db.leads.update_one({"id": lead["id"]}, {"$set": upd})
    if doc.get("done") and not doc.get("done_at"):
        await db.activities.update_one({"id": doc["id"]}, {"$set": {"done_at": now_iso()}})


hook("activities", after=activity_after)


async def survey_after(doc, old, user, creating):
    if doc.get("lead_id"):
        lead = await db.leads.find_one({"id": doc["lead_id"]}, {"_id": 0, "stage": 1})
        if lead and lead.get("stage") in ("new", "contacted", "survey_scheduled"):
            st = "survey_done" if doc.get("status") == "done" else "survey_scheduled"
            await db.leads.update_one({"id": doc["lead_id"]}, {"$set": {"stage": st, "probability": STAGE_PROB[st]}})
    if creating and doc.get("engineer_id"):
        await notify([doc["engineer_id"]], f"Site survey {str(doc.get('scheduled_at'))[:16].replace('T', ' ')}", doc.get("address") or "",
                     f"/erp/e/surveys/{doc['id']}", kind="assigned")


hook("surveys", after=survey_after)


async def qr_before(doc, old, user, creating):
    if creating and not doc.get("token"):
        doc["token"] = secrets.token_urlsafe(5)
        doc["scans"], doc["leads"] = 0, 0


hook("qr_codes", before=qr_before)


# ====================================================================== estimation
async def fill_item_lines(lines, rate_key="rate", cost_key="cost"):
    ids = list({ln.get("item_id") for ln in lines or [] if ln.get("item_id")})
    items = {i["id"]: i for i in await db.items.find({"id": {"$in": ids}}, {"_id": 0}).to_list(len(ids) or 1)}
    for ln in lines or []:
        it = items.get(ln.get("item_id"))
        if not it:
            continue
        if not ln.get("description"):
            ln["description"] = it["name"] + (f" — {it['spec']}" if it.get("spec") else "")
        if ln.get(rate_key) in (None, "") and rate_key:
            ln[rate_key] = it.get("std_rate") or 0
        if cost_key and ln.get(cost_key) in (None, ""):
            ln[cost_key] = it.get("cost_rate") or 0
        if not ln.get("unit"):
            ln["unit"] = it.get("unit") or "nos"
        if not ln.get("make") and it.get("make") and "make" in ln:
            ln["make"] = it["make"]
        if ln.get("gst_rate") in (None, "") and it.get("gst_rate"):
            ln["gst_rate"] = it["gst_rate"]


async def boq_before(doc, old, user, creating):
    await fill_item_lines(doc.get("lines"), "rate", "cost")


hook("boqs", before=boq_before)


async def ra_before(doc, old, user, creating):
    for ln in doc.get("lines") or []:
        if ln.get("item_id") and not ln.get("rate"):
            it = await db.items.find_one({"id": ln["item_id"]}, {"_id": 0, "cost_rate": 1})
            ln["rate"] = (it or {}).get("cost_rate") or 0


hook("rate_analyses", before=ra_before)


async def proposal_before(doc, old, user, creating):
    if doc.get("boq_id"):
        b = await db.boqs.find_one({"id": doc["boq_id"]}, {"_id": 0})
        if b:
            for k in ("subtotal", "discount_pct", "taxable", "gst", "total", "margin_pct"):
                doc[k] = b.get(k)
            doc.setdefault("account_id", b.get("account_id"))
            doc.setdefault("lead_id", b.get("lead_id"))
    if not doc.get("valid_until"):
        doc["valid_until"] = (today_ist() + timedelta(days=int(doc.get("validity_days") or 30))).isoformat()


async def proposal_action(name, new, old, user):
    extra = {}
    if name == "send":
        extra["sent_at"] = now_iso()
        extra["valid_until"] = (today_ist() + timedelta(days=int(new.get("validity_days") or 30))).isoformat()
        if new.get("lead_id"):
            await db.leads.update_one({"id": new["lead_id"], "stage": {"$in": ["new", "contacted", "survey_scheduled", "survey_done", "estimating"]}},
                                      {"$set": {"stage": "quoted", "probability": STAGE_PROB["quoted"]}})
    if name == "accept":
        extra["accepted_at"] = now_iso()
        extra["accepted_by"] = new.get("accepted_by") or (user or {}).get("name")
        if new.get("lead_id"):
            await db.leads.update_one({"id": new["lead_id"]}, {"$set": {"stage": "won", "probability": 100}})
    if name == "decline" and new.get("lead_id"):
        extra["decline_reason"] = new.get("status_reason")
    return extra


hook("proposals", before=proposal_before, action=proposal_action)


# ====================================================================== projects
async def project_before(doc, old, user, creating):
    if doc.get("actual_end") and doc.get("dlp_months"):
        e = d(doc["actual_end"])
        m = int(doc["dlp_months"])
        y, mo = e.year + (e.month - 1 + m) // 12, (e.month - 1 + m) % 12 + 1
        doc["dlp_until"] = date(y, mo, min(e.day, 28)).isoformat()
    if not doc.get("slug") and doc.get("name"):
        import re
        doc["slug"] = re.sub(r"[^a-z0-9]+", "-", (doc.get("public_title") or doc["name"]).lower()).strip("-")[:80]
    doc.setdefault("percent_complete", 0)


async def recompute_project(project_id):
    ms = await db.milestones.find({"project_id": project_id, "deleted": {"$ne": True}}, {"_id": 0}).to_list(500)
    tw = sum(float(m.get("weight_pct") or 0) for m in ms)
    pct = round(sum(float(m.get("weight_pct") or 0) * float(m.get("percent") or 0) for m in ms) / tw, 1) if tw else 0
    await db.projects.update_one({"id": project_id}, {"$set": {"percent_complete": pct}})


async def milestone_before(doc, old, user, creating):
    p = float(doc.get("percent") or 0)
    today = today_ist().isoformat()
    if p >= 100:
        doc["status"] = "done"
        doc.setdefault("actual_end", today) if not doc.get("actual_end") else None
    elif doc.get("planned_end") and doc["planned_end"] < today:
        doc["status"] = "delayed"
    elif p > 0:
        doc["status"] = "in_progress"
        if not doc.get("actual_start"):
            doc["actual_start"] = today
    else:
        doc["status"] = "not_started"


async def milestone_after(doc, old, user, creating):
    await recompute_project(doc["project_id"])


hook("projects", before=project_before)
hook("milestones", before=milestone_before, after=milestone_after)


async def dpr_after(doc, old, user, creating):
    if creating:
        p = await db.projects.find_one({"id": doc["project_id"]}, {"_id": 0, "manager_id": 1, "name": 1})
        if p and p.get("manager_id") and p["manager_id"] != (user or {}).get("id"):
            await notify([p["manager_id"]], f"Daily report: {p['name']} ({doc['date']})", f"{doc.get('manpower_total') or 0} people on site",
                         f"/erp/e/dprs/{doc['id']}")


hook("dprs", after=dpr_after)


async def drawing_action(name, new, old, user):
    if name == "submit":
        return {"submitted_on": today_ist().isoformat()}


hook("drawings", action=drawing_action)


async def ra_bill_before(doc, old, user, creating):
    p = await db.projects.find_one({"id": doc["project_id"]}, {"_id": 0}) or {}
    if creating:
        n = await db.ra_bills.count_documents({"project_id": doc["project_id"], "deleted": {"$ne": True}})
        doc["bill_no"] = n + 1
        if doc.get("retention_pct") in (None, ""):
            doc["retention_pct"] = p.get("retention_pct") or 0
        prev = await db.ra_bills.find({"project_id": doc["project_id"], "deleted": {"$ne": True}}, {"_id": 0, "lines": 1, "advance_recovery": 1}).to_list(200)
        done = {}
        for b in prev:
            for ln in b.get("lines") or []:
                k = (ln.get("description") or "").strip().lower()
                done[k] = done.get(k, 0) + float(ln.get("this_qty") or 0)
        for ln in doc.get("lines") or []:
            k = (ln.get("description") or "").strip().lower()
            if not ln.get("prev_qty"):
                ln["prev_qty"] = done.get(k, 0)
        if doc.get("advance_recovery") in (None, "") and p.get("mobilisation_advance"):
            recovered = sum(float(b.get("advance_recovery") or 0) for b in prev)
            left = float(p["mobilisation_advance"]) - recovered
            gross = sum(float(ln.get("this_qty") or 0) * float(ln.get("rate") or 0) for ln in doc.get("lines") or [])
            doc["advance_recovery"] = money(max(0, min(left, gross * float(p.get("advance_recovery_pct") or 0) / 100)))


async def ra_bill_approved(doc, user):
    await db.mb_entries.update_many({"ra_bill_id": doc["id"]}, {"$set": {"status": "billed"}})


hook("ra_bills", before=ra_bill_before, approved=ra_bill_approved)


async def generate_ra_from_mb(project_id, user, period_to=None):
    """Turns checked measurement-book entries into a draft RA bill (grouped by BOQ item)."""
    q = {"project_id": project_id, "status": "checked", "ra_bill_id": {"$in": [None, ""]}, "deleted": {"$ne": True}}
    if period_to:
        q["date"] = {"$lte": period_to}
    rows = await db.mb_entries.find(q, {"_id": 0}).to_list(5000)
    if not rows:
        raise HTTPException(409, "No checked measurements waiting to be billed")
    groups = {}
    for r in rows:
        k = (r.get("description") or "").strip()
        g = groups.setdefault(k, {"description": k, "unit": r.get("unit"), "this_qty": 0.0, "rate": r.get("rate") or 0})
        g["this_qty"] = round(g["this_qty"] + float(r.get("qty") or 0), 3)
    body = {"project_id": project_id, "period_from": min(r["date"] for r in rows), "period_to": period_to or max(r["date"] for r in rows),
            "lines": list(groups.values())}
    bill = await create_record("ra_bills", user, body)
    await db.mb_entries.update_many({"id": {"$in": [r["id"] for r in rows]}}, {"$set": {"ra_bill_id": bill["id"]}})
    return bill


async def variation_approved(doc, user):
    return None


hook("variations", approved=variation_approved)


# ====================================================================== testing & safety
async def test_action(name, new, old, user):
    if name == "issue":
        ins = await db.instruments.find_one({"id": new.get("instrument_id")}, {"_id": 0})
        if not ins:
            raise HTTPException(422, "Pick the instrument used")
        if not ins.get("calibration_due") or ins["calibration_due"] < (new.get("date") or today_ist().isoformat()):
            raise HTTPException(422, f"{ins['name']} ({ins.get('serial_no')}) was out of calibration on the test date — the certificate can't be issued")
        return {"issued_at": now_iso()}


hook("test_reports", action=test_action)


async def permit_before(doc, old, user, creating):
    if doc.get("ptype") == "ht_work" and doc.get("authorised_person_id"):
        ap = await db.authorised_persons.find_one({"user_id": doc["authorised_person_id"], "deleted": {"$ne": True},
                                                   "valid_until": {"$gte": today_ist().isoformat()}}, {"_id": 0})
        if not ap or not str(ap.get("level", "")).startswith(("HT", "EHV")):
            raise HTTPException(422, "HT work needs an authorised person from the HT register with a valid authorisation")
    if doc.get("valid_from") and doc.get("valid_to") and doc["valid_to"] <= doc["valid_from"]:
        raise HTTPException(422, "Permit end must be after its start")


async def permit_action(name, new, old, user):
    if name == "approve" and user["id"] == old.get("created_by"):
        raise HTTPException(403, "Someone else has to approve a permit you raised")
    if name == "close":
        return {"closed_at": now_iso()}
    if name in ("suspend",):
        await notify_roles(["safety", "project_manager"], f"Work stopped on permit {old.get('code')}", new.get("status_reason") or "", f"/erp/e/permits/{old['id']}", kind="alert")


hook("permits", before=permit_before, action=permit_action)


async def worker_before(doc, old, user, creating):
    if doc.get("id_last4"):
        digits = "".join(c for c in doc["id_last4"] if c.isdigit())
        doc["id_last4"] = digits[-4:]


hook("workers", before=worker_before)


# ====================================================================== procurement & stores
async def stock_qty(item_id, store_id):
    rows = await db.stock_moves.find({"item_id": item_id, "store_id": store_id}, {"_id": 0, "qty": 1}).to_list(100000)
    return round(sum(float(r["qty"]) for r in rows), 3)


async def avg_rate(item_id):
    rows = await db.stock_moves.find({"item_id": item_id, "qty": {"$gt": 0}}, {"_id": 0, "qty": 1, "rate": 1}).to_list(100000)
    q = sum(float(r["qty"]) for r in rows)
    v = sum(float(r["qty"]) * float(r.get("rate") or 0) for r in rows)
    if q:
        return round(v / q, 2)
    it = await db.items.find_one({"id": item_id}, {"_id": 0, "cost_rate": 1})
    return float((it or {}).get("cost_rate") or 0)


async def move(item_id, store_id, qty, kind, ref, user, rate=None, project_id=None, drum_no=None, serial_no=None, note=None, on=None):
    if rate is None:
        rate = await avg_rate(item_id)
    doc = {"id": new_id(), "date": on or today_ist().isoformat(), "item_id": item_id, "store_id": store_id, "qty": round(float(qty), 3),
           "rate": money(rate), "value": money(float(qty) * float(rate)), "kind": kind, "ref_code": ref.get("code"),
           "ref_entity": ref.get("_entity"), "ref_id": ref.get("id"), "project_id": project_id, "drum_no": drum_no,
           "serial_no": serial_no, "note": note, "created_at": now_iso(), "created_by": user["id"] if user else None, "deleted": False}
    await db.stock_moves.insert_one(dict(doc))
    return doc


async def po_before(doc, old, user, creating):
    for ln in doc.get("lines") or []:
        if ln.get("item_id") and ln.get("rate") in (None, ""):
            rc = await db.rate_contracts.find_one({"vendor_id": doc.get("vendor_id"), "item_id": ln["item_id"], "deleted": {"$ne": True},
                                                   "valid_to": {"$gte": today_ist().isoformat()}}, {"_id": 0})
            ln["rate"] = (rc or {}).get("rate")
    await fill_item_lines(doc.get("lines"), "rate", None)
    for ln in doc.get("lines") or []:
        ln.setdefault("received_qty", 0)


async def po_approved(doc, user):
    if doc.get("pr_id"):
        await db.purchase_requests.update_one({"id": doc["pr_id"]}, {"$set": {"status": "ordered"}})


hook("purchase_orders", before=po_before, approved=po_approved)


async def grn_before(doc, old, user, creating):
    po = await db.purchase_orders.find_one({"id": doc.get("po_id")}, {"_id": 0}) if doc.get("po_id") else None
    if po:
        doc.setdefault("vendor_id", po.get("vendor_id"))
        if not doc.get("project_id"):
            doc["project_id"] = po.get("project_id")
        open_qty = {}
        for ln in po.get("lines") or []:
            open_qty[ln.get("item_id")] = open_qty.get(ln.get("item_id"), 0) + float(ln.get("qty") or 0) - float(ln.get("received_qty") or 0)
        rates = {ln.get("item_id"): ln.get("rate") for ln in po.get("lines") or []}
        for ln in doc.get("lines") or []:
            ln["ordered_qty"] = round(open_qty.get(ln.get("item_id"), 0), 3)
            if ln.get("rate") in (None, ""):
                ln["rate"] = rates.get(ln.get("item_id"))
    for n, ln in enumerate(doc.get("lines") or [], 1):
        rec = float(ln.get("received_qty") or 0)
        acc = float(ln.get("accepted_qty") if ln.get("accepted_qty") not in (None, "") else rec)
        ln["accepted_qty"] = acc
        if acc > rec + 1e-9:
            raise HTTPException(422, f"Line {n}: accepted can't be more than received")
        if po and acc > float(ln.get("ordered_qty") or 0) + 1e-9:
            raise HTTPException(422, f"Line {n}: more than the open PO quantity ({ln.get('ordered_qty')}) — no over-receipt")
        short = po and rec + 1e-9 < float(ln.get("ordered_qty") or 0)
        if (acc < rec or short) and not (ln.get("reason") or "").strip() and doc.get("status") == "posted":
            raise HTTPException(422, f"Line {n}: give a reason for the shortage or rejection")


async def grn_action(name, new, old, user):
    if name != "post":
        return None
    for n, ln in enumerate(new.get("lines") or [], 1):
        rec = float(ln.get("received_qty") or 0)
        acc = float(ln.get("accepted_qty") or 0)
        short = new.get("po_id") and rec + 1e-9 < float(ln.get("ordered_qty") or 0)
        if (acc < rec or short) and not (ln.get("reason") or "").strip():
            raise HTTPException(422, f"Line {n}: give a reason for the shortage or rejection before posting")
    ref = {"code": new.get("code"), "_entity": "grns", "id": new["id"]}
    for ln in new.get("lines") or []:
        acc = float(ln.get("accepted_qty") or 0)
        if acc <= 0 or not ln.get("item_id"):
            continue
        await move(ln["item_id"], new["store_id"], acc, "grn", ref, user, rate=float(ln.get("rate") or 0), project_id=new.get("project_id"),
                   drum_no=ln.get("drum_no"), on=new.get("date"))
        it = await db.items.find_one({"id": ln["item_id"]}, {"_id": 0}) or {}
        if ln.get("drum_no"):
            await db.cable_drums.insert_one({"id": new_id(), "drum_no": ln["drum_no"], "item_id": ln["item_id"], "make": it.get("make"),
                                             "size": it.get("spec"), "initial_length": float(ln.get("drum_length") or acc),
                                             "remaining_length": float(ln.get("drum_length") or acc), "store_id": new["store_id"],
                                             "vendor_id": new.get("vendor_id"), "cuts": [], "status": "in_store", "returnable": True,
                                             "created_at": now_iso(), "created_by": user["id"], "deleted": False})
        for sn in [x.strip() for x in (ln.get("serial_nos") or "").splitlines() if x.strip()]:
            await db.serial_items.insert_one({"id": new_id(), "item_id": ln["item_id"], "serial_no": sn, "make": it.get("make"),
                                              "store_id": new["store_id"], "grn_id": new["id"], "status": "in_store",
                                              "created_at": now_iso(), "created_by": user["id"], "deleted": False})
    if new.get("po_id"):
        po = await db.purchase_orders.find_one({"id": new["po_id"]}, {"_id": 0})
        if po:
            got = {}
            for ln in new.get("lines") or []:
                got[ln.get("item_id")] = got.get(ln.get("item_id"), 0) + float(ln.get("accepted_qty") or 0)
            full = True
            for pl in po.get("lines") or []:
                add = min(got.get(pl.get("item_id"), 0), float(pl.get("qty") or 0) - float(pl.get("received_qty") or 0))
                pl["received_qty"] = round(float(pl.get("received_qty") or 0) + max(add, 0), 3)
                got[pl.get("item_id")] = got.get(pl.get("item_id"), 0) - max(add, 0)
                if pl["received_qty"] + 1e-9 < float(pl.get("qty") or 0):
                    full = False
            await db.purchase_orders.update_one({"id": po["id"]}, {"$set": {"lines": po["lines"], "status": "received" if full else "partly_received"}})
    return {"posted_at": now_iso()}


hook("grns", before=grn_before, action=grn_action)


async def mm_before(doc, old, user, creating):
    t = doc.get("mtype")
    if t in ("issue", "transfer", "scrap", "adjustment") and not doc.get("from_store_id"):
        raise HTTPException(422, "Pick the store the material leaves from")
    if t in ("return", "transfer") and not doc.get("to_store_id"):
        raise HTTPException(422, "Pick the store the material goes to")
    if t in ("issue", "return") and not doc.get("project_id"):
        raise HTTPException(422, "Pick the project")
    if t == "transfer" and doc.get("from_store_id") == doc.get("to_store_id"):
        raise HTTPException(422, "From and to stores must differ")


async def mm_action(name, new, old, user):
    t = new.get("mtype")
    ref = {"code": new.get("code"), "_entity": "material_moves", "id": new["id"]}
    lines = new.get("lines") or []
    if name == "post":
        if t in ("issue", "transfer", "scrap"):
            for n, ln in enumerate(lines, 1):
                have = await stock_qty(ln["item_id"], new["from_store_id"])
                if float(ln.get("qty") or 0) > have + 1e-9:
                    it = await db.items.find_one({"id": ln["item_id"]}, {"_id": 0, "name": 1})
                    raise HTTPException(422, f"Line {n}: only {have:g} of {(it or {}).get('name', 'this item')} in stock")
        for ln in lines:
            q = float(ln.get("qty") or 0)
            if t == "issue":
                await move(ln["item_id"], new["from_store_id"], -q, "issue", ref, user, project_id=new.get("project_id"), serial_no=ln.get("serial_no"), on=new.get("date"))
                await drum_cut(ln, q, new, user)
                if ln.get("serial_no"):
                    await db.serial_items.update_one({"serial_no": ln["serial_no"], "item_id": ln["item_id"]}, {"$set": {"status": "issued", "project_id": new.get("project_id"), "store_id": None}})
            elif t == "return":
                await move(ln["item_id"], new["to_store_id"], q, "return", ref, user, project_id=new.get("project_id"), on=new.get("date"))
            elif t == "transfer":
                await move(ln["item_id"], new["from_store_id"], -q, "transfer_out", ref, user, note="in transit", on=new.get("date"))
            elif t == "adjustment":
                await move(ln["item_id"], new["from_store_id"], q, "adjustment", ref, user, note=ln.get("remarks"), on=new.get("date"))
            elif t == "scrap":
                await move(ln["item_id"], new["from_store_id"], -q, "scrap", ref, user, on=new.get("date"))
        if t == "transfer":
            return {"status": "in_transit"}
    if name == "receive":
        for ln in lines:
            await move(ln["item_id"], new["to_store_id"], float(ln.get("qty") or 0), "transfer_in", ref, user, on=today_ist().isoformat())
        return {"received_at": now_iso()}
    return None


async def drum_cut(ln, qty, mm, user):
    if not ln.get("drum_id"):
        return
    dr = await db.cable_drums.find_one({"id": ln["drum_id"]}, {"_id": 0})
    if not dr:
        return
    if qty > float(dr.get("remaining_length") or 0) + 1e-6:
        raise HTTPException(422, f"Drum {dr['drum_no']} has only {dr.get('remaining_length')} m left")
    cuts = (dr.get("cuts") or []) + [{"date": mm.get("date"), "length": qty, "project_id": mm.get("project_id"), "circuit": ln.get("remarks"), "by": user.get("name")}]
    rem = round(float(dr["initial_length"]) - sum(float(c.get("length") or 0) for c in cuts), 2)
    await db.cable_drums.update_one({"id": dr["id"]}, {"$set": {"cuts": cuts, "remaining_length": rem, "project_id": mm.get("project_id"),
                                                               "status": "empty" if rem <= 0.5 else "at_site"}})


hook("material_moves", before=mm_before, action=mm_action)


async def drum_before(doc, old, user, creating):
    cut = sum(float(c.get("length") or 0) for c in doc.get("cuts") or [])
    doc["remaining_length"] = round(float(doc.get("initial_length") or 0) - cut, 2)
    if doc["remaining_length"] < -0.01:
        raise HTTPException(422, "Cuts add up to more than the drum length")
    if doc["remaining_length"] <= 0.5 and doc.get("status") in ("in_store", "at_site"):
        doc["status"] = "empty"


hook("cable_drums", before=drum_before)


async def vendor_bill_before(doc, old, user, creating):
    if not doc.get("po_id"):
        doc["match_status"] = "no_po"
        return
    po = await db.purchase_orders.find_one({"id": doc["po_id"]}, {"_id": 0}) or {}
    grns = await db.grns.find({"po_id": doc["po_id"], "status": "posted", "deleted": {"$ne": True}}, {"_id": 0}).to_list(200)
    if not grns:
        doc["match_status"] = "no_grn"
        return
    accepted = sum(float(ln.get("accepted_qty") or 0) for g in grns for ln in g.get("lines") or [])
    billed_qty = sum(float(ln.get("qty") or 0) for ln in doc.get("lines") or [])
    po_rates = sorted(float(ln.get("rate") or 0) for ln in po.get("lines") or [])
    bill_rates = sorted(float(ln.get("rate") or 0) for ln in doc.get("lines") or [])
    if abs(billed_qty - accepted) > 0.01:
        doc["match_status"] = "qty_mismatch"
    elif po_rates and bill_rates and any(b > max(po_rates) + 0.01 for b in bill_rates):
        doc["match_status"] = "rate_mismatch"
    else:
        doc["match_status"] = "matched"
    doc.setdefault("paid", 0)


hook("vendor_bills", before=vendor_bill_before)


async def vp_action(name, new, old, user):
    if name == "pay":
        amt = float(new.get("amount") or 0) + float(new.get("tds") or 0)
        if new.get("vendor_bill_id"):
            b = await db.vendor_bills.find_one({"id": new["vendor_bill_id"]}, {"_id": 0})
            if b:
                paid = round(float(b.get("paid") or 0) + float(new.get("amount") or 0), 2)
                bal = round(float(b.get("payable") or 0) - paid, 2)
                await db.vendor_bills.update_one({"id": b["id"]}, {"$set": {"paid": paid, "balance": bal, "status": "paid" if bal <= 0.5 else "part_paid"}})
        if new.get("sc_bill_id"):
            b = await db.sc_bills.find_one({"id": new["sc_bill_id"]}, {"_id": 0})
            if b:
                paid = round(float(b.get("paid") or 0) + amt, 2)
                await db.sc_bills.update_one({"id": b["id"]}, {"$set": {"paid": paid, "status": "paid" if paid >= float(b.get("net") or 0) - 0.5 else b.get("status")}})
        return {"paid_at": now_iso()}


hook("vendor_payments", action=vp_action)


async def sc_bill_before(doc, old, user, creating):
    wo = await db.work_orders.find_one({"id": doc.get("work_order_id")}, {"_id": 0}) or {}
    doc["vendor_id"] = doc.get("vendor_id") or wo.get("vendor_id")
    doc["project_id"] = doc.get("project_id") or wo.get("project_id")
    if creating:
        if doc.get("retention_pct") in (None, ""):
            doc["retention_pct"] = wo.get("retention_pct")
        if doc.get("tds_pct") in (None, ""):
            doc["tds_pct"] = wo.get("tds_pct")
        prev = await db.sc_bills.find({"work_order_id": doc.get("work_order_id"), "deleted": {"$ne": True}}, {"_id": 0, "lines": 1}).to_list(200)
        done = {}
        for b in prev:
            for ln in b.get("lines") or []:
                k = (ln.get("description") or "").strip().lower()
                done[k] = done.get(k, 0) + float(ln.get("this_qty") or 0)
        for ln in doc.get("lines") or []:
            if not ln.get("prev_qty"):
                ln["prev_qty"] = done.get((ln.get("description") or "").strip().lower(), 0)
    doc.setdefault("paid", 0)


hook("sc_bills", before=sc_bill_before)


async def vreg_after(doc, old, user, creating):
    if not creating and old and old.get("status") != "approved" and doc.get("status") == "approved" and not doc.get("vendor_id"):
        v = await create_record("vendors", user, {"name": doc["company"], "vtype": doc.get("vtype") or "supplier", "gstin": doc.get("gstin"),
                                                  "phone": doc.get("phone"), "email": doc.get("email"), "town": doc.get("town"),
                                                  "contact_person": doc.get("contact_person"), "licence_no": doc.get("licence_no")}, system=True)
        await db.vendor_registrations.update_one({"id": doc["id"]}, {"$set": {"vendor_id": v["id"]}})


hook("vendor_registrations", after=vreg_after)


# ====================================================================== finance
async def invoice_before(doc, old, user, creating):
    if doc.get("ra_bill_id") and not doc.get("lines"):
        ra = await db.ra_bills.find_one({"id": doc["ra_bill_id"]}, {"_id": 0})
        if ra:
            p = await db.projects.find_one({"id": ra["project_id"]}, {"_id": 0, "name": 1})
            doc["lines"] = [{"description": f"RA bill {ra.get('bill_no')} — {(p or {}).get('name', '')} (up to {ra.get('period_to')})", "hsn": "9954",
                             "qty": 1, "unit": "ls", "rate": ra.get("certified_amount") or ra.get("gross"), "gst_rate": ra.get("gst_rate") or "18"}]
            doc["retention"] = ra.get("retention")
            doc["tds_expected"] = ra.get("tds")
            doc["project_id"] = ra["project_id"]
            doc["itype"] = "ra_bill"
    doc.setdefault("paid", 0)
    if not doc.get("due_date") and doc.get("date"):
        acc = await db.accounts.find_one({"id": doc.get("account_id")}, {"_id": 0, "credit_days": 1}) or {}
        doc["due_date"] = (d(doc["date"]) + timedelta(days=int(acc.get("credit_days") or 30))).isoformat()


async def invoice_action(name, new, old, user):
    if name == "issue" and new.get("ra_bill_id"):
        await db.ra_bills.update_one({"id": new["ra_bill_id"]}, {"$set": {"status": "invoiced", "invoice_id": new["id"]}})
    if name == "issue":
        return {"issued_at": now_iso()}


hook("invoices", before=invoice_before, action=invoice_action)


async def apply_receipt(doc):
    allocs = doc.get("allocations") or []
    if not allocs:
        # oldest unpaid invoices of the client first
        left = float(doc.get("amount") or 0) + float(doc.get("tds") or 0)
        invs = await db.invoices.find({"account_id": doc["account_id"], "status": {"$in": ["issued", "part_paid"]}, "deleted": {"$ne": True}},
                                      {"_id": 0}).sort("date", 1).to_list(500)
        for inv in invs:
            if left <= 0:
                break
            take = min(left, float(inv.get("balance") or 0))
            if take > 0:
                allocs.append({"invoice_id": inv["id"], "amount": money(take)})
                left -= take
        await db.receipts.update_one({"id": doc["id"]}, {"$set": {"allocations": allocs}})
    for a in allocs:
        inv = await db.invoices.find_one({"id": a.get("invoice_id")}, {"_id": 0})
        if not inv:
            continue
        paid = money(float(inv.get("paid") or 0) + float(a.get("amount") or 0))
        bal = money(float(inv.get("receivable") or inv.get("total") or 0) - paid)
        await db.invoices.update_one({"id": inv["id"]}, {"$set": {"paid": paid, "balance": bal, "status": "paid" if bal <= 0.5 else "part_paid"}})
        if inv.get("ra_bill_id") and bal <= 0.5:
            await db.ra_bills.update_one({"id": inv["ra_bill_id"]}, {"$set": {"status": "paid"}})


async def receipt_before(doc, old, user, creating):
    if creating and user and user.get("role") not in ("client",):
        doc["status"] = "confirmed"


async def receipt_after(doc, old, user, creating):
    if creating and doc.get("status") == "confirmed":
        await apply_receipt(doc)
    if creating and doc.get("status") == "pending":
        await notify_roles(["accounts"], f"Client says they paid ₹{float(doc.get('amount') or 0):,.0f}", doc.get("reference") or "", f"/erp/e/receipts/{doc['id']}", kind="alert")


async def receipt_action(name, new, old, user):
    if name == "confirm":
        await apply_receipt(new)
        return {"confirmed_by": user["id"], "confirmed_at": now_iso()}


hook("receipts", before=receipt_before, after=receipt_after, action=receipt_action)


# ====================================================================== service
async def sla_hours(priority, amc_id=None):
    s = await get_settings()
    sla = {**SLA_DEFAULTS, **(s.get("sla") or {})}
    reply, fix = sla.get(priority or "normal", SLA_DEFAULTS["normal"])
    if amc_id:
        amc = await db.amc_contracts.find_one({"id": amc_id}, {"_id": 0})
        if amc and priority in ("urgent", "high"):
            reply, fix = min(reply, amc.get("response_hours") or reply), min(fix, amc.get("restore_hours") or fix)
    return reply, fix


async def ticket_before(doc, old, user, creating):
    if creating or (old and old.get("priority") != doc.get("priority")):
        amc_id = None
        if doc.get("asset_id"):
            a = await db.installed_assets.find_one({"id": doc["asset_id"]}, {"_id": 0})
            if a:
                doc.setdefault("account_id", a.get("account_id")) if not doc.get("account_id") else None
                amc_id = a.get("amc_id")
        reply, fix = await sla_hours(doc.get("priority"), amc_id)
        base = datetime.fromisoformat(doc.get("created_at") or now_iso()) if not creating else now()
        doc["respond_by"] = (base + timedelta(hours=reply)).isoformat()
        doc["restore_by"] = (base + timedelta(hours=fix)).isoformat()
    if doc.get("assigned_to") and doc.get("status") == "new":
        doc["status"] = "assigned"
    t = now_iso()
    if doc.get("status") in ("resolved", "closed") and not doc.get("resolved_at"):
        doc["resolved_at"] = t
    doc["sla_breached"] = bool((doc.get("restore_by") and (doc.get("resolved_at") or t) > doc["restore_by"]) or
                               (doc.get("respond_by") and not doc.get("first_response_at") and t > doc["respond_by"]))


async def ticket_after(doc, old, user, creating):
    if doc.get("assigned_to") and (creating or (old and old.get("assigned_to") != doc.get("assigned_to"))):
        await notify([doc["assigned_to"]], f"Service request {doc.get('code')}: {doc.get('title')}",
                     f"{doc.get('priority', '').capitalize()} priority, fix by {str(doc.get('restore_by'))[:16].replace('T', ' ')}", f"/erp/e/tickets/{doc['id']}", kind="assigned")
    if creating and doc.get("priority") == "urgent":
        await notify_roles(["service_manager"], f"Urgent service request: {doc.get('title')}", "", f"/erp/e/tickets/{doc['id']}", kind="sla")


async def ticket_action(name, new, old, user):
    extra = {}
    if not old.get("first_response_at") and name in ("start", "wait", "resolve"):
        extra["first_response_at"] = now_iso()
    if name == "resolve":
        extra["resolved_at"] = now_iso()
    if name == "reopen":
        extra["resolved_at"] = None
    return extra


hook("tickets", before=ticket_before, after=ticket_after, action=ticket_action)


async def asset_before(doc, old, user, creating):
    if creating and not doc.get("qr_token"):
        doc["qr_token"] = secrets.token_urlsafe(6)


hook("installed_assets", before=asset_before)


async def amc_action(name, new, old, user):
    if name == "activate":
        start, end = d(new["start"]), d(new["end"])
        n = max(1, int(new.get("visits_per_year") or 1))
        days = (end - start).days
        years = max(1, round(days / 365))
        count = n * years
        gap = days / count
        for k in range(count):
            when = start + timedelta(days=int(gap * k + gap / 2))
            await create_record("pm_jobs", user, {"amc_id": new["id"], "account_id": new["account_id"], "asset_ids": new.get("asset_ids") or [],
                                                  "scheduled_on": when.isoformat()}, system=True)
        await db.installed_assets.update_many({"id": {"$in": new.get("asset_ids") or []}}, {"$set": {"amc_id": new["id"]}})
    return None


hook("amc_contracts", action=amc_action)


async def pm_action(name, new, old, user):
    if name == "complete":
        today = today_ist()
        amc = await db.amc_contracts.find_one({"id": new.get("amc_id")}, {"_id": 0}) or {}
        gap = int(365 / max(1, int(amc.get("visits_per_year") or 4)))
        await db.installed_assets.update_many({"id": {"$in": new.get("asset_ids") or []}},
                                              {"$set": {"last_service_on": today.isoformat(), "next_service_on": (today + timedelta(days=gap)).isoformat()}})
        return {"completed_at": now_iso()}


hook("pm_jobs", action=pm_action)


# ====================================================================== HR
def haversine(a, b):
    R_ = 6371000
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lng"], b["lat"], b["lng"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R_ * math.asin(math.sqrt(h))


async def attendance_before(doc, old, user, creating):
    site = None
    if doc.get("project_id"):
        p = await db.projects.find_one({"id": doc["project_id"]}, {"_id": 0, "gps": 1})
        site = (p or {}).get("gps")
    elif doc.get("branch_id_at"):
        b = await db.branches.find_one({"id": doc["branch_id_at"]}, {"_id": 0, "lat": 1, "lng": 1})
        if b and b.get("lat"):
            site = {"lat": b["lat"], "lng": b["lng"]}
    flag = ""
    if site and doc.get("in_gps"):
        dist = haversine(site, doc["in_gps"])
        doc["distance_m"] = round(dist)
        s = await get_settings()
        if dist > float(s.get("geofence_m") or 300):
            flag = "outside"
    if doc.get("check_in") and doc.get("check_out"):
        a, b = datetime.fromisoformat(doc["check_in"]), datetime.fromisoformat(doc["check_out"])
        doc["hours"] = round(max((b - a).total_seconds(), 0) / 3600, 2)
    elif doc.get("check_in") and doc.get("date") and doc["date"] < today_ist().isoformat():
        flag = flag or "no_checkout"
    doc["flag"] = flag


hook("attendance", before=attendance_before)


async def liaison_before(doc, old, user, creating):
    if old and old.get("stage") != doc.get("stage"):
        stages = doc.get("stages") or []
        for s in stages:
            if s.get("stage") == old.get("stage") and not s.get("done_on"):
                s["done_on"] = today_ist().isoformat()
        if not any(s.get("stage") == doc.get("stage") for s in stages):
            stages.append({"stage": doc.get("stage"), "expected_on": None, "done_on": today_ist().isoformat() if doc.get("stage") in ("energised", "closed") else None, "notes": ""})
        doc["stages"] = stages


hook("liaisons", before=liaison_before)


async def insight_before(doc, old, user, creating):
    if doc.get("status") == "published" and not doc.get("publish_at"):
        doc["publish_at"] = now_iso()[:16]
    if doc.get("status") == "scheduled" and not doc.get("publish_at"):
        raise HTTPException(422, "Set the publish time for a scheduled post")


hook("insights", before=insight_before)


async def testimonial_before(doc, old, user, creating):
    if doc.get("published") and not doc.get("permission"):
        raise HTTPException(422, "Only testimonials the client agreed to share can be published")


hook("testimonials", before=testimonial_before)


async def account_before(doc, old, user, creating):
    if doc.get("show_logo") and not doc.get("logo"):
        pass


hook("accounts", before=account_before)
