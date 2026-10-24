"""Server-rendered page shell for search engines and link previews: title, description, canonical, Open Graph,
schema.org data and the page text inside the first HTML. Also /sitemap.xml, /robots.txt and /llms.txt.
Unknown pages answer 404; old links can be redirected (301) from Settings -> redirects."""
import json
import os
import re
from html import escape
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import Response, HTMLResponse, RedirectResponse

from calc import engine as CALC
from catalog import label_of
from core import db, get_settings, SITE_URL, today_ist

router = APIRouter()
SHELL = Path(os.environ.get("SITE_SHELL") or "/shell/index.html")
STATIC = {
    "/": ("Electrical contractors for LT & HT in Tamil Nadu", "HT substations, transformers, panels, cabling, earthing, solar and EV charging — designed, approved, built and maintained by Sellandiamman Power Infra."),
    "/about": ("About us", "A Sellandiamman Group company delivering LT and HT electrical infrastructure across Tamil Nadu — licensed, safety-first and engineering-led."),
    "/services": ("Services", "HT substations, LT electrification, HT & LT panels, transformers, cabling, earthing & lightning protection, DG & UPS, lighting, solar EPC, EV charging, TNPDCL & CEIG liaison, testing and AMC."),
    "/products": ("Products & solutions", "Panels, transformers, cables, switchgear, lighting, earthing, EV chargers, APFC and solar — supplied and installed."),
    "/industries": ("Industries we serve", "Factories, commercial buildings, residential towers, hospitals, education, infrastructure and government."),
    "/projects": ("Projects", "Substations, electrification and solar projects delivered across Tamil Nadu."),
    "/clients": ("Clients", "Companies and institutions that trust us with their power infrastructure."),
    "/gallery": ("Gallery", "Photos and videos from our substations, panels, cabling, solar and testing work."),
    "/tools": ("Electrical calculators & tools", "24 free calculators for LT/HT customers: load and maximum demand, LT vs HT, bills, transformer, cable size, voltage drop, fault level, PF correction, earthing, solar and more."),
    "/resources": ("Resources & guides", "Guides on HT connections, LT vs HT, transformers, approvals; FAQs, glossary and downloads."),
    "/insights": ("Insights", "Notes from our engineers on power quality, approvals, safety and energy savings."),
    "/safety-quality": ("Safety & quality", "Our HSE policy, permit-to-work system, QA/QC process and calibrated test instruments."),
    "/tenders": ("Invite us to bid", "Send your tender or BOQ and our estimation team will price it."),
    "/emergency": ("24×7 breakdown service", "Electrical breakdown at your plant or substation? Call or log it here and our duty engineer will respond."),
    "/amc": ("AMC & maintenance", "Annual maintenance contracts for substations, transformers, panels, DG sets, earthing and APFC panels."),
    "/careers": ("Careers", "Join our engineering, projects and service teams."),
    "/vendor-registration": ("Vendor & subcontractor registration", "Suppliers, subcontractors and labour contractors: register with Sellandiamman Power Infra."),
    "/contact": ("Contact us", "Call, WhatsApp or visit our branches. Book a site survey or ask for a quote."),
    "/get-quote": ("Get a quote", "Tell us about your electrical project and get a quote from our engineers."),
    "/book-survey": ("Book a site survey", "Pick a slot and our engineer will visit your site."),
    "/bill-review": ("Free electricity bill review", "Upload your last 12 bills — we check demand, power factor and tariff for savings."),
    "/privacy": ("Privacy notice", "How we collect, use and protect personal data under the Digital Personal Data Protection Act, 2023."),
    "/terms": ("Terms of use", "Terms for using this website and its calculators."),
    "/cookies": ("Cookie notice", "Which cookies this site uses and how to choose."),
    "/login": ("Client login", "Clients, consultants, vendors and partners sign in here."),
}
NOINDEX = ("/erp", "/client", "/consultant", "/vendor", "/subcontractor", "/partner", "/set-password", "/asset/", "/login")


