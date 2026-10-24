"""Generic record engine: list, read, add, change, delete and workflow actions for every entity in registry.py.

Rules applied to every record type:
  * permissions by role and module (roles.PERMS), checked here on the server
  * branch scope, project scope (project manager / site engineer), own-record scope and portal scope
  * hidden fields (cost, salary, bank) removed from what a role reads and ignored in what it writes
  * values checked by type; formulas (expr.py) computed on lines and totals; money rounded to paise
  * numbering per company, branch and financial year; history of every change in the activity log
  * approvals: submit -> approval rules (Settings) -> approve / reject in the Approvals inbox; nobody approves their own
"""
import re
import json
from datetime import date, datetime, timedelta
from fastapi import HTTPException

import registry as REG
from catalog import OPTIONS
from expr import evaluate
from core import (db, now_iso, new_id, today_ist, money, normalize_phone, normalize_email, audit, can, branch_filter,
                  in_branch, home_branch, my_project_ids, project_scoped, own_field, doc_number, simple_code, notify,
                  notify_roles, get_settings, allowed_branches)
from roles import HIDDEN_FIELD_TAGS, PORTAL_ROLES, DEFAULT_APPROVAL_RULES

HOOKS = {}  # entity -> {"before": fn, "after": fn, "action": fn} (filled by hooks.py)
SYSTEM = {"id", "code", "branch_id", "created_at", "created_by", "updated_at", "updated_by", "deleted", "deleted_reason",
          "deleted_at", "deleted_by", "status", "approval_id", "_refs", "sort_key", "source_entity"}
MAX_TEXT = {"text": 500, "textarea": 20000, "markdown": 60000}


def ent(key):
    e = REG.E.get(key)
    if not e:
        raise HTTPException(404, "Unknown record type")
    return e


def status_field(e):
    return (e.get("status") or {}).get("field")


def hidden_tags(user):
    return HIDDEN_FIELD_TAGS.get(user["role"], []) if user else []


def opts_of(f):
    o = f.get("opts")
    if isinstance(o, str):
        return OPTIONS.get(o, [])
    return o or []


# ------------------------------------------------------------------ scope
async def scope_filter(e, user):
    """Mongo filter for what this person may see of this record type."""
    q = {"deleted": {"$ne": True}}
    role = user["role"]
    key = e["key"]
    if role in PORTAL_ROLES:
        return await portal_filter(e, user, q)
    if e.get("branch"):
        q.update(branch_filter(user))
    of = own_field(user, key)
    if of:
        q[of] = user["id"]
    if project_scoped(user):
        if key == "projects":
            q["$or"] = [{"manager_id": user["id"]}, {"team_ids": user["id"]}]
        elif any(f["k"] == "project_id" for f in e["fields"]) and e.get("project"):
            q["project_id"] = {"$in": await my_project_ids(user)}
    return q


async def portal_filter(e, user, q):
    cfg = (e.get("portal") or {}).get(user["role"])
    if not cfg:
        raise HTTPException(403, "Not available in your portal")
    role, key = user["role"], e["key"]
    acc = user.get("account_id")
    ven = user.get("vendor_id")
    if role == "client":
        if not acc:
            raise HTTPException(403, "Your login is not linked to a client account")
        if cfg == "id":
            q["id"] = acc
        elif cfg == "account_id":
            q["account_id"] = acc
        elif cfg == "project":
            ids = [p["id"] for p in await db.projects.find({"account_id": acc, "deleted": {"$ne": True}}, {"_id": 0, "id": 1}).to_list(500)]
            q["project_id"] = {"$in": ids}
        elif cfg == "account_id_or_project":
            ids = [p["id"] for p in await db.projects.find({"account_id": acc, "deleted": {"$ne": True}}, {"_id": 0, "id": 1}).to_list(500)]
            q["$or"] = [{"account_id": acc}, {"project_id": {"$in": ids}}]
        # internal-only records stay hidden
        if key in ("dprs", "drawings", "documents", "liaisons"):
            q["share_with_client"] = True
        if key in ("proposals",):
            q["status"] = {"$in": ["sent", "accepted", "declined", "expired"]}
        if key in ("invoices",):
            q["status"] = {"$in": ["issued", "part_paid", "paid"]}
        if key in ("ra_bills",):
            q["status"] = {"$in": ["submitted", "certified", "invoiced", "paid"]}
        if key in ("variations",):
            q["status"] = {"$in": ["sent", "client_approved", "client_rejected"]}
        if key in ("test_reports",):
            q["status"] = "issued"
    elif role == "consultant":
        cid = user.get("contact_id")
        pids = [p["id"] for p in await db.projects.find({"consultant_ids": cid, "deleted": {"$ne": True}}, {"_id": 0, "id": 1}).to_list(500)]
        if cfg == "consultant_ids":
            q["consultant_ids"] = cid
        elif cfg == "project":
            q["project_id"] = {"$in": pids}
        if key in ("dprs", "drawings"):
            q["share_with_client"] = True
        if key == "test_reports":
            q["status"] = "issued"
    elif role in ("vendor", "subcontractor"):
        if not ven:
            raise HTTPException(403, "Your login is not linked to a vendor record")
        if cfg == "id":
            q["id"] = ven
        elif cfg == "worker":
            wids = [w["id"] for w in await db.workers.find({"contractor_id": ven}, {"_id": 0, "id": 1}).to_list(2000)]
            q["worker_id"] = {"$in": wids}
        elif cfg == "vendor_ids":
            q["vendor_ids"] = ven
            q["status"] = {"$in": ["sent", "compared", "closed"]}
        else:
            q[cfg] = ven
        if key == "purchase_orders":
            q["status"] = {"$in": ["sent", "partly_received", "received", "closed"]}
    elif role == "partner":
        raise HTTPException(403, "Not available in your portal")
    return q


