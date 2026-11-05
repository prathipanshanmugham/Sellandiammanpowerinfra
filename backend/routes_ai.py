"""AI agents and the MCP endpoint.

Owners create agents in Settings -> AI agents & MCP. Each agent works as one staff login: that person's role, branches
and hidden fields apply, every change it makes is in the activity log as "<person> (AI agent: <agent>)", and on top of
the role it is held to: read-only or read & write, never delete, never decide approvals, never touch logins, keys,
settings or attendance (see core.agent_blocked).

MCP: POST /api/mcp, JSON-RPC 2.0 over Streamable HTTP (plain JSON answers, no session needed). The key goes in
"Authorization: Bearer spi_...", "X-API-Key: spi_..." or "?key=spi_..." (the last one for connectors that only take a
URL; it then shows up in web-server access logs). Keys are stored as SHA-256 hashes and shown once. 240 calls a minute
per agent. Every tool call is kept in ai_agent_calls for 90 days.

Each tool runs as an ordinary API request inside this server, signed with a two-minute token for the agent, so the
same permission checks, business rules, numbering and audit trail apply as when the person clicks in the app.
"""
import hashlib
import json
import os
import random
import re
import secrets
import time
from datetime import timedelta

import httpx
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute

from core import (db, require, audit, now, now_iso, new_id, today_ist, get_settings, SITE_URL, APP_VERSION, client_ip,
                  agent_identity, agent_is_live, agent_blocked, make_agent_token, REQ_BRANCH, logger, AGENT_WRITE)
from roles import ROLES, PORTAL_ROLES

router = APIRouter()

KEY_PREFIX = "spi_"
CALLS_PER_MINUTE = 240
KEEP_CALLS_DAYS = 90
PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
MAX_TEXT = 60000

# Ready-made jobs. The person still chooses which staff login the agent works as; the suggestion follows the job.
TEMPLATES = [
    {"key": "analyst", "name": "Business analyst", "access": "read", "roles": ["director", "super_admin"],
     "purpose": "Answer questions about how the business is doing: order book, revenue, margins, cash, receivables, project delays and risks. "
                "Read only. Say which screen or report each figure comes from and the dates it covers."},
    {"key": "sales", "name": "Sales assistant", "access": "write", "roles": ["sales", "branch_manager"],
     "purpose": "Keep the sales pipeline moving: find leads waiting for a first reply or with an overdue follow-up, log calls and visits as activities, "
                "set the next follow-up date and move leads to the right stage. Never change prices, discounts or proposal values."},
    {"key": "projects", "name": "Project monitor", "access": "read", "roles": ["project_manager", "director"],
     "purpose": "Watch live projects: progress against plan, under-billing, open hindrances, RFIs and snags, TNPDCL and CEIG approvals and milestones due "
                "in the next two weeks. Flag what needs a person, with the project code."},
    {"key": "procurement", "name": "Procurement assistant", "access": "write", "roles": ["purchase"],
     "purpose": "Turn approved material requests into RFQs, compare vendor quotes, chase pending deliveries and keep items below reorder level visible. "
                "Purchase orders still go through approval in the app."},
    {"key": "collections", "name": "Collections assistant", "access": "read", "roles": ["accounts"],
     "purpose": "Track money owed: overdue invoices by client and age, retention due, payables, GST and TDS summaries. Prepare follow-up lists; "
                "don't record receipts or payments."},
    {"key": "service", "name": "Service desk assistant", "access": "write", "roles": ["service_manager"],
     "purpose": "Log breakdown calls as service tickets, check AMC visits due and renewals coming up, and keep ticket notes current. "
                "Make sure every urgent ticket has someone assigned."},
]
TEMPLATE_KEYS = {t["key"] for t in TEMPLATES}


# ------------------------------------------------------------------ keys
def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def new_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(30)


def base_url(request: Request) -> str:
    if SITE_URL:
        return SITE_URL
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme).split(",")[0].strip()
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "localhost").split(",")[0].strip()
    return f"{proto}://{host}"


def status_of(a):
    if a.get("revoked"):
        return "revoked"
    if a.get("expires_on") and a["expires_on"] < today_ist().isoformat():
        return "expired"
    return "active" if a.get("active") else "paused"


async def public_agents(rows):
    ids = list({a["user_id"] for a in rows} | {a.get("created_by") for a in rows if a.get("created_by")})
    users = {u["id"]: u for u in await db.users.find({"id": {"$in": ids}}, {"_id": 0, "id": 1, "name": 1, "role": 1, "active": 1}).to_list(500)}
    out = []
    for a in rows:
        u = users.get(a["user_id"]) or {}
        d = {k: v for k, v in a.items() if k not in ("_id", "key_hash")}
        d.update({"status": status_of(a), "user_name": u.get("name"), "user_role": u.get("role"), "user_role_label": ROLES.get(u.get("role")),
                  "user_active": bool(u.get("active"))})
        out.append(d)
    return out


# ------------------------------------------------------------------ managing agents (people only; agents can't reach /api/ai)
@router.get("/ai/info")
async def ai_info(request: Request, user=Depends(require("ai", "r"))):
    return {"mcp_url": f"{base_url(request)}/api/mcp", "templates": TEMPLATES, "calls_per_minute": CALLS_PER_MINUTE, "keep_calls_days": KEEP_CALLS_DAYS,
            "tools": [{"name": t["name"], "title": t["title"], "description": t["description"].split("\n")[0], "write": t.get("write", False)} for t in TOOLS],
            "prompts": [{"name": p["name"], "title": p["title"], "description": p["description"]} for p in PROMPTS]}


