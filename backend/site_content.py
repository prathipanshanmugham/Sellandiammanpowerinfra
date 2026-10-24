"""Starting website content: services, industries, products, FAQs, guides and terms. Editable in the staff app
(Website menu). Written as plain descriptions of the work — no claims, numbers or client names."""

SERVICES = [
    {"slug": "ht-substations", "service_key": "ht_substation", "icon": "zap", "title": "HT substations (11 / 22 / 33 kV)",
     "summary": "Complete indoor and outdoor substations — design, CEIG approval, supply, erection, testing and energisation with TNPDCL.",
     "body": "We build HT substations for factories, hospitals, commercial buildings and residential towers, from a single 11 kV pole-mounted "
             "structure to multi-transformer 33 kV yards. Our engineers size the transformer and protection from your load, prepare the "
             "single-line diagram and layout for CEIG approval, and coordinate the line extension and metering with TNPDCL.\n\n"
             "On site we handle civil foundations, cable trenches, HT panel or RMU, transformer erection, LT panel, earthing and fencing — under "
             "a permit-to-work system with an authorised person for every HT activity. Each substation is handed over with test certificates, "
             "as-built drawings and an optional maintenance contract.",
     "scope": ["Load study and transformer sizing", "Single-line diagram, layout and earthing design", "CEIG drawing approval and inspection",
               "Transformer, HT panel / VCB / RMU and LT panel supply", "Civil works, cable trenches and fencing", "Protection relay settings and testing",
               "Energisation with TNPDCL", "Handover documents and AMC"],
     "standards": [["IS 2026", "Power transformers"], ["IS 1180", "Distribution transformers"], ["IS 3043", "Earthing"], ["CEA Safety Regulations 2023", "Measures relating to safety and electric supply"]],
     "faqs": [{"q": "How long does a new HT substation take?", "a": "Typically 3 to 6 months from application to energisation, depending on TNPDCL line work and CEIG approvals. Our HT connection roadmap tool shows each step."},
              {"q": "Do you handle TNPDCL and CEIG paperwork?", "a": "Yes. Our liaison team prepares and files the applications, drawings and test reports, and follows up until energisation."}],
     "sectors": ["factory", "hospital", "commercial", "residential"], "order": 1},
    {"slug": "lt-electrification", "service_key": "lt_electrification", "icon": "plug", "title": "LT electrification",
     "summary": "Internal and external electrification for plants, buildings and campuses — power, lighting, cable trays, earthing and distribution.",
     "body": "From a new factory shed to a 20-storey residential tower, we design and install the low-tension distribution: main and sub-distribution "
             "boards, rising mains or bus ducts, cable trays, power and lighting circuits, socket outlets and final earthing.\n\nDesigns follow "
             "IS 732 and the National Building Code, with voltage drop and fault level checked for every feeder. We coordinate with your architect "
             "and MEP consultant, and test every circuit before handover.",
     "scope": ["Distribution design and load balancing", "Main LT panel, sub-DBs and bus ducts", "Cable trays, conduits and raceways",
               "Power, lighting and small-power circuits", "Equipment and system earthing", "Insulation and continuity testing"],
     "standards": [["IS 732", "Code of practice for electrical wiring installations"], ["NBC 2016 Part 8", "Building services — electrical"], ["IS 3043", "Earthing"]],
     "faqs": [{"q": "Can you work with our architect's drawings?", "a": "Yes. We check them for load, voltage drop and fault level and propose changes where needed before execution."}],
     "sectors": ["factory", "commercial", "residential", "education"], "order": 2},
    {"slug": "ht-lt-panels", "service_key": "ht_lt_panels", "icon": "server", "title": "HT & LT panels",
     "summary": "VCB and RMU panels, PCC, MCC, APFC and distribution boards — specified, supplied, installed and commissioned.",
     "body": "We specify panels around your load and fault level, source them from approved makes, inspect them at the factory, and install and "
             "commission them at site with relay settings and interlocks tested.\n\nFor existing plants we retrofit old panels, add APFC panels with "
             "detuned reactors, and upgrade protection.",
     "scope": ["HT VCB panels and RMUs", "Power control centres (PCC) with ACBs", "Motor control centres (MCC)", "APFC panels with detuned reactors",
               "Factory acceptance testing", "Installation, termination and commissioning"],
     "standards": [["IS/IEC 61439", "Low-voltage switchgear assemblies"], ["IS/IEC 62271-200", "HV metal-enclosed switchgear"], ["IS/IEC 60947", "LV switchgear"]],
     "faqs": [{"q": "Which panel makes do you work with?", "a": "We supply leading national and international makes and approved panel builders; we suggest makes to suit your specification and budget."}],
     "sectors": ["factory", "commercial", "hospital"], "order": 3},
    {"slug": "transformers", "service_key": "transformers", "icon": "box", "title": "Transformer supply & erection",
     "summary": "Oil-filled and dry-type distribution transformers up to 2500 kVA, with testing, erection and oil filtration.",
     "body": "We help you choose the rating and energy-efficiency level by total owning cost, not just price, then supply, transport, erect and test "
             "the transformer. Pre-commissioning tests include IR and PI, ratio, winding resistance, magnetic balance, vector group and oil BDV.",
     "scope": ["Rating and loss-level selection", "Oil-filled (ONAN) and cast-resin dry type", "Transport, unloading and erection", "Oil filtration and BDV testing",
               "Pre-commissioning tests", "Replacement and capacity upgrades"],
     "standards": [["IS 1180", "Outdoor type oil-immersed distribution transformers"], ["IS 2026", "Power transformers"], ["IS 11171", "Dry-type power transformers"]],
     "faqs": [{"q": "Oil-filled or dry type?", "a": "Dry-type (cast resin) is preferred inside buildings for fire safety; oil-filled is common and economical outdoors."}],
     "sectors": ["factory", "commercial", "residential"], "order": 4},
    {"slug": "cabling", "service_key": "cabling", "icon": "cable", "title": "HT & LT cabling",
     "summary": "Cable sizing, laying, jointing and termination for HT and LT feeders, with HV / VLF testing.",
     "body": "We size cables for current, voltage drop and short-circuit withstand, then lay them in trenches, trays or ducts with proper spacing and "
             "markers. Our certified jointers make HT straight-through joints and terminations, and every HT cable is tested before energisation.\n\n"
             "Cable drums are tracked drum by drum, so you see exactly how much cable went into your site.",
     "scope": ["Cable sizing with derating", "Trenching, sand cushioning and protection", "Tray and duct installation", "HT jointing and terminations",
               "HV / VLF and insulation testing", "Cable route markers and as-built routes"],
     "standards": [["IS 7098", "XLPE insulated cables"], ["IS 1554", "PVC insulated cables"], ["IS 1255", "Installation and maintenance of power cables"]],
     "faqs": [{"q": "Can you check if our existing cable is undersized?", "a": "Yes — our cable size and voltage drop tools give a quick check, and our engineers can measure loads and temperatures on site."}],
     "sectors": ["factory", "infrastructure", "commercial"], "order": 5},
    {"slug": "earthing-lightning-protection", "service_key": "earthing_lps", "icon": "anchor", "title": "Earthing & lightning protection",
     "summary": "Earthing design, pits, grids and lightning protection systems — measured, documented and maintained.",
     "body": "We measure soil resistivity on site, design the earthing to reach the target resistance, and install pipe, plate or chemical electrodes, "
             "strips and grids. For buildings and plants we assess lightning risk and install air terminals, down conductors, test joints and surge "
             "protection.",
     "scope": ["Soil resistivity measurement", "Earthing design and pit installation", "Substation earth grids", "Lightning risk assessment",
               "Air terminals, down conductors and test joints", "Surge protection devices", "Periodic earth resistance testing"],
     "standards": [["IS 3043", "Code of practice for earthing"], ["IS/IEC 62305", "Protection against lightning"]],
     "faqs": [{"q": "What earth resistance should we aim for?", "a": "Typically 1 Ω or less for HT substations and up to about 5 Ω for LT equipment earths. Our earthing tool estimates the pits you need."}],
     "sectors": ["factory", "commercial", "hospital", "infrastructure"], "order": 6},
    {"slug": "dg-ups", "service_key": "dg_ups", "icon": "fuel", "title": "DG sets & UPS",
     "summary": "Backup power sized for your running load and motor starting, with AMF panels, changeover and UPS.",
     "body": "We size DG sets for running load and motor starting, install them with acoustic enclosures, exhaust and fuel systems, and integrate "
             "them through AMF and synchronising panels. For critical loads we add online UPS systems with battery banks sized for your backup time.",
     "scope": ["DG sizing and selection", "AMF and synchronising panels", "Changeover and load management", "Online UPS and battery banks", "Exhaust, fuel and earthing", "Load testing"],
     "standards": [["ISO 8528", "Generating sets"], ["CPCB IV+", "Emission norms for DG sets"]],
     "faqs": [{"q": "Why does motor starting matter for DG size?", "a": "A large motor draws several times its running current when starting; the DG must handle that step without a deep voltage dip."}],
     "sectors": ["hospital", "commercial", "factory"], "order": 7},
    {"slug": "street-area-lighting", "service_key": "street_lighting", "icon": "lamp", "title": "Street & area lighting",
     "summary": "LED street, high-mast and area lighting for campuses, layouts, roads and industrial yards.",
     "body": "We design lighting to the right lux levels, then install poles, high masts, LED fixtures, feeder pillars and timers or smart controls. "
             "Lighting layouts and lux calculations are shared before installation.",
     "scope": ["Lux calculations and layouts", "Poles, high masts and foundations", "LED fixtures and feeder pillars", "Timers and smart controls", "Cabling and earthing"],
     "standards": [["IS 1944", "Code of practice for lighting of public thoroughfares"], ["IS 3646", "Interior illumination"]],
     "faqs": [], "sectors": ["infrastructure", "government", "residential"], "order": 8},
    {"slug": "solar-epc", "service_key": "solar_epc", "icon": "sun", "title": "Solar EPC",
     "summary": "Rooftop and ground-mounted solar plants with net or gross metering — delivered with our group's solar company.",
     "body": "Together with Sensoper Controls and Renewables, our group's solar company, we size solar plants from your consumption, roof area and "
             "sanctioned load, handle the TNPDCL metering application, and install, commission and maintain the plant.",
     "scope": ["Feasibility and generation estimate", "Structure design and installation", "Modules, inverters and protection", "Net / gross metering application", "Monitoring and O&M"],
     "standards": [["IS 16221", "PV inverters — safety"], ["IEC 61215", "PV module design qualification"], ["MNRE ALMM", "Approved list of models and manufacturers"]],
     "faqs": [{"q": "How big a plant can I install?", "a": "Usually up to your sanctioned load or contract demand, and limited by shadow-free roof area. Our solar tool shows the limiting factor."}],
     "sectors": ["factory", "commercial", "education", "home"], "order": 9},
    {"slug": "ev-charging", "service_key": "ev_charging", "icon": "plug-zap", "title": "EV charging",
     "summary": "AC and DC charging stations for fleets, apartments, offices and public sites — with load planning and metering.",
     "body": "We plan the added demand, check whether your connection needs an upgrade, and install AC and DC chargers with protection, metering and "
             "load management. For public stations we can apply for a separate EV tariff connection.",
     "scope": ["Charging load planning", "Connection upgrade or separate EV metering", "AC and DC charger installation", "Load management", "Earthing and protection"],
     "standards": [["CEA EV charging guidelines", "Technical standards for EV charging"], ["IS 17017", "EV conductive charging systems"]],
     "faqs": [], "sectors": ["residential", "commercial", "infrastructure"], "order": 10},
    {"slug": "tnpdcl-ceig-liaison", "service_key": "liaison", "icon": "stamp", "title": "TNPDCL & CEIG liaison",
     "summary": "New LT and HT services, load changes, tariff changes, name transfers, CEIG approvals and energisation — handled end to end.",
     "body": "Approvals are often the slowest part of a power project. Our liaison officers prepare the documents and drawings, file the applications, "
             "pay fees against receipts, follow up with the section office and CEIG, and show you each stage in your client portal.",
     "scope": ["New LT and HT service connections", "Load and contract demand changes", "Tariff changes and name transfers", "CEIG drawing approval and inspection",
               "Solar net metering", "Energisation and meter fixing"],
     "standards": [["TN Electricity Supply Code", "TNERC"], ["CEA Safety Regulations 2023", "Approval of installations"]],
     "faqs": [{"q": "Can you take over an application that is already filed?", "a": "Yes. Share the application number and documents; we'll review the status and follow it through."}],
     "sectors": ["factory", "commercial", "residential", "home"], "order": 11},
    {"slug": "testing-commissioning", "service_key": "testing", "icon": "activity", "title": "Testing & commissioning",
     "summary": "Pre-commissioning tests for transformers, cables, panels, relays and earthing — with calibrated instruments and certificates.",
     "body": "Every test is done with calibrated instruments and recorded on a digital test format, then issued as a certificate you can download. "
             "We test new installations, and existing ones before audits, insurance renewals or CEIG inspections.",
     "scope": ["Transformer tests (IR, ratio, winding resistance, BDV, vector group)", "HT cable HV / VLF tests", "CT / PT and relay testing", "Breaker timing",
               "Earth resistance and continuity", "Thermography and power-quality studies"],
     "standards": [["IS 2026", "Transformer tests"], ["IEC 60255", "Measuring relays and protection"], ["IS 3043", "Earthing"]],
     "faqs": [{"q": "Are your instruments calibrated?", "a": "Yes. A certificate can only be issued in our system if the instrument used was within its calibration date."}],
     "sectors": ["factory", "commercial", "hospital"], "order": 12},
    {"slug": "amc-om", "service_key": "amc", "icon": "calendar-check", "title": "AMC and O&M",
     "summary": "Annual maintenance for substations, transformers, panels, DG sets, earthing and APFC — with scheduled visits and breakdown response.",
     "body": "Our AMCs list the equipment covered, the number of visits and the response and restore times. Every visit follows a checklist, records "
             "readings and photos, and ends with a signed service report in your portal. Breakdown calls are tracked against their targets.",
     "scope": ["Preventive maintenance visits", "Transformer oil testing and filtration", "Panel cleaning and torque checks", "Relay and breaker testing",
               "Earth pit testing", "Thermography", "24×7 breakdown response"],
     "standards": [["IS 10028", "Code of practice for transformers — maintenance"], ["CEA Safety Regulations 2023", "Periodic inspection"]],
     "faqs": [{"q": "What response time do you commit to?", "a": "Each AMC states its response and restore times; urgent breakdowns typically have a 4-hour response target."}],
     "sectors": ["factory", "commercial", "hospital", "residential"], "order": 13},
    {"slug": "energy-audit", "service_key": "energy_audit", "icon": "gauge", "title": "Energy audits & power quality",
     "summary": "Find savings in demand charges, power factor, harmonics, lighting and motors — measured, not guessed.",
     "body": "We review 12 months of bills, log the load and power quality, and list savings with costs and payback: contract demand, power factor "
             "correction, harmonic filtering, LED lighting, VFDs and efficient motors.",
     "scope": ["Bill and tariff review", "Power-quality logging", "Contract demand optimisation", "PF correction and harmonic study", "Lighting and motor savings", "Report with payback"],
     "standards": [["IEEE 519", "Harmonic control"], ["BEE guidelines", "Energy audits"]],
     "faqs": [{"q": "Is the bill review free?", "a": "Yes — upload your last 12 bills and we'll point out demand, power factor and tariff savings."}],
     "sectors": ["factory", "commercial", "hospital", "education"], "order": 14},
]