async def check_write_scope(e, user, doc):
    if e.get("branch") and doc.get("branch_id") and not in_branch(user, doc.get("branch_id")):
        raise HTTPException(403, "You can only work with records of your own branch")
    if project_scoped(user) and e.get("project") and doc.get("project_id"):
        if doc["project_id"] not in await my_project_ids(user):
            raise HTTPException(403, "You can only work on your own projects")


# ------------------------------------------------------------------ reading
def strip_hidden(e, doc, tags):
    if not tags or not doc:
        return doc
    out = dict(doc)
    for f in e["fields"]:
        if f.get("hide") in tags:
            out.pop(f["k"], None)
        elif f["t"] == "lines" and isinstance(out.get(f["k"]), list):
            hid = [x["k"] for x in f["fields"] if x.get("hide") in tags]
            if hid:
                out[f["k"]] = [{k: v for k, v in (ln or {}).items() if k not in hid} for ln in out[f["k"]]]
    return out


def title_of(e, doc):
    t = doc.get(e.get("title") or "name")
    if e.get("title") == "code" or not t:
        t = doc.get("code") or doc.get("name") or doc.get("title") or doc.get("id")
    if isinstance(t, str) and len(t) > 80:
        t = t[:77] + "..."
    return t


async def nice_title(e, doc):
    """title_of, but a reference title (e.g. a leave's employee) shows the referenced record's name."""
    f = next((x for x in e["fields"] if x["k"] == e.get("title")), None)
    if f and f["t"] == "ref" and doc.get(f["k"]):
        names = (await ref_titles(e, [doc])).get(f["ref"]) or {}
        name = names.get(doc[f["k"]])
        if name:
            extra = doc.get("from_date") or doc.get("date") or doc.get("month")
            if isinstance(extra, str) and len(extra) == 10:
                from datetime import date as _d
                extra = "from " + _d.fromisoformat(extra).strftime("%d %b %Y").lstrip("0")
            return f"{name}{', ' + str(extra) if extra else ''}"
    return title_of(e, doc)


async def ref_titles(e, docs):
    """{entity: {id: title}} for the reference fields in these records, so lists show names, not ids."""
    want = {}
    for f in e["fields"]:
        if f["t"] in ("ref", "refs"):
            ids = set()
            for d in docs:
                v = d.get(f["k"])
                if isinstance(v, list):
                    ids.update(x for x in v if x)
                elif v:
                    ids.add(v)
            if ids:
                want.setdefault(f["ref"], set()).update(ids)
        if f["t"] == "lines":
            for sub in f["fields"]:
                if sub["t"] == "ref":
                    for d in docs:
                        for ln in d.get(f["k"]) or []:
                            if ln and ln.get(sub["k"]):
                                want.setdefault(sub["ref"], set()).add(ln[sub["k"]])
    if any(d.get("created_by") for d in docs):
        want.setdefault("users", set()).update(d["created_by"] for d in docs if d.get("created_by"))
    if any(d.get("branch_id") for d in docs):
        want.setdefault("branches", set()).update(d["branch_id"] for d in docs if d.get("branch_id"))
    out = {}
    for ref, ids in want.items():
        if ref == "users":
            rows = await db.users.find({"id": {"$in": list(ids)}}, {"_id": 0, "id": 1, "name": 1}).to_list(len(ids))
            out[ref] = {r["id"]: r.get("name") for r in rows}
            continue
        re_ = REG.E.get(ref)
        if not re_:
            continue
        proj = {"_id": 0, "id": 1, "code": 1, "name": 1, "title": 1, re_.get("title") or "name": 1}
        rows = await db[ref].find({"id": {"$in": list(ids)}}, proj).to_list(len(ids))
        out[ref] = {r["id"]: title_of(re_, r) for r in rows}
    return out


