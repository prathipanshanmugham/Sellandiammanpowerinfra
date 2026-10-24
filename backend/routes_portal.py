"""Customer and partner portals: client, consultant / architect, vendor, subcontractor and referral partner.
Each person sees only their own records (scope rules in engine.portal_filter)."""
import hashlib
import os
import secrets
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request

import engine as ENG
from catalog import label_of
from core import (db, portal_dep, current_user, now, now_iso, new_id, today_ist, audit, notify_roles, notify, send_whatsapp, rate_limit,
                  get_settings, normalize_phone)
from routes_public import LeadIn, intake

router = APIRouter(prefix="/portal")
client_user = portal_dep("client")
consultant_user = portal_dep("consultant")
vendor_user = portal_dep("vendor", "subcontractor")
sub_user = portal_dep("subcontractor")
partner_user = portal_dep("partner")
any_portal = portal_dep("client", "consultant", "vendor", "subcontractor", "partner")
DEMO_OTP = os.environ.get("DEMO_OTP_ANY") == "true"


async def lst(key, user, params=None, size=50):
    try:
        return (await ENG.list_records(key, user, {**(params or {}), "size": str(size)}))
    except HTTPException:
        return {"items": [], "refs": {}, "total": 0}


@router.get("/summary")
async def summary(user=Depends(any_portal)):
    role = user["role"]
    out = {"role": role}
    if role == "client":
        acc = await db.accounts.find_one({"id": user.get("account_id")}, {"_id": 0, "id": 1, "name": 1, "town": 1})
        projects = await lst("projects", user)
        out["account"] = acc
        out["projects"] = projects["items"]
        out["refs"] = projects["refs"]
        appr = []
        for d_ in (await lst("drawings", user, {"status": "submitted"}))["items"]:
            appr.append({"entity": "drawings", "id": d_["id"], "title": f"Drawing {d_['number']} {d_['title']} (rev {d_.get('revision')})", "project_id": d_["project_id"]})
        for v in (await lst("variations", user, {"status": "sent"}))["items"]:
            appr.append({"entity": "variations", "id": v["id"], "title": f"Variation {v['code']}: {v['title']}", "amount": v.get("amount"), "project_id": v["project_id"]})
        for p in (await lst("proposals", user, {"status": "sent"}))["items"]:
            appr.append({"entity": "proposals", "id": p["id"], "title": f"Proposal {p['code']}: {p['title']}", "amount": p.get("total")})
        for s_ in (await lst("snags", user, {"status": "fixed"}))["items"]:
            appr.append({"entity": "snags", "id": s_["id"], "title": f"Snag fixed — please check: {s_['description'][:60]}", "project_id": s_["project_id"]})
        out["approvals"] = appr
        inv = await lst("invoices", user, {"status": "issued,part_paid"})
        out["invoices_due"] = inv["items"]
        out["outstanding"] = round(sum(float(i.get("balance") or 0) for i in inv["items"]), 2)
        out["tickets"] = (await lst("tickets", user, {"status": "new,assigned,in_progress,waiting_customer,reopened"}))["items"]
        out["amc"] = (await lst("amc_contracts", user, {"status": "active"}))["items"]
        visits = await lst("pm_jobs", user, {"status": "scheduled", "sort": "scheduled_on"}, 3)
        out["next_visits"] = visits["items"]
        out["assets"] = (await lst("installed_assets", user))["total"]
        out["approvals_tracker"] = (await lst("liaisons", user))["items"]
    elif role == "consultant":
        out["projects"] = (await lst("projects", user))["items"]
        out["drawings_to_review"] = (await lst("drawings", user, {"status": "submitted"}))["items"]
        out["rfis"] = (await lst("rfis", user, {"status": "open"}))["items"]
        out["tests"] = (await lst("test_reports", user, {}, 10))["items"]
    elif role in ("vendor", "subcontractor"):
        out["vendor"] = await db.vendors.find_one({"id": user.get("vendor_id")}, {"_id": 0, "id": 1, "name": 1, "vtype": 1})
        if role == "vendor":
            out["rfqs"] = (await lst("rfqs", user))["items"]
            out["pos"] = (await lst("purchase_orders", user))["items"]
            out["bills"] = (await lst("vendor_bills", user))["items"]
        else:
            out["work_orders"] = (await lst("work_orders", user))["items"]
            out["bills"] = (await lst("sc_bills", user))["items"]
            out["workers"] = (await lst("workers", user))["items"]
        out["payments"] = (await lst("vendor_payments", user, {"status": "paid"}))["items"]
    elif role == "partner":
        out.update(await partner_leads(user))
    return out


