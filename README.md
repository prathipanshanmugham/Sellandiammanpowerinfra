# Sellandiamman Power Infra

Website, staff ERP and customer portals for Sellandiamman Power Infra, the LT and HT electrical contracting and consulting company of the Sellandiamman Group.

One app, three faces:

- **Public website** at `/`: services, products, industries, projects with case studies, clients, gallery, about, safety and quality, AMC plans, careers, vendor registration, guides, insights and FAQs, plus **24 LT/HT calculators** with worked results and PDF reports. Twelve ways in for enquiries: quote wizard, site-survey booking with time slots, free bill review, tender/BOQ invite, call-back, 24×7 breakdown line, calculator reports, gated guide downloads, product price requests, AMC enquiries, equipment QR codes and lead webhooks (IndiaMART, JustDial, Meta and Google lead forms, WhatsApp).
- **Staff ERP** at `/erp`: 94 record types across sales, estimation, tenders, projects, liaison (TNPDCL/CEIG), quality and testing, procurement, stores, tools and vehicles, subcontractors and labour, safety, service and AMC, finance, HR and payroll, documents and the website itself. 20 staff roles with branch, project and field-level permissions; approvals by amount; a CEO view with a health score and alerts; 24 reports; a hash-chained activity log; a password vault.
- **Portals** at `/client`, `/consultant`, `/vendor`, `/subcontractor`, `/partner`: each sees only their own projects, drawings, bills, RFQs, work orders or referrals, with OTP-confirmed approvals.

## How it's built

| Part | What | Where |
| --- | --- | --- |
| API | FastAPI, MongoDB (motor), argon2 passwords, JWT cookie sessions, TOTP 2-step sign-in, ReportLab letterhead PDFs, openpyxl exports | `backend/` |
| Registry | Every record type defined once (fields, formulas, numbering, status flows, approvals, portal rules); the API, the staff screens and the preview all read it | `backend/registry.py` |
| Business rules | Per-record hooks: lead scoring and routing, BOQ rates, RA bills from the measurement book, GRN to stock and cable drums, 3-way match, SLA timers, AMC visit plans, attendance geofence | `backend/hooks.py` |
| Calculators | One spec (`tools.json`, `constants.json` with the TNERC tariff order) and two identical engines, Python and TypeScript, checked against 124 recorded cases | `backend/calc/`, `frontend/src/calc/` |
| Frontend | React 18, Vite, Tailwind, Radix, TanStack Query, Recharts | `frontend/` |
| Hosted preview | The real API runs once in memory with sample data; its answers are saved and replayed in the browser | `demo/`, `frontend/src/demo/` |

## Run it locally

```bash
# API with sample data, in memory (no MongoDB needed)
cd backend
pip install -r requirements-dev.txt
MONGO_URL=mongomock://dev SEED_DEMO=true DEMO_OTP_ANY=true DISABLE_RATE_LIMIT=true COOKIE_SECURE=false \
  CORS_ORIGINS=http://localhost:5173 uvicorn server:app --port 8001

# website + ERP + portals
cd frontend
npm install
npm run dev            # http://localhost:5173
```

Sample logins: `director@demo.sellandiammanpowerinfra.test` (and `sales`, `pm`, `site`, `accounts`, `store`, `technician`, `hr`, … one per role), `client@…`, `vendor@…`, `consultant@…`, `subcontractor@…`, `partner@…`. Password `Demo@12345`. With `DEMO_OTP_ANY=true` any 6-digit approval code except 000000 works.

## Checks

```bash
cd backend && python -m pytest tests -q            # 146 tests: calculators, sign-in, scope, approvals, GST, intake, PDFs, audit chain
cd frontend && npm run test:calc                    # TypeScript calculators match Python (124/124)
cd frontend && npm run build
./scripts/build_preview.sh                          # the hosted preview in demo/build/site
```

After editing a calculator: `python scripts/sync_shared.py` copies the spec to the frontend and rewrites the parity cases.

## Deploy

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md): Docker Compose (MongoDB, API, Caddy, nightly backups) behind the existing nginx on the Hostinger VPS, port 127.0.0.1:8090.

What's in this release and what to fill in before going live: [WHATS_NEW.md](WHATS_NEW.md).