@router.get("/ai/agents")
async def ai_agents(user=Depends(require("ai", "r"))):
    rows = await db.ai_agents.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return await public_agents(rows)


async def _works_as(user, uid):
    target = await db.users.find_one({"id": uid}, {"_id": 0, "id": 1, "role": 1, "active": 1, "name": 1})
    if not target or not target.get("active"):
        raise HTTPException(422, "Choose an active staff login for the agent to work as")
    if target["role"] in PORTAL_ROLES:
        raise HTTPException(422, "An agent can only work as a staff login, not a customer or partner login")
    if target["role"] == "super_admin" and user["role"] != "super_admin":
        raise HTTPException(403, "Only a super admin can let an agent work as a super admin")
    return target


def _clean(body, partial=False):
    out = {}
    if "name" in body or not partial:
        name = str(body.get("name") or "").strip()[:60]
        if not name:
            raise HTTPException(422, "Give the agent a name")
        out["name"] = name
    if "purpose" in body:
        out["purpose"] = str(body.get("purpose") or "").strip()[:2000]
    if "access" in body or not partial:
        acc = body.get("access") or "read"
        if acc not in ("read", "write"):
            raise HTTPException(422, "Access is read or write")
        out["access"] = acc
    if "expires_on" in body:
        exp = body.get("expires_on") or None
        if exp and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(exp)):
            raise HTTPException(422, "Expiry date should look like 2026-12-31")
        out["expires_on"] = exp
    if "template" in body:
        out["template"] = body.get("template") if body.get("template") in TEMPLATE_KEYS else None
    return out


@router.post("/ai/agents")
async def ai_create(body: dict, request: Request, user=Depends(require("ai", "w"))):
    data = _clean(body)
    target = await _works_as(user, body.get("user_id") or user["id"])
    key = new_key()
    doc = {"id": new_id(), **data, "purpose": data.get("purpose", ""), "template": data.get("template"), "expires_on": data.get("expires_on"),
           "user_id": target["id"], "active": True, "revoked": False, "key_hash": hash_key(key), "key_prefix": key[:10], "key_version": 1,
           "created_by": user["id"], "created_by_name": user["name"], "created_at": now_iso(), "updated_at": now_iso(),
           "last_used_at": None, "last_ip": None, "last_client": None, "calls_total": 0}
    await db.ai_agents.insert_one(dict(doc))
    await audit(user, "ai_agent_created", "ai_agents", doc["id"], {"name": doc["name"], "works_as": target["name"], "access": doc["access"]})
    mcp = f"{base_url(request)}/api/mcp"
    return {"agent": (await public_agents([doc]))[0], "key": key, "mcp_url": mcp, "url_with_key": f"{mcp}?key={key}"}


async def _agent_or_404(aid):
    a = await db.ai_agents.find_one({"id": aid}, {"_id": 0})
    if not a:
        raise HTTPException(404, "Agent not found")
    return a


@router.patch("/ai/agents/{aid}")
async def ai_update(aid: str, body: dict, user=Depends(require("ai", "w"))):
    a = await _agent_or_404(aid)
    if a.get("revoked"):
        raise HTTPException(409, "This agent's key was revoked. Make a new agent instead.")
    upd = _clean(body, partial=True)
    if "user_id" in body and body["user_id"] != a["user_id"]:
        upd["user_id"] = (await _works_as(user, body["user_id"]))["id"]
    if "active" in body:
        upd["active"] = bool(body["active"])
    if not upd:
        return (await public_agents([a]))[0]
    upd["updated_at"] = now_iso()
    await db.ai_agents.update_one({"id": aid}, {"$set": upd})
    changed = {k: v for k, v in upd.items() if k != "updated_at" and k != "purpose"}
    await audit(user, "ai_agent_paused" if upd.get("active") is False else "ai_agent_changed", "ai_agents", aid, {"name": a["name"], **changed})
    return (await public_agents([await _agent_or_404(aid)]))[0]


@router.post("/ai/agents/{aid}/rotate")
async def ai_rotate(aid: str, request: Request, user=Depends(require("ai", "w"))):
    a = await _agent_or_404(aid)
    if a.get("revoked"):
        raise HTTPException(409, "This agent's key was revoked. Make a new agent instead.")
    key = new_key()
    await db.ai_agents.update_one({"id": aid}, {"$set": {"key_hash": hash_key(key), "key_prefix": key[:10], "updated_at": now_iso()}, "$inc": {"key_version": 1}})
    await audit(user, "ai_agent_new_key", "ai_agents", aid, {"name": a["name"]})
    mcp = f"{base_url(request)}/api/mcp"
    return {"agent": (await public_agents([await _agent_or_404(aid)]))[0], "key": key, "mcp_url": mcp, "url_with_key": f"{mcp}?key={key}"}


@router.post("/ai/agents/{aid}/revoke")
async def ai_revoke(aid: str, user=Depends(require("ai", "w"))):
    a = await _agent_or_404(aid)
    await db.ai_agents.update_one({"id": aid}, {"$set": {"revoked": True, "active": False, "revoked_at": now_iso(), "revoked_by": user["name"], "updated_at": now_iso()},
                                                 "$inc": {"key_version": 1}})
    await audit(user, "ai_agent_revoked", "ai_agents", aid, {"name": a["name"]})
    return (await public_agents([await _agent_or_404(aid)]))[0]