# ------------------------------------------------------------------ OTP for approvals by the client
@router.post("/otp")
async def send_otp(request: Request, user=Depends(any_portal)):
    rate_limit(request, "otp", 5, 600)
    code = f"{secrets.randbelow(10 ** 6):06d}"
    await db.otps.insert_one({"user_id": user["id"], "hash": hashlib.sha256(code.encode()).hexdigest(), "expires_at": (now() + timedelta(minutes=10)).isoformat(), "used": False})
    phone = user.get("phone")
    status = await send_whatsapp(phone, f"Your approval code is {code}. It is valid for 10 minutes. — Sellandiamman Power Infra")
    return {"sent_to": (phone or "")[-4:], "status": status}


async def check_otp(user, code):
    if DEMO_OTP and code and len(str(code)) == 6 and str(code) != "000000":
        return
    h = hashlib.sha256(str(code or "").encode()).hexdigest()
    rec = await db.otps.find_one({"user_id": user["id"], "hash": h, "used": False, "expires_at": {"$gt": now_iso()}})
    if not rec:
        raise HTTPException(422, "That code didn't work or has expired. Ask for a new one.")
    await db.otps.update_one({"_id": rec["_id"]}, {"$set": {"used": True}})


@router.post("/approve/{entity}/{rid}")
async def client_approve(entity: str, rid: str, body: dict, user=Depends(portal_dep("client", "consultant"))):
    decision = body.get("decision")
    comment = (body.get("comment") or "").strip()[:2000]
    await check_otp(user, body.get("otp"))
    doc = await ENG.get_record(entity, user, rid, raw=True)
    who = f"{user['name']} ({user['role']})"
    if entity == "drawings":
        if doc.get("status") != "submitted":
            raise HTTPException(409, "Already reviewed")
        st = {"approve": "approved", "approve_with_comments": "approved_with_comments", "reject": "rejected"}.get(decision)
        if not st:
            raise HTTPException(422, "Choose approve, approve with comments or reject")
        if st != "approved" and not comment:
            raise HTTPException(422, "Add your comments")
        upd = {"status": st, "comments": comment or doc.get("comments"), "approved_on": today_ist().isoformat() if st.startswith("approved") else None, "reviewed_by": who}
    elif entity == "variations" and user["role"] == "client":
        if doc.get("status") != "sent":
            raise HTTPException(409, "Already decided")
        st = {"approve": "client_approved", "reject": "client_rejected"}.get(decision)
        if not st:
            raise HTTPException(422, "Choose approve or reject")
        upd = {"status": st, "client_approved_on": today_ist().isoformat() if st == "client_approved" else None, "client_approved_by": who, "client_comment": comment}
    elif entity == "proposals" and user["role"] == "client":
        if doc.get("status") != "sent":
            raise HTTPException(409, "Already decided")
        st = {"approve": "accepted", "reject": "declined"}.get(decision)
        upd = {"status": st, "accepted_at": now_iso() if st == "accepted" else None, "accepted_by": who if st == "accepted" else None, "decline_reason": comment or None}
        if st == "accepted" and doc.get("lead_id"):
            await db.leads.update_one({"id": doc["lead_id"]}, {"$set": {"stage": "won", "probability": 100}})
    elif entity == "snags" and user["role"] == "client":
        st = {"approve": "verified", "reject": "open"}.get(decision)
        upd = {"status": st, "client_signoff": st == "verified", "client_comment": comment}
    else:
        raise HTTPException(404, "Nothing to approve here")
    await db[entity].update_one({"id": rid}, {"$set": {**upd, "updated_at": now_iso()}})
    await audit(user, f"portal_{decision}", entity, rid, {"code": doc.get("code"), "comment": comment[:200], "otp": True})
    pm = None
    if doc.get("project_id"):
        p = await db.projects.find_one({"id": doc["project_id"]}, {"_id": 0, "manager_id": 1})
        pm = (p or {}).get("manager_id")
    await notify([pm] if pm else [], f"Client {decision.replace('_', ' ')}: {doc.get('code') or doc.get('number') or ''}", comment, f"/erp/e/{entity}/{rid}", kind="approval")
    if not pm:
        await notify_roles(["branch_manager", "director"], f"Client {decision.replace('_', ' ')}: {doc.get('code') or ''}", comment, f"/erp/e/{entity}/{rid}", kind="approval")
    return {"ok": True, "status": upd.get("status")}


