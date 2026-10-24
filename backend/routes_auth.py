"""Sign-in, 2-step sign-in (TOTP), sessions, set-password links, users and roles, notifications."""
import io
import secrets
import hashlib
from datetime import timedelta
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel

import pyotp
from core import (db, now, now_iso, new_id, hash_password, verify_password, make_token, ACCESS_MINUTES, REFRESH_DAYS,
                  COOKIE_SECURE, rate_limit, client_ip, current_user, staff_user, require, audit, public_user, get_settings,
                  clear_settings_cache, normalize_email, normalize_phone, send_email, SITE_URL, today_ist, can)
from roles import ROLES, PORTAL_ROLES, STAFF_ROLES, MODULES, PERMS

router = APIRouter()
LOCK_AFTER = 8
LOCK_MINUTES = 15


class LoginIn(BaseModel):
    email: str
    password: str
    code: str | None = None
    portal: bool | None = None


def set_cookies(resp: Response, token: str, sid: str):
    resp.set_cookie("access_token", token, httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=ACCESS_MINUTES * 60, path="/")
    resp.set_cookie("refresh_sid", sid, httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=REFRESH_DAYS * 86400, path="/api/auth")


async def start_session(user, request: Request, resp: Response):
    sid = secrets.token_urlsafe(24)
    await db.sessions.insert_one({"sid": sid, "user_id": user["id"], "created_at": now_iso(), "expires_at": now() + timedelta(days=REFRESH_DAYS),
                                  "revoked": False, "ip": client_ip(request), "agent": (request.headers.get("user-agent") or "")[:200]})
    token = make_token(user["id"], sid, ACCESS_MINUTES)
    set_cookies(resp, token, sid)
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login": now_iso(), "failed": 0}})
    return token


def totp_ok(secret, code):
    try:
        return bool(secret) and pyotp.TOTP(secret).verify(str(code or "").replace(" ", ""), valid_window=1)
    except Exception:
        return False


@router.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response):
    rate_limit(request, "login", 10, 60)
    email = (body.email or "").strip().lower()
    u = await db.users.find_one({"email": email})
    if u and u.get("locked_until") and u["locked_until"] > now_iso():
        raise HTTPException(423, "Too many wrong attempts. Try again in 15 minutes or reset your password.")
    if not u or not u.get("active") or not verify_password(body.password or "", u.get("password_hash") or ""):
        if u:
            failed = int(u.get("failed") or 0) + 1
            upd = {"failed": failed}
            if failed >= LOCK_AFTER:
                upd["locked_until"] = (now() + timedelta(minutes=LOCK_MINUTES)).isoformat()
            await db.users.update_one({"id": u["id"]}, {"$set": upd})
        await audit(None, "login_failed", "users", u["id"] if u else None, {"email": email[:80]}, client_ip(request))
        raise HTTPException(401, "Email or password is wrong")
    if body.portal is True and u["role"] not in PORTAL_ROLES:
        raise HTTPException(403, "Staff sign in from the staff login page (link at the bottom of the website)")
    if body.portal is False and u["role"] in PORTAL_ROLES:
        raise HTTPException(403, "Customers and partners sign in from the Login button at the top of the website")
    if u.get("mfa_enabled"):
        if not body.code:
            return {"mfa_required": True}
        ok = totp_ok(u.get("mfa_secret"), body.code)
        if not ok:
            h = hashlib.sha256(str(body.code).strip().encode()).hexdigest()
            if h in (u.get("mfa_recovery") or []):
                await db.users.update_one({"id": u["id"]}, {"$pull": {"mfa_recovery": h}})
                ok = True
        if not ok:
            raise HTTPException(401, "That code didn't work. Use the 6-digit code from your authenticator app.")
    await start_session(u, request, response)
    await audit(u, "login", "users", u["id"], {}, client_ip(request))
    return {"user": public_user(u, await get_settings())}


@router.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    sid = request.cookies.get("refresh_sid")
    sess = await db.sessions.find_one({"sid": sid, "revoked": False}) if sid else None
    if not sess or sess["expires_at"] < now():
        raise HTTPException(401, "Please sign in again")
    u = await db.users.find_one({"id": sess["user_id"], "active": True})
    if not u:
        raise HTTPException(401, "Account not active")
    set_cookies(response, make_token(u["id"], sid, ACCESS_MINUTES), sid)
    return {"ok": True}