@router.get("/ai/calls")
async def ai_calls(user=Depends(require("ai", "r")), agent_id: str = "", errors: bool = False, page: int = 1):
    f = {}
    if agent_id:
        f["agent_id"] = agent_id
    if errors:
        f["ok"] = False
    total = await db.ai_agent_calls.count_documents(f)
    rows = await db.ai_agent_calls.find(f, {"_id": 0}).sort("at", -1).skip((max(1, page) - 1) * 50).limit(50).to_list(50)
    return {"items": rows, "total": total, "page": page, "size": 50}


# ------------------------------------------------------------------ MCP: running a tool as the agent
class ToolError(Exception):
    pass


class Ctx:
    def __init__(self, request: Request, agent: dict, user: dict):
        self.request, self.agent, self.user = request, agent, user
        self.write = agent.get("access") == "write"

    async def api(self, method, path, params=None, body=None, raw=False):
        """One request to this server's own API as the agent, with the person's permissions."""
        method = method.upper()
        if not path.startswith("/api/"):
            path = "/api/" + path.lstrip("/")
        why = agent_blocked(self.agent.get("access"), method, path.split("?")[0])
        if why:
            raise ToolError(why)
        headers = {"Authorization": f"Bearer {make_agent_token(self.agent)}", "X-Forwarded-For": client_ip(self.request),
                   "X-Forwarded-Host": self.request.headers.get("x-forwarded-host") or self.request.headers.get("host") or "",
                   "User-Agent": f"spi-ai-agent/{self.agent['id'][:8]}"}
        params = {k: (str(v).lower() if isinstance(v, bool) else v) for k, v in (params or {}).items() if v not in (None, "")}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.request.app), base_url="http://spi.internal", timeout=120) as c:
            r = await c.request(method, path, params=params, json=body if method in AGENT_WRITE else None, headers=headers)
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail")
            except Exception:
                detail = r.text[:300]
            if isinstance(detail, list):  # validation errors
                detail = "; ".join(f"{'.'.join(str(x) for x in d.get('loc', [])[1:])}: {d.get('msg')}" for d in detail[:5])
            raise ToolError(f"{r.status_code}: {detail or 'Request failed'}")
        if raw:
            return r
        ctype = r.headers.get("content-type", "")
        if "json" in ctype:
            return r.json()
        if ctype.startswith("text/") and "html" not in ctype:
            return {"content_type": ctype, "text": r.text[:MAX_TEXT]}
        return {"file": True, "content_type": ctype, "bytes": len(r.content),
                "note": "This address returns a file. Open it in the app to download it; its data is also available as JSON from the matching screen or report."}


def compact(doc):
    """Drops empty values so answers stay short."""
    if isinstance(doc, dict):
        return {k: compact(v) for k, v in doc.items() if v not in (None, "", [], {}) and not (k == "deleted" and v is False)}
    if isinstance(doc, list):
        return [compact(x) for x in doc]
    return doc


def schema(props=None, required=None):
    return {"type": "object", "properties": props or {}, "required": required or [], "additionalProperties": False}


TYPE_ARG = {"type": "string", "description": "Record type key from list_record_types, e.g. leads, projects, invoices, purchase_orders, tickets"}


# ---- tools
async def t_whoami(ctx: Ctx, a):
    s = await get_settings()
    branches = await db.branches.find({}, {"_id": 0, "id": 1, "name": 1, "code": 1}).to_list(50)
    allowed = ctx.user.get("branch_ids") or []
    return {"agent": ctx.agent["name"], "job": ctx.agent.get("purpose") or None,
            "access": "read & write (never delete)" if ctx.write else "read only",
            "works_as": {"name": ctx.user["name"], "role": ROLES.get(ctx.user["role"]), "email": ctx.user.get("email")},
            "branches": [b for b in branches if ctx.user["role"] in ("super_admin", "director", "auditor") or not allowed or b["id"] in allowed],
            "company": s.get("company_name") or "Sellandiamman Power Infra", "today": today_ist().isoformat(), "timezone": "Asia/Kolkata (IST)",
            "currency": "INR (₹); figures in lakh (L) = 1,00,000 and crore (Cr) = 1,00,00,000", "app_version": APP_VERSION}


async def t_overview(ctx: Ctx, a):
    out = {}
    for key, path, params in (("dashboard", "/api/dashboard", None), ("approvals", "/api/approvals/inbox", None),
                              ("expiring_30_days", "/api/calendar/expiries", {"days": 30})):
        try:
            out[key] = await ctx.api("GET", path, params)
        except ToolError as ex:
            out[key] = {"not_available": str(ex)}
    ap = out.get("approvals")
    if isinstance(ap, dict) and "to_decide" in ap:
        out["approvals"] = {"waiting_for_this_person": ap["count"], "items": [{"title": x.get("title"), "type": x.get("entity_label"), "amount": x.get("amount"),
                            "asked_by": x.get("requested_by_name"), "since": x.get("created_at")} for x in ap["to_decide"][:15]],
                            "note": "AI agents can't decide approvals; a person decides them in the app (Approvals)."}
    exp = out.get("expiring_30_days")
    if isinstance(exp, list):
        out["expiring_30_days"] = exp[:25]
    return compact(out)


async def _meta(ctx):
    return await ctx.api("GET", "/api/meta")


