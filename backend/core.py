"""Shared plumbing: database, settings, sign-in checks, permissions, branch and project scope, numbering,
tamper-evident activity log, notifications, uploads and money helpers."""
import os
import re
import json
import time
import uuid
import asyncio
import hashlib
import logging
from contextvars import ContextVar
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

import jwt  # noqa: E402
from argon2 import PasswordHasher  # noqa: E402
from argon2.exceptions import VerifyMismatchError, InvalidHashError  # noqa: E402
from fastapi import Request, HTTPException, Depends, UploadFile  # noqa: E402
from pymongo import ReturnDocument  # noqa: E402

from roles import ROLES, PERMS, PORTAL_ROLES, ALL_BRANCH_ROLES, HIDDEN_FIELD_TAGS, PROJECT_SCOPED_ROLES, OWN_SCOPE  # noqa: E402

logger = logging.getLogger("spi")
MONGO_URL = os.environ.get("MONGO_URL", "mongomock://local")
if MONGO_URL.startswith("mongomock://"):
    # In-memory database for tests, local trials and the preview export only. Never in production.
    from mongomock_motor import AsyncMongoMockClient  # noqa: E402
    client = AsyncMongoMockClient(tz_aware=True)
else:
    from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
    client = AsyncIOMotorClient(MONGO_URL, tz_aware=True)
db = client[os.environ.get("DB_NAME", "sellandiamman_power_infra")]

JWT_SECRET = os.environ.get("JWT_SECRET") or ("dev-only-" + "x" * 40)
if len(JWT_SECRET) < 32:
    logger.warning("JWT_SECRET is shorter than 32 characters; use a long random value")
JWT_ALG = "HS256"
ACCESS_MINUTES = int(os.environ.get("ACCESS_MINUTES", "30"))
REFRESH_DAYS = int(os.environ.get("REFRESH_DAYS", "14"))
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() != "false"
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR") or (ROOT / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
IST = timezone(timedelta(hours=5, minutes=30))
APP_VERSION = "2026.10.1"

_ph = PasswordHasher(time_cost=int(os.environ.get("ARGON2_TIME", "3")), memory_cost=int(os.environ.get("ARGON2_MEMORY", "65536")))


# ------------------------------------------------------------------ time and ids
def now():
    return datetime.now(timezone.utc)


def now_iso():
    return now().isoformat()


def today_ist() -> date:
    fixed = os.environ.get("FIXED_TODAY")  # the preview export pins "today" so sample dates stay meaningful
    return date.fromisoformat(fixed) if fixed else datetime.now(IST).date()


def now_ist():
    return datetime.now(IST)


def new_id():
    return str(uuid.uuid4())


def fy_of(d: date) -> str:
    """Indian financial year label for a date, e.g. 2026-10-24 -> '26-27'."""
    start = d.year if d.month >= 4 else d.year - 1
    return f"{start % 100:02d}-{(start + 1) % 100:02d}"


def pick(data: dict, allowed):
    return {k: data[k] for k in allowed if k in data}


