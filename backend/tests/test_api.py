"""Sign-in, permissions, data scope, approvals, numbering, money, the public website intake and the audit chain."""
import re


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["ok"]


def test_login_rules(client):
    assert client.post("/auth/login", {"email": "director@demo.sellandiammanpowerinfra.test", "password": "wrong"}).status_code == 401
    # staff can't use the customer login and customers can't use the staff one
    assert client.post("/auth/login", {"email": "director@demo.sellandiammanpowerinfra.test", "password": "Demo@12345", "portal": True}).status_code == 403
    assert client.post("/auth/login", {"email": "client@demo.sellandiammanpowerinfra.test", "password": "Demo@12345", "portal": False}).status_code == 403
    u = client.login("director")
    assert u["role"] == "director"
    assert client.get("/auth/me").json()["user"]["id"] == u["id"]
    client.post("/auth/logout")
    assert client.get("/auth/me").status_code == 401


def test_every_role_dashboard(as_role):
    for local in ("director", "manager.erode", "sales", "estimation", "tenders", "pm", "site", "liaison", "qaqc", "safety", "purchase", "store",
                  "accounts", "hr", "service", "technician", "marketing", "auditor", "employee"):
        c = as_role(local)
        assert c.get("/dashboard").status_code == 200, local
        assert c.get("/meta").status_code == 200, local


def test_portals_see_only_their_records(as_role, db, run):
    c = as_role("client", portal=True)
    me = c.get("/auth/me").json()["user"]
    projects = c.get("/e/projects").json()["items"]
    assert projects and all(p["account_id"] == me["account_id"] for p in projects)
    invoices = c.get("/e/invoices").json()["items"]
    assert all(i["account_id"] == me["account_id"] and i["status"] in ("issued", "part_paid", "paid") for i in invoices)
    assert c.get("/e/leads").status_code == 403
    assert c.get("/e/purchase_orders").status_code == 403
    other = run(db.projects.find_one({"account_id": {"$ne": me["account_id"]}}, {"_id": 0}))
    assert c.get(f"/e/projects/{other['id']}").status_code == 404
    # query parameters can't widen the scope
    assert all(p["account_id"] == me["account_id"] for p in c.get("/e/projects", params={"account_id": other["account_id"]}).json()["items"])
    v = as_role("vendor", portal=True)
    vid = v.get("/auth/me").json()["user"]["vendor_id"]
    assert all(po["vendor_id"] == vid for po in v.get("/e/purchase_orders").json()["items"])


def test_hidden_cost_fields(as_role):
    director = as_role("director").get("/e/projects").json()["items"][0]
    site = as_role("site").get("/e/projects").json()["items"]
    assert "budget_total" in director or director.get("budget") is not None
    assert all("budget_total" not in p and "budget" not in p for p in site)


def test_numbering_format(as_role):
    c = as_role("director")
    inv = c.get("/e/invoices").json()["items"][0]
    assert re.fullmatch(r"SPI/(PDR|ERD|CBE|HO)/INV/\d{2}-\d{2}/\d{4}", inv["code"]), inv["code"]
    lead = c.get("/e/leads").json()["items"][0]
    assert re.fullmatch(r"LEAD-\d{4}-\d{4}", lead["code"])


def test_invoice_gst_and_rounding(as_role):
    c = as_role("accounts")
    acc = c.get("/e/accounts").json()["items"][0]
    r = c.post("/e/invoices", {"account_id": acc["id"], "date": "2026-10-24", "lines": [{"description": "Test line", "qty": 3, "rate": 333.33, "gst_rate": "18"}]})
    assert r.status_code == 200, r.text
    inv = r.json()
    assert inv["subtotal"] == 999.99
    assert inv["gst"] == 180.0  # 999.99 × 18% = 179.998 → 180.00
    assert inv["cgst"] + inv["sgst"] == inv["gst"]
    assert inv["total"] == round(inv["subtotal"] + inv["gst"], 2)