async def t_list_types(ctx: Ctx, a):
    m = await _meta(ctx)
    groups = {}
    for k, e in m["entities"].items():
        perm = e.get("perm", "")
        acc = "read & write" if ("w" in perm and ctx.write) else "read" if "r" in perm else None
        if not acc:
            continue
        groups.setdefault(e.get("nav") or "Other", []).append(compact({
            "type": k, "label": e.get("plural") or e.get("label"), "access": acc, "numbered": bool(e.get("number")),
            "statuses": [s["value"] for s in (e.get("status") or {}).get("states", [])] or None, "needs_approval": bool(e.get("approval"))}))
    return {"groups": [{"group": g, "types": groups[g]} for g in (m.get("nav_order") or []) + [x for x in groups if x not in (m.get("nav_order") or [])] if g in groups],
            "tip": "describe_record_type gives the fields, choices and actions of a type."}


def _field_info(f, options):
    d = {"key": f["k"], "label": f.get("l"), "type": f["t"], "required": f.get("req") or None, "read_only": bool(f.get("ro") or f.get("calc")) or None,
         "help": f.get("help") or None, "ref_type": f.get("ref")}
    opts = f.get("opts")
    if isinstance(opts, str):
        opts = options.get(opts)
    if isinstance(opts, list):
        d["choices"] = [o["value"] if isinstance(o, dict) else o for o in opts][:60]
    if f["t"] == "lines":
        d["line_fields"] = [_field_info(x, options) for x in f.get("fields", [])]
    return compact(d)


async def t_describe(ctx: Ctx, a):
    m = await _meta(ctx)
    e = m["entities"].get(a.get("type"))
    if not e:
        raise ToolError(f"Unknown or not available record type '{a.get('type')}'. Use list_record_types.")
    st = (e.get("status") or {})
    acts = [{"action": k, "label": x.get("label"), "allowed_from": x.get("from"), "moves_to": x.get("to"), "needs_fields": x.get("need") or None,
             "needs_reason": bool(x.get("reason")) or None} for k, x in (e.get("actions") or {}).items()]
    if e.get("approval"):
        acts.insert(0, {"action": "submit", "label": "Submit for approval", "allowed_from": e["approval"].get("from")})
    return compact({"type": a["type"], "label": e.get("label"), "plural": e.get("plural"), "module": e.get("module"), "your_access": e.get("perm"),
                    "status_field": st.get("field"), "statuses": [{"value": s["value"], "label": s.get("label")} for s in st.get("states", [])],
                    "fields": [_field_info(f, m.get("options") or {}) for f in e["fields"]], "actions": [compact(x) for x in acts],
                    "search_looks_in": (e.get("search") or []) + (["code"] if e.get("number") else []), "default_sort": e.get("sort") or "-created_at",
                    "list_columns": e.get("list"),
                    "notes": "Refer to other records by id (ref fields). Dates YYYY-MM-DD. Money in rupees as numbers. Codes are given by the system."})


async def t_search(ctx: Ctx, a):
    q = str(a.get("query") or "").strip()
    if len(q) < 2:
        raise ToolError("Search needs at least 2 characters")
    return {"results": await ctx.api("GET", "/api/search", {"q": q})}


def _summarise_lines(item):
    out = {}
    for k, v in item.items():
        if isinstance(v, list) and v and isinstance(v[0], dict) and k not in ("files", "attachments", "photos"):
            out[k] = f"{len(v)} lines (get_record for detail)"
        else:
            out[k] = v
    return out


async def t_list(ctx: Ctx, a):
    size = max(1, min(100, int(a.get("page_size") or 20)))
    params = {"q": a.get("query"), "sort": a.get("sort"), "page": a.get("page") or 1, "size": size, "from": a.get("from"), "to": a.get("to"),
              "date_field": a.get("date_field")}
    for k, v in (a.get("filters") or {}).items():
        if k in params:
            continue
        params[k] = ",".join(str(x) for x in v) if isinstance(v, list) else v
    res = await ctx.api("GET", f"/api/e/{a['type']}", params)
    fields = a.get("fields")
    items = []
    for it in res["items"]:
        it = {k: v for k, v in it.items() if not fields or k in fields or k in ("id", "code")}
        items.append(compact(it if fields else _summarise_lines(it)))
    return {"total": res["total"], "page": res["page"], "page_size": res["size"], "items": items, "names_of_linked_records": compact(res.get("refs") or {})}


async def _resolve_id(ctx, typ, rid):
    if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-", str(rid)):
        return rid
    res = await ctx.api("GET", f"/api/e/{typ}", {"q": rid, "size": 5})
    hit = next((x for x in res["items"] if str(x.get("code", "")).lower() == str(rid).lower()), None) or (res["items"][0] if len(res["items"]) == 1 else None)
    if not hit:
        raise ToolError(f"No {typ} record with id or code '{rid}'")
    return hit["id"]


async def t_get(ctx: Ctx, a):
    rid = await _resolve_id(ctx, a["type"], a["id"])
    doc = await ctx.api("GET", f"/api/e/{a['type']}/{rid}")
    acts = doc.pop("_actions", [])
    out = {"record": compact({k: v for k, v in doc.items() if k not in ("_refs",)}), "names_of_linked_records": compact(doc.get("_refs") or {}),
           "actions_now": [x["key"] for x in acts] if ctx.write else [], }
    if a.get("include_history"):
        try:
            out["history"] = compact(await ctx.api("GET", f"/api/e/{a['type']}/{rid}/history"))
        except ToolError as ex:
            out["history"] = str(ex)
    return out


async def t_create(ctx: Ctx, a):
    doc = await ctx.api("POST", f"/api/e/{a['type']}", body=a.get("data") or {})
    return {"created": compact({k: doc.get(k) for k in ("id", "code", "status", "stage", "name", "title") if doc.get(k) is not None}), "record": compact(doc)}