# ------------------------------------------------------------------ client actions
@router.post("/payment-notice")
async def payment_notice(body: dict, user=Depends(client_user)):
    inv = await ENG.get_record("invoices", user, body.get("invoice_id"), raw=True)
    try:
        amt = float(body.get("amount") or 0)
    except ValueError:
        raise HTTPException(422, "Enter the amount")
    if amt <= 0:
        raise HTTPException(422, "Enter the amount")
    if not (body.get("reference") or "").strip():
        raise HTTPException(422, "Enter the UTR / cheque number")
    rec = await ENG.create_record("receipts", user, {"account_id": user["account_id"], "date": body.get("date") or today_ist().isoformat(), "amount": amt,
                                                     "mode": body.get("mode") or "neft", "reference": body["reference"].strip()[:60], "proof": body.get("proof"),
                                                     "allocations": [{"invoice_id": inv["id"], "amount": amt}], "notes": "Payment notice from the client portal",
                                                     "branch_id": inv.get("branch_id")}, system=True)
    await db.receipts.update_one({"id": rec["id"]}, {"$set": {"status": "pending"}})
    await notify_roles(["accounts"], f"Client says they paid ₹{amt:,.0f} for {inv['code']}", body["reference"], f"/erp/e/receipts/{rec['id']}", kind="alert")
    return {"ok": True, "reference": rec["code"]}


@router.get("/pay/{invoice_id}")
async def pay(invoice_id: str, user=Depends(client_user)):
    from routes_ops import upi
    return await upi(invoice_id, user)


@router.post("/tickets")
async def client_ticket(body: dict, user=Depends(client_user)):
    if not (body.get("title") or "").strip():
        raise HTTPException(422, "Describe the problem")
    asset = None
    if body.get("asset_id"):
        asset = await ENG.get_record("installed_assets", user, body["asset_id"], raw=True)
    t = await ENG.create_record("tickets", user, {"account_id": user["account_id"], "asset_id": (asset or {}).get("id"), "project_id": body.get("project_id"),
                                                  "channel": "portal", "category": body.get("category") or "breakdown",
                                                  "priority": body.get("priority") if body.get("priority") in ("urgent", "high", "normal", "low") else "normal",
                                                  "title": body["title"].strip()[:120], "description": (body.get("description") or "")[:4000], "photos": (body.get("photos") or [])[:6],
                                                  "contact_name": user["name"], "contact_phone": user.get("phone")}, system=True)
    return {"ok": True, "reference": t["code"], "id": t["id"]}


@router.post("/tickets/{tid}/rate")
async def rate_ticket(tid: str, body: dict, user=Depends(client_user)):
    t = await ENG.get_record("tickets", user, tid, raw=True)
    if t.get("status") not in ("resolved", "closed"):
        raise HTTPException(409, "You can rate after the request is resolved")
    r = int(body.get("rating") or 0)
    if r < 1 or r > 5:
        raise HTTPException(422, "Rate from 1 to 5")
    upd = {"rating": r, "feedback": (body.get("feedback") or "")[:1000]}
    if body.get("reopen"):
        upd["status"] = "reopened"
        upd["resolved_at"] = None
    await db.tickets.update_one({"id": tid}, {"$set": upd})
    await audit(user, "ticket_rated", "tickets", tid, {"rating": r})
    return {"ok": True}


