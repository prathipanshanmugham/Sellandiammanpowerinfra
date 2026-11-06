# Update, 6 Nov 2026: white header logo, phone layout and sturdier calculators

- **Header logo stays white**: on phones with dark mode for websites (Chrome's "darken websites", Samsung, MIUI) the header used to turn black and the dark "SELLANDIAMMAN" name disappeared. The site now tells browsers it is light only, so the header stays white with the grey and yellow SA mark, the same as the browser-tab icon. The header is solid white (no see-through blur), and the logo and buttons scale down to fit a 320px phone; the language code next to the globe shows from 400px up.
- **Phones**: checked every website page, ERP screen, portal and dialog (441 screens) at 320, 375 and 390px wide: nothing scrolls sideways and no text runs off the screen or gets cut. Long e-mail addresses wrap on the login and "My profile" screens.
- **Calculators**:
  - Clearing a box (for example the present power factor in PF correction) no longer freezes the page. Every box now has a sensible range, and a box that's empty or out of range turns red with a message saying what to enter. The last good result stays on screen, greyed out, until it's fixed.
  - Typing is cleaned as you go (letters and a second decimal point are dropped, at most 15 characters). Very small results show four significant figures instead of rounding to 0.
  - Boxes that don't apply to the chosen option are hidden: maximum demand, contract demand, peak and night share and power factor apply to HT tariffs only, and connected load to LT commercial and LT industrial only.
  - Results now show the input that decides the answer, so changing any box visibly changes the result:
    - Bill estimator: the power-factor incentive or penalty row.
    - Contract demand: the demand charge rate.
    - DG sizing: the size needed for motor starting.
    - UPS battery: the size needed before rounding up.
    - Rooftop solar: the three limits (consumption, roof area, sanctioned load).
    - Cable size: the voltage-drop limit.
    - PF correction: the non-linear load share behind the reactor advice.
  - The browser and the server give identical results and identical error messages on 159 recorded cases, including 35 typing and edge cases.

# Update, 5 Nov 2026: AI agents and MCP

- **Settings → AI agents & MCP** (director and super admin): make agents that let Claude, or any MCP app, work in the ERP. Each one works as one staff login (that person's role, branches and hidden fields), is read only or read & write, can have an end date, and can be paused, given a new key or revoked. Six ready-made jobs: business analyst, sales assistant, project monitor, procurement, collections, service desk. Keys are shown once and stored as hashes.
- **MCP endpoint** `https://www.sellandiammanpowerinfra.com/api/mcp` with 14 tools (who am I, today's position, record types and fields, search, list/open/add/change records, status actions, reports, the CEO, finance, stock, project and pipeline screens) and four ready-made prompts. Every call runs through the same permission checks and business rules as the app and shows in the activity log as "Person (AI agent: Name)".
- Agents never delete, decide approvals, change logins, keys or settings, publish the website, open the vault, or check in, apply for leave or run payroll. 240 calls a minute per agent; every call is listed under Activity for 90 days.
- Setup steps for Claude, Claude Code and other apps are on the screen and in `docs/AI_AGENTS.md`.

# Update, 5 Nov 2026: cleaner phone layout and new icons

- **Phones, staff ERP and portals**: no screen scrolls sideways any more (the dashboards and "My profile" did). Tables with three or more columns show one block per row (the first column as the title, then label and value), so codes, dates and names no longer break across three lines; this covers stock, service desk, finance, ageing, line items, reports' lists and every portal table. Approval cards and the CEO view's "Needs your attention" keep their text full width with the amount and buttons underneath. The dashboard's quick-add buttons sit in an even two-column grid; report dates are a From/To pair with the filter below.
- **Phones, website**: the menu opens with the main pages first, the 14 services folded under "Services", a 24×7 breakdown row, the language picker, and the quote and login buttons fixed at the bottom; the page behind no longer scrolls. Calculator load rows put Qty, kW and demand factor side by side; the "See result" bar no longer wraps; the home page's figures have room between columns.
- **Icons**: the browser-tab icon is the SA mark on a transparent background (grey and yellow, lighter in dark mode), with a favicon.ico fallback. Phone home-screen icons are the SA mark on white, kept clear of Android's round masks; a web manifest points to them. `python scripts/brand/build_brand.py --icons` rebuilds just the icons.

# What's in release 2026.10.1

The first complete version: public website, staff ERP, five portals and the 24 calculators, with sample data for the preview.

## Website

- Home with a single-line-diagram hero, services, sectors, recent projects, clients, calculators, the seven-stage process and articles.
- 14 service pages (scope, standards, FAQs, related calculators and projects), 11 product groups with spec tables, 7 sector pages, projects with filters and case studies, clients, gallery, about, safety and quality, AMC plans, careers, vendor registration, guides, insights, FAQs, town pages, privacy, terms and cookies.
- Ways to enquire: 4-step quote wizard (draft kept if the visitor leaves), site-survey booking with free slots and a calendar invite, free bill review with bill upload, tender/BOQ invite, call-back, 24×7 breakdown page (creates an urgent service ticket), calculator PDF reports and "ask an engineer", gated guide downloads, product price requests, AMC enquiries, equipment QR pages, WhatsApp and phone buttons, and webhooks for IndiaMART, JustDial, Meta and Google lead forms.
- Every enquiry carries its source, campaign tags and consent, is de-duplicated against the last 90 days, scored, routed to the right branch and person by town, and gets a 30-working-minute reply target.
- 20 languages, picked from the globe button in the header: English, Arabic, Chinese, French, German, Japanese, Portuguese, Russian and Spanish, plus Hindi, Bengali, Marathi, Telugu, Tamil, Gujarati, Urdu, Kannada, Odia, Malayalam and Punjabi. Menus, buttons, forms, headings and the main page text switch; long articles, service and product detail, calculator inputs and the legal pages stay in English. Arabic and Urdu run right to left. The first visit follows the browser's language; the choice is remembered. The staff ERP and the portals stay in English.
- Look: matches Sellandiamman Estates — white pages, slate navy (#0F172A) bands and footer, near-square corners, Outfit headings and Plus Jakarta Sans text — with the logo's yellow (#FFC400) as the accent where Estates uses red. Text on yellow is always navy. The header steps down to a menu button when a language needs more room. The website stays light even when a phone, browser or host page is in dark mode; only the staff ERP has a dark option.
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
- The translations are AI-written first drafts; have a native speaker check the languages you care about most (Tamil and Hindi first). They live in `frontend/src/lib/locales/<code>.json`, keyed by the English text.
