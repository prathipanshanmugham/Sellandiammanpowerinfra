"""Role dashboards, the CEO dashboard (health score, pillars, alerts, PDF report) and the reports centre."""
import io
from datetime import date, timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

import engine as ENG
import registry as REG
from catalog import label_of, OPTIONS
from core import now, db, require, staff_user, can, today_ist, now_iso, new_id, get_settings, audit, branch_filter, REQ_BRANCH
from routes_ops import project_numbers, receivables, balances, POSTED_RA
from routes_entities import xlsx
from pdf import Letterhead, ind

router = APIRouter()


def d(x):
    return date.fromisoformat(str(x)[:10]) if x else None


def rng(frm, to):
    t = today_ist()
    to_d = d(to) or t
    frm_d = d(frm) or (to_d - timedelta(days=29))
    span = (to_d - frm_d).days + 1
    prev_to = frm_d - timedelta(days=1)
    prev_frm = prev_to - timedelta(days=span - 1)
    return frm_d.isoformat(), to_d.isoformat(), prev_frm.isoformat(), prev_to.isoformat()


async def ssum(coll, q, field):
    rows = await db[coll].find({**q, "deleted": {"$ne": True}}, {"_id": 0, field: 1}).to_list(100000)
    return round(sum(float(r.get(field) or 0) for r in rows), 2)


def kpi(key, label, value, prev=None, fmt="int", link=None, good="up"):
    k = {"key": key, "label": label, "value": value, "fmt": fmt}
    if prev is not None:
        k["prev"] = prev
        k["change_pct"] = round((value - prev) / prev * 100, 1) if prev else None
        k["good"] = good
    if link:
        k["link"] = link
    return k


async def scoped(coll, user, q=None):
    e = REG.E.get(coll)
    base = await ENG.scope_filter(e, user) if e else {"deleted": {"$ne": True}}
    return {"$and": [base, q or {}]}


async def cnt(coll, user, q=None):
    return await db[coll].count_documents(await scoped(coll, user, q))


async def rows(coll, user, q=None, sort=("created_at", -1), limit=8, fields=None):
    out = await db[coll].find(await scoped(coll, user, q), {"_id": 0}).sort(*sort).to_list(limit)
    e = REG.E.get(coll)
    refs = await ENG.ref_titles(e, out) if e else {}
    return [{"id": r["id"], "code": r.get("code"), "title": ENG.title_of(e, r) if e else r.get("name"), "status": r.get((e.get("status") or {}).get("field") if e else "status"),
             "sub": ", ".join(str(x) for x in [(refs.get(f["ref"]) or {}).get(r.get(f["k"])) for f in (e["fields"] if e else []) if f["t"] == "ref" and f["k"] in (fields or [])] if x),
             "date": r.get("due_on") or r.get("due_at") or r.get("date") or r.get("scheduled_on") or r.get("restore_by") or r.get("next_follow_up") or r.get("created_at"),
             "amount": r.get("total") or r.get("amount") or r.get("value")} for r in out]


def L(title, entity, items, link=None, empty="Nothing here"):
    return {"title": title, "entity": entity, "items": items, "link": link or f"/erp/e/{entity}", "empty": empty}