async def t_update(ctx: Ctx, a):
    rid = await _resolve_id(ctx, a["type"], a["id"])
    doc = await ctx.api("PATCH", f"/api/e/{a['type']}/{rid}", body=a.get("changes") or {})
    return {"updated": True, "record": compact(doc)}


async def t_action(ctx: Ctx, a):
    rid = await _resolve_id(ctx, a["type"], a["id"])
    doc = await ctx.api("POST", f"/api/e/{a['type']}/{rid}/action/{a['action']}", body=a.get("data") or {})
    return {"done": a["action"], "record": compact({k: v for k, v in doc.items() if k != "_actions"}),
            "actions_now": [x["key"] for x in doc.get("_actions", [])]}


async def t_reports(ctx: Ctx, a):
    reps = await ctx.api("GET", "/api/reports")
    return {"reports": [compact({"report": r.get("key"), "title": r.get("title"), "group": r.get("group"), "about": r.get("sub") or r.get("desc")}) for r in reps]}


async def t_run_report(ctx: Ctx, a):
    mx = max(1, min(1000, int(a.get("max_rows") or 200)))
    res = await ctx.api("GET", f"/api/reports/{a['report']}", {"frm": a.get("from"), "to": a.get("to"), "branch": a.get("branch")})
    rows = res.get("rows") or []
    return {"title": res.get("title"), "columns": res.get("columns"), "rows": rows[:mx], "total_rows": len(rows),
            "truncated": len(rows) > mx or None, "dates": {"from": a.get("from") or "report default", "to": a.get("to") or "today"}}


ENDPOINT_HIDE = re.compile(r"^/api/(public|hooks|seo|robots|sitemap|llms|portal|auth|vault|ai|mcp|files|users|views|health|openapi|docs)(/|\.|$)")


def _endpoints(ctx: Ctx):
    out = []
    for r in ctx.request.app.routes:
        if not isinstance(r, APIRoute) or ENDPOINT_HIDE.search(r.path):
            continue
        for m in sorted(r.methods - {"HEAD", "OPTIONS"}):
            if m == "DELETE":
                continue
            doc = (r.endpoint.__doc__ or "").strip().split("\n")[0]
            q = [p.name for p in r.dependant.query_params]
            out.append(compact({"method": m, "path": r.path, "what": doc or r.name.replace("_", " ").strip().capitalize(), "query": q or None,
                                "takes_body": m in AGENT_WRITE or None, "allowed_for_this_agent": agent_blocked(ctx.agent.get("access"), m, r.path) is None}))
    return out


async def t_endpoints(ctx: Ctx, a):
    f = str(a.get("filter") or "").lower()
    eps = [x for x in _endpoints(ctx) if not f or f in x["path"].lower() or f in x["what"].lower()]
    return {"endpoints": eps, "notes": "Paths with {braces} take an id. Records (/api/e/...) are easier with the record tools. "
                                       "The person's role still decides what each one returns."}


async def t_call(ctx: Ctx, a):
    method = str(a.get("method") or "GET").upper()
    path = str(a.get("path") or "")
    if not path.startswith("/api/") or ".." in path or ENDPOINT_HIDE.search(path.split("?")[0]):
        raise ToolError("Use a path from list_endpoints, starting with /api/")
    res = await ctx.api(method, path, a.get("query") or {}, a.get("body") if method != "GET" else None)
    return compact(res) if isinstance(res, (dict, list)) else res


T_ARGS_LIST = {
    "type": TYPE_ARG,
    "query": {"type": "string", "description": "Text to look for (name, code, company, phone…)"},
    "filters": {"type": "object", "description": "Field = value, e.g. {\"status\": \"open\"} or {\"stage\": [\"new\", \"contacted\"]}, {\"owner_id\": \"<user id>\"}, "
                "{\"next_follow_up\": \"__empty\"}. Field keys from describe_record_type.", "additionalProperties": True},
    "from": {"type": "string", "description": "Start date YYYY-MM-DD (on date_field)"},
    "to": {"type": "string", "description": "End date YYYY-MM-DD"},
    "date_field": {"type": "string", "description": "Which date the range applies to (default: the record's date, else created_at)"},
    "sort": {"type": "string", "description": "Field to sort by; '-' for newest/largest first, e.g. -created_at, due_date"},
    "page": {"type": "integer", "minimum": 1},
    "page_size": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Default 20"},
    "fields": {"type": "array", "items": {"type": "string"}, "description": "Only these fields (id and code always come)"},
}