INDUSTRIES = [
    {"slug": "factories", "name": "Factories & industry", "sector": "factory", "order": 1,
     "summary": "Substations, PCC / MCC panels, cabling, APFC and earthing for textile, engineering, food and process plants.",
     "needs": ["Reliable HT supply and protection", "Low losses and good power factor", "Shutdown-friendly execution", "Fast breakdown response"]},
    {"slug": "commercial-buildings", "name": "Commercial buildings", "sector": "commercial", "order": 2,
     "summary": "Offices, malls and hotels — substations, rising mains, DG and UPS backup, lighting and EV charging.",
     "needs": ["Indoor dry-type transformers", "DG and UPS backup", "Coordinated MEP execution", "Energy-efficient lighting"]},
    {"slug": "residential-towers", "name": "Residential towers & apartments", "sector": "residential", "order": 3,
     "summary": "HT substations, metering rooms, rising mains, common-area lighting, lifts and EV charging for apartment projects.",
     "needs": ["Individual metering for flats", "TNPDCL approvals for multi-tenement", "Common-area backup", "EV-ready parking"]},
    {"slug": "hospitals", "name": "Hospitals", "sector": "hospital", "order": 4,
     "summary": "Redundant supply, essential and critical power, isolated power for theatres, UPS and earthing for medical equipment.",
     "needs": ["Redundant transformers and DG", "UPS for critical loads", "Low earth resistance", "Work without disrupting patient care"]},
    {"slug": "education", "name": "Schools & colleges", "sector": "education", "order": 5,
     "summary": "Campus substations, building electrification, lab power, lighting and solar for schools, colleges and universities.",
     "needs": ["Safe installations for students", "Campus-wide distribution", "Solar to cut bills", "Work during vacations"]},
    {"slug": "infrastructure", "name": "Infrastructure & utilities", "sector": "infrastructure", "order": 6,
     "summary": "Pumping stations, water treatment plants, street lighting and EV charging infrastructure.",
     "needs": ["Outdoor and harsh-environment equipment", "Long cable runs", "Remote monitoring", "Tender compliance"]},
    {"slug": "government", "name": "Government", "sector": "government", "order": 7,
     "summary": "Electrical works for government buildings and departments through GeM and state e-tenders.",
     "needs": ["Schedule-of-rates pricing", "Tender documentation", "Quality and safety records", "Timely completion"]},
]

