"""Build the data for the hosted preview.

Runs the real backend in memory (mongomock) with the sample data, then saves:
  data/db.json        every record the generic screens need (the preview's in-browser store)
  data/meta.json      /api/meta, /api/auth/me and per-role screens (dashboard, portal summary, inbox…)
  data/shared.json    computed screens recorded once as the director (project hub, finance, reports…)
  data/public.json    every public-website response
  pdf/*.pdf           a few real PDFs (invoice, proposal, test report, CEO report…) for the PDF buttons

Usage (from the repo root):  python demo/export.py  [out_dir]
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "demo" / "build"
FIXED = os.environ.get("FIXED_TODAY", "2026-10-24")
os.environ.update({"MONGO_URL": "mongomock://demo", "DB_NAME": "demo", "JWT_SECRET": "preview-" + "x" * 40, "DISABLE_AUTOMATIONS": "true",
                   "COOKIE_SECURE": "false", "ARGON2_TIME": "1", "ARGON2_MEMORY": "8192", "DISABLE_RATE_LIMIT": "true", "SEED_DEMO": "true",
                   "DEMO_OTP_ANY": "true", "FIXED_TODAY": FIXED, "VAULT_KEY": os.environ.get("VAULT_KEY", "00" * 32),
                   "UPLOAD_DIR": str(OUT / "_uploads")})
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")

import httpx  # noqa: E402
import server  # noqa: E402
from core import db  # noqa: E402
from registry import E  # noqa: E402
from roles import ROLES, PORTAL_ROLES  # noqa: E402

DOMAIN = "demo.sellandiammanpowerinfra.test"
PW = "Demo@12345"
LOGINS = {  # role -> demo login (local part)
    "super_admin": "admin", "director": "director", "branch_manager": "manager.erode", "sales": "sales", "estimator": "estimation",
    "tender_exec": "tenders", "project_manager": "pm", "site_engineer": "site", "liaison": "liaison", "qaqc": "qaqc", "safety": "safety",
    "purchase": "purchase", "store": "store", "accounts": "accounts", "hr": "hr", "service_manager": "service", "technician": "technician",
    "marketing": "marketing", "auditor": "auditor", "employee": "employee",
    "client": "client", "consultant": "consultant", "vendor": "vendor", "subcontractor": "subcontractor", "partner": "partner",
}
SKIP_COLLECTIONS = {"sessions", "calc_runs", "rate", "counters"}


def clean(doc):
    doc = {k: v for k, v in doc.items() if k != "_id"}
    for k in ("password_hash", "mfa_secret", "mfa_pending_secret", "mfa_recovery"):
        doc.pop(k, None)
    return json.loads(json.dumps(doc, default=str))


async def main():
    t0 = time.time()
    await server.startup()
    print(f"seeded in {time.time() - t0:.1f}s")
    (OUT / "data").mkdir(parents=True, exist_ok=True)
    (OUT / "pdf").mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ raw store
    store = {}
    for name in sorted(await db.list_collection_names()):
        if name in SKIP_COLLECTIONS:
            continue
        rows = [clean(r) async for r in db[name].find({})]
        if rows:
            store[name] = rows
    for f in store.get("files", []):
        f.pop("path", None)

    t = httpx.ASGITransport(app=server.app)
    meta, shared, public, pdfs = {}, {}, {}, {}
    async with httpx.AsyncClient(transport=t, base_url="http://preview.local", timeout=120) as c:
        async def get(path, params=None):
            r = await c.get("/api" + path, params=params)
            if r.status_code != 200:
                return None
            return r.json()

        async def pdf(name, path):
            r = await c.get("/api" + path)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/pdf"):
                (OUT / "pdf" / f"{name}.pdf").write_bytes(r.content)
                pdfs[name] = len(r.content)

        # ---------------------------------------------------------- public website
        for p in ["/public/site", "/public/products", "/public/industries", "/public/projects", "/public/clients", "/public/gallery",
                  "/public/insights", "/public/faqs", "/public/downloads", "/public/jobs", "/public/towns", "/public/amc-plans",
                  "/public/survey-slots", "/public/calc/constants"]:
            public[p] = await get(p)
        for s in public["/public/site"]["services"]:
            public[f"/public/services/{s['slug']}"] = await get(f"/public/services/{s['slug']}")
        for s in public["/public/industries"]:
            public[f"/public/industries/{s['slug']}"] = await get(f"/public/industries/{s['slug']}")
        for p in public["/public/projects"]["items"]:
            public[f"/public/projects/{p['slug']}"] = await get(f"/public/projects/{p['slug']}")
        for p in public["/public/insights"]:
            public[f"/public/insights/{p['slug']}"] = await get(f"/public/insights/{p['slug']}")
        for d in public["/public/downloads"]:
            if d.get("slug"):
                public[f"/public/guides/{d['slug']}"] = await get(f"/public/guides/{d['slug']}")
        for tw in public["/public/towns"]:
            r = await get(f"/public/towns/{tw['slug']}")
            if r:
                public[f"/public/towns/{tw['slug']}"] = r
        for a in store.get("installed_assets", [])[:40]:
            if a.get("qr_token"):
                public[f"/public/asset/{a['qr_token']}"] = await get(f"/public/asset/{a['qr_token']}")
        r = await c.post("/api/public/calc/connected-load/lead", json={"name": "Preview", "phone": "9876543210", "consent": True, "inputs": {}})
        if r.status_code == 200:
            await pdf("calc-report", r.json()["pdf"].replace("/api", "", 1))

        # ---------------------------------------------------------- per role
        for role, local in LOGINS.items():
            portal = role in PORTAL_ROLES
            r = await c.post("/api/auth/login", json={"email": f"{local}@{DOMAIN}", "password": PW, "portal": portal})
            if r.status_code != 200:
                print("login failed", role, r.status_code, r.text[:200])
                continue
            m = {"user": r.json()["user"], "meta": await get("/meta"), "screens": {}}
            paths = ["/notifications", "/approvals/inbox"]
            paths += ["/portal/summary"] if portal else ["/dashboard", "/hr/me", "/service/my-jobs"]
            for p in paths:
                v = await get(p)
                if v is not None:
                    m["screens"][p] = v
            meta[role] = m

            if role == "director":
                await record_shared(get, shared, store)
                await record_pdfs(pdf, store)
            await c.post("/api/auth/logout")

    # ------------------------------------------------------------------ write
    def dump(name, obj):
        p = OUT / "data" / f"{name}.json"
        p.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str))
        return p.stat().st_size

    # the registry once (as the super admin sees it); each role keeps only what differs: its permission letters and hidden fields
    reg = meta["super_admin"]["meta"]
    compact = {}
    for role, m in meta.items():
        ents = {}
        for k, e in m["meta"]["entities"].items():
            full = reg["entities"][k]
            have = {f["k"]: f for f in e["fields"]}
            d = {"perm": e["perm"], "drop": [f["k"] for f in full["fields"] if f["k"] not in have]}
            lines = {}
            for f in full["fields"]:
                if f["t"] == "lines" and f["k"] in have:
                    sub = {x["k"] for x in have[f["k"]]["fields"]}
                    miss = [x["k"] for x in f["fields"] if x["k"] not in sub]
                    if miss:
                        lines[f["k"]] = miss
            if lines:
                d["dropLines"] = lines
            ents[k] = d
        compact[role] = {"user": m["user"], "ents": ents, "screens": m["screens"]}
    sizes = {"db": dump("db", store), "meta": dump("meta", {"roles": ROLES, "portal_roles": list(PORTAL_ROLES), "fixed_today": FIXED,
                                                            "logins": {k: f"{v}@{DOMAIN}" for k, v in LOGINS.items()},
                                                            "registry": reg, "by_role": compact}),
             "shared": dump("shared", shared), "public": dump("public", public)}
    print("sizes KB", {k: round(v / 1024) for k, v in sizes.items()}, "pdfs", len(pdfs))
    print(f"done in {time.time() - t0:.1f}s")


async def record_shared(get, shared, store):
    """Computed screens: recorded as the director, then served to whoever may open them."""
    fixed = ["/ceo", "/crm/pipeline", "/crm/marketing", "/crm/routing", "/crm/duplicates", "/stores/stock", "/stores/in-transit",
             "/service/renewals", "/finance/balances", "/finance/receivables", "/finance/payables", "/finance/gst", "/finance/tds",
             "/finance/pnl", "/finance/cashflow", "/calendar/expiries", "/reports", "/settings", "/cms/site", "/cms/versions",
             "/settings/calc-constants", "/branches/all", "/roles", "/users", "/users/lookup", "/audit", "/audit/verify",
             "/vault/status", "/vault/meta", "/auth/sessions", "/finance/credit-report"]
    for p in fixed:
        v = await get(p)
        if v is not None:
            shared[p] = v
    reps = shared.get("/reports") or []
    for rep in (reps if isinstance(reps, list) else reps.get("reports", [])):
        v = await get(f"/reports/{rep['key']}")
        if v is not None:
            shared[f"/reports/{rep['key']}"] = v
    for p in store.get("projects", []):
        if p.get("deleted"):
            continue
        for sub in ("hub", "gantt", "materials"):
            v = await get(f"/projects/{p['id']}/{sub}")
            if v is not None:
                shared[f"/projects/{p['id']}/{sub}"] = v
    for r in store.get("rfqs", []):
        v = await get(f"/rfqs/{r['id']}/comparison")
        if v is not None:
            shared[f"/rfqs/{r['id']}/comparison"] = v
    for lead in store.get("leads", []):
        v = await get(f"/crm/leads/{lead['id']}/timeline")
        if v is not None:
            shared[f"/crm/leads/{lead['id']}/timeline"] = v
    for inv in store.get("invoices", []):
        if inv.get("status") in ("issued", "part_paid"):
            v = await get(f"/finance/upi/{inv['id']}")
            if v is not None:
                shared[f"/finance/upi/{inv['id']}"] = v
    for p in store.get("partners", []):
        v = await get(f"/crm/partners/{p['id']}/statement")
        if v is not None:
            shared[f"/crm/partners/{p['id']}/statement"] = v


async def record_pdfs(pdf, store):
    def first(coll, **q):
        for r in store.get(coll, []):
            if all(r.get(k) == v for k, v in q.items()):
                return r
        return None
    picks = [("invoice", "invoices", {"status": "issued"}), ("proposal", "proposals", {}), ("test_report", "test_reports", {}),
             ("permit", "permits", {}), ("purchase_order", "purchase_orders", {}), ("ra_bill", "ra_bills", {}), ("boq", "boqs", {}),
             ("work_order", "work_orders", {}), ("payslip", "payslips", {}), ("generic", "dprs", {})]
    for name, coll, q in picks:
        r = first(coll, **q) or first(coll)
        if r:
            await pdf(name, f"/e/{coll}/{r['id']}/pdf")
    await pdf("ceo-report", "/ceo/report.pdf")
    await pdf("credit-report", "/finance/credit-report")
    p = first("projects", status="handed_over") or first("projects")
    if p:
        await pdf("handover-pack", f"/projects/{p['id']}/handover-pack.pdf")
    await pdf("report", "/reports/project_status?fmt=pdf")
    await pdf("export", "/e/leads/export/pdf")


if __name__ == "__main__":
    asyncio.run(main())