@router.post("/auth/logout")
async def logout(request: Request, response: Response):
    sid = request.cookies.get("refresh_sid")
    if sid:
        await db.sessions.update_one({"sid": sid}, {"$set": {"revoked": True}})
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_sid", path="/api/auth")
    return {"ok": True}


@router.get("/auth/me")
async def me(user=Depends(current_user)):
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {"user": public_user(u, await get_settings())}


class PwIn(BaseModel):
    current: str
    new: str


def check_strength(p):
    if len(p or "") < 10 or p.lower() == p or not any(c.isdigit() for c in p):
        raise HTTPException(422, "Use at least 10 characters with a capital letter and a number")


@router.post("/auth/password")
async def change_password(body: PwIn, user=Depends(current_user)):
    u = await db.users.find_one({"id": user["id"]})
    if not verify_password(body.current, u.get("password_hash") or ""):
        raise HTTPException(401, "Current password is wrong")
    check_strength(body.new)
    await db.users.update_one({"id": user["id"]}, {"$set": {"password_hash": hash_password(body.new)}})
    await db.sessions.update_many({"user_id": user["id"], "sid": {"$ne": user["sid"]}}, {"$set": {"revoked": True}})
    await audit(user, "password_changed", "users", user["id"])
    return {"ok": True}


# ---------------------------------------------------------------- set-password links (invites and resets)
async def make_link(user_id, purpose="invite", days=7):
    token = secrets.token_urlsafe(32)
    await db.password_tokens.insert_one({"hash": hashlib.sha256(token.encode()).hexdigest(), "user_id": user_id, "purpose": purpose,
                                         "expires_at": (now() + timedelta(days=days)).isoformat(), "used": False})
    return f"{SITE_URL}/set-password?token={token}"


class ForgotIn(BaseModel):
    email: str


@router.post("/auth/forgot")
async def forgot(body: ForgotIn, request: Request):
    rate_limit(request, "forgot", 5, 300)
    u = await db.users.find_one({"email": (body.email or "").strip().lower(), "active": True})
    if u:
        link = await make_link(u["id"], "reset", days=1)
        await send_email(u["email"], "Set a new password — Sellandiamman Power Infra",
                         f"Hello {u.get('name')},\n\nUse this link within 24 hours to set a new password:\n{link}\n\nIf you didn't ask for this, ignore this email.")
    return {"ok": True, "message": "If that email has an account, a link to set a new password is on its way."}


class SetPwIn(BaseModel):
    token: str
    password: str


@router.post("/auth/set-password")
async def set_password(body: SetPwIn, request: Request):
    rate_limit(request, "setpw", 10, 300)
    h = hashlib.sha256((body.token or "").encode()).hexdigest()
    t = await db.password_tokens.find_one({"hash": h, "used": False})
    if not t or t["expires_at"] < now_iso():
        raise HTTPException(400, "This link has expired. Ask us for a new one.")
    check_strength(body.password)
    await db.users.update_one({"id": t["user_id"]}, {"$set": {"password_hash": hash_password(body.password), "failed": 0, "locked_until": None}})
    await db.password_tokens.update_one({"hash": h}, {"$set": {"used": True}})
    u = await db.users.find_one({"id": t["user_id"]}, {"_id": 0})
    await audit(u, "password_set", "users", u["id"])
    return {"ok": True, "portal": u["role"] in PORTAL_ROLES}


# ---------------------------------------------------------------- 2-step sign-in
def qr_svg(uri):
    import qrcode
    import qrcode.image.svg
    img = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode()


@router.post("/auth/mfa/setup")
async def mfa_setup(user=Depends(current_user)):
    secret = pyotp.random_base32()
    await db.users.update_one({"id": user["id"]}, {"$set": {"mfa_pending_secret": secret}})
    uri = pyotp.TOTP(secret).provisioning_uri(name=user["email"], issuer_name="Sellandiamman Power Infra")
    return {"secret": secret, "otpauth_uri": uri, "qr_svg": qr_svg(uri)}


class CodeIn(BaseModel):
    code: str


@router.post("/auth/mfa/enable")
async def mfa_enable(body: CodeIn, user=Depends(current_user)):
    u = await db.users.find_one({"id": user["id"]})
    if not totp_ok(u.get("mfa_pending_secret"), body.code):
        raise HTTPException(422, "That code didn't match. Check the time on your phone and try again.")
    codes = [secrets.token_hex(4) for _ in range(8)]
    await db.users.update_one({"id": user["id"]}, {"$set": {"mfa_enabled": True, "mfa_secret": u["mfa_pending_secret"],
                                                            "mfa_pending_secret": None,
                                                            "mfa_recovery": [hashlib.sha256(c.encode()).hexdigest() for c in codes]}})
    await audit(user, "mfa_enabled", "users", user["id"])
    return {"ok": True, "recovery_codes": codes}