PRODUCTS = [
    {"slug": "ht-vcb-panels", "name": "HT VCB panels & RMUs", "category": "panels", "order": 1, "summary": "Indoor VCB panels and ring main units for 11, 22 and 33 kV with numerical protection.",
     "specs": [["Voltage", "11 / 22 / 33 kV"], ["Rated current", "630–1250 A"], ["Breaking capacity", "20–26.3 kA"], ["Protection", "Numerical relays 50/51, 50N/51N"]]},
    {"slug": "lt-panels", "name": "LT panels (PCC, MCC, DB)", "category": "panels", "order": 2, "summary": "Type-tested power and motor control centres and distribution boards.",
     "specs": [["Rated current", "Up to 6300 A"], ["Form of separation", "Form 2 to Form 4b"], ["Standard", "IS/IEC 61439"]]},
    {"slug": "apfc-panels", "name": "APFC panels", "category": "apfc", "order": 3, "summary": "Automatic power factor correction with detuned reactors and thyristor switching options.",
     "specs": [["Range", "25–1000 kVAR"], ["Reactors", "7% / 14% detuned"], ["Controller", "Microprocessor, 6–14 steps"]]},
    {"slug": "distribution-transformers", "name": "Distribution transformers", "category": "transformers", "order": 4, "summary": "Oil-filled and dry-type transformers up to 2500 kVA in energy-efficiency levels to suit total owning cost.",
     "specs": [["Ratings", "63–2500 kVA"], ["Voltage", "11 / 22 / 33 kV to 433 V"], ["Types", "ONAN, cast resin"], ["Standard", "IS 1180, IS 11171"]]},
    {"slug": "power-cables", "name": "HT & LT power cables", "category": "cables", "order": 5, "summary": "XLPE armoured aluminium and copper cables, with jointing and termination kits.",
     "specs": [["Voltage", "1.1 kV to 33 kV"], ["Conductor", "Aluminium / copper"], ["Standard", "IS 7098"]]},
    {"slug": "switchgear", "name": "Switchgear (ACB, MCCB, MCB)", "category": "switchgear", "order": 6, "summary": "Air and moulded-case circuit breakers, miniature breakers, RCDs and changeovers.",
     "specs": [["ACB", "800–6300 A"], ["MCCB", "16–1600 A"], ["Standard", "IS/IEC 60947-2"]]},
    {"slug": "led-lighting", "name": "LED lighting", "category": "lighting", "order": 7, "summary": "High-bay, flood, street and indoor LED fixtures with lux designs.",
     "specs": [["Types", "High-bay, flood, street, panel"], ["Efficacy", "Up to 150 lm/W"]]},
    {"slug": "earthing-lps", "name": "Earthing & lightning protection", "category": "earthing", "order": 8, "summary": "Chemical and conventional electrodes, strips, ESE and conventional air terminals, SPDs.",
     "specs": [["Electrodes", "Pipe, plate, chemical"], ["Standard", "IS 3043, IS/IEC 62305"]]},
    {"slug": "ev-chargers", "name": "EV chargers", "category": "ev_chargers", "order": 9, "summary": "AC wall-box and DC fast chargers with load management and payment options.",
     "specs": [["AC", "3.3–22 kW"], ["DC", "30–120 kW"], ["Connectors", "Type 2, CCS2"]]},
    {"slug": "solar-systems", "name": "Solar systems", "category": "solar", "order": 10, "summary": "On-grid rooftop and ground-mounted systems with ALMM-listed modules and string inverters.",
     "specs": [["Sizes", "3 kWp to multi-MW"], ["Metering", "Net / gross"]]},
    {"slug": "dg-ups", "name": "DG sets & UPS", "category": "dg_ups", "order": 11, "summary": "CPCB IV+ DG sets with AMF panels; online UPS with battery banks.",
     "specs": [["DG", "15–2500 kVA"], ["UPS", "1–500 kVA"]]},
]