TOOLS = [
    {"name": "whoami", "title": "Who am I working as", "fn": t_whoami, "input": schema(),
     "description": "The agent, the staff login it works as (role, branches), its access level, today's date in India and the currency conventions. Start here."},
    {"name": "overview", "title": "Today's position", "fn": t_overview, "input": schema(),
     "description": "The person's dashboard for today: key figures, lists that need attention (leads waiting, tenders due, projects…), approvals waiting and "
                    "licences, calibrations, guarantees and permits expiring in 30 days."},
    {"name": "list_record_types", "title": "Record types", "fn": t_list_types, "input": schema(),
     "description": "Every kind of record this agent can open (leads, projects, invoices, purchase orders, tickets, permits…), grouped like the app's menu, "
                    "with read or write access and statuses."},
    {"name": "describe_record_type", "title": "Fields of a record type", "fn": t_describe, "input": schema({"type": TYPE_ARG}, ["type"]),
     "description": "Fields (key, label, type, required, choices, linked type), statuses and the actions that move a record on (e.g. submit for approval, "
                    "mark done). Read this before creating, changing or filtering records of a type."},
    {"name": "search", "title": "Search everything", "fn": t_search, "input": schema({"query": {"type": "string", "description": "Name, code, company, phone…"}}, ["query"]),
     "description": "Searches leads, clients, contacts, projects, proposals, BOQs, tenders, purchase orders, invoices, vendors, items, tickets, equipment, "
                    "employees, documents, approvals and drawings at once."},
    {"name": "list_records", "title": "List records", "fn": t_list, "input": schema(T_ARGS_LIST, ["type"]),
     "description": "Records of one type with text search, field filters, a date range, sorting and pages. Line items show as a count; use get_record "
                    "for the full record. Linked records come with their names."},
    {"name": "get_record", "title": "Open a record", "fn": t_get,
     "input": schema({"type": TYPE_ARG, "id": {"type": "string", "description": "Record id, or its code such as SPI/ERD/PO/26-27/0003 or LEAD-2026-0012"},
                      "include_history": {"type": "boolean", "description": "Also return who changed what and when"}}, ["type", "id"]),
     "description": "One record in full, with line items, the names of linked records and (for read & write agents) the actions possible right now."},
    {"name": "create_record", "title": "Add a record", "fn": t_create, "write": True,
     "input": schema({"type": TYPE_ARG, "data": {"type": "object", "description": "Field values by key (see describe_record_type). Leave out code, totals and status.",
                                                  "additionalProperties": True}}, ["type", "data"]),
     "description": "Adds a record (a lead, an activity/call log, a service ticket, a material request, a task…) exactly as a person would in the app: "
                    "numbering, totals, GST, routing and notifications happen as usual. Confirm with the person first."},
    {"name": "update_record", "title": "Change a record", "fn": t_update, "write": True,
     "input": schema({"type": TYPE_ARG, "id": {"type": "string", "description": "Record id or code"},
                      "changes": {"type": "object", "description": "Only the fields to change", "additionalProperties": True}}, ["type", "id", "changes"]),
     "description": "Changes some fields of a record. Locked records (approved, issued, paid) can't be changed, the same as in the app. Confirm with the person first."},
    {"name": "run_action", "title": "Move a record on", "fn": t_action, "write": True,
     "input": schema({"type": TYPE_ARG, "id": {"type": "string", "description": "Record id or code"},
                      "action": {"type": "string", "description": "Action key from describe_record_type or get_record (actions_now), e.g. submit, start, complete, close"},
                      "data": {"type": "object", "description": "Fields the action needs, and 'reason' where one is asked for", "additionalProperties": True}},
                     ["type", "id", "action"]),
     "description": "Runs a status action on a record, such as submitting it for approval, starting or completing work, issuing or closing. "
                    "Approvals themselves are decided by people in the app."},
    {"name": "list_reports", "title": "Reports", "fn": t_reports, "input": schema(),
     "description": "The reports this person may run (sales, tenders, projects, procurement, stores, finance, HR, safety, service)."},
    {"name": "run_report", "title": "Run a report", "fn": t_run_report,
     "input": schema({"report": {"type": "string", "description": "Report key from list_reports"}, "from": {"type": "string", "description": "YYYY-MM-DD"},
                      "to": {"type": "string", "description": "YYYY-MM-DD"}, "branch": {"type": "string", "description": "Branch id, if the person has several"},
                      "max_rows": {"type": "integer", "minimum": 1, "maximum": 1000, "description": "Default 200"}}, ["report"]),
     "description": "Runs a report for a date range and returns its columns and rows (the same figures as the Excel and PDF downloads)."},
    {"name": "list_endpoints", "title": "Other screens", "fn": t_endpoints,
     "input": schema({"filter": {"type": "string", "description": "Word to narrow the list, e.g. finance, ceo, stock, project, pipeline, service"}}),
     "description": "The app's computed screens as API addresses: CEO view and alerts, finance (balances, receivables, payables, GST, TDS, P&L, cash flow), "
                    "stock on hand, project hub, Gantt and materials, sales pipeline, marketing results, service jobs and renewals, expiry calendar."},
    {"name": "call_api", "title": "Open a screen's data", "fn": t_call,
     "input": schema({"method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH"], "description": "GET to read"},
                      "path": {"type": "string", "description": "Path from list_endpoints with ids filled in, e.g. /api/finance/receivables or /api/projects/<id>/hub"},
                      "query": {"type": "object", "description": "Query parameters", "additionalProperties": True},
                      "body": {"type": "object", "description": "JSON body for POST, PUT or PATCH", "additionalProperties": True}}, ["path"]),
     "description": "Calls one address from list_endpoints as this person and returns its JSON. Read-only agents can only use GET."},
]
TOOL_MAP = {t["name"]: t for t in TOOLS}


def tool_defs(agent):
    write = agent.get("access") == "write"
    out = []
    for t in TOOLS:
        if t.get("write") and not write:
            continue
        inp = t["input"]
        if t["name"] == "call_api" and not write:
            inp = json.loads(json.dumps(inp))
            inp["properties"]["method"]["enum"] = ["GET"]
            inp["properties"].pop("body")
        out.append({"name": t["name"], "title": t["title"], "description": t["description"], "inputSchema": inp,
                    "annotations": {"title": t["title"], "readOnlyHint": not t.get("write") and t["name"] != "call_api",
                                    "destructiveHint": False, "idempotentHint": not t.get("write") and t["name"] != "call_api", "openWorldHint": False}})
    return out