def org_ld(s, branches):
    base = SITE_URL or "https://sellandiammanpowerinfra.com"
    org = {"@context": "https://schema.org", "@type": "Organization", "name": s.get("company_name") or "Sellandiamman Power Infra", "url": base,
           "logo": f"{base}/icon-512.png", "telephone": s.get("phone"), "email": s.get("email"),
           "parentOrganization": {"@type": "Organization", "name": "Sellandiamman Group"}}
    lbs = []
    for b in branches:
        lb = {"@context": "https://schema.org", "@type": "Electrician", "name": f"{s.get('company_name') or 'Sellandiamman Power Infra'} — {b['name']}",
              "telephone": b.get("phone"), "address": {"@type": "PostalAddress", "streetAddress": b.get("address"), "addressLocality": b.get("city"), "addressRegion": "Tamil Nadu", "addressCountry": "IN"},
              "url": base}
        if b.get("lat"):
            lb["geo"] = {"@type": "GeoCoordinates", "latitude": b["lat"], "longitude": b["lng"]}
        lbs.append(lb)
    return [org] + lbs


def crumbs(items):
    base = SITE_URL or ""
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": n + 1, "name": name, "item": base + path} for n, (name, path) in enumerate(items)]}


async def page_data(path):
    """(status, title, description, image, json-ld list, html body text)."""
    s = await get_settings()
    name = s.get("company_name") or "Sellandiamman Power Infra"
    branches = await db.branches.find({"active": {"$ne": False}, "deleted": {"$ne": True}}, {"_id": 0}).to_list(20)
    p = path.rstrip("/") or "/"
    ld = []
    if p in STATIC:
        t, d = STATIC[p]
        ld = org_ld(s, branches) if p in ("/", "/contact", "/about") else [crumbs([("Home", "/"), (t, p)])]
        body = f"<h1>{escape(t)}</h1><p>{escape(d)}</p>"
        if p == "/services":
            for sv in await db.services.find({"published": True, "deleted": {"$ne": True}}, {"_id": 0}).sort("order", 1).to_list(50):
                body += f'<h2><a href="/services/{sv["slug"]}">{escape(sv["title"])}</a></h2><p>{escape(sv.get("summary") or "")}</p>'
        if p == "/tools":
            for tl in CALC.TOOLS["tools"]:
                body += f'<h2><a href="/tools/{tl["slug"]}">{escape(tl["title"])}</a></h2><p>{escape(tl["summary"])}</p>'
        if p == "/resources":
            faqs = await db.faqs.find({"published": True, "deleted": {"$ne": True}}, {"_id": 0}).sort("order", 1).to_list(60)
            if faqs:
                ld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": f["question"], "acceptedAnswer": {"@type": "Answer", "text": f["answer"]}} for f in faqs]})
                body += "".join(f"<h3>{escape(f['question'])}</h3><p>{escape(f['answer'])}</p>" for f in faqs)
        return 200, t, d, None, ld, body
    m = re.fullmatch(r"/services/([\w-]+)", p)
    if m:
        sv = await db.services.find_one({"slug": m.group(1), "published": True, "deleted": {"$ne": True}}, {"_id": 0})
        if sv:
            ld = [{"@context": "https://schema.org", "@type": "Service", "name": sv["title"], "description": sv.get("summary"), "areaServed": "Tamil Nadu",
                   "provider": {"@type": "Organization", "name": name}}, crumbs([("Home", "/"), ("Services", "/services"), (sv["title"], p)])]
            if sv.get("faqs"):
                ld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in sv["faqs"] if f.get("q")]})
            return 200, sv.get("seo_title") or sv["title"], sv.get("seo_description") or sv.get("summary"), None, ld, f"<h1>{escape(sv['title'])}</h1><p>{escape(sv.get('summary') or '')}</p><div>{escape(sv.get('body') or '')}</div>"
    m = re.fullmatch(r"/industries/([\w-]+)", p)
    if m:
        x = await db.industries.find_one({"slug": m.group(1), "published": True, "deleted": {"$ne": True}}, {"_id": 0})
        if x:
            return 200, f"Electrical works for {x['name']}", x.get("summary"), None, [crumbs([("Home", "/"), ("Industries", "/industries"), (x["name"], p)])], f"<h1>{escape(x['name'])}</h1><p>{escape(x.get('summary') or '')}</p>"
    m = re.fullmatch(r"/projects/([\w-]+)", p)
    if m:
        x = await db.projects.find_one({"slug": m.group(1), "publish": True, "deleted": {"$ne": True}}, {"_id": 0})
        if x:
            t = x.get("public_title") or x["name"]
            img = f"/api/public/media/{x['cover']['id']}" if x.get("cover") else None
            return 200, t, x.get("public_summary"), img, [crumbs([("Home", "/"), ("Projects", "/projects"), (t, p)])], f"<h1>{escape(t)}</h1><p>{escape(x.get('public_summary') or '')}</p><p>{escape(x.get('solution') or '')}</p>"
    m = re.fullmatch(r"/tools/([\w-]+)", p)
    if m and m.group(1) in CALC.SPEC:
        tl = CALC.SPEC[m.group(1)]
        ld = [{"@context": "https://schema.org", "@type": "WebApplication", "name": tl["title"], "applicationCategory": "UtilitiesApplication", "operatingSystem": "Any",
               "offers": {"@type": "Offer", "price": "0", "priceCurrency": "INR"}, "description": tl["summary"]}, crumbs([("Home", "/"), ("Tools", "/tools"), (tl["title"], p)])]
        return 200, tl["title"], f"{tl['summary']} Free calculator — {tl['basis']}.", None, ld, f"<h1>{escape(tl['title'])}</h1><p>{escape(tl['summary'])}</p><p>Basis: {escape(tl['basis'])}</p>"
    m = re.fullmatch(r"/insights/([\w-]+)", p)
    if m:
        x = await db.insights.find_one({"slug": m.group(1), "status": {"$in": ["published", "scheduled"]}, "deleted": {"$ne": True}}, {"_id": 0})
        if x and (x.get("publish_at") or "") <= today_ist().isoformat() + "T23:59":
            ld = [{"@context": "https://schema.org", "@type": "Article", "headline": x["title"], "datePublished": x.get("publish_at"), "author": {"@type": "Person", "name": x.get("author") or name}},
                  crumbs([("Home", "/"), ("Insights", "/insights"), (x["title"], p)])]
            return 200, x.get("seo_title") or x["title"], x.get("seo_description") or x.get("excerpt"), None, ld, f"<h1>{escape(x['title'])}</h1><div>{escape(x.get('body') or '')}</div>"
    m = re.fullmatch(r"/guides/([\w-]+)", p)
    if m:
        x = await db.downloads.find_one({"slug": m.group(1), "published": True, "deleted": {"$ne": True}}, {"_id": 0})
        if x:
            return 200, x["title"], x.get("summary"), None, [crumbs([("Home", "/"), ("Resources", "/resources"), (x["title"], p)])], f"<h1>{escape(x['title'])}</h1><div>{escape(x.get('body') or x.get('summary') or '')}</div>"
    m = re.fullmatch(r"/electrical-contractors-in/([\w-]+)", p)
    if m:
        x = await db.town_pages.find_one({"slug": m.group(1), "published": True, "deleted": {"$ne": True}}, {"_id": 0})
        if x and await db.projects.count_documents({"publish": True, "town": {"$regex": f"^{re.escape(x['town'])}$", "$options": "i"}}):
            t = f"Electrical contractors in {x['town']}"
            return 200, t, x.get("intro") or f"LT and HT electrical works in {x['town']}.", None, [crumbs([("Home", "/"), (t, p)])], f"<h1>{escape(t)}</h1><p>{escape(x.get('intro') or '')}</p>"
    if p.startswith(NOINDEX):
        return 200, name, None, None, [], ""
    return 404, "Page not found", "This page doesn't exist.", None, [], "<h1>Page not found</h1>"