FAQS = [
    ("general", "Which areas do you work in?", "We work across Tamil Nadu from our branches, and take up larger projects in neighbouring states."),
    ("general", "Are you a licensed electrical contractor?", "Yes. Our licence and registration details are shown on the About and Safety & quality pages and on every quote."),
    ("lt_connection", "What is the maximum load on an LT connection in Tamil Nadu?", "LT supply is available up to 150 kW. Above that, an HT connection is needed."),
    ("ht_connection", "When should I move from LT to HT?", "Above 150 kW you must take HT supply. Below that, HT can still save money if you use a lot of energy — try our LT or HT cost comparison tool."),
    ("ht_connection", "What does an HT connection cost?", "You pay TNPDCL charges for the line and metering, and build your own substation (transformer, HT panel, LT panel, earthing). Our HT roadmap tool gives an indicative range."),
    ("approvals", "What is CEIG approval?", "The Chief Electrical Inspector to Government approves the drawings of HT installations before work and inspects them before energisation."),
    ("approvals", "How long do approvals take?", "Typically several weeks for each stage; our liaison team tracks every stage and shows it in your client portal."),
    ("billing", "Why is my HT bill so high even when production is low?", "Demand charges are billed on the higher of recorded demand or 90% of your contract demand. If your contract demand is too high, you pay for capacity you don't use — try the contract demand optimiser."),
    ("billing", "How do I avoid the power factor penalty?", "Keep your average power factor at 0.90 or above with an APFC panel; with many VFDs or UPS loads, use detuned reactors."),
    ("amc", "What does an AMC include?", "Scheduled preventive maintenance visits with checklists and reports, breakdown response within agreed times, and testing as listed in the contract."),
    ("amc", "Can you maintain installations done by others?", "Yes. We start with a condition survey and then propose an AMC."),
    ("solar", "Can I add solar to an HT connection?", "Yes, within your contract demand and the current TNPDCL rules; we handle the metering application."),
    ("safety", "How do you keep sites safe?", "Every HT and isolation job runs under a permit to work with lock-out / tag-out, an authorised person, and daily toolbox talks. Safety officers can stop any job."),
    ("general", "Do you give fixed-price quotes?", "Yes, after a site survey we give an itemised techno-commercial proposal with clear inclusions and exclusions."),
    ("general", "How do I track my project?", "Clients get a portal login with progress, photos, drawings, approvals, bills and documents."),
]

