"""Website editor (site texts, sections, announcement bar, numbers) with draft / publish and the last 15 versions,
plus company settings: approval limits, numbering, calculator constants, SLA targets, integrations and payroll switches."""
import copy
from fastapi import APIRouter, Depends, HTTPException

from calc import engine as CALC
from core import db, require, staff_user, now_iso, new_id, audit, get_settings, clear_settings_cache, today_ist
from roles import DEFAULT_APPROVAL_RULES, ROLES
import os

router = APIRouter()
SITE_KEYS = ("company_name", "short_name", "tagline", "phone", "whatsapp", "email", "emergency_phone", "address", "gstin", "elb_licence", "licences",
             "website", "socials", "trust", "hero", "about", "process", "announcement", "home_sections", "map_url", "gbp_url", "founded_year",
             "leadership", "values", "timeline", "safety", "group_companies", "seo", "assistant_enabled", "amc_plans", "certifications", "survey_slots",
             "town_list", "brochure_file")
KEEP = 15


@router.get("/cms/site")
async def cms_site(user=Depends(require("cms", "r"))):
    s = await get_settings()
    draft = await db.site_draft.find_one({"id": "draft"}, {"_id": 0})
    live = {k: s.get(k) for k in SITE_KEYS if k in s}
    return {"live": live, "draft": (draft or {}).get("values") or live, "has_draft": bool(draft), "draft_by": (draft or {}).get("by"), "draft_at": (draft or {}).get("at")}


@router.put("/cms/site")
async def cms_save_draft(body: dict, user=Depends(require("cms", "w"))):
    vals = {k: v for k, v in (body.get("values") or {}).items() if k in SITE_KEYS}
    await db.site_draft.replace_one({"id": "draft"}, {"id": "draft", "values": vals, "by": user["name"], "at": now_iso()}, upsert=True)
    return {"ok": True}


@router.post("/cms/publish")
async def cms_publish(user=Depends(require("cms", "p"))):
    draft = await db.site_draft.find_one({"id": "draft"}, {"_id": 0})
    if not draft:
        raise HTTPException(409, "No changes to publish")
    s = await get_settings()
    await db.site_versions.insert_one({"id": new_id(), "values": {k: s.get(k) for k in SITE_KEYS if k in s}, "at": now_iso(), "by": user["name"], "note": "Before publish"})
    await db.settings.update_one({"id": "company"}, {"$set": draft["values"]}, upsert=True)
    await db.site_draft.delete_one({"id": "draft"})
    old = await db.site_versions.find({}, {"_id": 0, "id": 1}).sort("at", -1).skip(KEEP).to_list(1000)
    if old:
        await db.site_versions.delete_many({"id": {"$in": [o["id"] for o in old]}})
    clear_settings_cache()
    await audit(user, "website_published", "settings", "company")
    return {"ok": True}


@router.delete("/cms/draft")
async def cms_discard(user=Depends(require("cms", "w"))):
    await db.site_draft.delete_one({"id": "draft"})
    return {"ok": True}


@router.get("/cms/versions")
async def cms_versions(user=Depends(require("cms", "r"))):
    return await db.site_versions.find({}, {"_id": 0, "values": 0}).sort("at", -1).to_list(KEEP)


@router.post("/cms/versions/{vid}/restore")
async def cms_restore(vid: str, user=Depends(require("cms", "p"))):
    v = await db.site_versions.find_one({"id": vid}, {"_id": 0})
    if not v:
        raise HTTPException(404, "Version not found")
    await db.site_draft.replace_one({"id": "draft"}, {"id": "draft", "values": v["values"], "by": user["name"], "at": now_iso(), "restored_from": v["at"]}, upsert=True)
    return {"ok": True, "message": "Loaded into the draft — check it and publish."}


@router.get("/cms/preview")
async def cms_preview(user=Depends(require("cms", "r"))):
    """Site settings as the draft would publish them (the website shows this with ?preview=1 for staff)."""
    s = await get_settings()
    draft = await db.site_draft.find_one({"id": "draft"}, {"_id": 0})
    return {**{k: s.get(k) for k in SITE_KEYS if k in s}, **((draft or {}).get("values") or {})}


