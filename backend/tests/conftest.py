"""The API runs in memory (mongomock) with the sample data, once for the whole test run."""
import asyncio
import os
import sys
from pathlib import Path

import pytest

os.environ.update({"MONGO_URL": "mongomock://test", "DB_NAME": "test", "JWT_SECRET": "test-secret-" + "x" * 40, "DISABLE_AUTOMATIONS": "true",
                   "COOKIE_SECURE": "false", "ARGON2_TIME": "1", "ARGON2_MEMORY": "8192", "DISABLE_RATE_LIMIT": "true", "SEED_DEMO": "true",
                   "DEMO_OTP_ANY": "true", "FIXED_TODAY": "2026-10-24", "VAULT_KEY": "00" * 32})
os.environ.setdefault("UPLOAD_DIR", str(Path(__file__).resolve().parent / ".uploads"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DOMAIN = "demo.sellandiammanpowerinfra.test"
PW = "Demo@12345"


@pytest.fixture(scope="session")
def loop():
    lp = asyncio.new_event_loop()
    yield lp
    lp.close()


@pytest.fixture(scope="session")
def app(loop):
    import server
    loop.run_until_complete(server.startup())
    return server.app


class Client:
    """A signed-in browser: keeps cookies, runs requests on the shared loop."""

    def __init__(self, app, loop):
        import httpx
        self.loop = loop
        self.c = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test.local", timeout=60)

    def req(self, method, path, **kw):
        return self.loop.run_until_complete(self.c.request(method, "/api" + path, **kw))

    def get(self, path, **kw):
        return self.req("GET", path, **kw)

    def post(self, path, json=None, **kw):
        return self.req("POST", path, json=json, **kw)

    def patch(self, path, json=None, **kw):
        return self.req("PATCH", path, json=json, **kw)

    def login(self, local, portal=False):
        r = self.post("/auth/login", {"email": f"{local}@{DOMAIN}", "password": PW, "portal": portal})
        assert r.status_code == 200, r.text
        return r.json()["user"]


@pytest.fixture()
def client(app, loop):
    return Client(app, loop)


@pytest.fixture()
def as_role(app, loop):
    def make(local, portal=False):
        c = Client(app, loop)
        c.login(local, portal)
        return c
    return make


@pytest.fixture()
def db(app):
    from core import db as _db
    return _db


@pytest.fixture()
def run(loop):
    return lambda coro: loop.run_until_complete(coro)