@router.get("/seo/page")
async def seo_page(request: Request):
    path = request.headers.get("x-original-uri") or "/"
    path = path.split("?")[0]
    s = await get_settings()
    for r in s.get("redirects") or []:
        if r.get("from") == path and r.get("to"):
            return RedirectResponse(r["to"], status_code=301)
    if not SHELL.exists():
        return Response("shell missing", status_code=503)
    status, title, desc, img, ld, body = await page_data(path)
    name = s.get("company_name") or "Sellandiamman Power Infra"
    full = f"{title} | {name}" if title != name else name
    base = SITE_URL or ""
    html = SHELL.read_text()
    head = [f"<title>{escape(full)}</title>", f'<meta name="description" content="{escape(desc or "")}">' if desc else "",
            f'<link rel="canonical" href="{base}{path}">', f'<meta property="og:title" content="{escape(full)}">',
            f'<meta property="og:description" content="{escape(desc or "")}">', f'<meta property="og:url" content="{base}{path}">',
            f'<meta property="og:image" content="{base}{img or "/og-image.jpg"}">', '<meta property="og:type" content="website">',
            '<meta name="twitter:card" content="summary_large_image">']
    if path.startswith(NOINDEX) or status == 404:
        head.append('<meta name="robots" content="noindex">')
    for x in ld:
        js = json.dumps(x, ensure_ascii=False).replace("</", "<" + chr(92) + "/")
        head.append(f'<script type="application/ld+json" id="ssr-jsonld">{js}</script>')
    html = re.sub(r"<title>.*?</title>", "", html, flags=re.S)
    html = re.sub(r'<meta name="description"[^>]*>', "", html)
    html = html.replace("</head>", "\n".join(h for h in head if h) + "\n</head>", 1)
    if body:
        html = html.replace('<div id="root"></div>', f'<div id="root"><div id="ssr" style="max-width:860px;margin:40px auto;padding:0 16px;font-family:sans-serif">{body}</div></div>', 1)
    return HTMLResponse(html, status_code=status, headers={"Cache-Control": "no-cache"})