def _coerce_filter(f, v):
    if f["t"] in ("number", "money", "percent"):
        try:
            return float(v)
        except ValueError:
            return v
    if f["t"] == "bool":
        return v in ("1", "true", "yes", True)
    return v


async def list_records(key, user, params: dict):
    e = ent(key)
    if user["role"] not in PORTAL_ROLES and not can(user, e["module"], "r"):
        raise HTTPException(403, "You do not have permission to view this")
    scope_q = await scope_filter(e, user)
    fmap = {f["k"]: f for f in e["fields"]}
    sf = status_field(e)
    pq = {}
    for k, v in params.items():
        if v in (None, "", "all"):
            continue
        fk = sf if (k == "status" and sf) else k
        if fk in fmap or fk in ("status", "branch_id", "created_by", "id"):
            f = fmap.get(fk) or {"t": "select" if fk in ("status", "branch_id") else "text"}
            if isinstance(v, str) and "," in v and f["t"] not in ("text", "textarea"):
                pq[fk] = {"$in": [_coerce_filter(f, x) for x in v.split(",")]}
            elif f["t"] in ("refs", "multiselect"):
                pq[fk] = v
            elif v == "__empty":
                pq[fk] = {"$in": [None, ""]}
            else:
                pq[fk] = _coerce_filter(f, v)
    if params.get("from") or params.get("to"):
        dk = params.get("date_field") or ("date" if "date" in fmap else "created_at")
        rng = {}
        if params.get("from"):
            rng["$gte"] = params["from"]
        if params.get("to"):
            rng["$lte"] = params["to"] + ("T23:59:59" if dk.endswith("_at") or dk in ("created_at", "updated_at") else "")
        pq[dk] = rng
    parts = [scope_q, pq]
    text = (params.get("q") or "").strip()
    if text:
        rx = {"$regex": re.escape(text[:60]), "$options": "i"}
        ors = [{k: rx} for k in (e.get("search") or []) + (["code"] if e.get("number") else [])]
        if ors:
            parts.append({"$or": ors})
    q = {"$and": [p for p in parts if p]}
    sort = params.get("sort") or e.get("sort") or "-created_at"
    direction = -1 if sort.startswith("-") else 1
    sk = sort.lstrip("-")
    page = max(1, int(params.get("page") or 1))
    size = min(500, max(1, int(params.get("size") or 50)))
    total = await db[key].count_documents(q)
    rows = await db[key].find(q, {"_id": 0}).sort([(sk, direction), ("created_at", -1)]).skip((page - 1) * size).limit(size).to_list(size)
    tags = hidden_tags(user)
    rows = [strip_hidden(e, r, tags) for r in rows]
    return {"items": rows, "total": total, "page": page, "size": size, "refs": await ref_titles(e, rows)}


