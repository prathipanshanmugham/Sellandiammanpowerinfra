"""Background jobs (run in the backend process every 15 minutes; each job keeps its own last-run marker).

  * service requests past their reply-by / fix-by targets are flagged and the service manager is told
  * leads not answered within the first-response target are escalated to the branch manager
  * follow-up reminders; on-hold leads come back on their date; lost leads are re-engaged after N months
  * AMC renewal reminders at 60 and 30 days; expired AMCs, proposals and bank guarantees change status
  * expiry reminders (licences, insurance, calibration, permits, BGs...) once a week per item
  * scheduled Insights posts go live; milestones turn 'delayed'; a monthly progress snapshot feeds the S-curve
  * daily site summary (8 pm) and the weekly CEO report (Monday 9 am) to directors
"""
import asyncio
import logging
from datetime import datetime, timedelta

from core import db, now, now_iso, today_ist, notify, notify_roles, get_settings, send_email, IST, new_id

log = logging.getLogger("spi.scheduler")


async def ran_today(job, hour=None):
    t = datetime.now(IST)
    key = f"{job}:{t.date().isoformat()}"
    if hour is not None and t.hour < hour:
        return True
    if await db.jobs.find_one({"_id": key}):
        return True
    await db.jobs.insert_one({"_id": key, "at": now_iso()})
    return False


async def sla_job():
    t = now_iso()
    rows = await db.tickets.find({"status": {"$nin": ["resolved", "closed"]}, "deleted": {"$ne": True}, "sla_breached": {"$ne": True},
                                  "$or": [{"restore_by": {"$lt": t}}, {"respond_by": {"$lt": t}, "first_response_at": None}]}, {"_id": 0}).to_list(500)
    for r in rows:
        await db.tickets.update_one({"id": r["id"]}, {"$set": {"sla_breached": True}})
        await notify_roles(["service_manager"], f"Past target: {r.get('code')} {r.get('title')}", f"Fix-by was {str(r.get('restore_by'))[:16].replace('T', ' ')}",
                           f"/erp/e/tickets/{r['id']}", kind="sla", dedupe=f"sla:{r['id']}")


async def lead_jobs():
    t = now_iso()
    late = await db.leads.find({"stage": "new", "first_response_at": None, "escalated": {"$ne": True}, "response_due_at": {"$lt": t}, "deleted": {"$ne": True}}, {"_id": 0}).to_list(500)
    for l in late:
        await db.leads.update_one({"id": l["id"]}, {"$set": {"escalated": True}})
        await notify_roles(["branch_manager"], f"Lead not answered: {l['name']} ({l.get('code')})", "First-response target missed", f"/erp/e/leads/{l['id']}",
                           kind="alert", branch_id=l.get("branch_id"), dedupe=f"esc:{l['id']}")
    soon = (now() + timedelta(hours=1)).astimezone(IST).strftime("%Y-%m-%dT%H:%M")
    for l in await db.leads.find({"next_follow_up": {"$lte": soon}, "stage": {"$nin": ["won", "lost"]}, "deleted": {"$ne": True}}, {"_id": 0}).to_list(1000):
        if l.get("owner_id"):
            await notify([l["owner_id"]], f"Follow up: {l['name']}", l.get("company") or "", f"/erp/e/leads/{l['id']}", kind="assigned", dedupe=f"fu:{l['id']}:{l['next_follow_up']}")
    today = today_ist().isoformat()
    for l in await db.leads.find({"stage": "on_hold", "hold_until": {"$lte": today}, "deleted": {"$ne": True}}, {"_id": 0}).to_list(500):
        await db.leads.update_one({"id": l["id"]}, {"$set": {"stage": "contacted", "next_follow_up": f"{today}T10:00"}})
        await db.tasks.insert_one({"id": new_id(), "title": f"Re-engage {l['name']} (back from hold)", "assigned_to": l.get("owner_id"), "due_on": today, "status": "open",
                                   "priority": "normal", "link": f"/erp/e/leads/{l['id']}", "created_at": now_iso(), "deleted": False})
    s = await get_settings()
    months = int(s.get("re_engage_months") or 6)
    cut = (today_ist() - timedelta(days=30 * months)).isoformat()
    for l in await db.leads.find({"stage": "lost", "lost_reason": {"$nin": ["duplicate", "scope"]}, "updated_at": {"$lte": cut}, "re_engaged": {"$ne": True}, "deleted": {"$ne": True}}, {"_id": 0}).to_list(200):
        await db.leads.update_one({"id": l["id"]}, {"$set": {"re_engaged": True}})
        await db.tasks.insert_one({"id": new_id(), "title": f"Re-engage lost lead {l['name']} ({l.get('lost_reason')})", "assigned_to": l.get("owner_id"), "due_on": today,
                                   "status": "open", "priority": "low", "link": f"/erp/e/leads/{l['id']}", "created_at": now_iso(), "deleted": False})