@router.post("/requirement")
async def new_requirement(body: dict, request: Request, user=Depends(client_user)):
    acc = await db.accounts.find_one({"id": user["account_id"]}, {"_id": 0})
    li = LeadIn(form="existing_client", name=user["name"], phone=(user.get("phone") or acc.get("phone") or "")[-10:] or "9000000000", email=user.get("email"),
                company=acc.get("name"), service=body.get("service"), supply=body.get("supply"), load_kva=body.get("load_kva"), town=body.get("town") or acc.get("town"),
                message=body.get("message"), attachments=body.get("attachments") or [], consent=True)
    res = await intake(li, None, source="existing_client", user=None)
    return {"ok": True, "reference": res["reference"]}


# ------------------------------------------------------------------ consultant
@router.post("/rfis/{rid}/answer")
async def answer_rfi(rid: str, body: dict, user=Depends(consultant_user)):
    r = await ENG.get_record("rfis", user, rid, raw=True)
    if r.get("status") != "open":
        raise HTTPException(409, "Already answered")
    ans = (body.get("answer") or "").strip()
    if not ans:
        raise HTTPException(422, "Write the answer")
    await db.rfis.update_one({"id": rid}, {"$set": {"answer": ans[:4000], "answered_on": today_ist().isoformat(), "status": "answered", "answered_by": user["name"]}})
    await audit(user, "rfi_answered", "rfis", rid)
    return {"ok": True}


# ------------------------------------------------------------------ vendor
@router.post("/rfqs/{rid}/quote")
async def vendor_quote(rid: str, body: dict, user=Depends(portal_dep("vendor"))):
    rfq = await ENG.get_record("rfqs", user, rid, raw=True)
    if rfq.get("status") not in ("sent", "compared"):
        raise HTTPException(409, "This RFQ is closed")
    ex = await db.vendor_quotes.find_one({"rfq_id": rid, "vendor_id": user["vendor_id"], "deleted": {"$ne": True}}, {"_id": 0})
    lines = []
    for n, ln in enumerate(rfq.get("lines") or []):
        q = (body.get("lines") or [{}] * len(rfq["lines"]))[n] if n < len(body.get("lines") or []) else {}
        lines.append({"item_id": ln.get("item_id"), "description": ln.get("description"), "qty": ln.get("qty"), "rate": q.get("rate"),
                      "gst_rate": str(q.get("gst_rate") or "18"), "make": q.get("make"), "delivery_days": q.get("delivery_days")})
    data = {"rfq_id": rid, "vendor_id": user["vendor_id"], "lines": lines, "freight": body.get("freight"), "payment_terms": body.get("payment_terms"),
            "valid_until": body.get("valid_until")}
    if ex:
        out = await ENG.update_record("vendor_quotes", user, ex["id"], data, system=True)
    else:
        out = await ENG.create_record("vendor_quotes", user, data, system=True)
    await notify_roles(["purchase"], f"Quote received for {rfq['code']}", "", f"/erp/rfqs/{rid}/compare", kind="info")
    return {"ok": True, "id": out["id"], "total": out.get("total")}


@router.post("/vendor-bills")
async def vendor_bill(body: dict, user=Depends(portal_dep("vendor"))):
    po = await ENG.get_record("purchase_orders", user, body.get("po_id"), raw=True)
    if not (body.get("bill_no") or "").strip():
        raise HTTPException(422, "Enter your bill number")
    vb = await ENG.create_record("vendor_bills", user, {"vendor_id": user["vendor_id"], "po_id": po["id"], "project_id": po.get("project_id"),
                                                        "bill_no": body["bill_no"].strip()[:40], "bill_date": body.get("bill_date") or today_ist().isoformat(),
                                                        "lines": body.get("lines") or [{"description": ln.get("description"), "qty": ln.get("received_qty") or ln.get("qty"),
                                                                                        "rate": ln.get("rate"), "gst_rate": ln.get("gst_rate")} for ln in po.get("lines") or []],
                                                        "eway_bill_no": body.get("eway_bill_no"), "file": body.get("file"), "branch_id": po.get("branch_id")}, system=True)
    await notify_roles(["accounts", "purchase"], f"Vendor bill uploaded: {vb['bill_no']}", "", f"/erp/e/vendor_bills/{vb['id']}", kind="info")
    return {"ok": True, "reference": vb["code"]}


