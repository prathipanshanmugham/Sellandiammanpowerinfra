import os
import asyncio
import logging
from urllib.parse import urlparse
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from core import client, db, logger, SITE_URL, APP_VERSION
import hooks  # noqa: F401  (registers business rules on the engine)
import routes_auth
import routes_entities
import routes_public
import routes_crm
import routes_ops
import routes_dash
import routes_portal
import routes_cms
import routes_seo
import routes_vault
import scheduler
from seed import seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
app = FastAPI(title="Sellandiamman Power Infra API", version=APP_VERSION, docs_url="/api/docs", openapi_url="/api/openapi.json")
for r in (routes_auth, routes_entities, routes_public, routes_crm, routes_ops, routes_dash, routes_portal, routes_cms, routes_seo, routes_vault):
    app.include_router(r.router, prefix="/api")

ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", SITE_URL or "http://localhost:5173").split(",") if o.strip()]


@app.middleware("http")
async def security(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and not request.url.path.startswith("/api/hooks/"):
        origin = request.headers.get("origin")
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
        same = origin and urlparse(origin).netloc == host.split(",")[0].strip()
        if origin and not same and "*" not in ALLOWED_ORIGINS and origin not in ALLOWED_ORIGINS:
            return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
    try:
        resp = await call_next(request)
    except Exception:
        logger.exception("Unhandled error on %s", request.url.path)
        resp = JSONResponse({"detail": "Something went wrong. Please try again."}, status_code=500)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=(self)"
    if request.headers.get("x-forwarded-proto") == "https" or request.url.scheme == "https":
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.url.path.startswith("/api/") and not request.url.path.startswith(("/api/public", "/api/sitemap", "/api/robots", "/api/llms")):
        resp.headers.setdefault("Cache-Control", "no-store")
    return resp


app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=ALLOWED_ORIGINS, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    await seed()
    if os.environ.get("DISABLE_AUTOMATIONS") != "true":
        asyncio.create_task(scheduler.loop())


@app.get("/api/health")
async def health():
    try:
        await db.command("ping")
        return {"ok": True, "db": "ok", "version": APP_VERSION}
    except Exception:
        return JSONResponse({"ok": False, "db": "unreachable", "version": APP_VERSION}, status_code=503)


@app.on_event("shutdown")
async def shutdown():
    client.close()