async def status_jobs():
    today = today_ist().isoformat()
    await db.amc_contracts.update_many({"status": "active", "end": {"$lt": today}}, {"$set": {"status": "expired"}})
    await db.proposals.update_many({"status": "sent", "valid_until": {"$lt": today}}, {"$set": {"status": "expired"}})
    await db.bank_guarantees.update_many({"status": "active", "claim_until": {"$lt": today}}, {"$set": {"status": "expired"}})
    await db.milestones.update_many({"status": {"$in": ["not_started", "in_progress"]}, "planned_end": {"$lt": today}}, {"$set": {"status": "delayed"}})
    nowi = datetime.now(IST).strftime("%Y-%m-%dT%H:%M")
    await db.insights.update_many({"status": "scheduled", "publish_at": {"$lte": nowi}}, {"$set": {"status": "published"}})
    for days in (60, 30):
        lim = (today_ist() + timedelta(days=days)).isoformat()
        flag = f"reminded_{days}"
        for a in await db.amc_contracts.find({"status": "active", "end": {"$lte": lim}, flag: {"$ne": True}, "deleted": {"$ne": True}}, {"_id": 0}).to_list(200):
            await db.amc_contracts.update_one({"id": a["id"]}, {"$set": {flag: True}})
            await notify_roles(["service_manager", "sales"], f"AMC renewal in {days} days: {a['title']}", f"Ends {a['end']}", f"/erp/e/amc_contracts/{a['id']}", kind="alert")
    mk = today_ist().strftime("%Y-%m")
    for p in await db.projects.find({"status": {"$in": ["mobilising", "in_progress", "testing", "on_hold"]}, "deleted": {"$ne": True}}, {"_id": 0, "id": 1, "percent_complete": 1}).to_list(1000):
        await db.project_progress.update_one({"project_id": p["id"], "month": mk}, {"$set": {"percent": p.get("percent_complete") or 0}}, upsert=True)


async def expiry_job():
    if await ran_today("expiry", hour=9):
        return
    from routes_ops import expiries
    admin = await db.users.find_one({"role": "super_admin", "active": True}, {"_id": 0}) or {"id": None, "role": "super_admin", "branch_ids": []}
    rows = await expiries({**admin, "role": "super_admin"}, 30)
    week = today_ist().isocalendar()[1]
    for x in rows:
        await notify_roles(["director", "super_admin"], f"{x['what']}: {'expired' if x['days_left'] < 0 else 'due'} {x['date']}", "", x["link"], kind="alert",
                           dedupe=f"exp:{x['link']}:{x['date']}:{week}")


async def summaries():
    s = await get_settings()
    t = datetime.now(IST)
    hour = int((s.get("daily_summary_hour") or 20))
    if t.hour >= hour and not await ran_today("daily_summary", hour=hour):
        today = t.date().isoformat()
        dprs = await db.dprs.find({"date": today, "deleted": {"$ne": True}}, {"_id": 0}).to_list(500)
        leads = await db.leads.count_documents({"created_at": {"$gte": today}, "deleted": {"$ne": True}})
        body = f"{len(dprs)} daily reports, {sum(int(d.get('manpower_total') or 0) for d in dprs)} people on site, {leads} new leads today."
        await notify_roles(["director"], f"Site summary {today}", body, "/erp/ceo", kind="info", dedupe=f"daily:{today}")
    if t.weekday() == 0 and t.hour >= 9 and not await ran_today("weekly_ceo", hour=9):
        await notify_roles(["director"], "Weekly CEO report is ready", "Open the CEO dashboard or download the PDF.", "/erp/ceo", kind="info")
        for u in await db.users.find({"role": "director", "active": True}, {"_id": 0, "email": 1}).to_list(10):
            await send_email(u.get("email"), "Weekly CEO report", "Your weekly CEO report is ready in the staff workspace (CEO dashboard → Download PDF).")


async def run_once():
    for job in (sla_job, lead_jobs, status_jobs, expiry_job, summaries):
        try:
            await job()
        except Exception:
            log.exception("Job %s failed", job.__name__)


async def loop():
    await asyncio.sleep(20)
    while True:
        await run_once()
        await asyncio.sleep(900)