def test_approval_needs_someone_else(as_role):
    purchase = as_role("purchase")
    vendor = purchase.get("/e/vendors").json()["items"][0]
    item = purchase.get("/e/items").json()["items"][0]
    po = purchase.post("/e/purchase_orders", {"vendor_id": vendor["id"], "date": "2026-10-24", "lines": [{"item_id": item["id"], "qty": 10, "rate": 50000, "gst_rate": "18"}]}).json()
    sent = purchase.post(f"/e/purchase_orders/{po['id']}/action/submit", {}).json()
    assert sent["status"] == "pending_approval"
    # the requester can't decide; the director can
    inbox = purchase.get("/approvals/inbox").json()
    assert all(a["doc_id"] != po["id"] for a in inbox["to_decide"])
    boss = as_role("director")
    appr = next(a for a in boss.get("/approvals/inbox").json()["to_decide"] if a["doc_id"] == po["id"])
    assert boss.post(f"/approvals/{appr['id']}/decide", {"decision": "reject"}).status_code == 422  # reason needed
    assert boss.post(f"/approvals/{appr['id']}/decide", {"decision": "approve"}).status_code == 200
    assert boss.get(f"/e/purchase_orders/{po['id']}").json()["status"] == "approved"


def test_public_lead_intake_and_dedupe(client, as_role):
    body = {"form": "quote_wizard", "name": "Test Customer", "phone": "9876501234", "town": "Erode", "service": "ht_substation", "supply": "HT", "load_kva": 800, "consent": True}
    r = client.post("/public/leads", body)
    assert r.status_code == 200 and r.json()["reference"].startswith("LEAD-")
    again = client.post("/public/leads", {**body, "message": "Following up"}).json()
    assert again["merged"] is True and again["reference"] == r.json()["reference"]
    assert client.post("/public/leads", {**body, "consent": False}).status_code == 422
    assert "lead_id" not in r.json()  # the website never learns internal ids
    lead = as_role("director").get("/e/leads", params={"q": r.json()["reference"]}).json()["items"][0]
    assert lead["owner_id"] and lead["response_due_at"] and lead["score"] > 0


def test_calculator_lead_gives_pdf(client):
    r = client.post("/public/calc/pf-correction/lead", {"name": "Calc User", "phone": "9876505678", "consent": True, "inputs": {"kw": 100, "pf_now": 0.7, "pf_target": 0.95}})
    assert r.status_code == 200
    pdf = client.get(r.json()["pdf"].replace("/api", "", 1))
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_records_pdf(as_role, db, run):
    c = as_role("director")
    inv = run(db.invoices.find_one({"status": "issued"}, {"_id": 0}))
    r = c.get(f"/e/invoices/{inv['id']}/pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    assert c.get("/ceo/report.pdf").content[:4] == b"%PDF"


def test_client_approval_with_otp(as_role, db, run):
    c = as_role("client", portal=True)
    s = c.get("/portal/summary").json()
    drawing = next(a for a in s["approvals"] if a["entity"] == "drawings")
    assert c.post(f"/portal/approve/drawings/{drawing['id']}", {"decision": "approve", "otp": "000000"}).status_code == 422
    assert c.post(f"/portal/approve/drawings/{drawing['id']}", {"decision": "reject", "otp": "123456"}).status_code == 422  # comments needed
    r = c.post(f"/portal/approve/drawings/{drawing['id']}", {"decision": "approve_with_comments", "comment": "Move the meter cubicle 1 m left", "otp": "123456"})
    assert r.status_code == 200 and r.json()["status"] == "approved_with_comments"


def test_audit_chain_intact(as_role):
    c = as_role("director")
    v = c.get("/audit/verify").json()
    assert v["ok"] is True and v["entries"] > 100


def test_ceo_view(as_role):
    j = as_role("director").get("/ceo").json()
    assert 0 <= j["score"] <= 100 and len(j["pillars"]) == 7
    assert sum(p["weight"] for p in j["pillars"]) == 100
    assert as_role("sales").get("/ceo").status_code == 403


def test_reports_all_run(as_role):
    c = as_role("director")
    for rep in c.get("/reports").json():
        r = c.get(f"/reports/{rep['key']}")
        assert r.status_code == 200, rep["key"]
        assert "columns" in r.json()
