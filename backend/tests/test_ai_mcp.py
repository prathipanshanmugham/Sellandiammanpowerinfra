"""AI agents and the MCP endpoint: keys, access levels, the person's permissions, things agents may never do, the log."""
import json

import pytest

from conftest import DOMAIN


def rpc(client, key, method, params=None, mid=1, how="bearer"):
    body = {"jsonrpc": "2.0", "method": method, **({"params": params} if params is not None else {}), **({"id": mid} if mid is not None else {})}
    headers, path = {}, "/mcp"
    if how == "bearer":
        headers["Authorization"] = f"Bearer {key}"
    elif how == "header":
        headers["X-API-Key"] = key
    else:
        path = f"/mcp?key={key}"
    return client.post(path, body, headers=headers)


def call(client, key, tool, args=None):
    r = rpc(client, key, "tools/call", {"name": tool, "arguments": args or {}})
    assert r.status_code == 200, r.text
    res = r.json()
    assert "result" in res, res
    out = res["result"]
    text = out["content"][0]["text"]
    return out["isError"], (text if out["isError"] else json.loads(text))


@pytest.fixture()
def boss(as_role):
    return as_role("director")


def user_id(boss, local):
    return next(u["id"] for u in boss.get("/users").json() if u["email"] == f"{local}@{DOMAIN}")


def make_agent(boss, local, access="read", name="Test agent", purpose="Testing"):
    r = boss.post("/ai/agents", {"name": name, "purpose": purpose, "access": access, "user_id": user_id(boss, local)})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["key"].startswith("spi_") and d["url_with_key"].endswith(d["key"])
    assert "key_hash" not in d["agent"] and d["agent"]["status"] == "active"
    return d


def test_only_owners_manage_agents(as_role, boss):
    sales = as_role("sales")
    assert sales.get("/ai/agents").status_code == 403
    assert sales.post("/ai/agents", {"name": "x", "access": "read"}).status_code == 403
    # a director can't hand an agent super-admin powers
    r = boss.post("/ai/agents", {"name": "x", "access": "read", "user_id": user_id(boss, "admin")})
    assert r.status_code == 403
    # nor work as a customer login
    r = boss.post("/ai/agents", {"name": "x", "access": "read", "user_id": user_id(boss, "client")})
    assert r.status_code == 422
    info = boss.get("/ai/info").json()
    assert info["mcp_url"].endswith("/api/mcp") and len(info["templates"]) >= 5 and any(t["name"] == "run_report" for t in info["tools"])