@router.post("/auth/mfa/disable")
async def mfa_disable(body: CodeIn, user=Depends(current_user)):
    u = await db.users.find_one({"id": user["id"]})
    if not totp_ok(u.get("mfa_secret"), body.code):
        raise HTTPException(422, "That code didn't match")
    s = await get_settings()
    if user["role"] in (s.get("mfa_required_roles") or []):
        raise HTTPException(409, "2-step sign-in is required for your role")
    await db.users.update_one({"id": user["id"]}, {"$set": {"mfa_enabled": False, "mfa_secret": None, "mfa_recovery": []}})
    await audit(user, "mfa_disabled", "users", user["id"])
    return {"ok": True}


# ---------------------------------------------------------------- sessions
@router.get("/auth/sessions")
async def sessions(user=Depends(current_user)):
    rows = await db.sessions.find({"user_id": user["id"], "revoked": False, "expires_at": {"$gt": now()}}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return [{"sid": r["sid"][:8], "current": r["sid"] == user["sid"], "created_at": r["created_at"], "ip": r.get("ip"), "agent": r.get("agent")} for r in rows]


@router.post("/auth/sessions/sign-out-others")
async def sign_out_others(user=Depends(current_user)):
    r = await db.sessions.update_many({"user_id": user["id"], "sid": {"$ne": user["sid"]}}, {"$set": {"revoked": True}})
    return {"signed_out": r.modified_count}


# ---------------------------------------------------------------- notifications & preferences
@router.get("/notifications")
async def notifications(user=Depends(current_user), unread: bool = False):
    q = {"user_id": user["id"]}
    if unread:
        q["read"] = False
    rows = await db.notifications.find(q, {"_id": 0}).sort("created_at", -1).to_list(60)
    count = await db.notifications.count_documents({"user_id": user["id"], "read": False})
    return {"items": rows, "unread": count}


@router.post("/notifications/read")
async def notifications_read(body: dict, user=Depends(current_user)):
    q = {"user_id": user["id"]}
    if body.get("ids"):
        q["id"] = {"$in": body["ids"][:200]}
    await db.notifications.update_many(q, {"$set": {"read": True}})
    return {"ok": True}


@router.put("/me/preferences")
async def my_prefs(body: dict, user=Depends(current_user)):
    allowed = {k: bool(v) for k, v in (body.get("notify_prefs") or {}).items() if k in ("email", "whatsapp", "digest")}
    upd = {"notify_prefs": allowed}
    if "delegate_to" in body:
        upd["delegate_to"] = body.get("delegate_to") or None
        upd["delegate_until"] = body.get("delegate_until") or None
    await db.users.update_one({"id": user["id"]}, {"$set": upd})
    return {"ok": True}


# ---------------------------------------------------------------- users & roles (admin)
@router.get("/roles")
async def roles(user=Depends(staff_user)):
    return {"roles": [{"value": k, "label": v, "portal": k in PORTAL_ROLES} for k, v in ROLES.items()],
            "modules": MODULES, "perms": PERMS}


@router.get("/users")
async def list_users(user=Depends(require("users", "r")), role: str = "", q: str = "", portal: bool | None = None):
    f = {}
    if role:
        f["role"] = role
    if portal is not None:
        f["role"] = {"$in": list(PORTAL_ROLES)} if portal else {"$nin": list(PORTAL_ROLES)}
    if q:
        import re
        rx = {"$regex": re.escape(q[:40]), "$options": "i"}
        f["$or"] = [{"name": rx}, {"email": rx}]
    rows = await db.users.find(f, {"_id": 0, "password_hash": 0, "mfa_secret": 0, "mfa_pending_secret": 0, "mfa_recovery": 0}).sort("name", 1).to_list(1000)
    return [public_user(u) for u in rows]


@router.get("/users/lookup")
async def users_lookup(user=Depends(staff_user), q: str = ""):
    """Names for pickers (any staff member may see colleagues' names)."""
    f = {"active": True, "role": {"$nin": list(PORTAL_ROLES)}}
    if q:
        import re
        f["name"] = {"$regex": re.escape(q[:40]), "$options": "i"}
    rows = await db.users.find(f, {"_id": 0, "id": 1, "name": 1, "role": 1, "branch_ids": 1, "designation": 1}).sort("name", 1).to_list(500)
    return [{**r, "role_label": ROLES.get(r["role"])} for r in rows]


class UserIn(BaseModel):
    name: str
    email: str
    role: str
    phone: str | None = None
    branch_ids: list[str] = []
    designation: str | None = None
    department: str | None = None
    account_id: str | None = None
    vendor_id: str | None = None
    contact_id: str | None = None
    partner_id: str | None = None
    active: bool = True


@router.post("/users")
async def create_user(body: UserIn, user=Depends(require("users", "w"))):
    if body.role not in ROLES:
        raise HTTPException(422, "Unknown role")
    if body.role == "super_admin" and user["role"] != "super_admin":
        raise HTTPException(403, "Only a super admin can add another super admin")
    email = normalize_email(body.email, required=True)
    if await db.users.find_one({"email": email}):
        raise HTTPException(409, "There is already a login with this email")
    links = {"client": "account_id", "consultant": "contact_id", "vendor": "vendor_id", "subcontractor": "vendor_id", "partner": "partner_id"}
    if body.role in links and not getattr(body, links[body.role]):
        raise HTTPException(422, "Link this login to its client, contact, vendor or partner record")
    doc = {"id": new_id(), "name": body.name.strip()[:80], "email": email, "role": body.role,
           "phone": normalize_phone(body.phone, required=False) if body.phone else None, "branch_ids": body.branch_ids,
           "designation": body.designation, "department": body.department, "account_id": body.account_id, "vendor_id": body.vendor_id,
           "contact_id": body.contact_id, "partner_id": body.partner_id, "active": body.active, "created_at": now_iso(),
           "created_by": user["id"], "password_hash": None, "mfa_enabled": False}
    await db.users.insert_one(dict(doc))
    link = await make_link(doc["id"], "invite", days=7)
    portal = body.role in PORTAL_ROLES
    await send_email(email, "Your Sellandiamman Power Infra login",
                     f"Hello {doc['name']},\n\nA login has been made for you{' to follow your projects and requests' if portal else ''}.\n"
                     f"Set your password with this link (valid for 7 days):\n{link}\n\nSellandiamman Power Infra")
    await audit(user, "user_created", "users", doc["id"], {"email": email, "role": body.role})
    return {"user": public_user(doc), "set_password_link": link}


@router.patch("/users/{uid}")
async def update_user(uid: str, body: dict, user=Depends(require("users", "w"))):
    u = await db.users.find_one({"id": uid})
    if not u:
        raise HTTPException(404, "User not found")
    upd = {}
    for k in ("name", "designation", "department", "branch_ids", "active", "account_id", "vendor_id", "contact_id", "partner_id", "phone"):
        if k in body:
            upd[k] = body[k]
    if "role" in body:
        if body["role"] not in ROLES:
            raise HTTPException(422, "Unknown role")
        if "super_admin" in (body["role"], u["role"]) and user["role"] != "super_admin":
            raise HTTPException(403, "Only a super admin can change super admin logins")
        upd["role"] = body["role"]
    if uid == user["id"] and upd.get("active") is False:
        raise HTTPException(409, "You can't switch off your own login")
    await db.users.update_one({"id": uid}, {"$set": upd})
    if upd.get("active") is False or "role" in upd:
        await db.sessions.update_many({"user_id": uid}, {"$set": {"revoked": True}})
    await audit(user, "user_updated", "users", uid, {k: v for k, v in upd.items() if k != "phone"})
    u = await db.users.find_one({"id": uid}, {"_id": 0})
    return public_user(u)


@router.post("/users/{uid}/link")
async def user_link(uid: str, user=Depends(require("users", "w"))):
    u = await db.users.find_one({"id": uid})
    if not u:
        raise HTTPException(404, "User not found")
    link = await make_link(uid, "invite", days=7)
    await audit(user, "set_password_link", "users", uid)
    return {"set_password_link": link}


@router.post("/users/{uid}/reset-mfa")
async def reset_mfa(uid: str, user=Depends(require("users", "w"))):
    await db.users.update_one({"id": uid}, {"$set": {"mfa_enabled": False, "mfa_secret": None, "mfa_recovery": []}})
    await audit(user, "mfa_reset", "users", uid)
    return {"ok": True}