@router.get("/dashboard")
async def dashboard(user=Depends(staff_user)):
    role = user["role"]
    t = today_ist().isoformat()
    soon = (today_ist() + timedelta(days=7)).isoformat()
    month = t[:7]
    k, lists = [], []
    if role in ("super_admin", "director", "branch_manager", "auditor"):
        k += [kpi("new_leads", "New leads (7 days)", await cnt("leads", user, {"created_at": {"$gte": (today_ist() - timedelta(days=7)).isoformat()}}), link="/erp/crm"),
              kpi("open_projects", "Live projects", await cnt("projects", user, {"status": {"$in": ["mobilising", "in_progress", "testing"]}}), link="/erp/e/projects"),
              kpi("approvals", "Waiting for approval", await db.approvals.count_documents({"status": "pending"}), link="/erp/approvals"),
              kpi("open_tickets", "Open service requests", await cnt("tickets", user, {"status": {"$nin": ["resolved", "closed"]}}), link="/erp/e/tickets")]
        if can(user, "finance", "r"):
            rec = await receivables(user)
            k.append(kpi("overdue", "Overdue receivables", rec["overdue"], fmt="inr", link="/erp/finance"))
        lists += [L("Leads waiting for first response", "leads", await rows("leads", user, {"stage": "new", "first_response_at": None}, ("response_due_at", 1), fields=["owner_id"])),
                  L("Tenders due this week", "tenders", await rows("tenders", user, {"due_on": {"$lte": soon + "T23:59", "$gte": t}, "status": {"$in": ["identified", "preparing"]}}, ("due_on", 1))),
                  L("Projects", "projects", await rows("projects", user, {"status": {"$in": ["mobilising", "in_progress", "testing"]}}, ("end_date", 1), fields=["account_id"]))]
    if role == "sales":
        k += [kpi("my_new", "My new leads", await cnt("leads", user, {"stage": "new"}), link="/erp/crm"),
              kpi("follow", "Follow-ups due", await cnt("leads", user, {"next_follow_up": {"$lte": t + "T23:59"}, "stage": {"$nin": ["won", "lost"]}}), link="/erp/crm"),
              kpi("quoted", "Quoted", await cnt("leads", user, {"stage": {"$in": ["quoted", "negotiation"]}}), link="/erp/crm"),
              kpi("won_m", "Won this month", await cnt("leads", user, {"stage": "won", "updated_at": {"$regex": f"^{month}"}}))]
        lists += [L("Respond first", "leads", await rows("leads", user, {"stage": "new"}, ("response_due_at", 1))),
                  L("Follow-ups due", "leads", await rows("leads", user, {"next_follow_up": {"$lte": t + "T23:59"}, "stage": {"$nin": ["won", "lost"]}}, ("next_follow_up", 1))),
                  L("My site surveys", "surveys", await rows("surveys", user, {"status": "scheduled"}, ("scheduled_at", 1)))]
    if role in ("estimator", "tender_exec"):
        k += [kpi("boq", "Estimates in draft", await cnt("boqs", user, {"status": "draft"}), link="/erp/e/boqs"),
              kpi("tenders", "Tenders in preparation", await cnt("tenders", user, {"status": {"$in": ["identified", "preparing"]}}), link="/erp/e/tenders"),
              kpi("bg", "BGs expiring (30 days)", await cnt("bank_guarantees", user, {"status": "active", "valid_until": {"$lte": (today_ist() + timedelta(days=30)).isoformat()}}))]
        lists += [L("Tenders by due date", "tenders", await rows("tenders", user, {"status": {"$in": ["identified", "preparing"]}}, ("due_on", 1))),
                  L("Leads to estimate", "leads", await rows("leads", user, {"stage": {"$in": ["survey_done", "estimating"]}}, ("updated_at", -1)))]
    if role in ("project_manager", "site_engineer"):
        k += [kpi("projects", "My live projects", await cnt("projects", user, {"status": {"$in": ["mobilising", "in_progress", "testing"]}}), link="/erp/e/projects"),
              kpi("dpr", "Daily reports today", await cnt("dprs", user, {"date": t}), link="/erp/e/dprs"),
              kpi("snags", "Open snags", await cnt("snags", user, {"status": "open"}), link="/erp/e/snags"),
              kpi("permits", "Active permits", await cnt("permits", user, {"status": "active"}), link="/erp/e/permits")]
        lists += [L("My projects", "projects", await rows("projects", user, {"status": {"$in": ["mobilising", "in_progress", "testing"]}}, ("end_date", 1), fields=["account_id"])),
                  L("Milestones due in 7 days", "milestones", await rows("milestones", user, {"planned_end": {"$lte": soon}, "status": {"$ne": "done"}}, ("planned_end", 1), fields=["project_id"])),
                  L("Open RFIs", "rfis", await rows("rfis", user, {"status": "open"}, ("due_on", 1), fields=["project_id"])),
                  L("Material requests", "purchase_requests", await rows("purchase_requests", user, {"status": {"$in": ["draft", "pending_approval", "approved", "ordered"]}}, fields=["project_id"]))]
    if role == "liaison":
        k += [kpi("open", "Open applications", await cnt("liaisons", user, {"stage": {"$nin": ["energised", "closed"]}}), link="/erp/e/liaisons"),
              kpi("follow", "Follow-ups due", await cnt("liaisons", user, {"next_follow_up": {"$lte": t + "T23:59"}}))]
        lists += [L("Follow up today", "liaisons", await rows("liaisons", user, {"stage": {"$nin": ["energised", "closed"]}}, ("next_follow_up", 1), fields=["project_id"]))]
    if role == "qaqc":
        k += [kpi("ncr", "Open NCRs", await cnt("ncrs", user, {"status": {"$ne": "closed"}}), link="/erp/e/ncrs"),
              kpi("cal", "Instruments due for calibration (30 days)", await cnt("instruments", user, {"calibration_due": {"$lte": (today_ist() + timedelta(days=30)).isoformat()}}), link="/erp/e/instruments"),
              kpi("draft", "Test reports to issue", await cnt("test_reports", user, {"status": "draft"}), link="/erp/e/test_reports")]
        lists += [L("Test reports in draft", "test_reports", await rows("test_reports", user, {"status": "draft"}, fields=["project_id"])),
                  L("Open NCRs", "ncrs", await rows("ncrs", user, {"status": {"$ne": "closed"}}, ("due_on", 1), fields=["project_id"]))]
    if role == "safety":
        k += [kpi("permits", "Active permits", await cnt("permits", user, {"status": "active"}), link="/erp/e/permits"),
              kpi("req", "Permits to approve", await cnt("permits", user, {"status": "requested"}), link="/erp/e/permits"),
              kpi("inc", "Open incidents", await cnt("incidents", user, {"status": {"$ne": "closed"}}), link="/erp/e/incidents")]
        lists += [L("Permits to approve", "permits", await rows("permits", user, {"status": "requested"}, fields=["project_id"])),
                  L("Active permits", "permits", await rows("permits", user, {"status": "active"}, ("valid_to", 1), fields=["project_id"]))]
    if role == "purchase":
        k += [kpi("pr", "Approved requests to buy", await cnt("purchase_requests", user, {"status": "approved"}), link="/erp/e/purchase_requests"),
              kpi("po", "POs awaiting delivery", await cnt("purchase_orders", user, {"status": {"$in": ["sent", "partly_received"]}}), link="/erp/e/purchase_orders"),
              kpi("vreg", "New vendor registrations", await cnt("vendor_registrations", user, {"status": "new"}), link="/erp/e/vendor_registrations")]
        lists += [L("Material requests to process", "purchase_requests", await rows("purchase_requests", user, {"status": "approved"}, ("required_by", 1), fields=["project_id"])),
                  L("Deliveries due", "purchase_orders", await rows("purchase_orders", user, {"status": {"$in": ["sent", "partly_received"]}}, ("delivery_by", 1), fields=["vendor_id"]))]
    if role == "store":
        k += [kpi("grn", "GRNs to post", await cnt("grns", user, {"status": "draft"}), link="/erp/e/grns"),
              kpi("transit", "Transfers in transit", await cnt("material_moves", user, {"status": "in_transit"}), link="/erp/e/material_moves"),
              kpi("drums", "Cable drums at site", await cnt("cable_drums", user, {"status": "at_site"}), link="/erp/e/cable_drums")]
        lists += [L("Goods receipts in draft", "grns", await rows("grns", user, {"status": "draft"}, fields=["vendor_id"])),
                  L("In transit", "material_moves", await rows("material_moves", user, {"status": "in_transit"}))]
    if role == "accounts":
        rec = await receivables(user)
        bal = await balances(user)
        k += [kpi("overdue", "Overdue receivables", rec["overdue"], fmt="inr", link="/erp/finance"),
              kpi("cash", "Cash & bank", bal["total"], fmt="inr", link="/erp/finance"),
              kpi("pending", "Payments to confirm", await cnt("receipts", user, {"status": "pending"}), link="/erp/e/receipts"),
              kpi("bills", "Vendor bills to verify", await cnt("vendor_bills", user, {"status": "draft"}), link="/erp/e/vendor_bills")]
        lists += [L("Client payment notices", "receipts", await rows("receipts", user, {"status": "pending"}, fields=["account_id"])),
                  L("Invoices overdue", "invoices", await rows("invoices", user, {"status": {"$in": ["issued", "part_paid"]}, "due_date": {"$lt": t}}, ("due_date", 1), fields=["account_id"]))]
    if role == "hr":
        k += [kpi("leave", "Leave requests", await cnt("leaves", user, {"status": "pending_approval"}), link="/erp/e/leaves"),
              kpi("flags", "Attendance flags today", await cnt("attendance", user, {"date": t, "flag": {"$nin": ["", None]}}), link="/erp/e/attendance"),
              kpi("apps", "New job applications", await cnt("job_applications", user, {"status": "new"}), link="/erp/e/job_applications")]
        lists += [L("Leave requests", "leaves", await rows("leaves", user, {"status": "pending_approval"}, fields=["employee_id"]))]
    if role in ("service_manager", "technician"):
        k += [kpi("open", "Open requests", await cnt("tickets", user, {"status": {"$nin": ["resolved", "closed"]}}), link="/erp/e/tickets"),
              kpi("breach", "Past target", await cnt("tickets", user, {"sla_breached": True, "status": {"$nin": ["resolved", "closed"]}}), link="/erp/e/tickets"),
              kpi("visits", "Visits this week", await cnt("pm_jobs", user, {"status": "scheduled", "scheduled_on": {"$lte": soon}}), link="/erp/e/pm_jobs")]
        lists += [L("Requests by fix-by time", "tickets", await rows("tickets", user, {"status": {"$nin": ["resolved", "closed"]}}, ("restore_by", 1), fields=["account_id"])),
                  L("Maintenance visits", "pm_jobs", await rows("pm_jobs", user, {"status": "scheduled"}, ("scheduled_on", 1), fields=["account_id"]))]
        if role == "service_manager":
            lists.append(L("AMC renewals (60 days)", "amc_contracts", await rows("amc_contracts", user, {"status": "active", "end": {"$lte": (today_ist() + timedelta(days=60)).isoformat()}}, ("end", 1), fields=["account_id"])))
    if role == "marketing":
        k += [kpi("leads_m", "Leads this month", await cnt("leads", user, {"created_at": {"$regex": f"^{month}"}}), link="/erp/marketing"),
              kpi("posts", "Scheduled posts", await cnt("insights", user, {"status": "scheduled"}), link="/erp/e/insights")]
        lists += [L("Latest leads", "leads", await rows("leads", user, {}, ("created_at", -1)))]
    tasks = await rows("tasks", user, {"assigned_to": user["id"], "status": {"$ne": "done"}}, ("due_on", 1))
    lists.append(L("My tasks", "tasks", tasks, empty="No open tasks"))
    approvals = await db.approvals.find({"status": "pending", "approver_roles": user["role"]}, {"_id": 0}).sort("created_at", 1).to_list(10)
    return {"kpis": k, "lists": lists, "approvals": [{"id": a["id"], "title": a["title"], "amount": a.get("amount"), "at": a["created_at"]} for a in approvals if a.get("requested_by") != user["id"]]}


