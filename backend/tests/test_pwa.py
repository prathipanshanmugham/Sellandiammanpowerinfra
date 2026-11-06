"""The installable app: manifests, service worker and the page shell."""
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
PUBLIC = Path(__file__).resolve().parents[2] / "frontend" / "public"


def test_manifests_are_installable():
    for name, start in (("site", "/"), ("erp", "/erp"), ("portal", "/login")):
        m = json.loads((PUBLIC / f"{name}.webmanifest").read_text())
        assert m["display"] == "standalone" and m["name"] and m["short_name"] and m["id"]
        assert urlsplit(m["start_url"]).path == start
        assert urlsplit(m["start_url"]).path.startswith(m["scope"]), name  # the start page is inside the app
        sizes = {i["sizes"] for i in m["icons"] if i.get("purpose", "any") == "any"}
        assert {"192x192", "512x512"} <= sizes, name
        assert any(i.get("purpose") == "maskable" for i in m["icons"]), name
        for i in m["icons"] + [ic for sc in m.get("shortcuts", []) for ic in sc.get("icons", [])]:
            assert (PUBLIC / urlsplit(i["src"]).path.lstrip("/")).exists(), i["src"]
        for sc in m.get("shortcuts", []):
            assert urlsplit(sc["url"]).path.startswith(m["scope"]), sc


def test_service_worker_never_caches_the_api():
    sw = (PUBLIC / "sw.js").read_text()
    assert 'url.pathname.startsWith("/api/")) return' in sw
    assert "/offline.html" in sw and (PUBLIC / "offline.html").exists()


def test_app_shell_names_the_installable_app():
    """The page shell points ERP and portal pages at their own installable app; the website keeps its own."""
    import routes_seo
    shell = (PUBLIC.parent / "index.html").read_text()
    erp = routes_seo.app_shell(shell, "/erp/approvals")
    assert "/erp.webmanifest?v=3" in erp and 'content="SPI ERP"' in erp
    portal = routes_seo.app_shell(shell, "/client/bills")
    assert "/portal.webmanifest?v=3" in portal and 'content="SPI Portal"' in portal
    assert routes_seo.app_shell(shell, "/tools/cable-size") == shell
    assert routes_seo.app_shell(shell, "/erpx") == shell  # only the /erp area itself