# ------------------------------------------------------------------ subcontractor
@router.post("/sc-bills")
async def sc_bill(body: dict, user=Depends(sub_user)):
    wo = await ENG.get_record("work_orders", user, body.get("work_order_id"), raw=True)
    if wo.get("status") not in ("approved", "active", "completed"):
        raise HTTPException(409, "This work order is not active")
    lines = []
    for n, ln in enumerate(wo.get("lines") or []):
        q = next((x for x in body.get("lines") or [] if x.get("line") == n), None)
        if q and float(q.get("this_qty") or 0) > 0:
            lines.append({"description": ln.get("description"), "unit": ln.get("unit"), "this_qty": float(q["this_qty"]), "rate": ln.get("rate")})
    if not lines:
        raise HTTPException(422, "Enter the quantity done for at least one item")
    b = await ENG.create_record("sc_bills", user, {"work_order_id": wo["id"], "vendor_id": user["vendor_id"], "project_id": wo["project_id"],
                                                   "period_to": body.get("period_to") or today_ist().isoformat(), "lines": lines}, system=True)
    await notify_roles(["project_manager"], f"Subcontractor bill {b['code']}", "", f"/erp/e/sc_bills/{b['id']}", kind="info")
    return {"ok": True, "reference": b["code"]}


@router.post("/labour-attendance")
async def labour(body: dict, user=Depends(sub_user)):
    wos = await db.work_orders.find({"vendor_id": user["vendor_id"], "project_id": body.get("project_id"), "status": {"$in": ["approved", "active"]}}, {"_id": 0}).to_list(5)
    if not wos:
        raise HTTPException(403, "No active work order on this project")
    done = 0
    for r in (body.get("rows") or [])[:300]:
        w = await db.workers.find_one({"id": r.get("worker_id"), "contractor_id": user["vendor_id"]}, {"_id": 0, "id": 1})
        if not w:
            continue
        await ENG.create_record("labour_attendance", user, {"project_id": body["project_id"], "date": body.get("date") or today_ist().isoformat(), "worker_id": w["id"],
                                                            "present": r.get("present") or "present", "in_time": r.get("in_time"), "out_time": r.get("out_time")}, system=True)
        done += 1
    return {"ok": True, "saved": done}


# ------------------------------------------------------------------ referral partner
async def partner_leads(user):
    pid = user.get("partner_id")
    p = await db.partners.find_one({"id": pid}, {"_id": 0}) or {}
    leads = await db.leads.find({"partner_id": pid, "deleted": {"$ne": True}}, {"_id": 0}).sort("created_at", -1).to_list(500)
    pids = [l.get("project_id") for l in leads if l.get("project_id")]
    prj = {x["id"]: x for x in await db.projects.find({"id": {"$in": pids}}, {"_id": 0, "id": 1, "contract_value": 1}).to_list(500)}
    rows, total = [], 0.0
    for l in leads:
        v = float((prj.get(l.get("project_id")) or {}).get("contract_value") or 0) if l.get("stage") == "won" else 0
        c = round(v * float(p.get("commission_pct") or 0) / 100, 2)
        total += c
        rows.append({"code": l["code"], "name": l["name"], "company": l.get("company"), "service": label_of("services", l.get("service")),
                     "status": "Won" if l.get("stage") == "won" else "Closed" if l.get("stage") == "lost" else "In progress", "created_at": l["created_at"][:10],
                     "commission": c})
    return {"partner": {"name": p.get("name"), "commission_pct": p.get("commission_pct")}, "referrals": rows, "commission_total": round(total, 2)}


@router.post("/referrals")
async def refer(body: dict, user=Depends(partner_user)):
    li = LeadIn(form="referral", name=body.get("name") or "", phone=body.get("phone") or "", email=body.get("email"), company=body.get("company"),
                service=body.get("service"), supply=body.get("supply"), town=body.get("town"), load_kva=body.get("load_kva"), message=body.get("message"),
                consent=bool(body.get("consent")))
    if not li.name.strip():
        raise HTTPException(422, "Enter the customer's name")
    if not li.consent:
        raise HTTPException(422, "Confirm the customer agreed to be contacted")
    res = await intake(li, None, source="referral", partner_id=user.get("partner_id"))
    return {"ok": True, "reference": res["reference"]}