@router.get("/robots.txt")
async def robots():
    base = SITE_URL or ""
    return Response(f"User-agent: *\nAllow: /\nDisallow: /erp/\nDisallow: /client/\nDisallow: /consultant/\nDisallow: /vendor/\nDisallow: /subcontractor/\nDisallow: /partner/\nDisallow: /api/\n\nSitemap: {base}/sitemap.xml\n",
                    media_type="text/plain")


@router.get("/sitemap.xml")
async def sitemap():
    base = SITE_URL or ""
    urls = list(STATIC.keys())
    urls = [u for u in urls if u not in ("/login",)]
    urls += [f"/services/{x['slug']}" for x in await db.services.find({"published": True, "deleted": {"$ne": True}}, {"_id": 0, "slug": 1}).to_list(100)]
    urls += [f"/industries/{x['slug']}" for x in await db.industries.find({"published": True, "deleted": {"$ne": True}}, {"_id": 0, "slug": 1}).to_list(100)]
    urls += [f"/projects/{x['slug']}" for x in await db.projects.find({"publish": True, "deleted": {"$ne": True}}, {"_id": 0, "slug": 1}).to_list(500) if x.get("slug")]
    urls += [f"/tools/{t['slug']}" for t in CALC.TOOLS["tools"]]
    t = today_ist().isoformat()
    urls += [f"/insights/{x['slug']}" for x in await db.insights.find({"status": {"$in": ["published", "scheduled"]}, "publish_at": {"$lte": t + "T23:59"}, "deleted": {"$ne": True}}, {"_id": 0, "slug": 1}).to_list(500)]
    urls += [f"/guides/{x['slug']}" for x in await db.downloads.find({"published": True, "kind": "guide", "deleted": {"$ne": True}}, {"_id": 0, "slug": 1}).to_list(100)]
    for x in await db.town_pages.find({"published": True, "deleted": {"$ne": True}}, {"_id": 0}).to_list(100):
        if await db.projects.count_documents({"publish": True, "town": {"$regex": f"^{re.escape(x['town'])}$", "$options": "i"}}):
            urls.append(f"/electrical-contractors-in/{x['slug']}")
    body = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"  <url><loc>{base}{u}</loc></url>\n" for u in urls) + "</urlset>\n"
    return Response(body, media_type="application/xml")


@router.get("/llms.txt")
async def llms():
    s = await get_settings()
    name = s.get("company_name") or "Sellandiamman Power Infra"
    lines = [f"# {name}", "", f"> {STATIC['/'][1]}", "", "## Services"]
    for sv in await db.services.find({"published": True, "deleted": {"$ne": True}}, {"_id": 0}).sort("order", 1).to_list(50):
        lines.append(f"- [{sv['title']}]({SITE_URL}/services/{sv['slug']}): {sv.get('summary') or ''}")
    lines += ["", "## Calculators"] + [f"- [{t['title']}]({SITE_URL}/tools/{t['slug']}): {t['summary']}" for t in CALC.TOOLS["tools"]]
    lines += ["", "## Contact", f"- Phone: {s.get('phone') or ''}", f"- Email: {s.get('email') or ''}", f"- [Get a quote]({SITE_URL}/get-quote)"]
    return Response("\n".join(lines) + "\n", media_type="text/plain")