def test_handshake_and_tool_list(client, boss):
    a = make_agent(boss, "sales", "read", name="Sales reader")
    r = rpc(client, a["key"], "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "pytest", "version": "1"}})
    res = r.json()["result"]
    assert res["protocolVersion"] == "2025-06-18" and res["serverInfo"]["name"] == "sellandiamman-power-infra"
    assert "Sales reader" in res["instructions"] and "read only" in res["instructions"]
    assert rpc(client, a["key"], "initialize", {"protocolVersion": "1999-01-01"}).json()["result"]["protocolVersion"] == "2025-06-18"
    # notifications get 202 and no body
    r = rpc(client, a["key"], "notifications/initialized", mid=None)
    assert r.status_code == 202 and not r.content
    tools = {t["name"]: t for t in rpc(client, a["key"], "tools/list").json()["result"]["tools"]}
    assert "create_record" not in tools and "update_record" not in tools and "run_action" not in tools
    assert tools["call_api"]["inputSchema"]["properties"]["method"]["enum"] == ["GET"]
    assert tools["list_records"]["annotations"]["readOnlyHint"] is True
    prompts = rpc(client, a["key"], "prompts/list").json()["result"]["prompts"]
    assert {"daily_brief", "lead_followups"} <= {p["name"] for p in prompts}
    assert rpc(client, a["key"], "prompts/get", {"name": "daily_brief"}).json()["result"]["messages"][0]["role"] == "user"
    assert rpc(client, a["key"], "no/such").json()["error"]["code"] == -32601
    # batch
    r = client.post("/mcp", [{"jsonrpc": "2.0", "id": 1, "method": "ping"}, {"jsonrpc": "2.0", "method": "notifications/x"}],
                    headers={"Authorization": f"Bearer {a['key']}"})
    assert r.status_code == 200 and len(r.json()) == 1
    # the key can also come as a header or in the address
    assert rpc(client, a["key"], "ping", how="header").status_code == 200
    assert rpc(client, a["key"], "ping", how="query").status_code == 200
    assert rpc(client, "spi_wrong", "ping").status_code == 401
    assert client.get("/mcp").status_code == 405


def test_agent_sees_what_the_person_sees(client, boss):
    a = make_agent(boss, "sales", "read")
    err, me = call(client, a["key"], "whoami")
    assert not err and me["works_as"]["role"] == "Sales / BD" and me["access"] == "read only"
    err, leads = call(client, a["key"], "list_records", {"type": "leads", "page_size": 100, "fields": ["owner_id", "name"]})
    assert not err and leads["total"] > 0
    sid = user_id(boss, "sales")
    assert all(x.get("owner_id") == sid for x in leads["items"])  # a sales person sees only their own leads
    # cost prices stay hidden from sales
    err, items = call(client, a["key"], "list_records", {"type": "items", "page_size": 5})
    assert not err and all("cost_rate" not in x for x in items["items"])
    err, types = call(client, a["key"], "list_record_types")
    flat = {t["type"] for g in types["groups"] for t in g["types"]}
    assert "leads" in flat and "payroll_runs" not in flat
    err, d = call(client, a["key"], "describe_record_type", {"type": "leads"})
    assert not err and any(f["key"] == "stage" for f in d["fields"]) and d["status_field"] == "stage"
    # finance isn't part of the sales role
    err, msg = call(client, a["key"], "call_api", {"path": "/api/finance/receivables"})
    assert err and "403" in msg
    err, res = call(client, a["key"], "search", {"query": leads["items"][0]["name"][:4]})
    assert not err


def test_read_only_agent_cannot_write(client, boss):
    a = make_agent(boss, "director", "read")
    r = rpc(client, a["key"], "tools/call", {"name": "create_record", "arguments": {"type": "leads", "data": {"name": "X"}}})
    assert r.json()["error"]["code"] == -32602
    err, msg = call(client, a["key"], "call_api", {"method": "POST", "path": "/api/e/tasks", "body": {"title": "x"}})
    assert err and "read-only" in msg


def test_write_agent_works_through_the_rules(client, boss, db, run):
    a = make_agent(boss, "sales", "write", name="Sales helper")
    err, out = call(client, a["key"], "create_record", {"type": "leads", "data": {"name": "Agent Lead", "phone": "9876501234", "company": "MCP Mills",
                                                                                    "service": "ht_substation", "consent": True}})
    assert not err, out
    code = out["created"]["code"]
    assert code.startswith("LEAD-")
    err, rec = call(client, a["key"], "get_record", {"type": "leads", "id": code, "include_history": True})
    assert not err and rec["record"]["company"] == "MCP Mills"
    err, upd = call(client, a["key"], "update_record", {"type": "leads", "id": code, "changes": {"designation": "Plant head"}})
    assert not err and upd["record"]["designation"] == "Plant head"
    entry = run(db.audit_logs.find_one({"entity": "leads", "entity_id": rec["record"]["id"], "action": "create"}, {"_id": 0}))
    assert entry["agent_name"] == "Sales helper" and "(AI agent: Sales helper)" in entry["user_name"]
    # never delete, even with a role that may
    err, msg = call(client, a["key"], "call_api", {"method": "DELETE", "path": f"/api/e/leads/{rec['record']['id']}"})
    assert err
    lead = run(db.leads.find_one({"id": rec["record"]["id"]}))
    assert lead and not lead.get("deleted")


def test_agents_never_decide_approvals_or_reach_private_areas(client, boss, db, run):
    a = make_agent(boss, "director", "write")
    appr = run(db.approvals.find_one({"status": "pending"}, {"_id": 0}))
    err, msg = call(client, a["key"], "call_api", {"method": "POST", "path": f"/api/approvals/{appr['id']}/decide", "body": {"decision": "approve"}})
    assert err and "approvals" in msg
    for path in ("/api/vault/items", "/api/ai/agents", "/api/users", "/api/auth/me"):
        err, msg = call(client, a["key"], "call_api", {"path": path})
        assert err, path
    err, msg = call(client, a["key"], "call_api", {"method": "PUT", "path": "/api/settings", "body": {}})
    assert err
    # but reading the CEO view, finance and reports is fine for a director
    err, ceo = call(client, a["key"], "call_api", {"path": "/api/ceo"})
    assert not err and "score" in json.dumps(ceo)
    err, reps = call(client, a["key"], "list_reports")
    assert not err and reps["reports"]
    err, rep = call(client, a["key"], "run_report", {"report": reps["reports"][0]["report"], "max_rows": 5})
    assert not err and "columns" in rep and len(rep["rows"]) <= 5
    err, eps = call(client, a["key"], "list_endpoints", {"filter": "finance"})
    assert not err and any(e["path"] == "/api/finance/receivables" for e in eps["endpoints"])
    assert not any(e["path"].startswith("/api/vault") for e in eps["endpoints"])
    err, ov = call(client, a["key"], "overview")
    assert not err and "dashboard" in ov


def test_pause_rotate_revoke_and_log(client, boss):
    a = make_agent(boss, "sales", "read")
    aid, key = a["agent"]["id"], a["key"]
    assert rpc(client, key, "ping").status_code == 200
    assert boss.patch(f"/ai/agents/{aid}", {"active": False}).json()["status"] == "paused"
    r = rpc(client, key, "ping")
    assert r.status_code == 403 and "paused" in r.json()["error"]["message"]
    boss.patch(f"/ai/agents/{aid}", {"active": True})
    new = boss.post(f"/ai/agents/{aid}/rotate").json()
    assert rpc(client, key, "ping").status_code == 401
    assert rpc(client, new["key"], "ping").status_code == 200
    call(client, new["key"], "whoami")
    log = boss.get("/ai/calls", params={"agent_id": aid}).json()
    assert log["total"] >= 1 and log["items"][0]["tool"] == "whoami"
    agents = {x["id"]: x for x in boss.get("/ai/agents").json()}
    assert agents[aid]["calls_total"] >= 2 and agents[aid]["last_used_at"]
    assert boss.post(f"/ai/agents/{aid}/revoke").json()["status"] == "revoked"
    assert rpc(client, new["key"], "ping").status_code == 403
    assert boss.post(f"/ai/agents/{aid}/rotate").status_code == 409
    # the agent's own token can't be replayed once the key changes
    assert boss.patch(f"/ai/agents/{aid}", {"active": True}).status_code == 409


def test_agent_token_is_short_lived_and_scoped(client, boss, db, run):
    from core import make_agent_token
    a = make_agent(boss, "sales", "read")
    agent = run(db.ai_agents.find_one({"id": a["agent"]["id"]}, {"_id": 0}))
    tok = make_agent_token(agent)
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get("/e/leads", headers=h).status_code == 200
    assert client.post("/e/tasks", {"title": "x"}, headers=h).status_code == 403  # read-only
    assert client.get("/vault/items", headers=h).status_code in (401, 403)
    boss.post(f"/ai/agents/{a['agent']['id']}/rotate")
    assert client.get("/e/leads", headers=h).status_code == 401  # old key version