# ====================================================================== CEO dashboard
async def period_numbers(frm, to, bq):
    won = await db.projects.find({**bq, "wo_date": {"$gte": frm, "$lte": to}, "deleted": {"$ne": True}}, {"_id": 0, "contract_value": 1}).to_list(5000)
    intake = round(sum(float(p.get("contract_value") or 0) for p in won), 2)
    revenue = await ssum("invoices", {**bq, "date": {"$gte": frm, "$lte": to}, "status": {"$in": ["issued", "part_paid", "paid"]}, "itype": {"$ne": "proforma"}}, "subtotal")
    collected = await ssum("receipts", {**bq, "date": {"$gte": frm, "$lte": to}, "status": "confirmed"}, "amount")
    leads = await db.leads.count_documents({**bq, "created_at": {"$gte": frm, "$lte": to + "T23:59:59"}, "deleted": {"$ne": True}})
    won_leads = await db.leads.count_documents({**bq, "stage": "won", "updated_at": {"$gte": frm, "$lte": to + "T23:59:59"}, "deleted": {"$ne": True}})
    costs = (await ssum("vendor_bills", {**bq, "bill_date": {"$gte": frm, "$lte": to}}, "subtotal") +
             await ssum("sc_bills", {**bq, "period_to": {"$gte": frm, "$lte": to}, "status": {"$in": ["approved", "paid"]}}, "gross") +
             await ssum("expenses", {**bq, "date": {"$gte": frm, "$lte": to}, "status": {"$in": ["approved", "reimbursed"]}}, "amount"))
    incidents = await db.incidents.count_documents({**bq, "occurred_at": {"$gte": frm, "$lte": to + "T23:59"}, "kind": {"$in": ["lti", "medical", "fatality"]}, "deleted": {"$ne": True}})
    near = await db.incidents.count_documents({**bq, "occurred_at": {"$gte": frm, "$lte": to + "T23:59"}, "kind": "near_miss", "deleted": {"$ne": True}})
    return {"order_intake": intake, "revenue": revenue, "collected": collected, "leads": leads, "won_leads": won_leads,
            "gross_margin": round(revenue - costs, 2), "gross_margin_pct": round((revenue - costs) / revenue * 100, 1) if revenue else None,
            "recordable_incidents": incidents, "near_misses": near}


def clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))


@router.get("/ceo")
async def ceo(user=Depends(require("ceo", "r")), frm: str = "", to: str = "", branch: str = ""):
    frm, to, pfrm, pto = rng(frm, to)
    if branch and branch != "all":
        REQ_BRANCH.set(branch)
    bq = branch_filter(user)
    cur = await period_numbers(frm, to, bq)
    prev = await period_numbers(pfrm, pto, bq)
    live = await db.projects.find({**bq, "status": {"$in": ["mobilising", "in_progress", "testing", "on_hold"]}, "deleted": {"$ne": True}}, {"_id": 0}).to_list(500)
    order_book, health = 0.0, []
    accs = {a["id"]: a["name"] for a in await db.accounts.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(5000)}
    users = {u["id"]: u["name"] for u in await db.users.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(2000)}
    t = today_ist()
    late_count = 0
    for p in live:
        n = await project_numbers(p)
        order_book += max(n["contract_value"] - n["billed"], 0)
        sched_var = None
        if p.get("start_date") and p.get("end_date"):
            span = (d(p["end_date"]) - d(p["start_date"])).days or 1
            planned = clamp((t - d(p["start_date"])).days / span * 100)
            sched_var = round(n["percent_complete"] - planned, 1)
            if sched_var < -10:
                late_count += 1
        risk = "red" if (sched_var is not None and sched_var < -15) or (n["forecast_margin_pct"] is not None and n["forecast_margin_pct"] < 5) else \
               "amber" if (sched_var is not None and sched_var < -5) or n["over_under_billed"] < -0.1 * (n["contract_value"] or 1) else "green"
        health.append({"id": p["id"], "code": p.get("code"), "name": p["name"], "client": accs.get(p.get("account_id")), "manager": users.get(p.get("manager_id")),
                       "contract_value": n["contract_value"], "percent_complete": n["percent_complete"], "billed": n["billed"],
                       "billed_pct": round(n["billed"] / n["contract_value"] * 100, 1) if n["contract_value"] else 0, "over_under": n["over_under_billed"],
                       "schedule_variance": sched_var, "forecast_margin_pct": n["forecast_margin_pct"], "cost_to_complete": n["cost_to_complete"], "risk": risk})
    monthly_rev = cur["revenue"] / max(((d(to) - d(frm)).days + 1) / 30, 1)
    months_in_hand = round(order_book / monthly_rev, 1) if monthly_rev else None
    rec = await receivables(user)
    bal = await balances(user)
    payables = await ssum("vendor_bills", {"status": {"$in": ["draft", "verified", "part_paid"]}}, "balance")
    tenders = await db.tenders.find({**bq, "deleted": {"$ne": True}}, {"_id": 0, "status": 1, "value_estimate": 1, "our_quote": 1}).to_list(2000)
    tstat = {}
    for x in tenders:
        s = tstat.setdefault(x["status"], {"count": 0, "value": 0.0})
        s["count"] += 1
        s["value"] += float(x.get("our_quote") or x.get("value_estimate") or 0)
    decided = sum(tstat.get(s, {}).get("count", 0) for s in ("won", "lost"))
    win_rate = round(tstat.get("won", {}).get("count", 0) / decided * 100) if decided else None
    funnel = []
    for st_ in ("new", "contacted", "survey_done", "quoted", "negotiation", "won"):
        funnel.append({"stage": label_of("lead_stages", st_), "count": await db.leads.count_documents({**bq, "stage": st_, "deleted": {"$ne": True}})})
    open_t = await db.tickets.count_documents({**bq, "status": {"$nin": ["resolved", "closed"]}, "deleted": {"$ne": True}})
    breached = await db.tickets.count_documents({**bq, "sla_breached": True, "status": {"$nin": ["resolved", "closed"]}, "deleted": {"$ne": True}})
    renewals = await db.amc_contracts.count_documents({**bq, "status": "active", "end": {"$lte": (t + timedelta(days=60)).isoformat()}, "deleted": {"$ne": True}})
    mh = await ssum("hse_manhours", {"month": {"$gte": frm[:7], "$lte": to[:7]}}, "man_hours")
    ltis = await db.incidents.count_documents({"kind": "lti", "occurred_at": {"$gte": frm, "$lte": to + "T23:59"}, "deleted": {"$ne": True}})
    ltifr = round(ltis * 1_000_000 / mh, 2) if mh else None
    stuck = await db.approvals.count_documents({"status": "pending", "created_at": {"$lte": (now() - timedelta(days=2)).isoformat()}})
    from routes_ops import expiries
    exp = [x for x in await expiries(user, 30)]
    # ---- health score
    pillars = []
    growth = clamp(50 + ((cur["order_intake"] - prev["order_intake"]) / prev["order_intake"] * 50 if prev["order_intake"] else (25 if cur["order_intake"] else 0)) + (min(months_in_hand or 0, 6) * 5))
    pillars.append({"key": "growth", "label": "Order book & growth", "score": round(growth), "weight": 20, "note": f"{months_in_hand or 0} months of work in hand"})
    gm = cur["gross_margin_pct"]
    fm = [h["forecast_margin_pct"] for h in health if h["forecast_margin_pct"] is not None]
    avg_fm = round(sum(fm) / len(fm), 1) if fm else None
    prof = clamp((avg_fm if avg_fm is not None else (gm or 0)) * 4) if (avg_fm is not None or gm is not None) else 50
    pillars.append({"key": "profit", "label": "Profit", "score": round(prof), "weight": 20, "note": f"Forecast project margin {avg_fm if avg_fm is not None else '—'}%, book margin this period {gm if gm is not None else '—'}%"})
    overdue_share = rec["overdue"] / rec["total"] if rec["total"] else 0
    cash = clamp(100 - overdue_share * 100 + (10 if bal["total"] > payables else -10))
    pillars.append({"key": "cash", "label": "Cash", "score": round(cash), "weight": 20, "note": f"{round(overdue_share * 100)}% of receivables overdue"})
    reds = sum(1 for h in health if h["risk"] == "red")
    ambers = sum(1 for h in health if h["risk"] == "amber")
    execu = clamp(100 - reds * 20 - ambers * 8) if health else 70
    pillars.append({"key": "execution", "label": "Project execution", "score": round(execu), "weight": 20, "note": f"{reds} red, {ambers} amber of {len(health)} live"})
    safe = clamp(100 - cur["recordable_incidents"] * 30 + min(cur["near_misses"], 5) * 2)
    pillars.append({"key": "safety", "label": "Safety", "score": round(safe), "weight": 10, "note": f"{cur['recordable_incidents']} recordable incidents, {cur['near_misses']} near-misses reported"})
    serv = clamp(100 - (breached / open_t * 100 if open_t else 0) - renewals * 2)
    pillars.append({"key": "service", "label": "Service", "score": round(serv), "weight": 5, "note": f"{breached} of {open_t} open requests past target"})
    team = clamp(100 - stuck * 5)
    pillars.append({"key": "team", "label": "Team & approvals", "score": round(team), "weight": 5, "note": f"{stuck} approvals waiting more than 2 days"})
    score = round(sum(p["score"] * p["weight"] for p in pillars) / sum(p["weight"] for p in pillars))
    # ---- alerts (evidence, money, who acts, due date)
    alerts = await build_alerts(health, rec, exp, stuck, breached, user)
    kpis = [kpi("order_intake", "Order intake", cur["order_intake"], prev["order_intake"], "inr"),
            kpi("order_book", "Order book (unbilled)", round(order_book, 2), None, "inr"),
            kpi("months", "Months of work in hand", months_in_hand or 0, None, "1dp"),
            kpi("revenue", "Revenue (without GST)", cur["revenue"], prev["revenue"], "inr"),
            kpi("gm", "Gross margin %", cur["gross_margin_pct"] or 0, prev["gross_margin_pct"], "1dp"),
            kpi("cash", "Cash & bank", bal["total"], None, "inr"),
            kpi("collected", "Collected", cur["collected"], prev["collected"], "inr"),
            kpi("receivables", "Receivables", rec["total"], None, "inr", good="down"),
            kpi("retention", "Retention due", rec["retention_held"], None, "inr"),
            kpi("payables", "Payables", payables, None, "inr", good="down"),
            kpi("leads", "Leads", cur["leads"], prev["leads"]),
            kpi("win_rate", "Tender win rate %", win_rate or 0, None, "int")]
    return {"from": frm, "to": to, "prev_from": pfrm, "prev_to": pto, "score": score, "pillars": pillars, "kpis": kpis, "projects": health,
            "tenders": [{"status": label_of("x", k), "key": k, **v} for k, v in tstat.items()], "win_rate": win_rate, "funnel": funnel,
            "service": {"open": open_t, "breached": breached, "renewals_60d": renewals},
            "safety": {"man_hours": mh, "ltifr": ltifr, "recordable": cur["recordable_incidents"], "near_misses": cur["near_misses"]},
            "stuck_approvals": stuck, "expiring": exp[:15], "alerts": alerts}