# ------------------------------------------------------------------ company settings
SETTINGS_KEYS = ("company_code", "number_format", "fy_start_month", "mfa_required_roles", "email_notifications", "first_response_minutes", "working_hours",
                 "geofence_m", "sla", "upi_id", "bank_details", "payroll_statutory", "tally_company", "turnstile_site_key", "ga4_id", "first_response_text",
                 "approval_rules")


@router.get("/settings")
async def get_company_settings(user=Depends(require("settings", "r"))):
    s = await get_settings()
    out = {k: s.get(k) for k in SETTINGS_KEYS}
    out["approval_rules"] = s.get("approval_rules") or DEFAULT_APPROVAL_RULES
    out["integrations"] = {"email": bool(os.environ.get("SMTP_HOST")), "whatsapp": bool(os.environ.get("WHATSAPP_TOKEN")),
                           "turnstile": bool(os.environ.get("TURNSTILE_SECRET")), "lead_webhooks": bool(os.environ.get("LEAD_WEBHOOK_KEY")),
                           "vault": bool(os.environ.get("VAULT_KEY")), "ga4": bool(os.environ.get("GA4_ID") or s.get("ga4_id"))}
    out["roles"] = [{"value": k, "label": v} for k, v in ROLES.items()]
    return out


@router.put("/settings")
async def put_company_settings(body: dict, user=Depends(require("settings", "w"))):
    upd = {k: v for k, v in body.items() if k in SETTINGS_KEYS}
    if "approval_rules" in upd:
        rules = []
        for r in upd["approval_rules"][:80]:
            if not r.get("doc") or not r.get("roles"):
                continue
            rules.append({"doc": str(r["doc"]), "up_to": float(r["up_to"]) if r.get("up_to") not in (None, "") else None,
                          "roles": [x for x in r["roles"] if x in ROLES], "when": (r.get("when") or None)})
        upd["approval_rules"] = rules
    if "number_format" in upd and "{seq}" not in (upd["number_format"] or ""):
        raise HTTPException(422, "The number format must contain {seq}")
    await db.settings.update_one({"id": "company"}, {"$set": upd}, upsert=True)
    clear_settings_cache()
    await audit(user, "settings_updated", "settings", "company", {"keys": list(upd)})
    return await get_company_settings(user)


@router.get("/settings/calc-constants")
async def get_constants(user=Depends(require("settings", "r"))):
    s = await get_settings()
    cc = s.get("calc_constants") or {}
    hist = await db.calc_constants_history.find({}, {"_id": 0, "values": 0}).sort("at", -1).to_list(20)
    return {"defaults": CALC.DEFAULTS, "overrides": cc.get("values") or {}, "effective_from": cc.get("effective_from"), "reference": cc.get("reference"),
            "merged": CALC.merged_constants(cc.get("values")), "history": hist}


@router.put("/settings/calc-constants")
async def put_constants(body: dict, user=Depends(require("settings", "w"))):
    vals = body.get("values") or {}
    unknown = [k for k in vals if k not in CALC.DEFAULTS]
    if unknown:
        raise HTTPException(422, f"Unknown constant: {unknown[0]}")
    # check the calculators still run with the new values
    try:
        for slug in CALC.SPEC:
            CALC.run(slug, {}, vals)
    except Exception as ex:
        raise HTTPException(422, f"These values break a calculator ({slug}): {ex}")
    s = await get_settings()
    prev = s.get("calc_constants") or {}
    await db.calc_constants_history.insert_one({"id": new_id(), "values": prev.get("values") or {}, "effective_from": prev.get("effective_from"),
                                                "reference": prev.get("reference"), "at": now_iso(), "by": user["name"]})
    cc = {"values": vals, "effective_from": body.get("effective_from") or today_ist().isoformat(), "reference": body.get("reference") or ""}
    if vals.get("tariffs") or vals.get("rates_as_of"):
        cc["values"]["rates_as_of"] = vals.get("rates_as_of") or cc["effective_from"]
    await db.settings.update_one({"id": "company"}, {"$set": {"calc_constants": cc}}, upsert=True)
    clear_settings_cache()
    await audit(user, "calc_constants_updated", "settings", "company", {"keys": list(vals), "effective_from": cc["effective_from"]})
    return await get_constants(user)


@router.get("/branches/all")
async def all_branches(user=Depends(staff_user)):
    return await db.branches.find({"deleted": {"$ne": True}}, {"_id": 0}).sort("order", 1).to_list(100)
