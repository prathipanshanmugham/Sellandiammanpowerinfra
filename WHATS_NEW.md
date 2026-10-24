# What's in release 2026.10.1

The first complete version: public website, staff ERP, five portals and the 24 calculators, with sample data for the preview.

## Website

- Home with a single-line-diagram hero, services, sectors, recent projects, clients, calculators, the seven-stage process and articles.
- 14 service pages (scope, standards, FAQs, related calculators and projects), 11 product groups with spec tables, 7 sector pages, projects with filters and case studies, clients, gallery, about, safety and quality, AMC plans, careers, vendor registration, guides, insights, FAQs, town pages, privacy, terms and cookies. English and Tamil for menus, buttons and forms.
- Ways to enquire: 4-step quote wizard (draft kept if the visitor leaves), site-survey booking with free slots and a calendar invite, free bill review with bill upload, tender/BOQ invite, call-back, 24×7 breakdown page (creates an urgent service ticket), calculator PDF reports and "ask an engineer", gated guide downloads, product price requests, AMC enquiries, equipment QR pages, WhatsApp and phone buttons, and webhooks for IndiaMART, JustDial, Meta and Google lead forms.
- Every enquiry carries its source, campaign tags and consent, is de-duplicated against the last 90 days, scored, routed to the right branch and person by town, and gets a 30-working-minute reply target.
- Search engines get the page title, description, structured data and page text in the first HTML; sitemap, robots and llms.txt are generated.

## Calculators (24)

Connected load and maximum demand, LT vs HT cost, bill estimator, contract demand optimiser, HT connection roadmap, transformer sizing, transformer loss capitalisation, DG sizing, UPS battery, rooftop solar, EV charger load, cable size, voltage drop, fault level, breaker selector, motor current and starter, PF correction, harmonics check, energy savings, earthing, lightning risk, lighting lux, units and formulas, document checklists. Each shows the working and the standard it follows; tariffs follow TNERC T.O. No. 6 of 2025 and can be updated in Settings (every calculator is re-run before new rates are saved).

## Staff ERP

- **Sales**: leads with timeline, score and first-reply timer, drag-and-drop pipeline, site surveys, activities, clients and contacts, referral partners, campaigns and QR codes, marketing results by source (cost a lead, conversion, ROI, calculator use).
- **Estimation and tenders**: item master, rate analysis, schedule of rates, BOQs with margin, proposals with discount approval, tender register, bank guarantees, pre-qualification documents.
- **Projects**: project hub (contract, billed, received, under/over-billing, cost to complete, forecast margin, S-curve, risks), milestones and Gantt, daily progress reports, hindrances, RFIs, drawing register with client review, measurement book to RA bill, variations, snags, handover pack PDF, labour attendance.
- **Liaison, quality, safety**: TNPDCL/CEIG application tracker, inspections, NCRs, calibrated instruments, test certificates (blocked if the instrument's calibration has lapsed), permits to work with lock-out and an authorised person, toolbox talks, PPE, incidents, man-hours.
- **Procurement and stores**: material requests, RFQs with quote comparison and award, purchase orders with approval by amount, rate contracts, GRNs into stock with cable drums and serial numbers, issues, returns and transfers, stock value at average cost.
- **Subcontractors, tools and vehicles**: work orders, running bills with retention and TDS, workers with permits and medical fitness, tools, vehicles, trips and hires.
- **Service and AMC**: installed equipment with QR codes, AMC contracts that plan their own visits, breakdown tickets with response and restore targets, renewals.
- **Finance**: invoices with GST split and e-invoice fields, UPI QR, receipts, vendor bills with 3-way match, vendor payments, expenses, bank accounts, receivables and payables ageing, GSTR-1/3B summary, TDS, profit and loss, cash flow, daily credit report, Tally export.
- **HR**: employees, attendance with location check-in, leave, payroll, advances, job applications; each person's own page with check-in, leave, payslips and security.
- **Management**: role dashboards, CEO view (health score from seven weighted pillars, alerts with owners and dates, PDF report), approvals inbox, expiry calendar, 24 reports with Excel/CSV/PDF, website editor with draft, preview, publish and 15 versions, company settings, users and roles, activity log with a tamper check, password vault for portal logins.
- 20 staff roles; branch and project scope; cost and salary fields hidden by role; nobody approves their own request.

## Portals

- **Client**: projects with progress, drawings, variations, proposals and snags to approve with a one-time code, bills with UPI payment and "I've paid", service requests with rating, AMC visits, TNPDCL/CEIG status, new requirements.
- **Consultant**: drawings to review, RFIs to answer, test reports.
- **Vendor**: RFQs to quote, purchase orders, bills, payments. **Subcontractor**: work orders, running bills, payments. **Referral partner**: referrals and commission.

## Fill in before going live

- Domain and DNS for sellandiammanpowerinfra.com; `backend/.env` secrets (JWT_SECRET, VAULT_KEY with an off-server copy, first admin).
- Real phone, WhatsApp, emergency line, email, addresses and map points for Perundurai, Erode and Coimbatore; GSTIN and electrical contractor licence; leadership and certifications (Website editor).
- Real projects, client names (with permission), testimonials, photos and gallery; the sample ones are marked "Sample" and "Illustration".
- Users for the team; approval limits; lead routing towns and teams; UPI ID and bank details; payroll statutory switches.
- SMTP and WhatsApp Business connections; lead webhook key for IndiaMART/JustDial/ads; Cloudflare Turnstile; Google Analytics and Search Console.
- Check the tariff constants against the current TNERC order and your own substation cost figures.
- Privacy, terms and cookie texts are starting templates; have them reviewed.