async def build_alerts(health, rec, exp, stuck, breached, user):
    t = today_ist()
    found = []
    for h in health:
        if h["risk"] == "red":
            found.append({"key": f"project:{h['id']}:red", "title": f"{h['name']} is at risk", "evidence": f"Schedule {h['schedule_variance']}% vs plan, forecast margin {h['forecast_margin_pct']}%",
                          "money": h["cost_to_complete"], "owner": h["manager"], "link": f"/erp/projects/{h['id']}"})
        if h["over_under"] < -0.15 * (h["contract_value"] or 1):
            found.append({"key": f"project:{h['id']}:underbilled", "title": f"Under-billed on {h['name']}", "evidence": f"{h['percent_complete']}% done but {h['billed_pct']}% billed",
                          "money": -h["over_under"], "owner": h["manager"], "link": f"/erp/projects/{h['id']}"})
    for r in rec["rows"][:20]:
        old = [i for i in r["invoices"] if i["overdue_days"] > 60]
        if old:
            amt = round(sum(i["balance"] for i in old), 2)
            found.append({"key": f"ar:{r['account_id']}:60", "title": f"{r['client']} owes for more than 60 days", "evidence": f"{len(old)} invoice(s) overdue, oldest {max(i['overdue_days'] for i in old)} days",
                          "money": amt, "owner": "Accounts", "link": "/erp/finance"})
    for x in exp:
        if x["days_left"] <= 7:
            found.append({"key": f"exp:{x['link']}:{x['date']}", "title": f"{x['what']} {'expired' if x['days_left'] < 0 else 'expires'} {x['date']}",
                          "evidence": f"{abs(x['days_left'])} days {'ago' if x['days_left'] < 0 else 'left'}", "money": None, "owner": "Admin", "link": x["link"]})
    if stuck:
        found.append({"key": f"approvals:stuck:{t.isoformat()}", "title": f"{stuck} approvals waiting more than 2 days", "evidence": "Approvals inbox", "money": None, "owner": "Approvers", "link": "/erp/approvals"})
    if breached:
        found.append({"key": f"sla:{t.isoformat()}", "title": f"{breached} service requests past their target", "evidence": "Service requests", "money": None, "owner": "Service manager", "link": "/erp/e/tickets"})
    out = []
    for a in found:
        ex = await db.alerts.find_one({"key": a["key"]}, {"_id": 0})
        if not ex:
            ex = {"id": new_id(), **a, "status": "new", "created_at": now_iso(), "due": (t + timedelta(days=3)).isoformat()}
            await db.alerts.insert_one(dict(ex))
        else:
            await db.alerts.update_one({"key": a["key"]}, {"$set": {k: a[k] for k in ("title", "evidence", "money", "owner", "link")}})
            ex.update({k: a[k] for k in ("title", "evidence", "money", "owner", "link")})
        if ex.get("status") not in ("resolved", "not_a_problem"):
            out.append(ex)
    return out


