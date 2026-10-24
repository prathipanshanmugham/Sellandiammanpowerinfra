"""Operations helpers: project hub (P&L, S-curve, under/over-billing), RA bills from the measurement book, handover pack,
RFQ comparison and award, stock and drums, material reconciliation, service desk, attendance check-in, payroll,
finance views (balances, ageing, GST, TDS, P&L, cash flow, credit report), expiry calendar and Tally export."""
import calendar
import io
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

import engine as ENG
import hooks as H
from catalog import label_of
from core import (db, require, staff_user, current_user, can, now_iso, today_ist, money, audit, get_settings, branch_filter, new_id,
                  allowed_branches, IST)
from pdf import Letterhead, ind, rs

router = APIRouter()
POSTED_RA = ("approved", "submitted", "certified", "invoiced", "paid")


def d(x):
    return date.fromisoformat(str(x)[:10]) if x else None


async def _sum(coll, q, field):
    rows = await db[coll].find({**q, "deleted": {"$ne": True}}, {"_id": 0, field: 1}).to_list(100000)
    return round(sum(float(r.get(field) or 0) for r in rows), 2)


# ====================================================================== project hub
async def project_numbers(p):
    pid = p["id"]
    billed = await _sum("ra_bills", {"project_id": pid, "status": {"$in": list(POSTED_RA)}}, "gross")
    certified = await _sum("ra_bills", {"project_id": pid, "status": {"$in": ["certified", "invoiced", "paid"]}}, "certified_amount")
    invoiced = await _sum("invoices", {"project_id": pid, "status": {"$in": ["issued", "part_paid", "paid"]}}, "subtotal")
    received = await _sum("invoices", {"project_id": pid, "status": {"$in": ["issued", "part_paid", "paid"]}}, "paid")
    retention = await _sum("ra_bills", {"project_id": pid, "status": {"$in": list(POSTED_RA)}}, "retention")
    po = await _sum("purchase_orders", {"project_id": pid, "status": {"$in": ["approved", "sent", "partly_received", "received", "closed"]}}, "subtotal")
    wo = await _sum("work_orders", {"project_id": pid, "status": {"$in": ["approved", "active", "completed", "closed"]}}, "total")
    hires = await _sum("hires", {"project_id": pid}, "amount")
    committed = round(po + wo + hires, 2)
    mat_bills = await _sum("vendor_bills", {"project_id": pid}, "subtotal")
    sc = await _sum("sc_bills", {"project_id": pid, "status": {"$in": ["approved", "paid"]}}, "gross")
    exp = await _sum("expenses", {"project_id": pid, "status": {"$in": ["approved", "reimbursed"]}}, "amount")
    issues = await db.stock_moves.find({"project_id": pid, "kind": {"$in": ["issue", "return"]}}, {"_id": 0, "value": 1}).to_list(100000)
    issued_value = -round(sum(float(x.get("value") or 0) for x in issues), 2)
    labour_rows = await db.labour_attendance.find({"project_id": pid, "deleted": {"$ne": True}}, {"_id": 0, "worker_id": 1, "present": 1}).to_list(100000)
    wages = {w["id"]: float(w.get("daily_wage") or 0) for w in await db.workers.find({"id": {"$in": list({r["worker_id"] for r in labour_rows})}}, {"_id": 0, "id": 1, "daily_wage": 1}).to_list(5000)}
    labour = round(sum(wages.get(r["worker_id"], 0) * (1 if r.get("present") == "present" else 0.5 if r.get("present") == "half_day" else 0) for r in labour_rows), 2)
    actual = round(max(mat_bills, issued_value) + sc + exp + labour + hires, 2)
    budget = float(p.get("budget_total") or 0)
    cv = float(p.get("contract_value") or 0)
    pct = float(p.get("percent_complete") or 0)
    earned = round(cv * pct / 100, 2)
    over_under = round(billed - earned, 2)
    # Forecast final cost by head: material is bought early, so it is taken at the higher of budget and what is booked;
    # labour, subcontract, hire and expenses grow with progress, so they are projected from % complete.
    heads = {}
    for b in p.get("budget") or []:
        heads[b.get("head")] = heads.get(b.get("head"), 0) + float(b.get("amount") or 0)
    mat_actual = max(mat_bills, issued_value)
    if budget > 0:
        f = pct / 100 if pct >= 5 else None
        other = (("labour", labour), ("subcon", sc), ("tp", hires), ("expenses", exp))
        est_final = max(heads.get("material", 0), mat_actual)
        for head, a in other:
            bh = heads.get(head, 0) + (heads.get("liaison", 0) + heads.get("overhead", 0) + heads.get("other", 0) if head == "expenses" else 0)
            est_final += max(bh, a / f) if f else max(bh, a)
    else:
        est_final = actual / (pct / 100) if pct >= 5 else actual
    ctc = round(max(est_final - actual, 0), 2)
    margin = round(cv - (actual + ctc), 2)
    return {"contract_value": cv, "percent_complete": pct, "earned_value": earned, "billed": billed, "certified": certified, "invoiced": invoiced,
            "received": received, "retention_held": retention, "over_under_billed": over_under, "budget": budget, "committed": committed,
            "actual_cost": actual, "cost_to_complete": ctc, "forecast_margin": margin,
            "forecast_margin_pct": round(margin / cv * 100, 1) if cv else None,
            "cost_breakup": {"material": max(mat_bills, issued_value), "subcontract": sc, "expenses": exp, "labour": labour, "hire": hires}}