# ------------------------------------------------------------------ money (Decimal, never floats in sums)
def D(x) -> Decimal:
    if x is None or x == "":
        return Decimal("0")
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def money(x) -> float:
    """Rounds to paise (half up) and returns a JSON-friendly number."""
    return float(D(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def rupees(x) -> float:
    return float(D(x).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


# ------------------------------------------------------------------ passwords
def hash_password(p: str) -> str:
    return _ph.hash(p)


def verify_password(p: str, h: str) -> bool:
    try:
        return _ph.verify(h or "", p)
    except (VerifyMismatchError, InvalidHashError, Exception):
        return False


PHONE_RE = re.compile(r"^(?:\+?91|0)?([6-9]\d{9})$")


def normalize_phone(raw: str, required=True) -> str:
    digits = re.sub(r"[\s\-()]", "", raw or "")
    if not digits and not required:
        return ""
    m = PHONE_RE.match(digits)
    if not m:
        raise HTTPException(422, "Enter a valid 10-digit Indian mobile number")
    return "+91" + m.group(1)


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def normalize_email(raw: str, required=False) -> str:
    v = (raw or "").strip().lower()
    if not v:
        if required:
            raise HTTPException(422, "Email is required")
        return ""
    if not EMAIL_RE.match(v):
        raise HTTPException(422, "Enter a valid email address")
    return v


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[-1].strip() if fwd else (request.client.host if request.client else "unknown")


_rate: dict = {}


def rate_limit(request: Request, key: str, limit: int, window: int):
    """In-memory limiter (one backend process)."""
    if os.environ.get("DISABLE_RATE_LIMIT") == "true":
        return
    k = f"{key}:{client_ip(request)}"
    t = time.time()
    if len(_rate) > 20000:
        for old in [x for x, v in _rate.items() if not v or v[-1] < t - 3600]:
            _rate.pop(old, None)
    hits = [h for h in _rate.get(k, []) if h > t - window]
    if len(hits) >= limit:
        raise HTTPException(429, "Too many requests. Please try again in a minute.")
    hits.append(t)
    _rate[k] = hits


# ------------------------------------------------------------------ settings
_settings_cache = {"at": 0.0, "value": None}


async def get_settings(max_age=20):
    if _settings_cache["value"] is None or time.time() - _settings_cache["at"] > max_age:
        _settings_cache["value"] = await db.settings.find_one({"id": "company"}, {"_id": 0}) or {}
        _settings_cache["at"] = time.time()
    return _settings_cache["value"]


def clear_settings_cache():
    _settings_cache["value"] = None


# ------------------------------------------------------------------ users and sign-in
REQ_BRANCH: ContextVar = ContextVar("req_branch", default=None)
PROFILE_FIELDS = ("designation", "department", "reports_to", "whatsapp", "employee_id", "joined_on")


def mfa_required_for(user, settings) -> bool:
    return user.get("role") in (settings.get("mfa_required_roles") or [])


def public_user(u, settings=None):
    out = {"id": u["id"], "email": u["email"], "name": u.get("name"), "role": u["role"],
           "role_label": ROLES.get(u["role"]), "branch_ids": u.get("branch_ids", []), "active": u.get("active"),
           "phone": u.get("phone"), "permissions": PERMS.get(u["role"], {}), "created_at": u.get("created_at"),
           "mfa_enabled": bool(u.get("mfa_enabled")), "last_login": u.get("last_login"),
           "account_id": u.get("account_id"), "vendor_id": u.get("vendor_id"), "contact_id": u.get("contact_id"),
           "partner_id": u.get("partner_id"), "employee_ref": u.get("employee_ref"),
           "portal": u["role"] in PORTAL_ROLES,
           "all_branches": u["role"] in ALL_BRANCH_ROLES or not u.get("branch_ids"),
           "hidden": HIDDEN_FIELD_TAGS.get(u["role"], []),
           **{k: u.get(k) for k in PROFILE_FIELDS}}
    if settings is not None:
        out["mfa_setup_required"] = mfa_required_for(u, settings) and not u.get("mfa_enabled")
    return out


MFA_EXEMPT = ("/api/auth/",)


def make_token(user_id, sid, minutes):
    return jwt.encode({"sub": user_id, "sid": sid, "exp": now() + timedelta(minutes=minutes), "typ": "access"},
                      JWT_SECRET, algorithm=JWT_ALG)


async def current_user(request: Request):
    token = request.cookies.get("access_token")
    auth = request.headers.get("Authorization", "")
    if not token and auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        raise HTTPException(401, "Not signed in")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid session")
    sess = await db.sessions.find_one({"sid": payload.get("sid"), "revoked": False})
    if not sess or sess["expires_at"] < now():
        raise HTTPException(401, "Session expired or signed out")
    user = await db.users.find_one({"id": payload.get("sub"), "active": True},
                                   {"_id": 0, "password_hash": 0, "mfa_secret": 0, "mfa_pending_secret": 0,
                                    "mfa_recovery": 0})
    if not user:
        raise HTTPException(401, "Account not active")
    user["sid"] = sess["sid"]
    REQ_BRANCH.set((request.headers.get("x-branch") or "").strip()[:40] or None)
    if not user.get("mfa_enabled") and not request.url.path.startswith(MFA_EXEMPT):
        if mfa_required_for(user, await get_settings()):
            raise HTTPException(403, "mfa_setup_required")
    return user


async def optional_user(request: Request):
    try:
        return await current_user(request)
    except HTTPException:
        return None


async def staff_user(request: Request):
    user = await current_user(request)
    if user["role"] in PORTAL_ROLES:
        raise HTTPException(403, "This area is for staff accounts")
    return user


def portal_dep(*roles):
    async def dep(request: Request):
        user = await current_user(request)
        if user["role"] not in roles:
            raise HTTPException(403, "This portal is not for your account")
        return user
    return dep


def can(user, module, action):
    return bool(user) and action in PERMS.get(user["role"], {}).get(module, "")


def require(module, action):
    async def dep(request: Request, user=Depends(current_user)):
        if not can(user, module, action):
            await audit(user, "permission_denied", module, None, {"action": action, "path": request.url.path})
            raise HTTPException(403, "You do not have permission for this")
        return user
    return dep


# ------------------------------------------------------------------ branch and project scope
def allowed_branches(user):
    """None = every branch; otherwise the branch ids on the person's account."""
    if not user or user.get("role") in ALL_BRANCH_ROLES or not user.get("branch_ids"):
        return None
    return list(user["branch_ids"])


def branch_filter(user, field="branch_id"):
    allowed = allowed_branches(user)
    sel = REQ_BRANCH.get()
    if sel and sel != "all" and (allowed is None or sel in allowed):
        return {field: sel}
    if allowed is not None:
        return {field: {"$in": allowed + [None]}}
    return {}


def in_branch(user, branch_id) -> bool:
    allowed = allowed_branches(user)
    return allowed is None or not branch_id or branch_id in allowed


def check_branch(user, branch_id):
    if not in_branch(user, branch_id):
        raise HTTPException(403, "You can only work with records of your own branch")


def home_branch(user):
    sel = REQ_BRANCH.get()
    if sel and sel != "all" and in_branch(user, sel):
        return sel
    return (user.get("branch_ids") or [None])[0] if user else None


async def my_project_ids(user):
    """Projects a project manager / site engineer is on (as manager or team member)."""
    rows = await db.projects.find({"deleted": {"$ne": True}, "$or": [{"manager_id": user["id"]}, {"team_ids": user["id"]}]},
                                  {"_id": 0, "id": 1}).to_list(2000)
    return [r["id"] for r in rows]


def project_scoped(user):
    return user and user.get("role") in PROJECT_SCOPED_ROLES


def own_field(user, entity):
    return OWN_SCOPE.get(user["role"], {}).get(entity) if user else None


# ------------------------------------------------------------------ numbering
async def next_seq(name):
    doc = await db.counters.find_one_and_update({"_id": name}, {"$inc": {"seq": 1}}, upsert=True,
                                                return_document=ReturnDocument.AFTER)
    return doc["seq"]


async def branch_code(branch_id):
    if not branch_id:
        return "HO"
    b = await db.branches.find_one({"id": branch_id}, {"_id": 0, "code": 1})
    return (b or {}).get("code") or "HO"


async def doc_number(doc_code, branch_id=None, on=None, width=4):
    """Series per company, branch and financial year, e.g. SPI/ERD/QT/26-27/0001 (format editable in Settings)."""
    s = await get_settings()
    fmt = s.get("number_format") or "{co}/{br}/{doc}/{fy}/{seq}"
    co = s.get("company_code") or "SPI"
    br = await branch_code(branch_id)
    fy = fy_of(on or today_ist())
    seq = await next_seq(f"{doc_code}:{br}:{fy}")
    return fmt.format(co=co, br=br, doc=doc_code, fy=fy, seq=f"{seq:0{width}d}")


async def simple_code(name, prefix, width=4, yearly=True):
    y = today_ist().year
    seq = await next_seq(f"{name}:{y}" if yearly else name)
    return f"{prefix}-{y}-{seq:0{width}d}" if yearly else f"{prefix}-{seq:0{width}d}"


# ------------------------------------------------------------------ activity log (hash chain)
def _canon(entry):
    return json.dumps({k: entry[k] for k in sorted(entry) if k not in ("_id", "hash")}, sort_keys=True, default=str,
                      separators=(",", ":"))


_audit_lock = asyncio.Lock()


async def audit(user, action, entity, entity_id, details=None, ip=None):
    """Every add, change and delete with who and when. Each entry carries the hash of the one before it, so an
    edited or removed entry breaks the chain (Settings -> Activity log -> Check the chain)."""
    async with _audit_lock:
        last = await db.audit_logs.find_one({}, {"_id": 0, "hash": 1, "seq": 1}, sort=[("seq", -1)])
        entry = {"id": new_id(), "seq": (last or {}).get("seq", 0) + 1, "prev_hash": (last or {}).get("hash", ""),
                 "user_id": user["id"] if user else None, "user_name": (user or {}).get("name") or "Website visitor",
                 "role": (user or {}).get("role"), "action": action, "entity": entity, "entity_id": entity_id,
                 "details": details or {}, "ip": ip, "at": now_iso()}
        entry["hash"] = hashlib.sha256(_canon(entry).encode()).hexdigest()
        await db.audit_logs.insert_one(dict(entry))
        return entry


async def verify_audit_chain(limit=100000):
    rows = await db.audit_logs.find({}, {"_id": 0}).sort("seq", 1).to_list(limit)
    prev = ""
    for r in rows:
        if r.get("prev_hash") != prev or hashlib.sha256(_canon(r).encode()).hexdigest() != r.get("hash"):
            return {"ok": False, "broken_at": r.get("seq"), "entries": len(rows)}
        prev = r["hash"]
    return {"ok": True, "entries": len(rows)}


# ------------------------------------------------------------------ notifications (in-app; email / WhatsApp when set up)
SMTP = {k: os.environ.get(f"SMTP_{k}", "") for k in ("HOST", "PORT", "USER", "PASSWORD", "FROM", "TLS")}


def email_configured() -> bool:
    return bool(SMTP["HOST"] and SMTP["FROM"])


def _send_email_sync(to, subject, text):
    import smtplib
    import ssl
    from email.message import EmailMessage
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = SMTP["FROM"], to, subject
    msg.set_content(text)
    port = int(SMTP["PORT"] or 587)
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(SMTP["HOST"], port, context=ctx, timeout=20) as s:
            if SMTP["USER"]:
                s.login(SMTP["USER"], SMTP["PASSWORD"])
            s.send_message(msg)
    else:
        with smtplib.SMTP(SMTP["HOST"], port, timeout=20) as s:
            if SMTP["TLS"].lower() != "none":
                s.starttls(context=ctx)
            if SMTP["USER"]:
                s.login(SMTP["USER"], SMTP["PASSWORD"])
            s.send_message(msg)


async def send_email(to, subject, text) -> str:
    if not to:
        return "skipped"
    if not email_configured():
        logger.info("[EMAIL-DEV] to=%s subject=%s", to, subject)
        return "dev_logged"
    try:
        await asyncio.to_thread(_send_email_sync, to, subject, text)
        return "sent"
    except Exception:
        logger.exception("Email to %s failed", to)
        return "failed"


WA = {k: os.environ.get(f"WHATSAPP_{k}", "") for k in ("TOKEN", "PHONE_ID", "API")}


def whatsapp_configured():
    return bool(WA["TOKEN"] and WA["PHONE_ID"])


async def send_whatsapp(phone, text) -> str:
    """WhatsApp Business Cloud API when WHATSAPP_TOKEN / WHATSAPP_PHONE_ID are set; otherwise only logged and the
    staff screens offer a click-to-chat link instead."""
    if not phone:
        return "skipped"
    if not whatsapp_configured():
        logger.info("[WHATSAPP-DEV] to=%s %s", phone, text[:120])
        return "dev_logged"
    import httpx
    url = f"{WA['API'] or 'https://graph.facebook.com/v20.0'}/{WA['PHONE_ID']}/messages"
    body = {"messaging_product": "whatsapp", "to": phone.lstrip("+"), "type": "text", "text": {"body": text[:4000]}}
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(url, json=body, headers={"Authorization": f"Bearer {WA['TOKEN']}"})
        return "sent" if r.status_code < 300 else f"failed:{r.status_code}"
    except Exception:
        logger.exception("WhatsApp to %s failed", phone)
        return "failed"


async def notify(user_ids, title, body="", link="", kind="info", dedupe=None):
    settings = await get_settings()
    out = 0
    for uid in set(filter(None, user_ids)):
        key = f"{dedupe}:{uid}" if dedupe else new_id()
        if dedupe and await db.notifications.find_one({"dedupe_key": key}):
            continue
        prefs = (await db.users.find_one({"id": uid}, {"_id": 0, "notify_prefs": 1, "email": 1}) or {})
        doc = {"id": new_id(), "user_id": uid, "title": title, "body": body, "link": link, "kind": kind,
               "read": False, "created_at": now_iso(), "dedupe_key": key}
        await db.notifications.insert_one(dict(doc))
        out += 1
        p = prefs.get("notify_prefs") or {}
        if settings.get("email_notifications") and p.get("email", True) and kind in ("approval", "alert", "assigned", "sla"):
            asyncio.create_task(send_email(prefs.get("email"), title, f"{body}\n\n{SITE_URL}{link}"))
    return out


async def notify_roles(roles, title, body="", link="", kind="info", branch_id=None, dedupe=None):
    users = await db.users.find({"role": {"$in": list(roles)}, "active": True},
                                {"_id": 0, "id": 1, "role": 1, "branch_ids": 1}).to_list(500)
    ids = [u["id"] for u in users if not branch_id or allowed_branches(u) is None or branch_id in u["branch_ids"]]
    return await notify(ids, title, body, link, kind, dedupe)


# ------------------------------------------------------------------ uploads
MAGIC = {
    "application/pdf": [b"%PDF"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG"],
    "image/webp": [b"RIFF"],
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [b"PK"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [b"PK"],
    "application/zip": [b"PK"],
    "text/csv": [b""],
    "application/vnd.ms-excel": [b"\xd0\xcf", b"PK", b""],
    "image/vnd.dwg": [b"AC10"],
    "application/acad": [b"AC10"],
}
IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp")
DOC_TYPES = tuple(MAGIC.keys())


async def save_upload(file: UploadFile, allowed=DOC_TYPES, max_bytes=20 * 1024 * 1024, public=False):
    data = await file.read()
    ctype = file.content_type or ""
    if ctype not in allowed:
        raise HTTPException(422, f"File type not allowed: {ctype or 'unknown'}")
    if len(data) > max_bytes:
        raise HTTPException(422, f"File too large (max {max_bytes // (1024 * 1024)} MB)")
    if not data or not any(data.startswith(m) for m in MAGIC[ctype]):
        raise HTTPException(422, "File content does not match its type")
    stored = new_id()
    if ctype in IMAGE_TYPES:
        data, ctype = await asyncio.to_thread(_to_webp, data)
    await asyncio.to_thread((UPLOAD_DIR / stored).write_bytes, data)
    rec = {"id": stored, "stored_name": stored, "size": len(data), "content_type": ctype, "public": public,
           "original_name": re.sub(r"[^\w.\- ]", "_", file.filename or "file")[:120], "at": now_iso()}
    await db.files.insert_one(dict(rec))
    return rec


def _to_webp(data: bytes, max_side=2000):
    """Photos are resized (longest side 2000 px) and stored as WebP to keep pages fast."""
    import io
    from PIL import Image, ImageOps
    try:
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
        im.thumbnail((max_side, max_side))
        out = io.BytesIO()
        im.convert("RGB").save(out, "WEBP", quality=80, method=4)
        return out.getvalue(), "image/webp"
    except Exception:
        return data, "image/jpeg"


def sign_file(file_id, minutes=30):
    return jwt.encode({"f": file_id, "exp": now() + timedelta(minutes=minutes), "typ": "file"}, JWT_SECRET,
                      algorithm=JWT_ALG)


def check_file_token(token):
    try:
        p = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        if p.get("typ") != "file":
            raise jwt.InvalidTokenError()
        return p["f"]
    except jwt.InvalidTokenError:
        raise HTTPException(403, "This file link has expired")