@router.patch("/ceo/alerts/{aid}")
async def alert_status(aid: str, body: dict, user=Depends(require("ceo", "r"))):
    st = body.get("status")
    if st not in ("new", "seen", "handling", "resolved", "not_a_problem"):
        raise HTTPException(422, "Unknown status")
    await db.alerts.update_one({"id": aid}, {"$set": {"status": st, "note": (body.get("note") or "")[:500], "by": user["id"], "at": now_iso()}})
    await audit(user, "alert_status", "alerts", aid, {"status": st})
    return {"ok": True}


@router.get("/ceo/report.pdf")
async def ceo_pdf(user=Depends(require("ceo", "e")), frm: str = "", to: str = "", branch: str = ""):
    data = await ceo(user, frm, to, branch)
    s = await get_settings()
    L = Letterhead("CEO report", s, subtitle=f"{data['from']} to {data['to']}, compared with {data['prev_from']} to {data['prev_to']}")
    L.h(f"Health score: {data['score']} / 100")
    L.table(["Pillar", "Score", "Weight", "Why"], [[p["label"], p["score"], f"{p['weight']}%", p["note"]] for p in data["pillars"]], widths=[22, 10, 10, 58])
    L.h("Key numbers")

    def f(k):
        v = k["value"]
        return f"Rs. {ind(v, 0)}" if k["fmt"] == "inr" else str(v)
    L.table(["Measure", "This period", "Previous", "Change"], [[k["label"], f(k), (f"Rs. {ind(k['prev'], 0)}" if k["fmt"] == "inr" else str(k["prev"])) if k.get("prev") is not None else "—",
                                                            f"{k['change_pct']}%" if k.get("change_pct") is not None else "—"] for k in data["kpis"]], widths=[34, 24, 24, 18], align=list("LRRR"))
    L.h("Projects")
    L.table(["Project", "Value", "% done", "% billed", "Schedule", "Margin", "Risk"], [[p["name"], ind(p["contract_value"], 0), p["percent_complete"], p["billed_pct"],
                                                                                       p["schedule_variance"], p["forecast_margin_pct"], p["risk"].upper()] for p in data["projects"]],
            widths=[30, 14, 9, 9, 11, 10, 9], align=list("LRRRRRL"))
    if data["alerts"]:
        L.h("Alerts")
        L.table(["Alert", "Evidence", "Money", "Who acts"], [[a["title"], a["evidence"], ind(a["money"], 0) if a.get("money") else "", a.get("owner")] for a in data["alerts"]], widths=[34, 34, 14, 18])
    await audit(user, "ceo_report", "ceo", None, {"from": data["from"], "to": data["to"]})
    return Response(L.build(), media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="ceo-report.pdf"'})


# ====================================================================== reports centre
REPORTS = [
    {"key": "leads_by_source", "group": "Sales & CRM", "title": "Leads by source", "module": "crm"},
    {"key": "proposal_register", "group": "Sales & CRM", "title": "Proposal register", "module": "proposals"},
    {"key": "win_loss", "group": "Sales & CRM", "title": "Won and lost leads", "module": "crm"},
    {"key": "tender_register", "group": "Tenders", "title": "Tender register", "module": "tenders"},
    {"key": "bg_register", "group": "Tenders", "title": "EMD & bank guarantee register", "module": "tenders"},
    {"key": "project_status", "group": "Projects", "title": "Project status", "module": "projects"},
    {"key": "ra_register", "group": "Projects", "title": "RA bill register", "module": "projects"},
    {"key": "variation_register", "group": "Projects", "title": "Variation register", "module": "projects"},
    {"key": "dpr_summary", "group": "Projects", "title": "Daily report summary", "module": "site"},
    {"key": "po_register", "group": "Procurement", "title": "Purchase order register", "module": "procurement"},
    {"key": "pending_deliveries", "group": "Procurement", "title": "Pending deliveries", "module": "procurement"},
    {"key": "vendor_performance", "group": "Procurement", "title": "Vendor performance", "module": "procurement"},
    {"key": "stock", "group": "Stores", "title": "Stock statement", "module": "stores"},
    {"key": "drums", "group": "Stores", "title": "Cable drum statement", "module": "stores"},
    {"key": "sales_register", "group": "Finance", "title": "Sales register", "module": "finance"},
    {"key": "purchase_register", "group": "Finance", "title": "Purchase register", "module": "finance"},
    {"key": "receivables", "group": "Finance", "title": "Receivables ageing", "module": "finance"},
    {"key": "expenses", "group": "Finance", "title": "Expense register", "module": "finance"},
    {"key": "sla", "group": "Service", "title": "Service SLA compliance", "module": "service"},
    {"key": "amc_renewals", "group": "Service", "title": "AMC renewals", "module": "service"},
    {"key": "incidents", "group": "Safety", "title": "Incident register", "module": "hse"},
    {"key": "permit_register", "group": "Safety", "title": "Permit register", "module": "hse"},
    {"key": "attendance", "group": "HR", "title": "Attendance register", "module": "hr"},
    {"key": "expiry", "group": "Compliance", "title": "Expiry calendar", "module": "compliance"},
]
RMAP = {r["key"]: r for r in REPORTS}


@router.get("/reports")
async def reports_catalog(user=Depends(staff_user)):
    return [r for r in REPORTS if can(user, r["module"], "r") and (can(user, "reports", "r") or can(user, r["module"], "e"))]


async def ent_rows(key, user, params, cols):
    data = await ENG.list_records(key, user, {**params, "size": "5000"})
    e = REG.E[key]
    fmap = {f["k"]: f for f in e["fields"]}
    from routes_entities import cell_text
    sf = ENG.status_field(e)
    out = []
    for r in data["items"]:
        row = []
        for c in cols:
            if c == "status":
                row.append(next((s["label"] for s in e["status"]["states"] if s["value"] == r.get(sf)), r.get(sf)))
            elif fmap.get(c, {}).get("t") in ("money", "number", "percent"):
                row.append(r.get(c) or 0)
            else:
                row.append(cell_text(e, fmap.get(c), r.get(c), data["refs"]) if c in fmap else r.get(c, ""))
        out.append(row)
    heads = [("Status" if c == "status" else "Code" if c == "code" else fmap[c]["l"]) for c in cols]
    return heads, out


async def run_report(key, user, frm, to):
    t = today_ist()
    frm = frm or (t - timedelta(days=89)).isoformat()
    to = to or t.isoformat()
    p = {"from": frm, "to": to}
    if key == "leads_by_source":
        from routes_crm import marketing
        m = await marketing(user, frm, to)
        return ["Source", "Leads", "Won", "Conversion %", "Spend", "Cost per lead", "Revenue"], [[r["label"], r["leads"], r["won"], r["conversion_pct"], r["spend"], r["cost_per_lead"] or "", r["revenue"]] for r in m["by_source"]]
    if key == "proposal_register":
        return await ent_rows("proposals", user, {**p, "date_field": "created_at"}, ["code", "title", "account_id", "total", "margin_pct", "status", "valid_until"])
    if key == "win_loss":
        h, r = await ent_rows("leads", user, {**p, "date_field": "updated_at", "stage": "won,lost"}, ["code", "name", "company", "service", "source", "value", "status", "lost_reason"])
        return h, r
    if key == "tender_register":
        return await ent_rows("tenders", user, {}, ["code", "title", "authority", "portal", "due_on", "value_estimate", "our_quote", "l1_amount", "rank", "status"])
    if key == "bg_register":
        return await ent_rows("bank_guarantees", user, {}, ["kind", "bg_no", "bank", "amount", "issued_on", "valid_until", "claim_until", "status"])
    if key == "project_status":
        rows = []
        for pr in (await ENG.list_records("projects", user, {"size": "500"}))["items"]:
            n = await project_numbers(pr)
            rows.append([pr.get("code"), pr["name"], label_of("project_status", pr.get("status")), n["contract_value"], n["percent_complete"], n["billed"], n["received"], n["over_under_billed"]])
        return ["Code", "Project", "Status", "Contract value", "% complete", "Billed", "Received", "Over / under billed"], rows
    if key == "ra_register":
        return await ent_rows("ra_bills", user, {**p, "date_field": "period_to"}, ["code", "project_id", "bill_no", "period_to", "gross", "retention", "tds", "net", "certified_amount", "status"])
    if key == "variation_register":
        return await ent_rows("variations", user, {}, ["code", "project_id", "title", "amount", "status"])
    if key == "dpr_summary":
        return await ent_rows("dprs", user, p, ["date", "project_id", "manpower_total", "weather", "hindrances"])
    if key == "po_register":
        return await ent_rows("purchase_orders", user, p, ["code", "date", "vendor_id", "project_id", "subtotal", "gst", "total", "status"])
    if key == "pending_deliveries":
        return await ent_rows("purchase_orders", user, {"status": "sent,partly_received"}, ["code", "date", "vendor_id", "project_id", "delivery_by", "total", "status"])
    if key == "vendor_performance":
        vendors = (await ENG.list_records("vendors", user, {"size": "1000"}))["items"]
        rows = []
        for v in vendors:
            pos = await db.purchase_orders.find({"vendor_id": v["id"], "deleted": {"$ne": True}, "status": {"$in": ["sent", "partly_received", "received", "closed"]}}, {"_id": 0}).to_list(1000)
            grns = await db.grns.find({"vendor_id": v["id"], "status": "posted", "deleted": {"$ne": True}}, {"_id": 0}).to_list(2000)
            on_time = sum(1 for g in grns if any(po.get("delivery_by") and g["date"] <= po["delivery_by"] for po in pos if po["id"] == g.get("po_id")))
            rec = sum(float(ln.get("received_qty") or 0) for g in grns for ln in g.get("lines") or [])
            rej = sum(float(ln.get("rejected_qty") or 0) for g in grns for ln in g.get("lines") or [])
            if pos:
                rows.append([v["name"], len(pos), round(sum(float(x.get("total") or 0) for x in pos), 2), f"{round(on_time / len(grns) * 100) if grns else 0}%", f"{round(rej / rec * 100, 1) if rec else 0}%"])
        return ["Vendor", "POs", "Value", "On-time deliveries", "Rejection rate"], rows
    if key == "stock":
        from routes_ops import stock
        s = await stock(user)
        return ["Item", "Store", "Qty", "Unit", "Avg rate", "Value", "Below reorder"], [[r["item"], r["store"], r["qty"], r["unit"], r.get("avg_rate", ""), r.get("value", ""), "Yes" if r["below_reorder"] else ""] for r in s["rows"]]
    if key == "drums":
        return await ent_rows("cable_drums", user, {}, ["drum_no", "item_id", "size", "initial_length", "remaining_length", "store_id", "project_id", "status"])
    if key == "sales_register":
        return await ent_rows("invoices", user, {**p, "status": "issued,part_paid,paid"}, ["code", "date", "account_id", "subtotal", "cgst", "sgst", "igst", "total", "balance"])
    if key == "purchase_register":
        return await ent_rows("vendor_bills", user, {**p, "date_field": "bill_date"}, ["code", "bill_no", "bill_date", "vendor_id", "subtotal", "gst", "tds", "total", "match_status"])
    if key == "receivables":
        r = await receivables(user)
        return ["Client", "Not due", "0–30", "31–60", "61–90", "90+", "Total"], [[x["client"], x["not_due"], x["0–30"], x["31–60"], x["61–90"], x["90+"], x["total"]] for x in r["rows"]]
    if key == "expenses":
        return await ent_rows("expenses", user, p, ["code", "date", "category", "project_id", "employee_id", "amount", "status"])
    if key == "sla":
        tk = (await ENG.list_records("tickets", user, {**p, "date_field": "created_at", "size": "5000"}))["items"]
        by = {}
        for x in tk:
            b = by.setdefault(x.get("priority") or "normal", [0, 0])
            b[0] += 1
            b[1] += 0 if x.get("sla_breached") else 1
        return ["Priority", "Requests", "Within target", "Compliance %"], [[label_of("ticket_priority", k), v[0], v[1], round(v[1] / v[0] * 100) if v[0] else 0] for k, v in by.items()]
    if key == "amc_renewals":
        return await ent_rows("amc_contracts", user, {"status": "active"}, ["code", "title", "account_id", "price", "start", "end", "status"])
    if key == "incidents":
        return await ent_rows("incidents", user, {**p, "date_field": "occurred_at"}, ["code", "occurred_at", "kind", "project_id", "lost_days", "status"])
    if key == "permit_register":
        return await ent_rows("permits", user, {**p, "date_field": "valid_from"}, ["code", "project_id", "ptype", "location", "valid_from", "valid_to", "status"])
    if key == "attendance":
        return await ent_rows("attendance", user, p, ["date", "employee_id", "check_in", "check_out", "hours", "flag"])
    if key == "expiry":
        from routes_ops import expiries
        ex = await expiries(user, 120)
        return ["What", "Date", "Days left"], [[x["what"], x["date"], x["days_left"]] for x in ex]
    raise HTTPException(404, "Unknown report")


@router.get("/reports/{key}")
async def report(key: str, user=Depends(staff_user), frm: str = "", to: str = "", fmt: str = "json", branch: str = ""):
    r = RMAP.get(key)
    if not r or not can(user, r["module"], "r"):
        raise HTTPException(403, "Not available")
    if branch and branch != "all":
        REQ_BRANCH.set(branch)
    heads, rows = await run_report(key, user, frm, to)
    if fmt == "json":
        return {"title": r["title"], "columns": heads, "rows": rows}
    if not (can(user, "reports", "e") or can(user, r["module"], "e")):
        raise HTTPException(403, "You don't have permission to download reports")
    await audit(user, "report", key, None, {"format": fmt})
    name = f"{key}-{today_ist().isoformat()}"
    if fmt == "csv":
        import csv
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(heads)
        w.writerows(rows)
        return Response(buf.getvalue().encode("utf-8-sig"), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{name}.csv"'})
    if fmt == "xlsx":
        return Response(xlsx(heads, [[x if not isinstance(x, float) else round(x, 2) for x in row] for row in rows], r["title"]),
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{name}.xlsx"'})
    s = await get_settings()
    L = Letterhead(r["title"], s, subtitle=f"{frm or ''} {('to ' + to) if to else ''}, {len(rows)} rows, {user['name']}", landscape_mode=len(heads) > 6)
    L.table(heads, [[ind(x, 2) if isinstance(x, float) else ("" if x is None else x) for x in row] for row in rows],
            align=["R" if rows and isinstance(rows[0][i], (int, float)) else "L" for i in range(len(heads))])
    return Response(L.build(), media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{name}.pdf"'})