GUIDES = [
    {"slug": "ht-connection-tamil-nadu", "title": "Getting an HT connection in Tamil Nadu", "kind": "guide", "order": 1,
     "summary": "The steps, documents and timelines for a new HT service, from application to energisation.",
     "body": "## When you need HT\n\nLT supply in Tamil Nadu is available up to 150 kW. Above that, you need a high-tension (HT) connection at 11, 22 or 33 kV, "
             "with your own substation.\n\n## The steps\n\n- Apply to TNPDCL with the contract demand you need and your site documents.\n"
             "- TNPDCL inspects the site and issues an estimate for the line extension and metering.\n- Your substation drawings go to CEIG for approval.\n"
             "- The substation is built: transformer, HT panel or RMU, cabling, earthing and LT panel.\n- Testing, CEIG inspection, meter fixing and energisation.\n\n"
             "## Documents\n\nOwnership or lease proof, company documents, site plan with the substation location, single-line diagram and layout, "
             "and test reports for the equipment.\n\n## How long it takes\n\nTypically three to six months, depending on line work and approvals. "
             "Our HT connection roadmap tool shows each step for your load."},
    {"slug": "lt-or-ht", "title": "LT or HT? How to decide", "kind": "guide", "order": 2,
     "summary": "Compare running costs, the substation investment and payback before you choose.",
     "body": "## The rule\n\nAbove 150 kW, HT is required. Below that, it's a choice.\n\n## What changes on HT\n\n- Lower energy rate per unit.\n"
             "- Demand charges on kVA instead of fixed charges on kW.\n- Time-of-day charges: more in peak hours, a rebate at night.\n"
             "- You own and maintain the substation, and transformer losses are billed to you.\n\n## When HT pays\n\nHigh, steady consumption and "
             "a good power factor make HT attractive. Use our LT or HT cost comparison to see your payback."},
    {"slug": "choosing-a-transformer", "title": "Choosing a transformer", "kind": "guide", "order": 3,
     "summary": "Rating, type and efficiency level — and why total owning cost matters more than price.",
     "body": "## Rating\n\nStart from maximum demand, add growth, and keep loading under about 80%. Pick the next standard rating.\n\n## Type\n\n"
             "Oil-filled transformers suit outdoor substations; cast-resin dry type is preferred inside buildings.\n\n## Efficiency\n\nA cheaper "
             "transformer with higher losses can cost much more over 15 years. Compare offers on total owning cost: price plus the cost of no-load "
             "and load losses over its life. Our transformer losses tool does this for you."},
]