async def get_record(key, user, rid, raw=False):
    e = ent(key)
    if user["role"] not in PORTAL_ROLES and not can(user, e["module"], "r"):
        raise HTTPException(403, "You do not have permission to view this")
    q = await scope_filter(e, user)
    doc = await db[key].find_one({"$and": [q, {"id": rid}]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Record not found")
    if raw:
        return doc
    out = strip_hidden(e, doc, hidden_tags(user))
    out["_refs"] = await ref_titles(e, [doc])
    return out


# ------------------------------------------------------------------ writing
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _num(v, f):
    if v in (None, ""):
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        raise HTTPException(422, f"{f['l']}: enter a number")
    if n != n or abs(n) > 1e13:
        raise HTTPException(422, f"{f['l']}: number out of range")
    if f["t"] == "money":
        return money(n)
    return round(n, 6)


async def clean_value(f, v, tags, ctx_path=""):
    t = f["t"]
    label = f["l"]
    if v is None:
        return None
    if t in ("text", "textarea", "markdown"):
        s = str(v).strip()
        if len(s) > MAX_TEXT[t]:
            raise HTTPException(422, f"{label}: too long")
        return s
    if t in ("number", "money", "percent"):
        return _num(v, f)
    if t == "bool":
        return bool(v) and v not in ("false", "0", 0)
    if t == "date":
        s = str(v)[:10]
        if s and not DATE_RE.match(s):
            raise HTTPException(422, f"{label}: use a date like 2026-10-24")
        if s:
            try:
                date.fromisoformat(s)
            except ValueError:
                raise HTTPException(422, f"{label}: not a real date")
        return s or None
    if t == "datetime":
        s = str(v)[:25]
        if s:
            try:
                datetime.fromisoformat(s.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(422, f"{label}: use a date and time")
        return s or None
    if t == "select":
        s = str(v)
        if s and opts_of(f) and s not in [o["value"] for o in opts_of(f)]:
            raise HTTPException(422, f"{label}: '{s}' is not one of the choices")
        return s or None
    if t == "multiselect":
        vals = [str(x) for x in (v if isinstance(v, list) else [v]) if x not in (None, "")]
        allowed = [o["value"] for o in opts_of(f)]
        bad = [x for x in vals if allowed and x not in allowed]
        if bad:
            raise HTTPException(422, f"{label}: '{bad[0]}' is not one of the choices")
        return vals
    if t == "phone":
        return normalize_phone(str(v), required=False) or None
    if t == "email":
        return normalize_email(str(v)) or None
    if t == "ref":
        s = str(v)
        if not s:
            return None
        coll = "users" if f["ref"] == "users" else f["ref"]
        if not await db[coll].find_one({"id": s, "deleted": {"$ne": True}}, {"_id": 1}):
            raise HTTPException(422, f"{label}: the selected record was not found")
        return s
    if t == "refs":
        vals = [str(x) for x in (v if isinstance(v, list) else [v]) if x]
        coll = "users" if f["ref"] == "users" else f["ref"]
        if vals:
            found = await db[coll].count_documents({"id": {"$in": vals}})
            if found != len(set(vals)):
                raise HTTPException(422, f"{label}: a selected record was not found")
        return list(dict.fromkeys(vals))
    if t in ("file",):
        if isinstance(v, dict) and v.get("id"):
            return {k: v.get(k) for k in ("id", "name", "type", "size", "url") if v.get(k) is not None}
        return None
    if t == "files":
        out = []
        for x in (v or [])[:50]:
            if isinstance(x, dict) and x.get("id"):
                out.append({k: x.get(k) for k in ("id", "name", "type", "size", "url", "lat", "lng", "at") if x.get(k) is not None})
        return out
    if t == "geo":
        if isinstance(v, dict) and v.get("lat") is not None and v.get("lng") is not None:
            try:
                return {"lat": float(v["lat"]), "lng": float(v["lng"]), "acc": float(v.get("acc") or 0), "at": v.get("at") or now_iso()}
            except (TypeError, ValueError):
                raise HTTPException(422, f"{label}: bad location")
        return None
    if t == "json":
        if isinstance(v, (dict, list)):
            s = json.dumps(v, default=str)
            if len(s) > 50000:
                raise HTTPException(422, f"{label}: too large")
            return v
        return None
    if t == "lines":
        if not isinstance(v, list):
            raise HTTPException(422, f"{label}: expected a list of lines")
        if len(v) > 1000:
            raise HTTPException(422, f"{label}: too many lines")
        out = []
        for i, ln in enumerate(v):
            if not isinstance(ln, dict):
                continue
            row = {}
            for sf in f["fields"]:
                if sf.get("hide") in tags or sf.get("ro"):
                    if sf["k"] in ln and sf.get("hide") not in tags and not sf.get("calc"):
                        row[sf["k"]] = ln[sf["k"]]  # server-kept read-only values travel back unchanged
                    continue
                if sf["k"] in ln:
                    row[sf["k"]] = await clean_value(sf, ln.get(sf["k"]), tags, f"{label} line {i + 1}")
            if ln.get("_id"):
                row["_id"] = str(ln["_id"])[:40]
            out.append(row)
        return out
    return v


def apply_defaults(e, doc):
    for f in e["fields"]:
        if f["k"] not in doc and "default" in f:
            d = f["default"]
            doc[f["k"]] = json.loads(json.dumps(d)) if isinstance(d, (list, dict)) else d
    sf = status_field(e)
    if sf and not doc.get(sf):
        doc[sf] = e["status"]["default"]


def compute(e, doc):
    """Line formulas, then record formulas, in field order (twice so later fields can feed earlier ones)."""
    for f in e["fields"]:
        if f["t"] == "lines" and isinstance(doc.get(f["k"]), list):
            for ln in doc[f["k"]]:
                for sf in f["fields"]:
                    if sf.get("calc"):
                        ln[sf["k"]] = _round(sf, evaluate(sf["calc"], {**doc, **ln}))
    for _ in range(2):
        for f in e["fields"]:
            if f.get("calc") and f["t"] != "lines":
                doc[f["k"]] = _round(f, evaluate(f["calc"], doc))
    return doc


def _round(f, v):
    if isinstance(v, (int, float)):
        if f["t"] == "money":
            return money(v)
        return round(float(v), 6)
    return v


def check_required(e, doc):
    missing = []
    for f in e["fields"]:
        if f.get("req") and not f.get("ro") and doc.get(f["k"]) in (None, "", []):
            show = f.get("show")
            if show and any(doc.get(k) != v for k, v in show.items()):
                continue
            missing.append(f["l"])
        if f["t"] == "lines":
            for i, ln in enumerate(doc.get(f["k"]) or []):
                for sf in f["fields"]:
                    if sf.get("req") and ln.get(sf["k"]) in (None, ""):
                        missing.append(f"{f['l']} line {i + 1}: {sf['l']}")
    if missing:
        raise HTTPException(422, "Please fill in: " + ", ".join(missing[:6]))


async def assign_number(e, doc):
    cfg = e.get("number")
    if not cfg or doc.get("code"):
        return
    if cfg.get("doc"):
        d = doc.get("date") or doc.get("bill_date") or None
        on = date.fromisoformat(d[:10]) if isinstance(d, str) and DATE_RE.match(d[:10]) else today_ist()
        doc["code"] = await doc_number(cfg["doc"], doc.get("branch_id"), on)
    else:
        doc["code"] = await simple_code(e["key"], cfg["prefix"], cfg.get("width", 4), yearly=cfg.get("kind") == "year")


def diff(old, new, e):
    out = {}
    for f in e["fields"]:
        k = f["k"]
        if f["t"] in ("lines", "markdown", "textarea", "files", "json"):
            if old.get(k) != new.get(k):
                out[k] = "changed"
            continue
        if old.get(k) != new.get(k) and k in new:
            out[k] = [old.get(k), new.get(k)]
    sf = status_field(e)
    if sf and old.get(sf) != new.get(sf):
        out[sf] = [old.get(sf), new.get(sf)]
    return out


async def clean_input(e, data, user, existing=None):
    tags = hidden_tags(user)
    out = {}
    sf = status_field(e)
    for f in e["fields"]:
        k = f["k"]
        if k not in data:
            continue
        if f.get("ro") or f.get("hide") in tags:
            continue
        if f["k"] == sf:
            continue
        out[k] = await clean_value(f, data[k], tags)
    if sf and sf in data and data[sf]:
        out["__status"] = str(data[sf])
    return out


async def create_record(key, user, data, *, system=False, source=None):
    e = ent(key)
    if e.get("readonly") and not system:
        raise HTTPException(403, "These records are made by the system")
    if not system and not can(user, e["module"], "w"):
        raise HTTPException(403, "You do not have permission to add this")
    vals = await clean_input(e, data, user) if not system else {k: v for k, v in data.items()}
    status_in = vals.pop("__status", None)
    doc = {"id": new_id(), **vals}
    apply_defaults(e, doc)
    sf = status_field(e)
    if sf and status_in and not system:
        allowed_direct = not e.get("approval") and not e.get("actions")
        if allowed_direct and status_in in [s["value"] for s in e["status"]["states"]]:
            doc[sf] = status_in
    if e.get("branch"):
        doc["branch_id"] = data.get("branch_id") if data.get("branch_id") and in_branch(user, data.get("branch_id")) else (doc.get("branch_id") or home_branch(user))
        if not doc.get("branch_id") and doc.get("project_id"):
            p = await db.projects.find_one({"id": doc["project_id"]}, {"_id": 0, "branch_id": 1})
            doc["branch_id"] = (p or {}).get("branch_id")
    if user and not system:
        await check_write_scope(e, user, doc)
    hook = HOOKS.get(key, {})
    if hook.get("before"):
        await hook["before"](doc, None, user, True)
    compute(e, doc)
    if not system:
        check_required(e, doc)
    await assign_number(e, doc)
    doc.update({"created_at": now_iso(), "created_by": user["id"] if user else None, "updated_at": now_iso(),
                "updated_by": user["id"] if user else None, "deleted": False})
    if source:
        doc["source_entity"] = source
    await db[key].insert_one(dict(doc))
    await audit(user, "create", key, doc["id"], {"code": doc.get("code"), "title": title_of(e, doc)})
    if hook.get("after"):
        await hook["after"](doc, None, user, True)
    return await _fresh(key, doc["id"], user)


async def _fresh(key, rid, user):
    e = ent(key)
    doc = await db[key].find_one({"id": rid}, {"_id": 0})
    out = strip_hidden(e, doc, hidden_tags(user))
    out["_refs"] = await ref_titles(e, [doc])
    return out


async def update_record(key, user, rid, data, *, system=False):
    e = ent(key)
    if e.get("readonly") and not system:
        raise HTTPException(403, "These records are made by the system")
    if not system and not can(user, e["module"], "w"):
        raise HTTPException(403, "You do not have permission to change this")
    old = await get_record(key, user, rid, raw=True) if not system else await db[key].find_one({"id": rid}, {"_id": 0})
    if not old:
        raise HTTPException(404, "Record not found")
    sf = status_field(e)
    if not system and sf and old.get(sf) in (e.get("locked") or []):
        raise HTTPException(409, "This record is final and can't be edited")
    if not system and e.get("approval") and old.get(sf) == e["approval"]["pending"]:
        raise HTTPException(409, "This record is waiting for approval; it can be changed after a decision")
    vals = await clean_input(e, data, user) if not system else dict(data)
    status_in = vals.pop("__status", None)
    new = {**old, **vals}
    if sf and status_in and status_in != old.get(sf) and not system:
        allowed_direct = not e.get("approval") and not e.get("actions")
        if not allowed_direct:
            raise HTTPException(409, "Use the action buttons to change the status")
        if status_in not in [s["value"] for s in e["status"]["states"]]:
            raise HTTPException(422, "Unknown status")
        new[sf] = status_in
    elif system and status_in:
        new[sf] = status_in
    if not system:
        await check_write_scope(e, user, new)
    hook = HOOKS.get(key, {})
    if hook.get("before"):
        await hook["before"](new, old, user, False)
    compute(e, new)
    if not system:
        check_required(e, new)
    changes = diff(old, new, e)
    new["updated_at"] = now_iso()
    new["updated_by"] = user["id"] if user else None
    new.pop("_refs", None)
    await db[key].replace_one({"id": rid}, new)
    if changes:
        await audit(user, "update", key, rid, {"code": new.get("code"), "changes": changes})
    if hook.get("after"):
        await hook["after"](new, old, user, False)
    return await _fresh(key, rid, user)


async def delete_record(key, user, rid, reason=""):
    e = ent(key)
    doc = await get_record(key, user, rid, raw=True)
    sf = status_field(e)
    first = e["status"]["states"][0]["value"] if sf else None
    is_draft = not sf or doc.get(sf) in (first, "draft")
    if not (can(user, e["module"], "d") or (can(user, e["module"], "w") and is_draft and doc.get("created_by") == user["id"])):
        raise HTTPException(403, "You can delete only your own drafts. Ask a manager to delete this record.")
    if sf and doc.get(sf) in (e.get("locked") or []):
        raise HTTPException(409, "This record is final and can't be deleted")
    if not (reason or "").strip():
        raise HTTPException(422, "Give a reason for deleting")
    await db[key].update_one({"id": rid}, {"$set": {"deleted": True, "deleted_reason": reason.strip()[:500],
                                                   "deleted_at": now_iso(), "deleted_by": user["id"]}})
    await db.approvals.update_many({"doc_id": rid, "status": "pending"}, {"$set": {"status": "cancelled"}})
    await audit(user, "delete", key, rid, {"code": doc.get("code"), "reason": reason.strip()[:500]})
    return {"ok": True}


# ------------------------------------------------------------------ actions and approvals
async def approval_rules():
    s = await get_settings()
    return s.get("approval_rules") or DEFAULT_APPROVAL_RULES


async def rule_for(e, doc):
    """First rule for this record type whose amount ceiling covers the amount (and whose condition holds)."""
    amt_field = (e.get("approval") or {}).get("amount")
    amount = float(doc.get(amt_field) or 0) if amt_field else 0
    for r in await approval_rules():
        if r.get("doc") != e["key"]:
            continue
        if r.get("when"):
            try:
                if not evaluate(r["when"].replace(" or ", " or ").replace(" and ", " and "), doc):
                    return None
            except Exception:
                pass
        if r.get("up_to") is None or amount <= float(r["up_to"]):
            return {**r, "amount": amount}
    return None


def available_actions(e, doc, user):
    """Buttons for this record and this person."""
    sf = status_field(e)
    if not sf:
        return []
    cur = doc.get(sf)
    out = []
    ap = e.get("approval")
    if ap and cur in ap["from"] and can(user, e["module"], "w"):
        out.append({"key": "submit", "label": "Submit for approval", "tone": "primary"})
    for k, a in (e.get("actions") or {}).items():
        if cur in a["from"] and can(user, e["module"], a.get("perm", "w")):
            out.append({"key": k, "label": a["label"], "confirm": a.get("confirm"), "reason": a.get("reason"),
                        "need": a.get("need", [])})
    return out


async def run_action(key, user, rid, action, body=None):
    body = body or {}
    e = ent(key)
    doc = await get_record(key, user, rid, raw=True)
    await check_write_scope(e, user, doc)
    sf = status_field(e)
    cur = doc.get(sf)
    if action == "submit":
        ap = e.get("approval")
        if not ap or cur not in ap["from"]:
            raise HTTPException(409, "This can't be submitted now")
        if not can(user, e["module"], "w"):
            raise HTTPException(403, "You do not have permission")
        return await submit_for_approval(e, doc, user)
    a = (e.get("actions") or {}).get(action)
    if not a:
        raise HTTPException(404, "Unknown action")
    if cur not in a["from"]:
        raise HTTPException(409, f"Not possible while the record is '{cur}'")
    if not can(user, e["module"], a.get("perm", "w")):
        raise HTTPException(403, "You do not have permission for this")
    if a.get("not_self") and doc.get("created_by") == user["id"]:
        raise HTTPException(403, "Someone else has to approve a permit you raised")
    if a.get("needs_approval_clear") and e.get("approval") and cur == "draft":
        rule = await rule_for(e, doc)
        if rule:
            raise HTTPException(409, "This needs approval first. Use 'Submit for approval'.")
    upd = {}
    for k in a.get("need", []):
        v = body.get(k, doc.get(k))
        if v in (None, "", []):
            f = REG.field(key, k)
            raise HTTPException(422, f"Fill in '{f['l'] if f else k}' first")
        if k in body:
            f = REG.field(key, k)
            upd[k] = await clean_value(f, body[k], hidden_tags(user)) if f else body[k]
    if a.get("need_lines_done"):
        lines = doc.get(a["need_lines_done"]) or []
        if any(not ln.get("done") for ln in lines):
            raise HTTPException(422, "Tick every precaution before starting work")
    if a.get("reason"):
        if not (body.get("reason") or "").strip():
            raise HTTPException(422, "Give a reason")
        upd["status_reason"] = body["reason"].strip()[:500]
    hook = HOOKS.get(key, {})
    new = {**doc, **upd, sf: a["to"]}
    if hook.get("action"):
        extra = await hook["action"](action, new, doc, user)
        if extra:
            new.update(extra)
    compute(e, new)
    new["updated_at"] = now_iso()
    new["updated_by"] = user["id"]
    await db[key].replace_one({"id": rid}, new)
    await audit(user, f"action:{action}", key, rid, {"code": doc.get("code"), "from": cur, "to": new.get(sf),
                                                       "reason": upd.get("status_reason")})
    return await _fresh(key, rid, user)


async def submit_for_approval(e, doc, user):
    ap = e["approval"]
    sf = status_field(e)
    hook = HOOKS.get(e["key"], {})
    if hook.get("before_submit"):
        await hook["before_submit"](doc, user)
    rule = await rule_for(e, doc)
    if not rule:
        upd = {sf: ap["approved"], "approved_at": now_iso(), "approved_by": None, "approval_note": "Within limits — approved automatically"}
        await db[e["key"]].update_one({"id": doc["id"]}, {"$set": upd})
        await audit(user, "auto_approved", e["key"], doc["id"], {"code": doc.get("code")})
        new = {**doc, **upd}
        if hook.get("approved"):
            await hook["approved"](new, user)
        return await _fresh(e["key"], doc["id"], user)
    nice = await nice_title(e, doc)
    appr = {"id": new_id(), "doc_entity": e["key"], "doc_id": doc["id"], "doc_code": doc.get("code") or nice,
            "title": f"{e['label']}: {nice}", "amount": rule["amount"], "requested_by": user["id"],
            "approver_roles": rule["roles"], "branch_id": doc.get("branch_id"), "status": "pending", "created_at": now_iso(),
            "created_by": user["id"], "deleted": False, "module": e["module"]}
    await db.approvals.insert_one(dict(appr))
    await db[e["key"]].update_one({"id": doc["id"]}, {"$set": {sf: ap["pending"], "approval_id": appr["id"], "submitted_at": now_iso(), "submitted_by": user["id"]}})
    await audit(user, "submitted", e["key"], doc["id"], {"code": doc.get("code"), "approvers": rule["roles"], "amount": rule["amount"]})
    await notify_roles(rule["roles"], f"Approval needed: {appr['title']}", f"Amount ₹{rule['amount']:,.0f}", "/erp/approvals",
                       kind="approval", branch_id=doc.get("branch_id"))
    return await _fresh(e["key"], doc["id"], user)


async def can_decide(user, appr):
    if appr.get("requested_by") == user["id"]:
        return False, "You can't approve your own request"
    roles = set(appr.get("approver_roles") or [])
    ok = user["role"] in roles or user["role"] == "super_admin"
    if not ok:
        # delegation: someone in an approver role handed their approvals to this person while away
        today = today_ist().isoformat()
        delegators = await db.users.find({"delegate_to": user["id"], "delegate_until": {"$gte": today}, "role": {"$in": list(roles)}},
                                         {"_id": 0, "id": 1}).to_list(10)
        ok = bool(delegators)
    if not ok:
        return False, "Your role can't approve this"
    if appr.get("branch_id") and allowed_branches(user) is not None and appr["branch_id"] not in allowed_branches(user):
        return False, "This belongs to another branch"
    return True, ""


async def decide(user, approval_id, decision, reason=""):
    appr = await db.approvals.find_one({"id": approval_id}, {"_id": 0})
    if not appr:
        raise HTTPException(404, "Approval not found")
    if appr["status"] != "pending":
        raise HTTPException(409, "Already decided")
    ok, why = await can_decide(user, appr)
    if not ok:
        raise HTTPException(403, why)
    if decision not in ("approve", "reject"):
        raise HTTPException(422, "Choose approve or reject")
    if decision == "reject" and not (reason or "").strip():
        raise HTTPException(422, "Give a reason for rejecting")
    e = ent(appr["doc_entity"])
    ap = e["approval"]
    sf = status_field(e)
    to = ap["approved"] if decision == "approve" else ap["rejected"]
    await db.approvals.update_one({"id": approval_id}, {"$set": {"status": "approved" if decision == "approve" else "rejected",
                                                                 "decided_by": user["id"], "decided_at": now_iso(), "reason": (reason or "").strip()[:500]}})
    upd = {sf: to, "approved_by" if decision == "approve" else "rejected_by": user["id"], "decided_at": now_iso(), "decision_note": (reason or "").strip()[:500]}
    await db[e["key"]].update_one({"id": appr["doc_id"]}, {"$set": upd})
    await audit(user, decision, e["key"], appr["doc_id"], {"code": appr.get("doc_code"), "reason": reason})
    await notify([appr["requested_by"]], f"{'Approved' if decision == 'approve' else 'Rejected'}: {appr['title']}", reason or "",
                 f"/erp/e/{e['key']}/{appr['doc_id']}", kind="approval")
    if decision == "approve":
        hook = HOOKS.get(e["key"], {})
        if hook.get("approved"):
            doc = await db[e["key"]].find_one({"id": appr["doc_id"]}, {"_id": 0})
            await hook["approved"](doc, user)
    return await db.approvals.find_one({"id": approval_id}, {"_id": 0})


async def history(key, user, rid):
    await get_record(key, user, rid, raw=True)
    rows = await db.audit_logs.find({"entity": key, "entity_id": rid}, {"_id": 0, "hash": 0, "prev_hash": 0}).sort("seq", -1).to_list(200)
    return rows