def months_between(a, b):
    out, y, m = [], a.year, a.month
    while (y, m) <= (b.year, b.month):
        out.append(f"{y}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


async def s_curve(p):
    ms = await db.milestones.find({"project_id": p["id"], "deleted": {"$ne": True}}, {"_id": 0}).to_list(500)
    if not ms:
        return []
    start = min(d(m["planned_start"]) for m in ms)
    end = max(d(m["planned_end"]) for m in ms)
    tw = sum(float(m.get("weight_pct") or 0) for m in ms) or 1
    t = today_ist()
    snaps = {s["month"]: s["percent"] for s in await db.project_progress.find({"project_id": p["id"]}, {"_id": 0}).to_list(500)}
    out = []
    for mk in months_between(start, max(end, t)):
        y, mo = map(int, mk.split("-"))
        last = date(y, mo, calendar.monthrange(y, mo)[1])
        planned = 0.0
        for m in ms:
            a, b = d(m["planned_start"]), d(m["planned_end"])
            span = max((b - a).days, 1)
            frac = 0 if last < a else 1 if last >= b else (last - a).days / span
            planned += float(m.get("weight_pct") or 0) * frac
        actual = snaps.get(mk)
        if mk == t.strftime("%Y-%m"):
            actual = float(p.get("percent_complete") or 0)
        out.append({"month": mk, "planned": round(planned / tw * 100, 1), "actual": actual if last <= max(t, last) and (actual is not None) else None})
    return out


@router.get("/projects/{pid}/hub")
async def project_hub(pid: str, user=Depends(require("projects", "r"))):
    p = await ENG.get_record("projects", user, pid)
    nums = await project_numbers(p)
    if "cost" in (user.get("hidden") or []) or user["role"] in ("site_engineer", "sales"):
        for k in ("budget", "committed", "actual_cost", "cost_to_complete", "forecast_margin", "forecast_margin_pct", "cost_breakup"):
            nums.pop(k, None)
    counts = {}
    for coll, q in (("rfis", {"status": "open"}), ("snags", {"status": {"$ne": "verified"}}), ("ncrs", {"status": {"$ne": "closed"}}),
                    ("hindrances", {"status": "open"}), ("drawings", {"status": "submitted"}), ("permits", {"status": "active"}),
                    ("purchase_requests", {"status": {"$in": ["draft", "pending_approval", "approved"]}}), ("variations", {"status": {"$in": ["sent", "pending_approval"]}})):
        counts[coll] = await db[coll].count_documents({"project_id": pid, "deleted": {"$ne": True}, **q})
    t = today_ist().isoformat()
    upcoming = await db.milestones.find({"project_id": pid, "deleted": {"$ne": True}, "status": {"$ne": "done"}}, {"_id": 0}).sort("planned_end", 1).to_list(6)
    dprs = await db.dprs.find({"project_id": pid, "deleted": {"$ne": True}}, {"_id": 0}).sort("date", -1).to_list(5)
    liaison = await db.liaisons.find({"project_id": pid, "deleted": {"$ne": True}}, {"_id": 0}).to_list(20)
    risks = []
    late = [m for m in upcoming if m.get("planned_end") and m["planned_end"] < t]
    if late:
        risks.append({"tone": "red", "text": f"{len(late)} milestone(s) past their planned finish", "link": f"/erp/projects/{pid}?tab=milestones"})
    if p.get("end_date") and p["end_date"] < t and p.get("status") not in ("handed_over", "closed"):
        risks.append({"tone": "red", "text": f"Past the planned finish ({p['end_date']}) — LD exposure {p.get('ld_pct_per_week', 0)}% per week"})
    if nums.get("over_under_billed", 0) < -0.1 * (nums["contract_value"] or 1):
        risks.append({"tone": "amber", "text": f"Under-billed by {rs(-nums['over_under_billed'], 0)} — raise an RA bill"})
    if nums.get("forecast_margin_pct") is not None and nums["forecast_margin_pct"] < 8:
        risks.append({"tone": "red", "text": f"Forecast margin {nums['forecast_margin_pct']}% is below 8%"})
    if counts["hindrances"]:
        risks.append({"tone": "amber", "text": f"{counts['hindrances']} open hindrance(s)"})
    if not dprs or dprs[0]["date"] < (today_ist() - timedelta(days=2)).isoformat():
        if p.get("status") in ("mobilising", "in_progress"):
            risks.append({"tone": "amber", "text": "No daily progress report in the last 2 days"})
    return {"project": p, "numbers": nums, "counts": counts, "upcoming": upcoming, "dprs": dprs, "liaison": liaison, "risks": risks,
            "s_curve": await s_curve(p)}


@router.get("/projects/{pid}/gantt")
async def gantt(pid: str, user=Depends(require("projects", "r"))):
    await ENG.get_record("projects", user, pid, raw=True)
    ms = await db.milestones.find({"project_id": pid, "deleted": {"$ne": True}}, {"_id": 0}).sort("planned_start", 1).to_list(500)
    return ms


@router.post("/projects/{pid}/ra-from-mb")
async def ra_from_mb(pid: str, body: dict | None = None, user=Depends(require("projects", "w"))):
    await ENG.get_record("projects", user, pid, raw=True)
    return await H.generate_ra_from_mb(pid, user, (body or {}).get("period_to"))


@router.get("/projects/{pid}/handover-pack.pdf")
async def handover_pack(pid: str, user=Depends(current_user)):
    p = await ENG.get_record("projects", user, pid)
    s = await get_settings()
    L = Letterhead("Handover pack", s, subtitle=f"{p.get('code')}, {p.get('name')}")
    acc = await db.accounts.find_one({"id": p.get("account_id")}, {"_id": 0, "name": 1}) or {}
    L.meta([("Client", acc.get("name")), ("Project", p.get("name")), ("Capacity", f"{p.get('capacity_kva') or ''} kVA {p.get('voltage') or ''}"),
            ("Completed", p.get("actual_end")), ("Defects liability until", p.get("dlp_until")), ("Work order", p.get("wo_no"))])
    draw = await db.drawings.find({"project_id": pid, "status": {"$in": ["as_built", "approved", "approved_with_comments"]}, "deleted": {"$ne": True}}, {"_id": 0}).to_list(200)
    L.h("Drawings")
    L.table(["Drawing no.", "Title", "Revision", "Status"], [[x["number"], x["title"], x.get("revision"), label_of("x", x.get("status"))] for x in draw] or [["—", "No drawings recorded", "", ""]])
    tests = await db.test_reports.find({"project_id": pid, "status": "issued", "deleted": {"$ne": True}}, {"_id": 0}).to_list(200)
    L.h("Test certificates")
    L.table(["Certificate", "Test", "Equipment", "Date", "Result"], [[x["code"], label_of("test_types", x["test_type"]), x["equipment"], x["date"], (x.get("result") or "").upper()] for x in tests] or [["—", "", "", "", ""]])
    lia = await db.liaisons.find({"project_id": pid, "deleted": {"$ne": True}}, {"_id": 0}).to_list(50)
    L.h("Approvals")
    L.table(["Application", "Authority", "No.", "Stage"], [[label_of("liaison_kinds", x["kind"]), x.get("authority"), x.get("application_no"), label_of("liaison_stages", x.get("stage"))] for x in lia] or [["—", "", "", ""]])
    assets = await db.installed_assets.find({"project_id": pid, "deleted": {"$ne": True}}, {"_id": 0}).to_list(200)
    L.h("Equipment installed and warranties")
    L.table(["Code", "Equipment", "Make / rating", "Serial no.", "Warranty until"], [[a["code"], label_of("asset_kinds", a["kind"]), f"{a.get('make') or ''} {a.get('rating') or ''}", a.get("serial_no"), a.get("warranty_until")] for a in assets] or [["—", "", "", "", ""]])
    snags = await db.snags.find({"project_id": pid, "deleted": {"$ne": True}}, {"_id": 0}).to_list(500)
    open_s = [x for x in snags if x.get("status") != "verified"]
    L.h("Snag list")
    L.p(f"{len(snags)} snags recorded, {len(open_s)} open." + (" Open items are listed below." if open_s else " All verified."))
    if open_s:
        L.table(["Snag", "Location", "Status"], [[x["description"], x.get("location"), x.get("status")] for x in open_s])
    L.signature("Handed over by", "Taken over by (client)")
    await audit(user, "handover_pack", "projects", pid)
    return Response(L.build(), media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="handover-{p.get("code", "").replace("/", "-")}.pdf"'})


@router.get("/projects/{pid}/materials")
async def material_reconciliation(pid: str, user=Depends(require("projects", "r"))):
    """BOQ quantity vs issued vs returned vs used (daily reports) -> wastage %."""
    p = await ENG.get_record("projects", user, pid, raw=True)
    boq = await db.boqs.find_one({"project_id": pid, "deleted": {"$ne": True}}, {"_id": 0})
    if not boq and p.get("proposal_id"):
        prop = await db.proposals.find_one({"id": p["proposal_id"]}, {"_id": 0, "boq_id": 1})
        boq = await db.boqs.find_one({"id": (prop or {}).get("boq_id")}, {"_id": 0}) if prop else None
    rows = {}
    for ln in (boq or {}).get("lines") or []:
        if ln.get("item_id"):
            r = rows.setdefault(ln["item_id"], {"item_id": ln["item_id"], "boq": 0, "issued": 0, "returned": 0, "used": 0})
            r["boq"] += float(ln.get("qty") or 0)
    for mv in await db.stock_moves.find({"project_id": pid, "kind": {"$in": ["issue", "return"]}}, {"_id": 0}).to_list(100000):
        r = rows.setdefault(mv["item_id"], {"item_id": mv["item_id"], "boq": 0, "issued": 0, "returned": 0, "used": 0})
        if mv["kind"] == "issue":
            r["issued"] += -float(mv["qty"])
        else:
            r["returned"] += float(mv["qty"])
    for dpr in await db.dprs.find({"project_id": pid, "deleted": {"$ne": True}}, {"_id": 0, "materials": 1}).to_list(5000):
        for ln in dpr.get("materials") or []:
            if ln.get("item_id"):
                r = rows.setdefault(ln["item_id"], {"item_id": ln["item_id"], "boq": 0, "issued": 0, "returned": 0, "used": 0})
                r["used"] += float(ln.get("qty") or 0)
    items = {i["id"]: i for i in await db.items.find({"id": {"$in": list(rows)}}, {"_id": 0, "id": 1, "name": 1, "unit": 1}).to_list(len(rows) or 1)}
    out = []
    for r in rows.values():
        net = r["issued"] - r["returned"]
        r["net_issued"] = round(net, 3)
        r["balance_at_site"] = round(net - r["used"], 3)
        r["wastage_pct"] = round((net - r["used"]) / net * 100, 1) if net and r["used"] else None
        r["vs_boq_pct"] = round(net / r["boq"] * 100, 1) if r["boq"] else None
        r["name"] = (items.get(r["item_id"]) or {}).get("name")
        r["unit"] = (items.get(r["item_id"]) or {}).get("unit")
        out.append(r)
    return sorted(out, key=lambda x: x["name"] or "")


# ====================================================================== procurement
@router.post("/purchase_requests/{prid}/to-rfq")
async def pr_to_rfq(prid: str, body: dict | None = None, user=Depends(require("procurement", "w"))):
    pr = await ENG.get_record("purchase_requests", user, prid, raw=True)
    if pr.get("status") != "approved":
        raise HTTPException(409, "Approve the material request first")
    return await ENG.create_record("rfqs", user, {"pr_id": prid, "project_id": pr.get("project_id"), "vendor_ids": (body or {}).get("vendor_ids") or [],
                                                  "lines": [{k: ln.get(k) for k in ("item_id", "description", "qty", "unit")} for ln in pr.get("lines") or []],
                                                  "due_on": (today_ist() + timedelta(days=3)).isoformat()})


@router.get("/rfqs/{rid}/comparison")
async def comparison(rid: str, user=Depends(require("procurement", "r"))):
    rfq = await ENG.get_record("rfqs", user, rid, raw=True)
    quotes = await db.vendor_quotes.find({"rfq_id": rid, "deleted": {"$ne": True}}, {"_id": 0}).to_list(50)
    vendors = {v["id"]: v["name"] for v in await db.vendors.find({"id": {"$in": [q["vendor_id"] for q in quotes]}}, {"_id": 0, "id": 1, "name": 1}).to_list(50)}
    rows = []
    for n, ln in enumerate(rfq.get("lines") or []):
        cells = []
        for q in quotes:
            m = next((x for x in q.get("lines") or [] if (ln.get("item_id") and x.get("item_id") == ln.get("item_id")) or (x.get("description") or "").strip().lower() == (ln.get("description") or "").strip().lower()), None)
            cells.append({"vendor_id": q["vendor_id"], "rate": (m or {}).get("rate"), "make": (m or {}).get("make"), "delivery_days": (m or {}).get("delivery_days"),
                          "amount": round(float((m or {}).get("rate") or 0) * float(ln.get("qty") or 0), 2) if m else None})
        rates = [c["rate"] for c in cells if c["rate"]]
        low = min(rates) if rates else None
        for c in cells:
            c["lowest"] = c["rate"] == low and low is not None
        rows.append({"line": n + 1, "item_id": ln.get("item_id"), "description": ln.get("description"), "qty": ln.get("qty"), "unit": ln.get("unit"), "quotes": cells})
    totals = [{"vendor_id": q["vendor_id"], "vendor": vendors.get(q["vendor_id"]), "total": q.get("total"), "payment_terms": q.get("payment_terms"),
               "valid_until": q.get("valid_until"), "quote_id": q["id"]} for q in quotes]
    totals.sort(key=lambda x: float(x["total"] or 1e18))
    for n, t in enumerate(totals):
        t["rank"] = f"L{n + 1}"
    if quotes and rfq.get("status") == "sent":
        await db.rfqs.update_one({"id": rid}, {"$set": {"status": "compared"}})
    return {"rfq": rfq, "rows": rows, "totals": totals, "vendors": vendors}


@router.post("/rfqs/{rid}/award")
async def award(rid: str, body: dict, user=Depends(require("procurement", "w"))):
    rfq = await ENG.get_record("rfqs", user, rid, raw=True)
    q = await db.vendor_quotes.find_one({"id": body.get("quote_id"), "rfq_id": rid}, {"_id": 0})
    if not q:
        raise HTTPException(404, "Quote not found")
    po = await ENG.create_record("purchase_orders", user, {"vendor_id": q["vendor_id"], "project_id": rfq.get("project_id"), "rfq_id": rid,
                                                           "pr_id": rfq.get("pr_id"), "date": today_ist().isoformat(), "freight": q.get("freight"),
                                                           "lines": [{"item_id": ln.get("item_id"), "description": ln.get("description"), "make": ln.get("make"),
                                                                      "qty": ln.get("qty"), "rate": ln.get("rate"), "gst_rate": ln.get("gst_rate") or "18"} for ln in q.get("lines") or []]})
    await db.rfqs.update_one({"id": rid}, {"$set": {"status": "closed", "awarded_to": q["vendor_id"]}})
    return po


# ====================================================================== stores
@router.get("/stores/stock")
async def stock(user=Depends(require("stores", "r")), store_id: str = "", item_id: str = "", low: bool = False, q: str = ""):
    f = {}
    if store_id:
        f["store_id"] = store_id
    if item_id:
        f["item_id"] = item_id
    moves = await db.stock_moves.find(f, {"_id": 0, "item_id": 1, "store_id": 1, "qty": 1, "value": 1, "rate": 1}).to_list(200000)
    agg = {}
    inq = {}
    for m in moves:
        k = (m["item_id"], m["store_id"])
        a = agg.setdefault(k, {"qty": 0.0, "value": 0.0})
        a["qty"] += float(m["qty"])
        a["value"] += float(m.get("value") or 0)
        if float(m["qty"]) > 0:
            iq = inq.setdefault(m["item_id"], [0.0, 0.0])
            iq[0] += float(m["qty"])
            iq[1] += float(m["qty"]) * float(m.get("rate") or 0)
    items = {i["id"]: i for i in await db.items.find({"id": {"$in": list({k[0] for k in agg})}}, {"_id": 0}).to_list(10000)}
    stores = {s["id"]: s for s in await db.stores.find({}, {"_id": 0}).to_list(500)}
    allowed = allowed_branches(user)
    rows = []
    hide_cost = "cost" in (user.get("hidden") or [])
    for (iid, sid), a in agg.items():
        it = items.get(iid) or {}
        st = stores.get(sid) or {}
        if allowed is not None and st.get("branch_id") not in allowed:
            continue
        if q and q.lower() not in (it.get("name") or "").lower():
            continue
        avg = inq[iid][1] / inq[iid][0] if inq.get(iid) and inq[iid][0] else float(it.get("cost_rate") or 0)
        qty = round(a["qty"], 3)
        if abs(qty) < 1e-9:
            continue
        r = {"item_id": iid, "item": it.get("name"), "code": it.get("code"), "unit": it.get("unit"), "group": it.get("group"), "store_id": sid,
             "store": st.get("name"), "qty": qty, "reorder_level": it.get("min_stock"), "below_reorder": bool(it.get("min_stock")) and qty < float(it["min_stock"])}
        if not hide_cost:
            r["avg_rate"] = round(avg, 2)
            r["value"] = round(qty * avg, 2)
        if low and not r["below_reorder"]:
            continue
        rows.append(r)
    rows.sort(key=lambda r: (r["store"] or "", r["item"] or ""))
    return {"rows": rows, "total_value": None if hide_cost else round(sum(r.get("value", 0) for r in rows), 2)}


@router.get("/stores/in-transit")
async def in_transit(user=Depends(require("stores", "r"))):
    return await db.material_moves.find({"status": "in_transit", "deleted": {"$ne": True}}, {"_id": 0}).to_list(200)


# ====================================================================== service desk
@router.get("/service/my-jobs")
async def my_jobs(user=Depends(require("service", "r"))):
    t = today_ist()
    tickets = await db.tickets.find({"assigned_to": user["id"], "status": {"$nin": ["closed", "resolved"]}, "deleted": {"$ne": True}}, {"_id": 0}).sort("restore_by", 1).to_list(100)
    pms = await db.pm_jobs.find({"technician_id": user["id"], "status": {"$in": ["scheduled", "in_progress"]}, "scheduled_on": {"$lte": (t + timedelta(days=7)).isoformat()},
                                 "deleted": {"$ne": True}}, {"_id": 0}).sort("scheduled_on", 1).to_list(100)
    accs = {a["id"]: a for a in await db.accounts.find({"id": {"$in": list({x.get("account_id") for x in tickets + pms if x.get("account_id")})}}, {"_id": 0, "id": 1, "name": 1, "address": 1, "phone": 1, "sites": 1}).to_list(200)}
    return {"tickets": tickets, "visits": pms, "accounts": accs}


@router.get("/service/renewals")
async def renewals(user=Depends(require("service", "r")), days: int = 60):
    t = today_ist()
    rows = await db.amc_contracts.find({"status": "active", "end": {"$lte": (t + timedelta(days=days)).isoformat()}, "deleted": {"$ne": True}}, {"_id": 0}).sort("end", 1).to_list(200)
    return rows


# ====================================================================== HR self-service
async def my_employee(user):
    e = await db.employees.find_one({"user_id": user["id"], "deleted": {"$ne": True}}, {"_id": 0})
    if not e:
        raise HTTPException(404, "Your login is not linked to an employee record yet — ask HR")
    return e


@router.post("/hr/check-in")
async def check_in(body: dict, user=Depends(staff_user)):
    emp = await my_employee(user)
    t = today_ist().isoformat()
    ex = await db.attendance.find_one({"employee_id": emp["id"], "date": t, "deleted": {"$ne": True}}, {"_id": 0})
    if ex:
        raise HTTPException(409, "Already checked in today")
    gps = body.get("gps")
    if not gps or gps.get("lat") is None:
        raise HTTPException(422, "Allow location access to check in")
    rec = await ENG.create_record("attendance", user, {"employee_id": emp["id"], "date": t, "check_in": datetime.now(IST).isoformat(timespec="seconds"),
                                                       "in_gps": gps, "project_id": body.get("project_id") or emp.get("work_site"),
                                                       "branch_id_at": body.get("branch_id")}, system=True)
    return rec


@router.post("/hr/check-out")
async def check_out(body: dict, user=Depends(staff_user)):
    emp = await my_employee(user)
    t = today_ist().isoformat()
    ex = await db.attendance.find_one({"employee_id": emp["id"], "date": t, "deleted": {"$ne": True}}, {"_id": 0})
    if not ex:
        raise HTTPException(409, "Check in first")
    return await ENG.update_record("attendance", user, ex["id"], {"check_out": datetime.now(IST).isoformat(timespec="seconds"), "out_gps": body.get("gps")}, system=True)


@router.get("/hr/me")
async def hr_me(user=Depends(staff_user)):
    emp = await db.employees.find_one({"user_id": user["id"], "deleted": {"$ne": True}}, {"_id": 0})
    if not emp:
        return {"employee": None}
    t = today_ist()
    att = await db.attendance.find({"employee_id": emp["id"], "date": {"$gte": t.replace(day=1).isoformat()}, "deleted": {"$ne": True}}, {"_id": 0}).sort("date", -1).to_list(40)
    leaves = await db.leaves.find({"employee_id": emp["id"], "deleted": {"$ne": True}}, {"_id": 0}).sort("from_date", -1).to_list(20)
    runs = await db.payroll_runs.find({"status": {"$in": ["approved", "paid"]}, "lines.employee_id": emp["id"], "deleted": {"$ne": True}}, {"_id": 0}).sort("month", -1).to_list(12)
    slips = [{"run_id": r["id"], "month": r["month"], **next(ln for ln in r["lines"] if ln.get("employee_id") == emp["id"])} for r in runs]
    tasks = await db.tasks.find({"assigned_to": user["id"], "status": {"$ne": "done"}, "deleted": {"$ne": True}}, {"_id": 0}).sort("due_on", 1).to_list(50)
    safe = {k: emp.get(k) for k in ("id", "code", "name", "designation", "department", "joined_on", "phone", "email", "work_site", "shift")}
    return {"employee": safe, "attendance": att, "leaves": leaves, "payslips": slips, "tasks": tasks, "today": next((a for a in att if a["date"] == t.isoformat()), None)}


@router.post("/hr/my-leave")
async def my_leave(body: dict, user=Depends(staff_user)):
    emp = await my_employee(user)
    rec = await ENG.create_record("leaves", user, {"employee_id": emp["id"], "ltype": body.get("ltype") or "casual", "from_date": body.get("from_date"),
                                                   "to_date": body.get("to_date"), "reason": body.get("reason")}, system=True)
    return await ENG.submit_for_approval(ENG.ent("leaves"), await db.leaves.find_one({"id": rec["id"]}, {"_id": 0}), user)


@router.post("/hr/payroll/generate")
async def payroll_generate(body: dict, user=Depends(require("hr", "w"))):
    month = str(body.get("month") or "")
    try:
        y, m = map(int, month.split("-"))
    except ValueError:
        raise HTTPException(422, "Month as YYYY-MM")
    if await db.payroll_runs.find_one({"month": month, "deleted": {"$ne": True}, "branch_id": body.get("branch_id")}):
        raise HTTPException(409, "Payroll for this month already exists")
    s = await get_settings()
    st = s.get("payroll_statutory") or {"pf": False, "esi": False, "pt": False, "tds": False}
    days_in = calendar.monthrange(y, m)[1]
    emps = await db.employees.find({"status": "active", "deleted": {"$ne": True}, **({"branch_id": body["branch_id"]} if body.get("branch_id") else {})}, {"_id": 0}).to_list(2000)
    lines = []
    for e in emps:
        att = await db.attendance.count_documents({"employee_id": e["id"], "date": {"$regex": f"^{month}"}, "deleted": {"$ne": True}})
        lv = await db.leaves.find({"employee_id": e["id"], "status": "approved", "ltype": "unpaid", "from_date": {"$regex": f"^{month}"}}, {"_id": 0, "days": 1}).to_list(50)
        unpaid = sum(float(x.get("days") or 0) for x in lv)
        paid_days = max(days_in - unpaid, 0)
        gross = money(float(e.get("monthly_ctc") or 0) * paid_days / days_in)
        basic = float(e.get("basic") or gross * 0.5) * paid_days / days_in
        pf = money(min(basic, 15000) * 0.12) if st.get("pf") and e.get("pf") else 0
        esi = money(gross * 0.0075) if st.get("esi") and e.get("esi") and gross <= 21000 else 0
        pt = 208 if st.get("pt") and e.get("pt") and gross > 21000 else 0
        adv = 0.0
        for a in await db.advances.find({"employee_id": e["id"], "status": "approved", "deleted": {"$ne": True}}, {"_id": 0}).to_list(10):
            left = float(a.get("amount") or 0) - float(a.get("recovered") or 0)
            adv += min(left, float(a.get("monthly_recovery") or left))
        lines.append({"employee_id": e["id"], "days_paid": paid_days, "gross": gross, "pf": pf, "esi": esi, "pt": pt, "tds": 0, "advance": money(adv),
                      "attendance_days": att})
    run = await ENG.create_record("payroll_runs", user, {"month": month, "lines": lines, "branch_id": body.get("branch_id")})
    return run


# ====================================================================== finance
@router.get("/finance/balances")
async def balances(user=Depends(require("finance", "r"))):
    accs = await db.bank_accounts.find({"deleted": {"$ne": True}, **branch_filter(user)}, {"_id": 0}).to_list(200)
    out = []
    for a in accs:
        inflow = await _sum("receipts", {"bank_account_id": a["id"], "status": "confirmed"}, "amount")
        outflow = await _sum("vendor_payments", {"bank_account_id": a["id"], "status": "paid"}, "amount")
        exp = await _sum("expenses", {"paid_from": a["id"], "status": {"$in": ["approved", "reimbursed"]}}, "amount")
        tin = await _sum("transfers", {"to_account": a["id"]}, "amount")
        tout = await _sum("transfers", {"from_account": a["id"]}, "amount")
        bal = round(float(a.get("opening_balance") or 0) + inflow - outflow - exp + tin - tout, 2)
        await db.bank_accounts.update_one({"id": a["id"]}, {"$set": {"balance": bal}})
        out.append({**a, "balance": bal, "in": inflow, "out": round(outflow + exp, 2)})
    return {"accounts": out, "total": round(sum(x["balance"] for x in out), 2)}


def bucket(days):
    return "0–30" if days <= 30 else "31–60" if days <= 60 else "61–90" if days <= 90 else "90+"


@router.get("/finance/receivables")
async def receivables(user=Depends(require("finance", "r"))):
    t = today_ist()
    invs = await db.invoices.find({"status": {"$in": ["issued", "part_paid"]}, "deleted": {"$ne": True}, **branch_filter(user)}, {"_id": 0}).to_list(20000)
    names = {a["id"]: a for a in await db.accounts.find({"id": {"$in": list({i["account_id"] for i in invs})}}, {"_id": 0, "id": 1, "name": 1, "owner_id": 1, "phone": 1}).to_list(5000)}
    by = {}
    for i in invs:
        bal = float(i.get("balance") or 0)
        if bal <= 0.5:
            continue
        overdue = (t - d(i.get("due_date") or i["date"])).days
        r = by.setdefault(i["account_id"], {"account_id": i["account_id"], "client": (names.get(i["account_id"]) or {}).get("name"), "0–30": 0, "31–60": 0, "61–90": 0, "90+": 0,
                                            "not_due": 0, "total": 0, "invoices": []})
        if overdue <= 0:
            r["not_due"] += bal
        else:
            r[bucket(overdue)] += bal
        r["total"] += bal
        r["invoices"].append({"id": i["id"], "code": i["code"], "date": i["date"], "due_date": i.get("due_date"), "balance": bal, "overdue_days": max(overdue, 0)})
    rows = sorted(by.values(), key=lambda r: -r["total"])
    for r in rows:
        for k in ("0–30", "31–60", "61–90", "90+", "not_due", "total"):
            r[k] = round(r[k], 2)
    retention = await _sum("ra_bills", {"status": {"$in": list(POSTED_RA)}}, "retention")
    return {"rows": rows, "total": round(sum(r["total"] for r in rows), 2), "overdue": round(sum(r["total"] - r["not_due"] for r in rows), 2),
            "retention_held": retention}


@router.get("/finance/payables")
async def payables(user=Depends(require("finance", "r"))):
    t = today_ist()
    bills = await db.vendor_bills.find({"status": {"$in": ["draft", "verified", "part_paid"]}, "deleted": {"$ne": True}}, {"_id": 0}).to_list(20000)
    names = {v["id"]: v["name"] for v in await db.vendors.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(5000)}
    by = {}
    for b in bills:
        bal = float(b.get("balance") if b.get("balance") is not None else b.get("payable") or 0)
        if bal <= 0.5:
            continue
        overdue = (t - d(b.get("due_date") or b["bill_date"])).days
        r = by.setdefault(b["vendor_id"], {"vendor_id": b["vendor_id"], "vendor": names.get(b["vendor_id"]), "0–30": 0, "31–60": 0, "61–90": 0, "90+": 0, "not_due": 0, "total": 0})
        if overdue <= 0:
            r["not_due"] += bal
        else:
            r[bucket(overdue)] += bal
        r["total"] += bal
    sc = await db.sc_bills.find({"status": "approved", "deleted": {"$ne": True}}, {"_id": 0}).to_list(5000)
    for b in sc:
        bal = float(b.get("net") or 0) - float(b.get("paid") or 0)
        if bal > 0.5:
            r = by.setdefault(b["vendor_id"], {"vendor_id": b["vendor_id"], "vendor": names.get(b["vendor_id"]), "0–30": 0, "31–60": 0, "61–90": 0, "90+": 0, "not_due": 0, "total": 0})
            r["0–30"] += bal
            r["total"] += bal
    rows = sorted(by.values(), key=lambda r: -r["total"])
    return {"rows": rows, "total": round(sum(r["total"] for r in rows), 2)}


@router.get("/finance/gst")
async def gst(user=Depends(require("finance", "r")), month: str = ""):
    month = month or today_ist().strftime("%Y-%m")
    invs = await db.invoices.find({"date": {"$regex": f"^{month}"}, "status": {"$in": ["issued", "part_paid", "paid"]}, "itype": {"$ne": "proforma"}, "deleted": {"$ne": True}}, {"_id": 0}).to_list(10000)
    accs = {a["id"]: a for a in await db.accounts.find({"id": {"$in": list({i["account_id"] for i in invs})}}, {"_id": 0, "id": 1, "name": 1, "gstin": 1}).to_list(5000)}
    b2b, b2c = [], {"taxable": 0, "cgst": 0, "sgst": 0, "igst": 0}
    for i in invs:
        a = accs.get(i["account_id"]) or {}
        row = {"invoice": i["code"], "date": i["date"], "client": a.get("name"), "gstin": a.get("gstin"), "taxable": i.get("subtotal"), "cgst": i.get("cgst"), "sgst": i.get("sgst"),
               "igst": i.get("igst"), "total": i.get("total"), "place_of_supply": i.get("place_of_supply")}
        if a.get("gstin"):
            b2b.append(row)
        else:
            for k in ("taxable", "cgst", "sgst", "igst"):
                b2c[k] += float(row[k] or 0)
    bills = await db.vendor_bills.find({"bill_date": {"$regex": f"^{month}"}, "deleted": {"$ne": True}}, {"_id": 0}).to_list(10000)
    out_tax = round(sum(float(i.get("gst") or 0) for i in invs), 2)
    itc = round(sum(float(b.get("gst") or 0) for b in bills), 2)
    exp_gst = await _sum("expenses", {"date": {"$regex": f"^{month}"}, "status": {"$in": ["approved", "reimbursed"]}}, "gst")
    return {"month": month, "gstr1_b2b": b2b, "gstr1_b2c": {k: round(v, 2) for k, v in b2c.items()},
            "gstr3b": {"outward_taxable": round(sum(float(i.get("subtotal") or 0) for i in invs), 2), "output_tax": out_tax, "itc_purchases": itc,
                       "itc_expenses": exp_gst, "net_payable": round(out_tax - itc - exp_gst, 2)},
            "note": "Summary for the accountant to check before filing; GST rate for works contracts is set per line."}


@router.get("/finance/tds")
async def tds(user=Depends(require("finance", "r")), frm: str = "", to: str = ""):
    t = today_ist()
    frm = frm or t.replace(day=1).isoformat()
    to = to or t.isoformat()
    pays = await db.vendor_payments.find({"date": {"$gte": frm, "$lte": to}, "status": "paid", "deleted": {"$ne": True}}, {"_id": 0}).to_list(10000)
    names = {v["id"]: v for v in await db.vendors.find({}, {"_id": 0, "id": 1, "name": 1, "pan": 1}).to_list(5000)}
    deducted = [{"date": p["date"], "vendor": (names.get(p["vendor_id"]) or {}).get("name"), "pan": (names.get(p["vendor_id"]) or {}).get("pan"), "paid": p["amount"],
                 "tds": p.get("tds") or 0, "section": "194C"} for p in pays if float(p.get("tds") or 0) > 0]
    rec = await db.receipts.find({"date": {"$gte": frm, "$lte": to}, "status": "confirmed", "deleted": {"$ne": True}}, {"_id": 0}).to_list(10000)
    by_client = [{"date": r["date"], "receipt": r["code"], "tds": r.get("tds")} for r in rec if float(r.get("tds") or 0) > 0]
    return {"from": frm, "to": to, "deducted_by_us": deducted, "deducted_by_clients": by_client,
            "total_deducted": round(sum(float(x["tds"]) for x in deducted), 2), "total_by_clients": round(sum(float(x["tds"]) for x in by_client), 2)}


@router.get("/finance/pnl")
async def pnl(user=Depends(require("finance", "r")), frm: str = "", to: str = "", project_id: str = "", branch: str = ""):
    t = today_ist()
    frm = frm or t.replace(month=4 if t.month >= 4 else 4, day=1, year=t.year if t.month >= 4 else t.year - 1).isoformat()
    to = to or t.isoformat()
    q = {"deleted": {"$ne": True}}
    if project_id:
        q["project_id"] = project_id
    if branch:
        q["branch_id"] = branch
    inc = await _sum("invoices", {**q, "date": {"$gte": frm, "$lte": to}, "status": {"$in": ["issued", "part_paid", "paid"]}, "itype": {"$ne": "proforma"}}, "subtotal")
    mat = await _sum("vendor_bills", {**q, "bill_date": {"$gte": frm, "$lte": to}}, "subtotal")
    sc = await _sum("sc_bills", {**q, "period_to": {"$gte": frm, "$lte": to}, "status": {"$in": ["approved", "paid"]}}, "gross")
    exp = await _sum("expenses", {**q, "date": {"$gte": frm, "$lte": to}, "status": {"$in": ["approved", "reimbursed"]}}, "amount")
    pay = 0.0
    if not project_id:
        runs = await db.payroll_runs.find({"month": {"$gte": frm[:7], "$lte": to[:7]}, "status": {"$in": ["approved", "paid"]}, "deleted": {"$ne": True}, **({"branch_id": branch} if branch else {})}, {"_id": 0, "gross_total": 1}).to_list(100)
        pay = round(sum(float(r.get("gross_total") or 0) for r in runs), 2)
    cost = round(mat + sc + exp + pay, 2)
    return {"from": frm, "to": to, "income": inc, "costs": {"material_and_services": mat, "subcontract": sc, "expenses": exp, "payroll": pay}, "total_cost": cost,
            "gross_margin": round(inc - cost, 2), "gross_margin_pct": round((inc - cost) / inc * 100, 1) if inc else None,
            "note": "Without GST. Material is counted when the vendor bill is booked."}


@router.get("/finance/cashflow")
async def cashflow(user=Depends(require("finance", "r")), months: int = 6):
    t = today_ist()
    out = []
    for k in range(months - 1, -1, -1):
        y, m = t.year, t.month - k
        while m <= 0:
            y, m = y - 1, m + 12
        mk = f"{y}-{m:02d}"
        inflow = await _sum("receipts", {"date": {"$regex": f"^{mk}"}, "status": "confirmed"}, "amount")
        vp = await _sum("vendor_payments", {"date": {"$regex": f"^{mk}"}, "status": "paid"}, "amount")
        exp = await _sum("expenses", {"date": {"$regex": f"^{mk}"}, "status": {"$in": ["approved", "reimbursed"]}}, "amount")
        runs = await db.payroll_runs.find({"month": mk, "status": "paid", "deleted": {"$ne": True}}, {"_id": 0, "net_total": 1}).to_list(10)
        payroll = sum(float(r.get("net_total") or 0) for r in runs)
        out.append({"month": mk, "in": inflow, "out": round(vp + exp + payroll, 2), "net": round(inflow - vp - exp - payroll, 2)})
    return out


@router.get("/finance/credit-report")
async def credit_report(user=Depends(require("finance", "r")), fmt: str = "json"):
    rec = await receivables(user)
    t = today_ist()
    rows = []
    for r in rec["rows"]:
        for i in r["invoices"]:
            if i["overdue_days"] > 0:
                last = await db.activities.find_one({"account_id": r["account_id"], "deleted": {"$ne": True}}, {"_id": 0}, sort=[("created_at", -1)])
                rows.append({"client": r["client"], "invoice": i["code"], "due_date": i["due_date"], "overdue_days": i["overdue_days"], "balance": i["balance"],
                             "last_follow_up": (last or {}).get("created_at", "")[:10], "note": (last or {}).get("subject")})
    rows.sort(key=lambda x: -x["overdue_days"])
    if fmt == "pdf":
        s = await get_settings()
        L = Letterhead("Daily credit report", s, subtitle=f"Overdue invoices as of {t.strftime('%d %b %Y')}")
        L.table(["Client", "Invoice", "Due", "Days overdue", "Balance", "Last follow-up"], [[x["client"], x["invoice"], x["due_date"], x["overdue_days"], ind(x["balance"]), x["last_follow_up"]] for x in rows],
                widths=[26, 18, 12, 10, 14, 14], align=list("LLLRRL"))
        L.totals([("Total overdue", sum(x["balance"] for x in rows))])
        return Response(L.build(), media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="credit-report.pdf"'})
    return {"date": t.isoformat(), "rows": rows, "total": round(sum(x["balance"] for x in rows), 2)}


@router.get("/finance/tally.xml")
async def tally_export(user=Depends(require("finance", "e")), frm: str = "", to: str = ""):
    """Sales vouchers in Tally XML (import into Tally Prime: Gateway -> Import -> Vouchers). Check ledger names first."""
    from xml.sax.saxutils import escape as x
    t = today_ist()
    frm = frm or t.replace(day=1).isoformat()
    to = to or t.isoformat()
    s = await get_settings()
    invs = await db.invoices.find({"date": {"$gte": frm, "$lte": to}, "status": {"$in": ["issued", "part_paid", "paid"]}, "itype": {"$ne": "proforma"}, "deleted": {"$ne": True}}, {"_id": 0}).to_list(10000)
    accs = {a["id"]: a["name"] for a in await db.accounts.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(5000)}
    company = x(s.get("tally_company") or s.get("company_name") or "Sellandiamman Power Infra")
    vouchers = []
    for i in invs:
        party = x(accs.get(i["account_id"]) or "Client")
        dt = i["date"].replace("-", "")
        entries = [f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>{party}</LEDGERNAME><ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE><AMOUNT>-{i['total']:.2f}</AMOUNT></ALLLEDGERENTRIES.LIST>",
                   f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>Sales - Works Contract</LEDGERNAME><ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE><AMOUNT>{i['subtotal']:.2f}</AMOUNT></ALLLEDGERENTRIES.LIST>"]
        if i.get("interstate"):
            entries.append(f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>Output IGST</LEDGERNAME><ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE><AMOUNT>{float(i.get('igst') or 0):.2f}</AMOUNT></ALLLEDGERENTRIES.LIST>")
        else:
            entries.append(f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>Output CGST</LEDGERNAME><ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE><AMOUNT>{float(i.get('cgst') or 0):.2f}</AMOUNT></ALLLEDGERENTRIES.LIST>")
            entries.append(f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>Output SGST</LEDGERNAME><ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE><AMOUNT>{float(i.get('sgst') or 0):.2f}</AMOUNT></ALLLEDGERENTRIES.LIST>")
        vouchers.append(f'<TALLYMESSAGE xmlns:UDF="TallyUDF"><VOUCHER VCHTYPE="Sales" ACTION="Create"><DATE>{dt}</DATE><VOUCHERNUMBER>{x(i["code"])}</VOUCHERNUMBER>'
                        f"<PARTYLEDGERNAME>{party}</PARTYLEDGERNAME><VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>{''.join(entries)}</VOUCHER></TALLYMESSAGE>")
    xml = (f"<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME>"
           f"<STATICVARIABLES><SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY></STATICVARIABLES></REQUESTDESC><REQUESTDATA>{''.join(vouchers)}</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>")
    await audit(user, "tally_export", "invoices", None, {"from": frm, "to": to, "count": len(vouchers)})
    return Response(xml, media_type="application/xml", headers={"Content-Disposition": f'attachment; filename="tally-sales-{frm}-{to}.xml"'})


@router.get("/finance/upi/{invoice_id}")
async def upi(invoice_id: str, user=Depends(current_user)):
    inv = await ENG.get_record("invoices", user, invoice_id, raw=True)
    s = await get_settings()
    vpa = s.get("upi_id")
    if not vpa:
        raise HTTPException(409, "UPI is not set up yet (Settings → Collection account)")
    from urllib.parse import quote
    amt = max(float(inv.get("balance") or inv.get("total") or 0), 0)
    uri = f"upi://pay?pa={quote(vpa)}&pn={quote(s.get('short_name') or 'SA Power Infra')}&am={amt:.2f}&cu=INR&tn={quote(inv['code'])}"
    from routes_auth import qr_svg
    return {"upi_uri": uri, "qr_svg": qr_svg(uri), "amount": amt, "bank_details": s.get("bank_details")}


# ====================================================================== expiry calendar
@router.get("/calendar/expiries")
async def expiries(user=Depends(staff_user), days: int = 60):
    t = today_ist()
    lim = (t + timedelta(days=days)).isoformat()
    out = []

    async def add(coll, field, label_fn, link, module, extra=None):
        if not can(user, module, "r"):
            return
        for r in await db[coll].find({field: {"$lte": lim, "$ne": None}, "deleted": {"$ne": True}, **(extra or {})}, {"_id": 0}).to_list(2000):
            v = r.get(field)
            if not v:
                continue
            out.append({"what": label_fn(r), "kind": coll, "date": v, "days_left": (d(v) - t).days, "link": f"{link}/{r['id']}"})

    await add("compliance_items", "valid_until", lambda r: r["name"], "/erp/e/compliance_items", "compliance")
    for f, lab in (("insurance_until", "insurance"), ("fitness_until", "fitness"), ("permit_until", "permit"), ("puc_until", "PUC"), ("driver_licence_until", "driver licence")):
        await add("vehicles", f, lambda r, lab=lab: f"{r['reg_no']} {lab}", "/erp/e/vehicles", "plant", {"status": {"$ne": "sold"}})
    await add("instruments", "calibration_due", lambda r: f"{r['name']} calibration", "/erp/e/instruments", "testing")
    await add("bank_guarantees", "valid_until", lambda r: f"BG {r['bg_no']} ({r['bank']})", "/erp/e/bank_guarantees", "tenders", {"status": "active"})
    await add("workers", "permit_valid_until", lambda r: f"{r['name']} wireman permit", "/erp/e/workers", "subcon", {"active": True})
    await add("workers", "medical_fit_until", lambda r: f"{r['name']} medical fitness", "/erp/e/workers", "subcon", {"active": True})
    await add("authorised_persons", "valid_until", lambda r: f"{r['name']} HT authorisation", "/erp/e/authorised_persons", "hse")
    await add("trainings", "valid_until", lambda r: f"{r['person']} {label_of('x', r.get('course'))}", "/erp/e/trainings", "hse")
    await add("amc_contracts", "end", lambda r: f"AMC {r['title']}", "/erp/e/amc_contracts", "service", {"status": "active"})
    await add("vendors", "licence_valid_until", lambda r: f"{r['name']} licence", "/erp/e/vendors", "procurement", {"active": True})
    await add("prequal_docs", "valid_until", lambda r: r["name"], "/erp/e/prequal_docs", "tenders")
    await add("employees", "licence_valid_until", lambda r: f"{r['name']} licence", "/erp/e/employees", "hr", {"status": "active"})
    out.sort(key=lambda x: x["date"])
    return out