TERMS = [
    {"name": "Standard terms", "kind": "terms", "body": "- Prices are in Indian rupees, without GST unless stated. GST is extra at the rates applicable on the date of invoice.\n"
     "- Delivery and completion periods start from the date of advance and approved drawings.\n- Civil works, statutory fees and TNPDCL / CEIG charges are excluded unless listed in the scope.\n"
     "- The client provides free access, storage space, water and construction power at site.\n- Variations to scope are priced and approved in writing before execution.\n"
     "- Warranty on equipment is as per the manufacturer; workmanship is warranted for 12 months from handover.\n- Payment is due within the agreed credit days; delayed payments may affect the schedule.\n"
     "- Disputes are subject to the courts at Erode."},
    {"name": "Government / tender terms", "kind": "terms", "body": "- Rates are as per the tender schedule; taxes as per the tender conditions.\n- EMD and performance security as per the tender.\n- All other conditions as per the tender documents."},
    {"name": "AMC terms", "kind": "terms", "body": "- The AMC covers the equipment and visits listed in the schedule.\n- Spares and consumables are charged extra unless included.\n"
     "- Response and restore times apply from the time the request is logged.\n- Work on equipment not in good condition at the start may need a condition repair first."},
]

PROCESS = [
    {"step": "Site survey", "text": "An engineer visits, measures the load and studies your supply."},
    {"step": "Design", "text": "Single-line diagram, layouts and an itemised proposal."},
    {"step": "Approvals", "text": "TNPDCL and CEIG applications filed and followed up."},
    {"step": "Build", "text": "Safe execution under permits, with daily reports you can see."},
    {"step": "Test", "text": "Calibrated instruments and certificates for every test."},
    {"step": "Handover", "text": "As-built drawings, certificates, warranties and training."},
    {"step": "AMC", "text": "Scheduled maintenance and breakdown response."},
]