# ---- prompts (ready-made requests that show up in Claude's prompt list)
PROMPTS = [
    {"name": "daily_brief", "title": "Daily brief",
     "description": "Today's position: what needs attention, approvals waiting, expiries, and the three things to do first.",
     "text": "Give me today's brief for Sellandiamman Power Infra. Use overview first; if the CEO view is available (list_endpoints 'ceo'), add the health "
             "score and the top alerts. Then list approvals waiting, anything expiring in the next 7 days, and leads or tickets past their target. "
             "End with the three things I should do first today. Keep it short and give record codes."},
    {"name": "lead_followups", "title": "Lead follow-ups",
     "description": "Leads with no first reply or an overdue follow-up, oldest first, with a suggested next step.",
     "text": "Find leads that are still waiting for a first reply or whose next follow-up date has passed (list_records on leads). Sort oldest first and "
             "show code, name, company, service, value, owner and days waiting, with a one-line suggested next step for each."},
    {"name": "project_risks", "title": "Project risk review",
     "description": "Live projects behind plan, under-billed or with open hindrances and pending approvals.",
     "text": "Review the live projects: progress against plan, under-billing, open hindrances, RFIs and snags, and TNPDCL/CEIG approvals still pending. "
             "Use list_records on projects and the project hub (list_endpoints 'project'). Rank them by risk and say what each needs."},
    {"name": "collections", "title": "Collections list",
     "description": "Overdue receivables by client and age, with retention due, as a calling list.",
     "text": "Make a collections list from receivables (list_endpoints 'finance', then the receivables screen): overdue amounts by client and age bucket, "
             "the oldest invoices, and retention due. Order it by amount overdue and suggest who to call first."},
]


def instructions(agent, user, company):
    acc = "read and write (it can add and change records but never delete)" if agent.get("access") == "write" else "read only"
    job = (agent.get("purpose") or "").strip()
    return (f"You are connected to the business system of {company}, an LT/HT electrical contractor in Tamil Nadu, India (sales, estimation, tenders, "
            f"projects, TNPDCL and CEIG liaison, quality, safety, procurement, stores, service and AMC, finance, HR). This connection is the AI agent "
            f"'{agent['name']}', working as {user['name']} ({ROLES.get(user['role'])}); that person's permissions, branches and hidden fields apply. Access: {acc}.\n"
            "How to work: whoami and overview first. Find records with search, or list_record_types -> describe_record_type -> list_records / get_record. "
            "Computed screens (CEO view, finance, stock, project hub, pipeline, service) are in list_endpoints and call_api; reports in list_reports and run_report.\n"
            "Money is in Indian rupees (lakh and crore); dates are YYYY-MM-DD in India time. Every change is recorded in the activity log under the person's name "
            "with this agent's name. Approvals are decided by people in the app; you may submit records for approval. Confirm with the person you are "
            "working for before adding or changing anything."
            + (f"\nThis agent's job: {job}" if job else ""))


# ------------------------------------------------------------------ MCP endpoint
_rate: dict = {}


def _rate_ok(aid):
    if os.environ.get("DISABLE_RATE_LIMIT") == "true":
        return True
    t = time.time()
    hits = [h for h in _rate.get(aid, []) if h > t - 60]
    if len(hits) >= CALLS_PER_MINUTE:
        _rate[aid] = hits
        return False
    hits.append(t)
    _rate[aid] = hits
    return True


def _key_from(request: Request):
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer ") and auth[7:].strip().startswith(KEY_PREFIX):
        return auth[7:].strip()
    return (request.headers.get("x-api-key") or request.query_params.get("key") or "").strip()


def _rpc_error(mid, code, message, status=200, headers=None):
    return JSONResponse({"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}, status_code=status, headers=headers)


def _redact(args):
    try:
        text = json.dumps(args, ensure_ascii=False, default=str)
    except Exception:
        text = str(args)
    text = re.sub(r'("(?:password|secret|otp|token|key)"\s*:\s*)"[^"]*"', r'\1"***"', text, flags=re.I)
    return text[:600]


async def _log(ctx: Ctx, method, tool, args, ok, error, ms):
    await db.ai_agent_calls.insert_one({"id": new_id(), "agent_id": ctx.agent["id"], "agent_name": ctx.agent["name"], "user_id": ctx.user["id"],
                                        "user_name": ctx.user["name"], "method": method, "tool": tool, "args": _redact(args) if args else None,
                                        "ok": ok, "error": (error or "")[:400] or None, "ms": ms, "ip": client_ip(ctx.request), "at": now_iso()})
    if random.random() < 0.01:
        await db.ai_agent_calls.delete_many({"at": {"$lt": (now() - timedelta(days=KEEP_CALLS_DAYS)).isoformat()}})


async def _handle(ctx: Ctx, msg, company):
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
        return {"jsonrpc": "2.0", "id": msg.get("id") if isinstance(msg, dict) else None, "error": {"code": -32600, "message": "Invalid request"}}
    mid, method, params = msg.get("id"), msg["method"], msg.get("params") or {}
    is_note = "id" not in msg

    def ok(result):
        return None if is_note else {"jsonrpc": "2.0", "id": mid, "result": result}

    def err(code, text):
        return None if is_note else {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": text}}

    if method.startswith("notifications/"):
        return None
    if method == "initialize":
        want = params.get("protocolVersion")
        ci = params.get("clientInfo") or {}
        await db.ai_agents.update_one({"id": ctx.agent["id"]}, {"$set": {"last_client": f"{ci.get('name', '')} {ci.get('version', '')}".strip()[:80] or None}})
        await _log(ctx, "initialize", None, {"client": ci.get("name")}, True, None, 0)
        return ok({"protocolVersion": want if want in PROTOCOLS else PROTOCOLS[0],
                   "capabilities": {"tools": {"listChanged": False}, "prompts": {"listChanged": False}},
                   "serverInfo": {"name": "sellandiamman-power-infra", "title": "Sellandiamman Power Infra", "version": APP_VERSION},
                   "instructions": instructions(ctx.agent, ctx.user, company)})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": tool_defs(ctx.agent)})
    if method == "prompts/list":
        return ok({"prompts": [{"name": p["name"], "title": p["title"], "description": p["description"], "arguments": []} for p in PROMPTS]})
    if method == "prompts/get":
        p = next((x for x in PROMPTS if x["name"] == params.get("name")), None)
        if not p:
            return err(-32602, "Unknown prompt")
        return ok({"description": p["description"], "messages": [{"role": "user", "content": {"type": "text", "text": p["text"]}}]})
    if method == "resources/list":
        return ok({"resources": []})
    if method == "resources/templates/list":
        return ok({"resourceTemplates": []})
    if method == "logging/setLevel":
        return ok({})
    if method == "completion/complete":
        return ok({"completion": {"values": [], "hasMore": False}})
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        t = TOOL_MAP.get(name)
        if not t or (t.get("write") and ctx.agent.get("access") != "write"):
            return err(-32602, f"Unknown tool: {name}")
        if not isinstance(args, dict):
            return err(-32602, "arguments must be an object")
        missing = [k for k in t["input"].get("required", []) if args.get(k) in (None, "")]
        t0 = time.time()
        try:
            if missing:
                raise ToolError(f"Missing: {', '.join(missing)}")
            result = await t["fn"](ctx, args)
            text = json.dumps(result, ensure_ascii=False, default=str, separators=(",", ":"))
            if len(text) > MAX_TEXT:
                text = text[:MAX_TEXT] + ' …(cut short: ask for fewer rows, a smaller page_size or specific fields)'
            await _log(ctx, "tools/call", name, args, True, None, int((time.time() - t0) * 1000))
            return ok({"content": [{"type": "text", "text": text}], "isError": False})
        except (ToolError, HTTPException) as ex:
            text = str(ex) if isinstance(ex, ToolError) else str(ex.detail)
            await _log(ctx, "tools/call", name, args, False, text, int((time.time() - t0) * 1000))
            return ok({"content": [{"type": "text", "text": text}], "isError": True})
        except Exception as ex:  # a fault in the server: tell the agent plainly, keep the details in the server log
            logger.exception("MCP tool %s failed", name)
            await _log(ctx, "tools/call", name, args, False, f"server error: {type(ex).__name__}", int((time.time() - t0) * 1000))
            return ok({"content": [{"type": "text", "text": "Something went wrong on the server with this request. Try different arguments, or tell the person."}],
                       "isError": True})
    return err(-32601, f"Method not found: {method}")


@router.post("/mcp")
async def mcp(request: Request):
    """Model Context Protocol endpoint for AI agents (Streamable HTTP, JSON-RPC 2.0)."""
    REQ_BRANCH.set(None)
    key = _key_from(request)
    agent = await db.ai_agents.find_one({"key_hash": hash_key(key)}, {"_id": 0}) if key.startswith(KEY_PREFIX) else None
    if not agent:
        return _rpc_error(None, -32001, "Missing or wrong AI agent key. Make one in the app: Settings -> AI agents & MCP.", 401,
                          {"WWW-Authenticate": 'Bearer realm="sellandiamman-power-infra"'})
    if not agent_is_live(agent):
        return _rpc_error(None, -32001, f"This AI agent is {status_of(agent)}. An administrator can switch it back on in Settings -> AI agents & MCP.", 403)
    user = await agent_identity(agent)
    if not user:
        return _rpc_error(None, -32001, "The staff login this agent works as is switched off.", 403)
    try:
        body = await request.json()
    except Exception:
        return _rpc_error(None, -32700, "Parse error: send JSON-RPC 2.0", 400)
    if not _rate_ok(agent["id"]):
        mid = body.get("id") if isinstance(body, dict) else None
        return _rpc_error(mid, -32000, f"Too many calls: this agent may make {CALLS_PER_MINUTE} a minute. Wait a moment and try again.", 429)
    ctx = Ctx(request, agent, user)
    company = (await get_settings()).get("company_name") or "Sellandiamman Power Infra"
    await db.ai_agents.update_one({"id": agent["id"]}, {"$set": {"last_used_at": now_iso(), "last_ip": client_ip(request)}, "$inc": {"calls_total": 1}})
    if isinstance(body, list):
        if not body:
            return _rpc_error(None, -32600, "Empty batch", 400)
        out = [r for r in [await _handle(ctx, m, company) for m in body] if r is not None]
        return JSONResponse(out) if out else Response(status_code=202)
    res = await _handle(ctx, body, company)
    return JSONResponse(res) if res is not None else Response(status_code=202)


@router.get("/mcp")
async def mcp_get():
    """This server answers each POST directly and doesn't keep a stream open."""
    return Response(status_code=405, headers={"Allow": "POST"})


@router.delete("/mcp")
async def mcp_delete():
    return Response(status_code=405, headers={"Allow": "POST"})
