"""Sample data for the hosted preview and local trials (SEED_DEMO=true). Every name, number and record here is made up."""
import os
import random
from datetime import date, timedelta, datetime

import engine as ENG
import hooks as H
from core import db, now_iso, new_id, hash_password, today_ist, clear_settings_cache, IST
from roles import ROLES
from seed import DEMO_DOMAIN

R = random.Random(7)
T = None
PW = os.environ.get("DEMO_PASSWORD", "Demo@12345")


def day(n):
    return (T + timedelta(days=n)).isoformat()


def dt(n, h=10, m=0):
    return f"{day(n)}T{h:02d}:{m:02d}"


async def C(entity, data, user=None):
    return await ENG.create_record(entity, user, data, system=True)


BOSS = {}


async def A(entity, rid, action, user, body=None):
    try:
        return await ENG.run_action(entity, user, rid, action, body or {})
    except Exception as ex:
        if getattr(ex, "status_code", None) in (403, 404) and BOSS:
            return await ENG.run_action(entity, BOSS["u"], rid, action, body or {})
        raise


async def backdate(coll, rid, days_ago, hour=11):
    t = (datetime.now(IST) - timedelta(days=days_ago)).replace(hour=hour, minute=R.randint(0, 59)).astimezone().isoformat()
    await db[coll].update_one({"id": rid}, {"$set": {"created_at": t, "updated_at": t}})
    return t


async def approve(entity, doc, requester, approver):
    e = ENG.ent(entity)
    fresh = await db[entity].find_one({"id": doc["id"]}, {"_id": 0})
    await ENG.submit_for_approval(e, fresh, requester)
    fresh = await db[entity].find_one({"id": doc["id"]}, {"_id": 0})
    if fresh.get("approval_id"):
        ok, _ = await ENG.can_decide(approver, await db.approvals.find_one({"id": fresh["approval_id"]}, {"_id": 0}))
        await ENG.decide(approver if ok else (BOSS["u"] if requester["id"] != BOSS["u"]["id"] else BOSS["admin"]), fresh["approval_id"], "approve", "")
    return await db[entity].find_one({"id": doc["id"]}, {"_id": 0})


PEOPLE = {
    "super_admin": ("Admin Desk", "admin"), "director": ("Arun Velusamy", "director"), "branch_manager": ("Senthil Kumar", "manager.erode"),
    "sales": ("Priya Natarajan", "sales"), "estimator": ("Gokul Raj", "estimation"), "tender_exec": ("Divya Shankar", "tenders"),
    "project_manager": ("Manoj Krishnan", "pm"), "site_engineer": ("Vignesh Murugan", "site"), "liaison": ("Ramesh Babu", "liaison"),
    "qaqc": ("Karthika Devi", "qaqc"), "safety": ("Suresh Pandian", "safety"), "purchase": ("Lakshmi Narayanan", "purchase"),
    "store": ("Muthu Selvam", "store"), "accounts": ("Anitha Ravi", "accounts"), "hr": ("Kavitha Mohan", "hr"),
    "service_manager": ("Prakash Elango", "service"), "technician": ("Ajith Kumar", "technician"), "marketing": ("Nivetha Sundar", "marketing"),
    "auditor": ("External Auditor", "auditor"), "employee": ("Saravanan P", "employee"),
}
EXTRA_STAFF = [("sales", "Hari Prasad", "sales2", "CBE"), ("site_engineer", "Dinesh Kumar", "site2", "ERD"), ("technician", "Balaji S", "technician2", "PDR"),
               ("project_manager", "Revathi Sekar", "pm2", "CBE")]


async def mk_user(role, name, local, branch_ids=None, **extra):
    u = {"id": new_id(), "name": name, "email": f"{local}@{DEMO_DOMAIN}", "role": role, "password_hash": hash_password(PW), "active": True,
         "branch_ids": branch_ids or [], "phone": f"+9198{R.randint(10000000, 99999999)}", "created_at": now_iso(), "mfa_enabled": False, **extra}
    await db.users.insert_one(dict(u))
    return u


ITEMS = [
    # name, group, make, spec, unit, std_rate, cost_rate, gst, drum, serial
    ("XLPE Al armoured cable 3.5C × 16 sq mm", "cable", "Polycab", "1.1 kV, IS 7098-1", "m", 165, 128, "18", True, False),
    ("XLPE Al armoured cable 3.5C × 35 sq mm", "cable", "Polycab", "1.1 kV, IS 7098-1", "m", 265, 205, "18", True, False),
    ("XLPE Al armoured cable 3.5C × 70 sq mm", "cable", "Havells", "1.1 kV, IS 7098-1", "m", 445, 352, "18", True, False),
    ("XLPE Al armoured cable 3.5C × 120 sq mm", "cable", "Havells", "1.1 kV, IS 7098-1", "m", 690, 548, "18", True, False),
    ("XLPE Al armoured cable 3.5C × 240 sq mm", "cable", "KEI", "1.1 kV, IS 7098-1", "m", 1290, 1030, "18", True, False),
    ("XLPE Al armoured cable 3.5C × 300 sq mm", "cable", "KEI", "1.1 kV, IS 7098-1", "m", 1580, 1265, "18", True, False),
    ("HT XLPE Al armoured cable 3C × 95 sq mm 11 kV", "cable", "KEI", "11 kV (E), IS 7098-2", "m", 1180, 945, "18", True, False),
    ("HT XLPE Al armoured cable 3C × 185 sq mm 11 kV", "cable", "Polycab", "11 kV (E), IS 7098-2", "m", 1720, 1380, "18", True, False),
    ("Cu flexible cable 4 sq mm", "cable", "Finolex", "1.1 kV FR-LSH", "m", 68, 52, "18", False, False),
    ("Distribution transformer 500 kVA 11/0.433 kV", "transformer", "Kirloskar", "ONAN, Dyn11, IS 1180 Level 2", "nos", 1185000, 985000, "18", False, True),
    ("Distribution transformer 1000 kVA 11/0.433 kV", "transformer", "Voltamp", "ONAN, Dyn11, IS 1180 Level 2", "nos", 1950000, 1640000, "18", False, True),
    ("Cast resin transformer 630 kVA 11/0.433 kV", "transformer", "Schneider", "AN, Dyn11, IS 11171", "nos", 2150000, 1820000, "18", False, True),
    ("HT VCB panel 11 kV 630 A 20 kA", "panel", "Siemens", "Indoor, numerical relay", "nos", 690000, 575000, "18", False, True),
    ("RMU 11 kV 3-way (2 load break + 1 VCB)", "panel", "ABB", "SF6-free, 630 A", "nos", 1450000, 1210000, "18", False, True),
    ("LT PCC panel 1600 A with ACB incomer", "panel", "Local panel builder", "Form 3b, IS/IEC 61439", "nos", 1285000, 1040000, "18", False, False),
    ("APFC panel 300 kVAR with 7% detuned reactors", "apfc", "Epcos / local", "12 steps, thyristor-ready", "nos", 685000, 548000, "18", False, False),
    ("ACB 1600 A 4P 65 kA draw-out", "switchgear", "L&T", "Microprocessor release LSIG", "nos", 345000, 286000, "18", False, True),
    ("MCCB 250 A 4P 36 kA", "switchgear", "Schneider", "TM-D release", "nos", 28500, 23100, "18", False, False),
    ("MCB 32 A 4P C curve 10 kA", "switchgear", "Legrand", "", "nos", 3150, 2480, "18", False, False),
    ("Chemical earthing electrode 3 m", "earthing", "Local", "Cu-bonded, with backfill compound", "set", 14500, 10800, "18", False, False),
    ("GI strip 50 × 6 mm", "earthing", "Tata", "Hot-dip galvanised", "m", 420, 330, "18", False, False),
    ("Copper strip 25 × 3 mm", "earthing", "", "Electrolytic", "m", 1150, 920, "18", False, False),
    ("ESE lightning arrester", "earthing", "", "Level II, with mast", "set", 98000, 76000, "18", False, False),
    ("LED high bay 150 W", "lighting", "Philips", "IP65, 140 lm/W", "nos", 9200, 7300, "18", False, False),
    ("LED street light 60 W", "lighting", "Wipro", "IP66, with surge protection", "nos", 5600, 4300, "18", False, False),
    ("Perforated cable tray 300 mm", "conduit_tray", "", "GI, 2 mm", "m", 1050, 810, "18", False, False),
    ("Aluminium lugs 240 sq mm", "accessories", "Dowells", "", "nos", 180, 128, "18", False, False),
    ("HT termination kit 11 kV 185 sq mm (indoor)", "accessories", "Raychem", "Heat shrink", "set", 9800, 7600, "18", False, False),
    ("HT straight-through joint 11 kV 185 sq mm", "accessories", "Raychem", "Heat shrink", "set", 16500, 12900, "18", False, False),
    ("AC EV charger 7.4 kW", "ev", "Delta", "Type 2, OCPP", "nos", 62000, 48500, "18", False, True),
    ("DC fast charger 60 kW", "ev", "Exicom", "CCS2", "nos", 1480000, 1230000, "18", False, True),
    ("DG set 250 kVA CPCB IV+", "dg_ups", "Kirloskar", "Acoustic enclosure, AMF", "nos", 2350000, 1990000, "18", False, True),
    ("Cable laying in trench (up to 240 sq mm)", "labour", "", "Including sand and brick", "m", 180, 120, "18", False, False),
    ("HT cable jointing / termination labour", "labour", "", "Certified jointer", "nos", 3500, 2400, "18", False, False),
    ("Transformer erection & testing", "labour", "", "Up to 1000 kVA", "nos", 45000, 32000, "18", False, False),
    ("Earth pit installation labour", "labour", "", "", "nos", 3200, 2200, "18", False, False),
    ("Crane hire (25 T) per day", "tp", "", "", "day", 18000, 15000, "18", False, False),
    ("Civil works for transformer plinth", "civil", "", "RCC M20", "ls", 85000, 64000, "18", False, False),
]


async def seed_demo():
    global T
    T = today_ist()
    s = await db.settings.find_one({"id": "company"})
    sample_contact = {"phone": "+91 98765 43210", "whatsapp": "+91 98765 43210", "emergency_phone": "+91 98765 43211",
                      "email": "info@sellandiammanpowerinfra.com", "address": "Perundurai, Erode district, Tamil Nadu",
                      "gstin": None, "elb_licence": None, "upi_id": "sapowerinfra@sampleupi",
                      "bank_details": "Sample Bank, A/c 0000 0000 1234, IFSC SMPL0000123 (sample details)",
                      "announcement": {"text": "Preview with sample data — names, projects and figures are made up.", "link": "", "active": True},
                      "town_list": ["Perundurai", "Erode", "Coimbatore", "Tiruppur", "Namakkal", "Salem"],
                      "timeline": [{"year": "Today", "text": "Electrical contracting and consulting arm of the Sellandiamman Group"}],
                      "assistant_enabled": True}
    await db.settings.update_one({"id": "company"}, {"$set": sample_contact})
    clear_settings_cache()
    branches = {b["code"]: b for b in await db.branches.find({}, {"_id": 0}).to_list(10)}
    await db.branches.update_one({"code": "PDR"}, {"$set": {"address": "Sample address, Perundurai, Erode district 638052", "phone": "+91 98765 43210", "whatsapp": "+91 98765 43210",
                                                            "email": "perundurai@sellandiammanpowerinfra.com", "lat": 11.2755, "lng": 77.5871}})
    await db.branches.update_one({"code": "ERD"}, {"$set": {"address": "Sample address, Erode 638001", "phone": "+91 98765 43212", "lat": 11.3410, "lng": 77.7172}})
    cbe = {"id": new_id(), "name": "Coimbatore", "code": "CBE", "city": "Coimbatore", "is_head_office": False, "active": True, "order": 3,
           "address": "Sample address, Coimbatore 641018", "phone": "+91 98765 43213", "lat": 11.0168, "lng": 76.9558, "hours": "Mon–Sat 9:30 am – 6:30 pm",
           "created_at": now_iso(), "deleted": False}
    await db.branches.insert_one(dict(cbe))
    branches = {b["code"]: b for b in await db.branches.find({}, {"_id": 0}).to_list(10)}
    PDR, ERD, CBE = branches["PDR"]["id"], branches["ERD"]["id"], branches["CBE"]["id"]

    # ------------------------------------------------------------------ staff
    U = {}
    for role, (name, local) in PEOPLE.items():
        bids = [ERD] if role == "branch_manager" else ([PDR] if role in ("sales", "site_engineer", "technician", "store") else [])
        U[role] = await mk_user(role, name, local, bids, designation=ROLES[role].split(" (")[0])
    for role, name, local, br in EXTRA_STAFF:
        U[local] = await mk_user(role, name, local, [branches[br]["id"]], designation=ROLES[role])
    boss, pm, se, sales, acc_u = U["director"], U["project_manager"], U["site_engineer"], U["sales"], U["accounts"]
    BOSS["u"] = boss
    BOSS["admin"] = U["super_admin"]
    await db.users.update_many({"role": {"$in": ["sales", "estimator", "project_manager"]}}, {"$set": {"takes_surveys": True}})
    await db.settings.update_one({"id": "company"}, {"$set": {"routing_rules": [
        {"name": "Coimbatore & Tiruppur", "towns": ["Coimbatore", "Tiruppur", "Pollachi"], "branch_id": CBE, "team": [U["sales2"]["id"]]},
        {"name": "Erode & Perundurai", "towns": ["Erode", "Perundurai", "Bhavani", "Gobichettipalayam"], "branch_id": PDR, "team": [sales["id"]]}]}})
    clear_settings_cache()
    depts = {"director": "mgmt", "branch_manager": "mgmt", "sales": "f1", "estimator": "f1", "tender_exec": "f1", "project_manager": "f3", "site_engineer": "f3",
             "liaison": "f5", "qaqc": "f7", "safety": "f7", "purchase": "f4", "store": "f4", "accounts": "f8", "hr": "f8", "service_manager": "f6",
             "technician": "f6", "marketing": "f1", "employee": "f3", "super_admin": "f8"}
    EMP = {}
    for key, u in U.items():
        if u["role"] in ("auditor",):
            continue
        ctc = {"director": 250000, "branch_manager": 120000, "project_manager": 95000, "estimator": 70000}.get(u["role"], R.choice([28000, 35000, 42000, 55000]))
        e = await C("employees", {"name": u["name"], "user_id": u["id"], "designation": u.get("designation"), "department": depts.get(u["role"], "f3"),
                                  "phone": u["phone"], "email": u["email"], "joined_on": day(-R.randint(60, 900)), "monthly_ctc": ctc, "basic": round(ctc * 0.5),
                                  "hra": round(ctc * 0.2), "allowances": round(ctc * 0.3), "pf": True, "esi": ctc <= 21000, "pt": True,
                                  "branch_id": (u.get("branch_ids") or [PDR])[0]})
        EMP[key] = e

    # ------------------------------------------------------------------ masters
    IT = []
    for name, grp, make, spec, unit, rate, cost, gst, drum, serial in ITEMS:
        cat = "labour" if grp == "labour" else "tp" if grp == "tp" else "material"
        IT.append(await C("items", {"name": name, "group": grp, "category": cat, "make": make, "spec": spec, "unit": unit, "std_rate": rate, "cost_rate": cost,
                                    "gst_rate": gst, "drum_tracked": drum, "serial_tracked": serial, "hsn": "8544" if grp == "cable" else "8504" if grp == "transformer" else "9954" if cat == "labour" else "8537",
                                    "min_stock": 500 if drum else (2 if grp in ("switchgear", "accessories") else None)}))
    item = {i["name"]: i for i in IT}
    stores = {}
    stores["PDR"] = await C("stores", {"name": "Perundurai central store", "stype": "warehouse", "branch_id": PDR, "keeper_id": U["store"]["id"]})
    stores["ERD"] = await C("stores", {"name": "Erode store", "stype": "warehouse", "branch_id": ERD})
    vendors = []
    for name, vt, town in [("Kongu Cables & Wires", "supplier", "Erode"), ("Shakthi Switchgear Traders", "supplier", "Coimbatore"),
                           ("Bhavani Transformers Pvt Ltd", "supplier", "Perundurai"), ("Annai Panel Builders", "supplier", "Coimbatore"),
                           ("Velan Lighting Solutions", "supplier", "Tiruppur"), ("Earthing Systems India", "supplier", "Chennai"),
                           ("Sellandiamman Traders", "supplier", "Perundurai"), ("Karthik Electricals (subcontract)", "subcontractor", "Erode"),
                           ("Murugan Cable Jointing Works", "subcontractor", "Salem"), ("Thangam Labour Services", "labour_contractor", "Erode"),
                           ("Sri Vinayaga Crane Services", "transporter", "Perundurai"), ("Gowtham Civil Contractors", "subcontractor", "Perundurai")]:
        vendors.append(await C("vendors", {"name": name, "vtype": vt, "town": town, "phone": f"+9194{R.randint(10000000, 99999999)}", "payment_terms_days": R.choice([15, 30, 45]),
                                           "categories": ["cable"] if "Cable" in name else [], "licence_no": f"EA-{R.randint(1000, 9999)}" if vt == "subcontractor" else None,
                                           "licence_valid_until": day(R.randint(-10, 400)) if vt == "subcontractor" else None, "rating": round(R.uniform(3.2, 4.8), 1)}))
    V = {v["name"]: v for v in vendors}
    for nm, it_name, rate in [("Kongu Cables & Wires", "XLPE Al armoured cable 3.5C × 240 sq mm", 1010), ("Kongu Cables & Wires", "XLPE Al armoured cable 3.5C × 70 sq mm", 345)]:
        await C("rate_contracts", {"vendor_id": V[nm]["id"], "item_id": item[it_name]["id"], "rate": rate, "valid_from": day(-60), "valid_to": day(300)})
    partners = [await C("partners", {"name": n, "type": t, "phone": f"+9193{R.randint(10000000, 99999999)}", "town": tw, "commission_pct": pct})
                for n, t, tw, pct in [("Er. Balasubramaniam (consultant)", "consultant", "Erode", 2), ("Kumar Electrical Works", "electrician", "Perundurai", 3),
                                      ("Studio Arka Architects", "architect", "Coimbatore", 1.5)]]

    # ------------------------------------------------------------------ clients
    CLIENTS = [("Kaveri Spinning Mills", "factory", "factory", "Perundurai"), ("Bhavani Textile Processors", "factory", "factory", "Bhavani"),
               ("Sri Annapoorna Hospital", "hospital", "hospital", "Erode"), ("Kongu Engineering Works", "factory", "factory", "Erode"),
               ("Nila Residency (builder)", "builder", "residential", "Coimbatore"), ("Velavan Polymers", "factory", "factory", "Perundurai"),
               ("Amaravathi College of Engineering", "education", "education", "Tiruppur"), ("Green Valley Foods", "factory", "factory", "Gobichettipalayam"),
               ("Skyline Business Park", "commercial", "commercial", "Coimbatore"), ("Erode Corporation (Water Works)", "government", "infrastructure", "Erode"),
               ("Thirumalai Rice Mill", "factory", "factory", "Perundurai"), ("Lakshmi Hosiery Exports", "factory", "factory", "Tiruppur"),
               ("Sakthi Auto Components", "factory", "factory", "Perundurai"), ("Arul Mega Mart", "commercial", "commercial", "Namakkal"),
               ("Sunrise Apartments Owners' Association", "residential", "residential", "Erode"), ("Meenakshi Cold Storage", "factory", "warehouse", "Salem"),
               ("Kumaran Steel Rolling", "factory", "factory", "Erode"), ("St. Joseph's Matriculation School", "education", "education", "Perundurai")]
    ACC = []
    for n, (name, typ, sector, town) in enumerate(CLIENTS):
        br = CBE if town in ("Coimbatore", "Tiruppur") else ERD if town in ("Erode", "Salem", "Namakkal") else PDR
        a = await C("accounts", {"name": name, "type": typ, "sector": sector, "town": town, "phone": f"+9190{R.randint(10000000, 99999999)}",
                                 "email": f"office{n}@example.com", "credit_days": R.choice([30, 30, 45, 60]), "owner_id": sales["id"] if br != CBE else U["sales2"]["id"],
                                 "branch_id": br, "show_logo": n < 10, "gstin": f"33AAACK{1000 + n}A1Z{n % 9 + 1}" if n % 3 else None,
                                 "connections": [{"number": f"0{R.randint(10, 99)}-{R.randint(100, 999)}-{R.randint(1000, 9999)}", "supply": "HT" if sector in ("factory", "hospital", "commercial") else "LT",
                                                  "tariff": "HT I" if sector == "factory" else "HT III" if sector == "commercial" else "LT V", "sanctioned_kva": R.choice([150, 300, 500, 750, 1000])}],
                                 "sites": [{"name": "Main site", "address": f"Sample site, {town}", "town": town}]})
        ACC.append(a)
        await C("contacts", {"name": R.choice(["Mr. ", "Ms. "]) + R.choice(["Ganesan", "Bharathi", "Shanmugam", "Vasanthi", "Rajendran", "Malathi", "Kannan", "Deepa"]) + f" {chr(65 + n % 26)}.",
                             "account_id": a["id"], "designation": R.choice(["Managing Director", "Plant Head", "Maintenance Manager", "Facility Manager"]),
                             "role": R.choice(["owner", "facility", "accounts"]), "phone": f"+9191{R.randint(10000000, 99999999)}", "email": f"contact{n}@example.com", "is_primary": True})
    consultant_contact = await C("contacts", {"name": "Er. Deepak Varadharajan", "account_id": ACC[4]["id"], "designation": "MEP consultant", "role": "consultant",
                                              "phone": "+919500000101", "email": "consultant@example.com"})

    # ------------------------------------------------------------------ leads (every source)
    srcs = ["quote_wizard", "survey_booking", "calculator", "bill_review", "tender_invite", "callback", "whatsapp", "phone", "emergency", "amc_enquiry",
            "download", "referral", "existing_client", "google_ads", "meta_ads", "indiamart", "justdial", "email", "qr", "missed_call", "walk_in", "exhibition", "contact_form", "product_enquiry"]
    stages = ["new"] * 8 + ["contacted"] * 9 + ["survey_scheduled"] * 5 + ["survey_done"] * 5 + ["estimating"] * 6 + ["quoted"] * 8 + ["negotiation"] * 5 + ["won"] * 7 + ["lost"] * 5 + ["on_hold"] * 2
    first = ["Ravi", "Selvi", "Ganesh", "Meena", "Arjun", "Vani", "Bala", "Kumar", "Saranya", "Muthu", "Prabhu", "Uma", "Naveen", "Geetha", "Siva", "Hema"]
    cos = ["Kongu Fabrics", "Sri Murugan Oil Mill", "Amman Dyeing", "Vetri Packaging", "Royal Granites", "Sai Hospital", "Green Fields Dairy", "Shree Balaji Tex",
           "Pioneer Foundry", "Sun Pharma Distributors", "Lotus Residency", "Kovai Plastics", "Annai Cotton", "Ambika Paper Mills", "Vel Motors", "Raja Feeds"]
    towns = ["Perundurai", "Erode", "Coimbatore", "Tiruppur", "Bhavani", "Gobichettipalayam", "Namakkal", "Salem"]
    services = ["ht_substation", "lt_electrification", "ht_lt_panels", "transformers", "cabling", "earthing_lps", "dg_ups", "solar_epc", "ev_charging", "liaison", "testing", "amc", "energy_audit"]
    LEADS = []
    for n in range(62):
        st = stages[n % len(stages)]
        src = srcs[n % len(srcs)]
        svc = services[n % len(services)]
        kva = R.choice([60, 100, 160, 250, 400, 500, 750, 1000, 1500])
        body = {"name": f"{R.choice(first)} {R.choice(['K', 'S', 'R', 'M', 'P'])}", "phone": f"+9197{R.randint(10000000, 99999999)}", "email": f"lead{n}@example.com" if n % 3 else None,
                "company": cos[n % len(cos)] + ("" if n < 16 else f" Unit {n // 16 + 1}"), "service": svc, "supply": "HT" if kva >= 200 else R.choice(["LT", "not_sure"]),
                "load_kva": kva, "site_type": R.choice(["factory", "factory", "commercial", "hospital", "residential", "education"]), "town": towns[n % len(towns)],
                "timeline": R.choice(["now", "1_3m", "3_6m", "later"]), "message": R.choice(["Need a new substation for plant expansion.", "Existing panel tripping often, need inspection.",
                "Planning LT to HT conversion.", "Require AMC for transformer and HT panel.", "Want solar on factory roof.", "EV chargers for our apartment parking.",
                "Need earthing improvement — high resistance found in audit."]), "source": src, "consent": True, "consent_text": "Agreed on the website form",
                "value": kva * R.choice([3500, 4200, 5200]), "partner_id": partners[n % 3]["id"] if src == "referral" else None,
                "utm_source": "google" if src == "google_ads" else "facebook" if src == "meta_ads" else None,
                "utm_campaign": "ht-substation-oct" if src == "google_ads" else None}
        if src == "calculator":
            body["calculator"] = {"slug": "lt-vs-ht", "title": "LT or HT? Cost comparison", "headline": {"label": "HT saves per year", "value": 412000}, "verdict": "HT saves about ₹4.12 lakh a year.", "want": "review", "inputs": {}}
        lead = await C("leads", body)
        upd = {"stage": st}
        days_ago = R.randint(0, 85) if st != "new" else R.randint(0, 3)
        created = await backdate("leads", lead["id"], days_ago, R.randint(9, 18))
        if st != "new":
            upd["first_response_at"] = (datetime.fromisoformat(created) + timedelta(minutes=R.choice([12, 20, 25, 45, 90]))).isoformat()
        if st == "lost":
            upd["lost_reason"] = R.choice(["price", "competitor", "timeline", "no_response"])
        if st == "on_hold":
            upd["hold_until"] = day(R.randint(5, 40))
        if st in ("contacted", "quoted", "negotiation", "estimating"):
            upd["next_follow_up"] = dt(R.randint(-2, 6), R.randint(10, 17))
        upd["probability"] = H.STAGE_PROB[st]
        await db.leads.update_one({"id": lead["id"]}, {"$set": upd})
        lead.update(upd)
        LEADS.append(lead)
        if st != "new":
            await C("activities", {"kind": R.choice(["call", "whatsapp", "meeting"]), "subject": R.choice(["First call — understood requirement", "Shared company profile on WhatsApp", "Met plant head on site"]),
                                   "lead_id": lead["id"], "done": True, "owner_id": lead.get("owner_id")})
    for l in LEADS[:5]:
        if l["stage"] == "new":
            await db.leads.update_one({"id": l["id"]}, {"$set": {"response_due_at": (datetime.now(IST) - timedelta(minutes=R.randint(5, 50))).isoformat()}})
    for n, l in enumerate([x for x in LEADS if x["stage"] in ("survey_scheduled", "survey_done")][:8]):
        await C("surveys", {"survey_type": "site_survey", "lead_id": l["id"], "scheduled_at": dt(R.randint(1, 6) if l["stage"] == "survey_scheduled" else -R.randint(2, 10), R.choice([10, 12, 15])),
                            "engineer_id": R.choice([sales["id"], U["estimator"]["id"]]), "address": f"{l.get('company')}, {l.get('town')}",
                            "load_list": [{"description": "Motors", "qty": 12, "kw": 7.5, "pf": 0.85, "df": 0.7}, {"description": "Lighting", "qty": 1, "kw": 18, "pf": 0.95, "df": 0.8}],
                            "findings": "Existing 250 kVA transformer loaded above 90% at peak; LT panel needs replacement." if l["stage"] == "survey_done" else None})
        if l["stage"] == "survey_done":
            sv = await db.surveys.find_one({"lead_id": l["id"]}, {"_id": 0})
            await db.surveys.update_one({"id": sv["id"]}, {"$set": {"status": "done", "recommended_supply": "HT", "recommended_kva": 500}})

    # ------------------------------------------------------------------ estimates, proposals, tenders
    def boq_lines(scale=1.0):
        rows = [("Supply", "Distribution transformer 500 kVA 11/0.433 kV", 1), ("Supply", "HT VCB panel 11 kV 630 A 20 kA", 1),
                ("Supply", "LT PCC panel 1600 A with ACB incomer", 1), ("Supply", "APFC panel 300 kVAR with 7% detuned reactors", 1),
                ("Supply", "HT XLPE Al armoured cable 3C × 185 sq mm 11 kV", round(120 * scale)), ("Supply", "XLPE Al armoured cable 3.5C × 300 sq mm", round(260 * scale)),
                ("Supply", "Chemical earthing electrode 3 m", 8), ("Supply", "GI strip 50 × 6 mm", round(180 * scale)),
                ("Erection", "Transformer erection & testing", 1), ("Erection", "Cable laying in trench (up to 240 sq mm)", round(380 * scale)),
                ("Erection", "HT cable jointing / termination labour", 2), ("Erection", "Earth pit installation labour", 8), ("Civil", "Civil works for transformer plinth", 1)]
        return [{"section": sec, "item_id": item[n]["id"], "qty": q} for sec, n, q in rows]
    est_leads = [l for l in LEADS if l["stage"] in ("estimating", "quoted", "negotiation", "won")]
    PROPS = []
    for n, l in enumerate(est_leads[:12]):
        b = await C("boqs", {"title": f"{l.get('company')} — {l.get('load_kva')} kVA substation", "lead_id": l["id"], "lines": boq_lines(R.uniform(0.7, 1.4)),
                             "discount_pct": R.choice([0, 2, 3, 5, 8]), "branch_id": l.get("branch_id")}, U["estimator"])
        if l["stage"] in ("quoted", "negotiation", "won"):
            b = await approve("boqs", b, U["estimator"], boss)
            p = await C("proposals", {"title": f"Techno-commercial proposal — {l.get('load_kva')} kVA HT substation", "lead_id": l["id"], "boq_id": b["id"],
                                      "cover_letter": f"Dear Sir / Madam,\n\nThank you for the opportunity to quote for the HT substation at your {l.get('town')} site. Please find our offer below.",
                                      "scope": "- Design and CEIG approval\n- Supply, erection, testing and commissioning of the substation\n- Liaison with TNPDCL up to energisation",
                                      "exclusions": "- TNPDCL charges and deposits\n- Civil works beyond the transformer plinth", "branch_id": l.get("branch_id")}, sales)
            p = await approve("proposals", p, sales, boss)
            p = await A("proposals", p["id"], "send", sales)
            if l["stage"] == "won":
                p = await A("proposals", p["id"], "accept", sales)
            PROPS.append(p)
    TND = []
    tstat = ["identified", "preparing", "preparing", "submitted", "submitted", "tech_qualified", "financial_opened", "won", "won", "lost", "lost", "cancelled"]
    for n, stt in enumerate(tstat):
        val = R.choice([1800000, 3200000, 5600000, 8900000, 12500000])
        tn = await C("tenders", {"title": R.choice(["Electrification of new hostel block", "11 kV substation for water treatment plant", "Street lighting — ward roads",
                                                     "HT cabling and RMU replacement", "Solar rooftop for government offices", "Earthing and LPS for pumping stations"]) + f" ({n + 1})",
                                 "authority": R.choice(["TWAD Board", "Erode Corporation", "PWD Electrical", "Bharathiar University", "TNHB", "Private — Sakthi Group"]),
                                 "portal": R.choice(["tntenders", "gem", "cppp", "private"]), "tender_no": f"TN/{T.year}/{1000 + n}", "value_estimate": val,
                                 "emd_amount": round(val * 0.01, -2), "tender_fee": 2950, "emd_mode": R.choice(["online", "bg", "exempt"]), "published_on": day(-R.randint(10, 60)),
                                 "due_on": dt(R.randint(2, 20) if stt in ("identified", "preparing") else -R.randint(5, 40), 15), "owner_id": U["tender_exec"]["id"],
                                 "our_quote": round(val * R.uniform(0.92, 1.05), -3) if stt not in ("identified", "preparing", "cancelled") else None,
                                 "l1_amount": round(val * 0.94, -3) if stt in ("won", "lost", "financial_opened") else None, "rank": 1 if stt == "won" else (2 if stt == "lost" else None),
                                 "loss_reason": "price" if stt == "lost" else None, "branch_id": R.choice([PDR, ERD]),
                                 "competitors": [{"bidder": "Competitor A", "amount": round(val * 0.94, -3), "rank": 1 if stt != "won" else 2}, {"bidder": "Competitor B", "amount": round(val * 1.02, -3), "rank": 3}] if stt in ("won", "lost") else []})
        await db.tenders.update_one({"id": tn["id"]}, {"$set": {"status": stt}})
        TND.append(tn)
    for n in range(5):
        await C("bank_guarantees", {"kind": ["emd", "pbg", "pbg", "advance", "retention"][n], "tender_id": TND[n + 3]["id"] if n < 2 else None, "bank": R.choice(["Indian Bank", "SBI", "Canara Bank"]),
                                    "bg_no": f"BG{T.year}{4400 + n}", "amount": R.choice([45000, 125000, 380000, 560000]), "issued_on": day(-R.randint(30, 200)),
                                    "valid_until": day(R.randint(-5, 300)), "claim_until": day(R.randint(30, 360)), "beneficiary": R.choice(["TWAD Board", "Erode Corporation", "Sakthi Group"])})
    for name, cat in [("Audited financials (last 3 years)", "financials"), ("Work completion certificates", "experience"), ("Electrical contractor licence", "licences"),
                      ("GST registration certificate", "certificates"), ("Company profile", "profiles")]:
        await db.prequal_docs.insert_one({"id": new_id(), "name": name, "category": cat, "file": {"id": "sample", "name": f"{name}.pdf"}, "valid_until": day(R.randint(20, 400)),
                                          "created_at": now_iso(), "deleted": False})

    # ------------------------------------------------------------------ projects
    PJ = []
    spec = [("Kaveri Spinning Mills — 1000 kVA HT substation", 0, "ht_substation", "HT", "11kV", 1000, "in_progress", 64, "Perundurai", True),
            ("Sri Annapoorna Hospital — 2 × 630 kVA substation & DG", 2, "ht_substation", "HT", "11kV", 1260, "in_progress", 41, "Erode", True),
            ("Nila Residency — residential tower electrification", 4, "lt_electrification", "HT", "11kV", 750, "in_progress", 28, "Coimbatore", True),
            ("Velavan Polymers — LT to HT conversion", 5, "ht_substation", "HT", "11kV", 500, "testing", 92, "Perundurai", True),
            ("Amaravathi College — campus substation & solar", 6, "solar_epc", "HT", "11kV", 630, "mobilising", 8, "Tiruppur", True),
            ("Kongu Engineering Works — PCC & APFC upgrade", 3, "ht_lt_panels", "LT", "415V", 400, "in_progress", 55, "Erode", False),
            ("Skyline Business Park — EV charging hub", 8, "ev_charging", "LT", "415V", 250, "planned", 0, "Coimbatore", False),
            ("Erode Corporation — pumping station 22 kV RMU", 9, "cabling", "HT", "22kV", 750, "on_hold", 35, "Erode", False),
            ("Green Valley Foods — earthing & LPS", 7, "earthing_lps", "LT", "415V", 0, "in_progress", 70, "Gobichettipalayam", False),
            ("Lakshmi Hosiery Exports — 750 kVA substation", 11, "ht_substation", "HT", "11kV", 750, "in_progress", 47, "Tiruppur", False)]
    done_spec = [("Bhavani Textile Processors — 1500 kVA substation", 1, "ht_substation", "HT", "11kV", 1500, "Bhavani", "2025"),
                 ("Thirumalai Rice Mill — 500 kVA HT conversion", 10, "ht_substation", "HT", "11kV", 500, "Perundurai", "2025"),
                 ("Sakthi Auto Components — transformer replacement", 12, "transformers", "HT", "11kV", 1000, "Perundurai", "2026"),
                 ("Arul Mega Mart — LT electrification & DG", 13, "lt_electrification", "LT", "415V", 320, "Namakkal", "2026"),
                 ("Sunrise Apartments — EV chargers & metering", 14, "ev_charging", "LT", "415V", 120, "Erode", "2026"),
                 ("Meenakshi Cold Storage — 630 kVA dry-type substation", 15, "ht_substation", "HT", "11kV", 630, "Salem", "2026"),
                 ("Kumaran Steel Rolling — 33 kV cabling & RMU", 16, "cabling", "HT", "33kV", 2000, "Erode", "2026"),
                 ("St. Joseph's School — rooftop solar 120 kWp", 17, "solar_epc", "LT", "415V", 120, "Perundurai", "2026"),
                 ("Kaveri Spinning Mills — APFC & harmonic filter", 0, "ht_lt_panels", "LT", "415V", 600, "Perundurai", "2024"),
                 ("Velavan Polymers — earthing upgrade", 5, "earthing_lps", "LT", "415V", 0, "Perundurai", "2026"),
                 ("Green Valley Foods — 250 kVA substation", 7, "ht_substation", "HT", "11kV", 250, "Gobichettipalayam", "2024"),
                 ("Skyline Business Park — LED retrofit", 8, "street_lighting", "LT", "415V", 0, "Coimbatore", "2026")]
    case = {
        "Bhavani Textile Processors — 1500 kVA substation": ("Bhavani Textile Processors: 1500 kVA substation for a dyeing expansion",
            "The plant was adding a new dyeing line and its 750 kVA LT-fed supply could not carry the load.",
            "We designed an 11 kV indoor substation with two transformers, a VCB panel and an LT PCC with APFC, got CEIG approval, and energised it during a planned weekend shutdown.",
            "Production expanded without load shedding; power factor held above 0.98.", [("Capacity", "1500 kVA"), ("Shutdown used", "36 hours"), ("Power factor", "0.98+")]),
        "Thirumalai Rice Mill — 500 kVA HT conversion": ("Thirumalai Rice Mill: LT to HT conversion",
            "High LT fixed charges and frequent tripping during the milling season.", "A 500 kVA outdoor substation with energy-efficient transformer, new LT panel and earthing.",
            "Lower monthly bills and no trips through the season.", [("Capacity", "500 kVA"), ("Delivery", "14 weeks")]),
        "Meenakshi Cold Storage — 630 kVA dry-type substation": ("Meenakshi Cold Storage: dry-type substation inside the building",
            "No space outdoors and a fire-safety requirement for an indoor transformer.", "Cast-resin 630 kVA transformer, RMU and LT panel in a compact substation room with fire detection.",
            "Safe indoor installation approved by CEIG at first inspection.", [("Capacity", "630 kVA"), ("Type", "Cast resin")]),
        "St. Joseph's School — rooftop solar 120 kWp": ("St. Joseph's School: 120 kWp rooftop solar",
            "High daytime consumption and a large flat roof.", "A 120 kWp rooftop plant with net metering, delivered with our group's solar company.",
            "Most of the school's daytime power now comes from the roof.", [("Plant", "120 kWp"), ("Metering", "Net")]),
        "Kumaran Steel Rolling — 33 kV cabling & RMU": ("Kumaran Steel Rolling: 33 kV cabling and RMU",
            "An ageing overhead line and frequent faults on the 33 kV incoming feeder.", "Underground 33 kV XLPE cable with joints, a new RMU and protection grading.",
            "Fault-free incoming supply since commissioning.", [("Voltage", "33 kV"), ("Cable route", "1.2 km")]),
        "Sakthi Auto Components — transformer replacement": ("Sakthi Auto Components: overnight transformer replacement",
            "A failed 1000 kVA transformer stopped the plant.", "We sourced, transported and erected a replacement transformer overnight with crane, testing and energisation.",
            "Plant back in production the next morning.", [("Capacity", "1000 kVA"), ("Turnaround", "Overnight")]),
    }
    for n, (name, ai, svc, sup, vol, kva, status, pct, town, rich) in enumerate(spec):
        br = CBE if town in ("Coimbatore", "Tiruppur") else ERD if town in ("Erode", "Salem", "Namakkal") else PDR
        start = -12 if status == "mobilising" else (-R.randint(40, 160) if status != "planned" else 15)
        span = round(-start / max((pct + R.randint(-6, 10)) / 100, 0.08)) if pct > 0 else 150
        cv = (kva or 300) * R.choice([3800, 4300, 4900]) if kva else R.choice([1450000, 2350000])
        bs = [0.9, 1.1, 0.92, 0.97, 1.0, 0.88, 0.95, 1.05, 0.9, 0.98][n]  # budget as planned: margins differ by project
        p = await C("projects", {"name": name, "account_id": ACC[ai]["id"], "service": svc, "supply": sup, "voltage": vol, "capacity_kva": kva or None,
                                 "contract_value": cv, "wo_no": f"WO/{T.year}/{210 + n}", "wo_date": day(min(start - 10, -6)), "start_date": day(start), "end_date": day(start + max(span, 45)),
                                 "manager_id": pm["id"] if n % 2 == 0 else U["pm2"]["id"], "team_ids": [se["id"], U["site2"]["id"]] if n < 6 else [U["site2"]["id"]],
                                 "consultant_ids": [consultant_contact["id"]] if n in (2, 4) else [], "town": town, "site_address": f"Sample site, {town}",
                                 "gps": {"lat": 11.27 + R.uniform(-0.3, 0.3), "lng": 77.58 + R.uniform(-0.6, 0.3), "acc": 10}, "retention_pct": 5, "mobilisation_advance": round(cv * 0.1, -3),
                                 "budget": [{"head": "material", "amount": round(cv * 0.55 * bs)}, {"head": "labour", "amount": round(cv * 0.08 * bs)}, {"head": "subcon", "amount": round(cv * 0.09 * bs)},
                                            {"head": "tp", "amount": round(cv * 0.02 * bs)}, {"head": "liaison", "amount": round(cv * 0.02 * bs)}, {"head": "overhead", "amount": round(cv * 0.04 * bs)}],
                                 "sector": ACC[ai]["sector"], "branch_id": br})
        await db.projects.update_one({"id": p["id"]}, {"$set": {"status": status}})
        p["status"] = status
        PJ.append((p, rich, pct))
        # milestones
        names = ["Design & CEIG approval", "Material procurement", "Civil & earthing", "Erection & cabling", "Testing & commissioning", "Energisation & handover"]
        weights = [10, 25, 15, 30, 12, 8]
        s0 = start
        left = pct
        unit = max(span, 45) / 5.2
        for k, (mn, w) in enumerate(zip(names, weights)):
            dur = round(unit * R.uniform(0.9, 1.3))
            done = 100 if left >= w else (round(left / w * 100) if left > 0 else 0)
            left -= w
            await C("milestones", {"project_id": p["id"], "name": mn, "wbs": f"{k + 1}", "weight_pct": w, "planned_start": day(s0), "planned_end": day(s0 + dur),
                                   "percent": done, "billing_pct": [10, 30, 0, 40, 10, 10][k]})
            s0 += round(unit * 0.85)
        await H.recompute_project(p["id"])
    DONE = []
    for p, rich, pct in PJ:
        if not rich and pct >= 30:
            inv = await C("invoices", {"itype": "tax_invoice", "account_id": p["account_id"], "project_id": p["id"], "date": day(-R.randint(8, 14)), "branch_id": p.get("branch_id"),
                                       "lines": [{"description": f"{p['name']}: running bill for work done", "hsn": "995461", "qty": 1, "unit": "ls", "rate": round(float(p["contract_value"]) * pct / 100 * 0.85, -2), "gst_rate": "18"}]}, acc_u)
            await A("invoices", inv["id"], "issue", acc_u)
    for n, (name, ai, svc, sup, vol, kva, town, year) in enumerate(done_spec):
        br = CBE if town in ("Coimbatore", "Tiruppur") else ERD if town in ("Erode", "Salem", "Namakkal") else PDR
        cv = (kva or 300) * R.choice([3600, 4100]) if kva else R.choice([850000, 1250000])
        c = case.get(name)
        if int(year) == T.year:
            end_d = T - timedelta(days=R.randint(25, 200))
        else:
            end_d = date(int(year), R.randint(2, 11), R.randint(1, 28))
        start_d = end_d - timedelta(days=2 if "replacement" in name else R.randint(70, 170))
        p = await C("projects", {"name": name, "account_id": ACC[ai]["id"], "service": svc, "supply": sup, "voltage": vol, "capacity_kva": kva or None,
                                 "contract_value": cv, "start_date": start_d.isoformat(), "end_date": (end_d - timedelta(days=R.randint(0, 12))).isoformat(), "actual_end": end_d.isoformat(),
                                 "wo_date": (start_d - timedelta(days=10)).isoformat(),
                                 "manager_id": pm["id"], "town": town, "sector": ACC[ai]["sector"], "branch_id": br, "year": year,
                                 "publish": bool(c) or n < 8, "featured": bool(c) and n < 4, "public_title": c[0] if c else name.replace(" — ", ": "),
                                 "public_summary": (c[1] + " " + c[3]) if c else f"{label(svc)} for {ACC[ai]['name']} in {town}.",
                                 "challenge": c[1] if c else None, "solution": c[2] if c else None, "results": c[3] if c else None,
                                 "highlights": [{"label": a, "value": b} for a, b in (c[4] if c else [])], "sample": True})
        await db.projects.update_one({"id": p["id"]}, {"$set": {"status": "handed_over" if n % 3 else "closed", "percent_complete": 100, "sample": True}})
        DONE.append((p, start_d, end_d))
    # testimonials (sample)
    for q, person, des, company in [("The substation was energised on the date they promised, and the paperwork was complete the first time.", "Plant Head", "Operations", "Bhavani Textile Processors"),
                                    ("Their AMC team responds quickly and the reports are clear. We always know the condition of our transformers.", "Maintenance Manager", "Engineering", "Sakthi Auto Components"),
                                    ("They handled the CEIG approval and TNPDCL work so we could focus on the building.", "Project Director", "Projects", "Meenakshi Cold Storage")]:
        await C("testimonials", {"quote": q, "person": person, "designation": des, "company": company, "permission": True, "published": True, "rating": 5, "sample": True})
    await db.testimonials.update_many({}, {"$set": {"sample": True}})
    for town in ("Perundurai", "Erode", "Coimbatore", "Tiruppur"):
        await C("town_pages", {"town": town, "slug": town.lower(), "intro": f"LT and HT electrical contracting in {town}: substations, panels, cabling, earthing, solar and AMC.", "published": True})
    gal = [("11 kV indoor substation", "substations", "substation"), ("VCB panel commissioning", "panels", "panel"), ("HT cable jointing", "cabling", "cable"),
           ("1000 kVA transformer erection", "transformers", "transformer"), ("Rooftop solar plant", "solar", "solar"), ("Chemical earthing pits", "earthing", "earthing"),
           ("Relay testing", "testing", "testing"), ("High-mast lighting", "lighting", "lighting"), ("Toolbox talk at site", "safety", "safety"),
           ("LT PCC panel", "panels", "panel"), ("Cable trench", "cabling", "cable"), ("EV charging bay", "lighting", "ev")]
    for n, (t, cat, ill) in enumerate(gal):
        await C("gallery", {"title": t, "category": cat, "image": {"id": f"ill-{ill}", "name": f"{ill}.svg", "url": f"/illustrations/{ill}.svg"}, "order": n, "published": True, "taken_on": day(-R.randint(20, 400))})
    await db.gallery.update_many({}, {"$set": {"sample": True}})
    for title, slug, tag, body in [
        ("Why your HT bill has a demand charge — and how to lower it", "ht-demand-charges", "energy_audit",
         "Demand charges are billed on the higher of your recorded maximum demand and 90% of your contract demand. If your contract demand was set for a load you no longer run, you pay for capacity you don't use.\n\nLook at the last 12 months of recorded demand. If the highest is well below your contract demand, apply to reduce it — our contract demand optimiser finds the value with the lowest yearly charges.\n\nIf your demand spikes, stagger large motor starts and check whether your APFC is switching correctly."),
        ("Detuned reactors: when plain capacitors are not enough", "detuned-reactors", "ht_lt_panels",
         "Variable-speed drives, UPS systems and LED drivers draw distorted current. Plain capacitors can resonate with the transformer at a harmonic frequency, overheating and failing early.\n\nWith more than about 15% non-linear load, use 7% detuned reactors in the APFC panel. Above about 30%, measure with a power-quality analyser and consider an active filter."),
        ("Five things to check before CEIG inspection", "ceig-inspection-checklist", "liaison",
         "- Test reports for transformer, HT cable, relays and earthing signed and dated.\n- Danger boards, rubber mats, fire buckets and first-aid charts in place.\n- Earth resistance values recorded for every pit.\n- Fencing and clearances as per the approved layout.\n- Relay settings recorded and matching the approved scheme."),
        ("Permit to work on HT jobs: how we run it", "permit-to-work-ht", "testing",
         "Every HT job starts with a permit: the circuit is isolated, locked and tagged, tested dead and earthed on both sides. An authorised person issues the permit, someone else approves it, and the work stops if anything changes. At closure, locks come off only after everyone is clear."),
    ]:
        await C("insights", {"title": title, "slug": slug, "excerpt": body.split("\n")[0][:180], "body": body, "tags": [tag], "author": "Engineering team", "publish_at": dt(-R.randint(5, 60), 9)})
        await db.insights.update_one({"slug": slug}, {"$set": {"status": "published"}})
    for title, dept, desc in [("Site engineer — HT projects", "f3", "Run HT substation sites: daily reports, measurements, safety and quality."),
                              ("Estimation engineer", "f1", "Prepare BOQs, rate analyses and techno-commercial proposals for LT/HT projects."),
                              ("Service technician (AMC)", "f6", "Carry out maintenance visits and breakdown calls for substations and panels.")]:
        await C("jobs", {"title": title, "department": dept, "location": "Perundurai / Erode", "description": desc, "requirements": "- Diploma or degree in electrical engineering\n- Valid licence where applicable\n- Two-wheeler", "published": True, "closes_on": day(45)})

    # ------------------------------------------------------------------ rich project detail
    instruments = []
    for n, (nm, typ, due) in enumerate([("Megger MIT525 insulation tester", "insulation_tester", 140), ("Kyoritsu 4106 earth tester", "earth_tester", 90),
                                        ("Omicron CPC 100", "ctpt_analyser", 200), ("Megger SVERKER relay test set", "relay_test_kit", 60),
                                        ("BDV test kit 80 kV", "bdv_kit", -12), ("Fluke Ti480 thermal camera", "thermal_camera", 220)]):
        instruments.append(await C("instruments", {"name": nm, "itype": typ, "serial_no": f"SN{40021 + n * 37}", "calibration_on": day(due - 365), "calibration_due": day(due)}))
    await C("authorised_persons", {"user_id": se["id"], "name": se["name"], "level": "HT 11 kV", "authorised_by": boss["name"], "valid_until": day(250)})
    await C("authorised_persons", {"user_id": pm["id"], "name": pm["name"], "level": "HT 33 kV", "authorised_by": boss["name"], "valid_until": day(180)})
    await C("authorised_persons", {"user_id": U["safety"]["id"], "name": U["safety"]["name"], "level": "LT", "authorised_by": boss["name"], "valid_until": day(20)})
    workers = []
    contractor = V["Thangam Labour Services"]
    for n in range(20):
        workers.append(await C("workers", {"name": f"{R.choice(['Murugan', 'Selvam', 'Raja', 'Kannan', 'Arumugam', 'Velu', 'Sekar', 'Mani'])} {chr(65 + n)}", "trade": R.choice(["electrician", "helper", "lineman", "cable_jointer", "wireman", "rigger"]),
                                           "contractor_id": contractor["id"] if n % 2 else None, "id_last4": f"{R.randint(1000, 9999)}", "permit_no": f"WP{R.randint(10000, 99999)}" if n % 3 == 0 else None,
                                           "permit_valid_until": day(R.randint(-15, 500)) if n % 3 == 0 else None, "medical_fit_until": day(R.randint(5, 300)),
                                           "induction_on": day(-R.randint(10, 200)), "daily_wage": R.choice([650, 750, 850, 950, 1200]), "phone": f"+9196{R.randint(10000000, 99999999)}"}))
    for (p, rich, pct) in PJ:
        if not rich:
            continue
        pid = p["id"]
        mgr = pm if p.get("manager_id") == pm["id"] else U["pm2"]
        site_store = await C("stores", {"name": f"Site store — {p['name'].split(' —')[0]}", "stype": "site_store", "project_id": pid, "branch_id": p.get("branch_id")})
        stores[pid] = site_store
        for k in range(8):
            if p["status"] in ("planned", "mobilising") and k > 2:
                break
            await C("dprs", {"project_id": pid, "date": day(-k), "weather": R.choice(["clear", "clear", "cloudy", "rain", "hot"]),
                             "manpower": [{"trade": "electrician", "own": R.randint(2, 5), "subcon": R.randint(0, 6)}, {"trade": "helper", "own": R.randint(1, 3), "subcon": R.randint(2, 8)}],
                             "work_done": [{"description": R.choice(["Cable laying in trench", "Earth pit excavation", "Panel erection", "Transformer plinth curing", "HT termination", "Tray installation"]),
                                            "qty": R.randint(10, 120), "unit": R.choice(["m", "nos"]), "location": R.choice(["Substation yard", "Trench A", "LT panel room", "Main building"])}],
                             "materials": [{"item_id": item["XLPE Al armoured cable 3.5C × 300 sq mm"]["id"], "qty": R.randint(10, 60), "unit": "m"}] if k % 2 == 0 else [],
                             "hindrances": "Client's civil work in panel room pending." if k == 3 else "", "safety": "Toolbox talk on HT safety; all PPE in use.",
                             "gps": p.get("gps"), "share_with_client": True}, se)
            d_ = await db.dprs.find_one({"project_id": pid, "date": day(-k)}, {"_id": 0, "id": 1})
            await backdate("dprs", d_["id"], k, 19)
        for k, (num, title, typ, st) in enumerate([("SPI-SLD-01", "Single-line diagram", "sld", "approved"), ("SPI-LAY-02", "Substation layout", "substation", "submitted"),
                                                   ("SPI-ERT-03", "Earthing layout", "earthing", "approved_with_comments"), ("SPI-CS-04", "Cable schedule", "cable_schedule", "draft")]):
            dr = await C("drawings", {"project_id": pid, "number": num, "title": title, "dtype": typ, "revision": "R1" if st != "draft" else "R0", "share_with_client": True,
                                      "submitted_on": day(-R.randint(5, 30)) if st != "draft" else None, "approved_on": day(-R.randint(1, 5)) if st.startswith("approved") else None,
                                      "comments": "Add spare feeder in PCC." if st == "approved_with_comments" else None})
            await db.drawings.update_one({"id": dr["id"]}, {"$set": {"status": st}})
        await C("rfis", {"project_id": pid, "subject": "Location of metering cubicle", "question": "Please confirm the metering cubicle position — near gate or inside the substation fence?", "to": "client", "due_on": day(3)})
        await C("hindrances", {"project_id": pid, "raised_on": day(-6), "description": "Panel room civil work by client not complete", "cause": "client", "impact_days": 4})
        await C("snags", {"project_id": pid, "description": "Cable tray cover missing near DB-3", "location": "Ground floor", "priority": "normal", "assigned_to": se["id"], "due_on": day(5)})
        sn = await C("snags", {"project_id": pid, "description": "Danger board to be fixed on transformer fence", "location": "Substation yard", "priority": "high", "assigned_to": se["id"]})
        await db.snags.update_one({"id": sn["id"]}, {"$set": {"status": "fixed"}})
        await C("inspections", {"project_id": pid, "itype": "cable_laying", "date": day(-8), "checklist": [{"check": "Depth of trench as per drawing", "result": "ok"},
                                {"check": "Sand cushioning and brick protection", "result": "ok"}, {"check": "Bending radius maintained", "result": "ok"}], "result": "pass", "inspected_by": U["qaqc"]["id"]})
        await C("ncrs", {"project_id": pid, "description": "Lug crimping done with wrong die size on two terminations", "severity": "minor", "raised_on": day(-9),
                         "corrective_action": "Re-crimp with correct die; toolbox talk for jointers", "due_on": day(2)})
        await C("toolbox_talks", {"project_id": pid, "date": day(-1), "topic": "Working near energised HT equipment", "conducted_by": U["safety"]["name"],
                                  "attendees": [{"name": w["name"], "trade": w.get("trade")} for w in workers[:R.randint(6, 12)]]})
        for mth in range(3):
            mk = (T.replace(day=1) - timedelta(days=30 * mth)).strftime("%Y-%m")
            await C("hse_manhours", {"project_id": pid, "month": mk, "man_hours": R.randint(1800, 5200)})
        lia = await C("liaisons", {"kind": "new_ht_service" if p["supply"] == "HT" else "load_change", "project_id": pid, "account_id": p["account_id"], "authority": "TNPDCL",
                                   "application_no": f"HT/{T.year}/{R.randint(1000, 9999)}", "office": f"AE/O&M {p['town']}", "officer_name": "Asst. Engineer (sample)",
                                   "next_follow_up": dt(R.randint(0, 4), 11), "status_note": "Estimate paid; waiting for line extension work.",
                                   "fees": [{"description": "Application & registration", "amount": 2500, "paid_on": day(-40), "receipt_no": f"R{R.randint(10000, 99999)}"},
                                            {"description": "Development charges", "amount": R.choice([185000, 260000, 340000]), "paid_on": day(-20), "receipt_no": f"R{R.randint(10000, 99999)}"}],
                                   "stages": [{"stage": "applied", "expected_on": day(-45), "done_on": day(-44)}, {"stage": "feasibility", "expected_on": day(-30), "done_on": day(-28)},
                                              {"stage": "estimate_paid", "expected_on": day(-20), "done_on": day(-20)}, {"stage": "drawing_approved", "expected_on": day(10)},
                                              {"stage": "energised", "expected_on": day(60)}], "branch_id": p.get("branch_id")})
        await db.liaisons.update_one({"id": lia["id"]}, {"$set": {"stage": "estimate_paid"}})
        await C("liaisons", {"kind": "ceig_drawing", "project_id": pid, "account_id": p["account_id"], "authority": "CEIG", "application_no": f"CEIG/{R.randint(100, 999)}",
                             "office": "Electrical Inspector, Erode", "next_follow_up": dt(R.randint(1, 6), 12), "branch_id": p.get("branch_id")})
        # measurement book and RA bills
        for k in range(6):
            mb = await C("mb_entries", {"project_id": pid, "date": day(-20 + k * 3), "description": R.choice(["Laying 3.5C × 300 sq mm cable in trench", "Earth pit with chemical electrode", "HT termination 185 sq mm"]),
                                        "location": R.choice(["Trench A", "Trench B", "Yard"]), "nos": 1, "length": R.choice([25, 40, 60]) if k % 3 == 0 else None,
                                        "unit": "m" if k % 3 == 0 else "nos", "rate": R.choice([180, 3200, 3500])})
            if k < 4:
                await A("mb_entries", mb["id"], "check", mgr)
        if pct > 20:
            bill = await C("ra_bills", {"project_id": pid, "period_from": day(-60), "period_to": day(-30),
                                        "lines": [{"description": "Supply of transformer and HT panel (60%)", "unit": "ls", "this_qty": 1, "rate": round(p["contract_value"] * 0.25, -3)},
                                                  {"description": "Cable laying", "unit": "m", "this_qty": 420, "rate": 180}]}, mgr)
            bill = await approve("ra_bills", bill, mgr, boss)
            bill = await A("ra_bills", bill["id"], "submit_client", mgr)
            bill = await A("ra_bills", bill["id"], "certify", mgr, {"certified_amount": round(bill["gross"] * 0.97, -2), "certified_on": day(-18)})
            inv = await C("invoices", {"account_id": p["account_id"], "project_id": pid, "ra_bill_id": bill["id"], "date": day(-17), "branch_id": p.get("branch_id")}, acc_u)
            inv = await A("invoices", inv["id"], "issue", acc_u)
            if pct > 45:
                await C("receipts", {"account_id": p["account_id"], "date": day(-5), "amount": round(inv["receivable"] * R.choice([0.5, 1.0]), 2), "mode": "neft",
                                     "reference": f"UTR{R.randint(10 ** 9, 10 ** 10)}", "allocations": [{"invoice_id": inv["id"], "amount": round(inv["receivable"] * 0.5, 2)}]}, acc_u)
        if pct > 40:
            await H.generate_ra_from_mb(pid, mgr)
        v = await C("variations", {"project_id": pid, "title": "Additional 2 earth pits and 60 m GI strip", "reason": "Soil resistivity higher than assumed",
                                   "lines": [{"description": "Chemical earth pit", "qty": 2, "unit": "nos", "rate": 17700}, {"description": "GI strip 50 × 6", "qty": 60, "unit": "m", "rate": 420}]}, mgr)
        v = await approve("variations", v, mgr, boss)
        await A("variations", v["id"], "send", mgr)
        tr = await C("test_reports", {"project_id": pid, "test_type": "earth", "equipment": "Substation earth pits 1–8", "instrument_id": instruments[1]["id"], "date": day(-4),
                                      "readings": [{"point": f"Pit {k + 1}", "value": str(round(R.uniform(0.6, 1.8), 2)), "unit": "Ω", "limit": "≤ 2 Ω", "result": "pass"} for k in range(8)],
                                      "result": "pass", "tested_by": U["qaqc"]["id"], "witnessed_by": "Client representative"}, U["qaqc"])
        await A("test_reports", tr["id"], "issue", U["qaqc"])
        await C("test_reports", {"project_id": pid, "test_type": "oil_bdv", "equipment": "Transformer T1", "instrument_id": instruments[4]["id"], "date": day(-1),
                                 "readings": [{"point": "Sample 1", "value": "62", "unit": "kV", "limit": "≥ 50 kV", "result": "pass"}], "result": "pass", "tested_by": U["qaqc"]["id"]}, U["qaqc"])
        pt = await C("permits", {"project_id": pid, "ptype": "ht_work", "location": "11 kV yard", "equipment": "VCB panel incomer", "description": "Termination of 11 kV cable at VCB incomer",
                                 "hazards": ["electric_shock", "arc_flash"], "authorised_person_id": se["id"], "valid_from": dt(0, 9), "valid_to": dt(0, 18),
                                 "isolations": [{"point": "TNPDCL AB switch", "lock_no": "L-07", "tag_no": "T-22", "locked_by": se["name"]}]}, U["site2"])
        if p["status"] == "in_progress":
            pre = [{"check": x["check"], "done": True} for x in (await db.permits.find_one({"id": pt["id"]}))["precautions"]]
            await db.permits.update_one({"id": pt["id"]}, {"$set": {"precautions": pre}})
            await A("permits", pt["id"], "approve", U["safety"])
            await A("permits", pt["id"], "activate", se)
        for w in workers[:8]:
            for k in range(4):
                await C("labour_attendance", {"project_id": pid, "date": day(-k), "worker_id": w["id"], "present": R.choice(["present", "present", "present", "half_day"]), "in_time": "08:30", "out_time": "17:30"})
    await C("incidents", {"project_id": PJ[0][0]["id"], "occurred_at": dt(-12, 15), "kind": "near_miss", "description": "Ladder slipped on wet floor; no one hurt.", "root_cause": "Ladder not tied; floor wet",
                          "actions": [{"action": "Ladder tie-off rule at toolbox talk", "owner": "Safety officer", "due": day(-10), "done": True}]})
    await C("incidents", {"project_id": PJ[1][0]["id"], "occurred_at": dt(-25, 11), "kind": "first_aid", "description": "Minor cut on hand while stripping cable.", "person": "Helper (contract)"})
    # ------------------------------------------------------------------ procurement & stores
    prj_main = PJ[0][0]
    pr = await C("purchase_requests", {"project_id": prj_main["id"], "store_id": stores[prj_main["id"]]["id"], "required_by": day(7),
                                       "lines": [{"item_id": item["XLPE Al armoured cable 3.5C × 300 sq mm"]["id"], "qty": 500, "unit": "m"}, {"item_id": item["Aluminium lugs 240 sq mm"]["id"], "qty": 40, "unit": "nos"}]}, se)
    pr = await approve("purchase_requests", pr, se, pm)
    rfq = await C("rfqs", {"pr_id": pr["id"], "project_id": prj_main["id"], "vendor_ids": [V["Kongu Cables & Wires"]["id"], V["Sellandiamman Traders"]["id"], V["Shakthi Switchgear Traders"]["id"]],
                           "lines": [{"item_id": ln["item_id"], "qty": ln["qty"], "unit": ln["unit"], "description": item_by_id(IT, ln["item_id"])["name"]} for ln in pr["lines"]], "due_on": day(2)}, U["purchase"])
    await A("rfqs", rfq["id"], "send", U["purchase"])
    for vn, f in (("Kongu Cables & Wires", 1.0), ("Sellandiamman Traders", 0.985), ("Shakthi Switchgear Traders", 1.04)):
        await C("vendor_quotes", {"rfq_id": rfq["id"], "vendor_id": V[vn]["id"], "lines": [{"item_id": ln["item_id"], "description": ln["description"], "qty": ln["qty"],
                                  "rate": round(item_by_id(IT, ln["item_id"])["cost_rate"] * f, 2), "gst_rate": "18", "make": item_by_id(IT, ln["item_id"])["make"], "delivery_days": R.choice([3, 5, 7])} for ln in rfq["lines"]],
                                  "freight": R.choice([0, 2500, 4000]), "payment_terms": "30 days", "valid_until": day(15)})
    POS = []
    po_specs = [("Kongu Cables & Wires", [("XLPE Al armoured cable 3.5C × 300 sq mm", 600), ("XLPE Al armoured cable 3.5C × 70 sq mm", 300)], "PDR"),
                ("Bhavani Transformers Pvt Ltd", [("Distribution transformer 1000 kVA 11/0.433 kV", 1)], "PDR"),
                ("Annai Panel Builders", [("LT PCC panel 1600 A with ACB incomer", 1), ("APFC panel 300 kVAR with 7% detuned reactors", 1)], "PDR"),
                ("Shakthi Switchgear Traders", [("ACB 1600 A 4P 65 kA draw-out", 2), ("MCCB 250 A 4P 36 kA", 8), ("MCB 32 A 4P C curve 10 kA", 20)], "ERD"),
                ("Earthing Systems India", [("Chemical earthing electrode 3 m", 24), ("GI strip 50 × 6 mm", 400)], "PDR"),
                ("Kongu Cables & Wires", [("HT XLPE Al armoured cable 3C × 185 sq mm 11 kV", 400), ("XLPE Al armoured cable 3.5C × 240 sq mm", 600)], "ERD"),
                ("Velan Lighting Solutions", [("LED high bay 150 W", 40), ("LED street light 60 W", 30)], "ERD"),
                ("Sellandiamman Traders", [("Aluminium lugs 240 sq mm", 200), ("Perforated cable tray 300 mm", 150)], "PDR")]
    for n, (vn, lines, st) in enumerate(po_specs):
        po = await C("purchase_orders", {"vendor_id": V[vn]["id"], "project_id": PJ[[0, 0, 1, 5, 8, 1, 2, 3][n]][0]["id"], "store_id": stores[st]["id"], "date": day(-R.randint(15, 40)), "delivery_by": day(-R.randint(2, 10)),
                                         "lines": [{"item_id": item[i]["id"], "qty": q, "rate": item[i]["cost_rate"], "gst_rate": "18"} for i, q in lines]}, U["purchase"])
        po = await approve("purchase_orders", po, U["purchase"], boss if po["total"] > 100000 else U["branch_manager"])
        po = await A("purchase_orders", po["id"], "send", U["purchase"])
        POS.append(po)
        if n < 7:
            glines = []
            for ln in po["lines"]:
                rec = ln["qty"] if n != 6 else round(ln["qty"] * 0.8)
                acc_q = rec if n != 4 else rec - (1 if ln["qty"] > 20 else 0)
                gl = {"item_id": ln["item_id"], "received_qty": rec, "accepted_qty": acc_q, "rate": ln["rate"],
                      "reason": "Short supply — balance next week" if n == 6 else ("1 electrode damaged in transit" if acc_q < rec else "")}
                it = item_by_id(IT, ln["item_id"])
                if it.get("drum_tracked"):
                    drums = max(1, round(rec / 500))
                    gl["drum_no"] = f"D{T.year % 100}{R.randint(1000, 9999)}"
                    gl["drum_length"] = rec
                if it.get("serial_tracked"):
                    gl["serial_nos"] = "\n".join(f"{it['make'][:3].upper()}{R.randint(100000, 999999)}" for _ in range(int(rec)))
                glines.append(gl)
            g = await C("grns", {"po_id": po["id"], "vendor_id": po["vendor_id"], "store_id": po["store_id"], "date": day(-R.randint(3, 12)), "dc_no": f"DC{R.randint(1000, 9999)}",
                                 "vehicle_no": f"TN 33 {chr(65 + n)}{chr(66 + n)} {R.randint(1000, 9999)}", "lines": glines}, U["store"])
            await A("grns", g["id"], "post", U["store"])
            if n >= 4:
                continue  # goods received, vendor's bill not in yet
            vb = await C("vendor_bills", {"vendor_id": po["vendor_id"], "po_id": po["id"], "project_id": po.get("project_id"), "bill_no": f"INV/{R.randint(100, 999)}", "bill_date": day(-R.randint(6, 28)),
                                          "lines": [{"description": item_by_id(IT, ln["item_id"])["name"], "qty": ln["accepted_qty"], "rate": ln["rate"], "gst_rate": "18"} for ln in glines], "tds_pct": 0}, acc_u)
            if n < 3:
                vb = await A("vendor_bills", vb["id"], "verify", acc_u)
                pay = await C("vendor_payments", {"vendor_id": po["vendor_id"], "vendor_bill_id": vb["id"], "date": day(-1), "amount": round(vb["payable"] * (1 if n < 2 else 0.5), 2), "mode": "neft"}, acc_u)
                if n == 0:
                    pay = await approve("vendor_payments", pay, acc_u, boss)
                    await A("vendor_payments", pay["id"], "pay", acc_u, {"reference": f"UTR{R.randint(10 ** 9, 10 ** 10)}"})
    pending_po = await C("purchase_orders", {"vendor_id": V["Bhavani Transformers Pvt Ltd"]["id"], "project_id": PJ[4][0]["id"], "store_id": stores["PDR"]["id"], "date": day(-1),
                                             "lines": [{"item_id": item["Cast resin transformer 630 kVA 11/0.433 kV"]["id"], "qty": 1, "rate": 1820000, "gst_rate": "18"}]}, U["purchase"])
    await ENG.submit_for_approval(ENG.ent("purchase_orders"), await db.purchase_orders.find_one({"id": pending_po["id"]}, {"_id": 0}), U["purchase"])
    drums = await db.cable_drums.find({}, {"_id": 0}).to_list(20)
    if drums:
        dr0 = drums[0]
        mm = await C("material_moves", {"mtype": "issue", "from_store_id": dr0["store_id"], "project_id": prj_main["id"], "date": day(-6),
                                        "lines": [{"item_id": dr0["item_id"], "qty": 180, "drum_id": dr0["id"], "remarks": "Feeder to PCC"}]}, U["store"])
        await A("material_moves", mm["id"], "post", U["store"])
        mm = await C("material_moves", {"mtype": "issue", "from_store_id": dr0["store_id"], "project_id": prj_main["id"], "date": day(-2),
                                        "lines": [{"item_id": dr0["item_id"], "qty": 95, "drum_id": dr0["id"], "remarks": "Compressor feeder"}]}, U["store"])
        await A("material_moves", mm["id"], "post", U["store"])
        mm = await C("material_moves", {"mtype": "return", "to_store_id": dr0["store_id"], "project_id": prj_main["id"], "date": day(-1),
                                        "lines": [{"item_id": dr0["item_id"], "qty": 12, "remarks": "Off-cut returned"}]}, U["store"])
        await A("material_moves", mm["id"], "post", U["store"])
    tr_lines = [{"item_id": item["MCCB 250 A 4P 36 kA"]["id"], "qty": 2}]
    tmm = await C("material_moves", {"mtype": "transfer", "from_store_id": stores["ERD"]["id"], "to_store_id": stores["PDR"]["id"], "date": day(0), "lines": tr_lines, "vehicle_no": "TN 33 AX 1122"}, U["store"])
    await A("material_moves", tmm["id"], "post", U["store"])
    # subcontract
    sub = V["Karthik Electricals (subcontract)"]
    for n in range(3):
        mgr = pm if PJ[n][0].get("manager_id") == pm["id"] else U["pm2"]
        wo = await C("work_orders", {"vendor_id": sub["id"], "project_id": PJ[n][0]["id"], "scope": "Cable laying, termination and earthing labour as per BOQ",
                                     "lines": [{"description": "Cable laying up to 300 sq mm", "unit": "m", "qty": 800, "rate": 95}, {"description": "Earth pit installation", "unit": "nos", "qty": 12, "rate": 1900}],
                                     "start": day(-50), "end": day(40)}, mgr)
        wo = await approve("work_orders", wo, mgr, boss)
        await A("work_orders", wo["id"], "start", mgr)
        b = await C("sc_bills", {"work_order_id": wo["id"], "vendor_id": sub["id"], "period_to": day(-10), "lines": [{"description": "Cable laying up to 300 sq mm", "unit": "m", "this_qty": 320, "rate": 95},
                                                                                                                   {"description": "Earth pit installation", "unit": "nos", "this_qty": 6, "rate": 1900}]}, mgr)
        if n == 0:
            await approve("sc_bills", b, mgr, boss)
    # tools & vehicles
    for n, (nm, cat) in enumerate([("Hydraulic crimping tool 16–400 sq mm", "crimping"), ("Cable drum jack set", "cable_pulling"), ("Cable pulling winch 3 T", "cable_pulling"),
                                   ("Aluminium ladder 12 ft", "ladder_scaffold"), ("HT discharge rod set", "safety_equipment"), ("Rotary hammer drill", "power_tool")]):
        t_ = await C("tools", {"name": nm, "tcat": cat, "make": R.choice(["Dowells", "Bosch", "Jhalani", "Local"]), "value": R.choice([8500, 24000, 65000, 135000]),
                               "store_id": stores["PDR"]["id"], "issued_to": se["name"] if n % 2 == 0 else None, "issued_on": day(-10) if n % 2 == 0 else None,
                               "expected_return": day(R.randint(-3, 10)) if n % 2 == 0 else None, "project_id": prj_main["id"] if n % 2 == 0 else None})
        if n % 2 == 0:
            await db.tools.update_one({"id": t_["id"]}, {"$set": {"status": "issued"}})
    for reg, typ, ins in [("TN 33 BK 4521", "pickup", 120), ("TN 33 AZ 9087", "truck", 9), ("TN 56 Q 3310", "car", 240)]:
        v = await C("vehicles", {"reg_no": reg, "vtype": typ, "make_model": R.choice(["Tata Yodha", "Ashok Leyland Dost", "Mahindra Bolero"]), "insurance_until": day(ins),
                                 "fitness_until": day(R.randint(30, 400)), "permit_until": day(R.randint(30, 400)), "puc_until": day(R.randint(-5, 150)), "driver_name": R.choice(["Kumar", "Ravi", "Selvam"]),
                                 "driver_licence_until": day(R.randint(60, 900))})
        await C("trips", {"vehicle_id": v["id"], "date": day(-2), "from_place": "Perundurai store", "to_place": prj_main["town"], "project_id": prj_main["id"], "purpose": "Cable delivery",
                          "odo_start": 41200, "odo_end": 41262, "fuel_litres": 8, "fuel_cost": 760})
    await C("hires", {"equipment": "25 T crane", "vendor_id": V["Sri Vinayaga Crane Services"]["id"], "project_id": prj_main["id"], "from_date": day(-14), "to_date": day(-13), "unit": "day", "qty": 2, "rate": 18000})

    # ------------------------------------------------------------------ service & AMC
    ASSETS = []
    for n, a in enumerate(ACC[:14]):
        for kind, make, rating in [("transformer", R.choice(["Kirloskar", "Voltamp", "Siemens"]), f"{R.choice([500, 750, 1000, 1500])} kVA"), ("ht_panel", R.choice(["Siemens", "ABB", "Schneider"]), "11 kV VCB"),
                                   ("lt_panel", "Local panel builder", "1600 A PCC"), ("earth_pit", "", "Chemical electrode")][: (4 if n < 6 else 2)]:
            ASSETS.append(await C("installed_assets", {"account_id": a["id"], "site": "Main site", "kind": kind, "make": make, "rating": rating, "serial_no": f"{kind[:2].upper()}{R.randint(10000, 99999)}",
                                                       "installed_on": day(-R.randint(200, 1500)), "warranty_until": day(R.randint(-300, 500)), "location": R.choice(["Substation yard", "Panel room", "Utility block"])}))
    for n, a in enumerate(ACC[:20 if len(ACC) >= 20 else len(ACC)]):
        if n >= 16:
            break
        a_assets = [x["id"] for x in ASSETS if x["account_id"] == a["id"]]
        start = day(-R.randint(30, 330))
        amc = await C("amc_contracts", {"account_id": a["id"], "title": f"AMC — {a['name']} substation", "scope": "Preventive maintenance of transformer, HT panel, LT panel and earthing; breakdown support.",
                                        "asset_ids": a_assets, "visits_per_year": R.choice([2, 4, 4, 12]), "price": R.choice([48000, 72000, 96000, 145000, 210000]),
                                        "billing": R.choice(["yearly", "quarterly"]), "start": start, "end": (datetime.fromisoformat(start) + timedelta(days=364)).date().isoformat(),
                                        "branch_id": a.get("branch_id")}, U["service_manager"])
        await A("amc_contracts", amc["id"], "activate", U["service_manager"])
        jobs = await db.pm_jobs.find({"amc_id": amc["id"]}, {"_id": 0}).sort("scheduled_on", 1).to_list(20)
        for j in jobs:
            await db.pm_jobs.update_one({"id": j["id"]}, {"$set": {"technician_id": R.choice([U["technician"]["id"], U["technician2"]["id"]])}})
            if j["scheduled_on"] < day(-3):
                await db.pm_jobs.update_one({"id": j["id"]}, {"$set": {"status": "done", "completed_at": j["scheduled_on"] + "T16:00:00+05:30", "signed_by": "Maintenance in-charge",
                                                                      "report": "All parameters normal. Tightened LT busbar joints; IR values recorded.",
                                                                      "checklist": [{"check": c["check"], "result": "ok", "remarks": ""} for c in j.get("checklist") or []]}})
        if n < 6:
            inv = await C("invoices", {"itype": "amc", "account_id": a["id"], "amc_id": amc["id"], "date": start, "lines": [{"description": f"AMC charges — {amc['title']} ({amc['billing']})", "hsn": "998719",
                                       "qty": 1, "unit": "ls", "rate": amc["price"] if amc["billing"] == "yearly" else round(amc["price"] / 4), "gst_rate": "18"}], "branch_id": a.get("branch_id")}, acc_u)
            inv = await A("invoices", inv["id"], "issue", acc_u)
            if n % 2 == 0:
                await C("receipts", {"account_id": a["id"], "date": day(-R.randint(1, 20)), "amount": inv["total"], "mode": "upi", "reference": f"UPI{R.randint(10 ** 8, 10 ** 9)}"}, acc_u)
    await db.amc_contracts.update_one({"account_id": ACC[1]["id"]}, {"$set": {"end": day(25)}})
    tickets = [("Transformer oil level low, silica gel pink", "maintenance", "normal", "in_progress", 0), ("VCB not closing — spring charge fault", "breakdown", "urgent", "assigned", 1),
               ("APFC panel showing 0.82 PF", "breakdown", "high", "new", 2), ("Earth leakage tripping in LT panel", "breakdown", "high", "resolved", 3),
               ("Thermography requested before audit", "testing", "low", "waiting_customer", 4), ("Panel room light fitting failed", "maintenance", "low", "closed", 5),
               ("HT cable termination smoke smell", "breakdown", "urgent", "in_progress", 0), ("DG not taking load on AMF", "breakdown", "high", "assigned", 6)]
    for n, (title, cat, pri, st, ai) in enumerate(tickets):
        a_assets = [x for x in ASSETS if x["account_id"] == ACC[ai]["id"]]
        t = await C("tickets", {"account_id": ACC[ai]["id"], "asset_id": a_assets[0]["id"] if a_assets else None, "channel": R.choice(["phone", "portal", "whatsapp", "qr"]), "category": cat,
                                "priority": pri, "title": title, "description": title + ". Please attend.", "contact_name": "Maintenance in-charge", "contact_phone": "+919000000123",
                                "assigned_to": R.choice([U["technician"]["id"], U["technician2"]["id"]]) if st != "new" else None, "branch_id": ACC[ai].get("branch_id")}, U["service_manager"])
        ago = R.randint(1, 30) if st in ("resolved", "closed") else R.choice([0, 1, 2])
        created = (datetime.now(IST) - timedelta(days=ago, hours=R.randint(1, 12)))
        reply, fix = await H.sla_hours(pri)
        upd = {"created_at": created.isoformat(), "respond_by": (created + timedelta(hours=reply)).isoformat(), "restore_by": (created + timedelta(hours=fix)).isoformat(), "status": st}
        if st in ("in_progress", "waiting_customer", "resolved", "closed"):
            upd["first_response_at"] = (created + timedelta(hours=1)).isoformat()
        if st in ("resolved", "closed"):
            upd["resolved_at"] = (created + timedelta(hours=R.randint(3, 20))).isoformat()
            upd["resolution"] = "Fault rectified and tested."
            upd["rating"] = R.choice([4, 5])
        upd["sla_breached"] = (upd.get("resolved_at") or datetime.now(IST).isoformat()) > upd["restore_by"]
        await db.tickets.update_one({"id": t["id"]}, {"$set": upd})

    # ------------------------------------------------------------------ finance, HR, misc
    for nm, kind, op in [("Indian Bank — current a/c", "bank", 2450000), ("Cash in hand — head office", "cash", 85000), ("Petty cash — Kaveri site", "petty_cash", 25000)]:
        await C("bank_accounts", {"name": nm, "kind": kind, "bank": "Indian Bank" if kind == "bank" else None, "account_last4": "4421" if kind == "bank" else None, "opening_balance": op,
                                  "opening_date": day(-120), "project_id": prj_main["id"] if kind == "petty_cash" else None, "branch_id": PDR, "custodian_id": se["id"] if kind == "petty_cash" else acc_u["id"]})
    bank = await db.bank_accounts.find_one({"kind": "bank"}, {"_id": 0})
    await db.receipts.update_many({}, {"$set": {"bank_account_id": bank["id"]}})
    await db.vendor_payments.update_many({}, {"$set": {"bank_account_id": bank["id"]}})
    for n in range(14):
        e = await C("expenses", {"date": day(-R.randint(0, 40)), "category": R.choice(["fuel", "travel", "food", "site_petty", "repairs", "liaison_fees", "printing"]),
                                 "project_id": PJ[n % 5][0]["id"] if n % 3 else None, "employee_id": R.choice([se["id"], pm["id"], U["liaison"]["id"], sales["id"]]),
                                 "amount": R.choice([450, 820, 1250, 2600, 5400, 12500]), "description": R.choice(["Diesel for site vehicle", "Bus fare to Erode", "Team lunch at site", "Printing of drawings", "Section office fee"])}, se)
        if n < 9:
            await approve("expenses", e, se, U["branch_manager"] if e["amount"] <= 10000 else boss)
        elif n < 12:
            await ENG.submit_for_approval(ENG.ent("expenses"), await db.expenses.find_one({"id": e["id"]}, {"_id": 0}), se)
    # client payment notice (pending)
    inv_open = await db.invoices.find_one({"status": {"$in": ["issued", "part_paid"]}, "account_id": ACC[0]["id"]}, {"_id": 0})
    # attendance
    for key, e in list(EMP.items())[:14]:
        for k in range(1, 9):
            dday = T - timedelta(days=k)
            if dday.weekday() == 6:
                continue
            cin = f"{dday.isoformat()}T{R.choice(['09:12', '09:25', '09:31', '09:48', '10:05'])}:00+05:30"
            cout = f"{dday.isoformat()}T{R.choice(['17:55', '18:20', '18:40', '19:10'])}:00+05:30"
            await C("attendance", {"employee_id": e["id"], "date": dday.isoformat(), "check_in": cin, "check_out": cout, "project_id": prj_main["id"] if key in ("site_engineer", "project_manager") else None,
                                   "branch_id_at": PDR if key not in ("site_engineer", "project_manager") else None,
                                   "in_gps": {"lat": 11.2755 + R.uniform(-0.002, 0.002), "lng": 77.5871 + R.uniform(-0.002, 0.002)} if key not in ("site_engineer",) else {"lat": prj_main["gps"]["lat"] + (0.01 if k == 3 else 0.0005), "lng": prj_main["gps"]["lng"]}})
    for key, lt, f, t_, st in [("site_engineer", "casual", 3, 4, "pending"), ("sales", "sick", -6, -5, "approved"), ("store", "earned", 10, 14, "pending"), ("technician", "casual", -20, -20, "approved")]:
        lv = await C("leaves", {"employee_id": EMP[key]["id"], "ltype": lt, "from_date": day(f), "to_date": day(t_), "reason": "Family function" if lt != "sick" else "Fever"}, U[key])
        if st == "approved":
            await approve("leaves", lv, U[key], U["hr"])
        else:
            await ENG.submit_for_approval(ENG.ent("leaves"), await db.leaves.find_one({"id": lv["id"]}, {"_id": 0}), U[key])
    import routes_ops as RO
    prev_month = (T.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    run = await RO.payroll_generate({"month": prev_month}, U["hr"])
    await approve("payroll_runs", run, U["hr"], boss)
    await A("payroll_runs", run["id"], "pay", U["accounts"])
    # marketing
    for nm, ch, sp in [("Google Ads — HT substation (Oct)", "google_ads", 42000), ("Meta lead ads — solar", "meta", 18000), ("IndiaMART subscription", "indiamart", 25000), ("Exhibition — Erode industrial expo", "event", 60000)]:
        await C("campaigns", {"name": nm, "channel": ch, "start": day(-75), "end": day(15), "spend": sp, "utm_campaign": "ht-substation-oct" if ch == "google_ads" else None})
    for lab, kind in [("Site board — Kaveri project", "site_board"), ("Van — TN 33 BK 4521", "van"), ("Company brochure", "brochure")]:
        q = await C("qr_codes", {"label": lab, "kind": kind, "target": "/get-quote"})
        await db.qr_codes.update_one({"id": q["id"]}, {"$set": {"scans": R.randint(8, 60), "leads": R.randint(1, 6)}})
    for (nm, cat, auth, num, days) in [("Electrical contractor licence (Grade A)", "licence", "Electrical Licensing Board", "EA/0000/sample", 140), ("GST registration", "tax", "GSTN", "33XXXXX0000X1Z5", 9999),
                                       ("Contractor's all-risk (CAR) policy", "insurance", "Sample Insurance Co.", "CAR/26/0001", 22), ("Workmen's compensation policy", "insurance", "Sample Insurance Co.", "WC/26/0007", 75),
                                       ("Public liability insurance", "insurance", "Sample Insurance Co.", "PL/26/0003", 190), ("PF registration", "tax", "EPFO", "TN/CBE/0000000", 9999),
                                       ("ISO 9001 surveillance audit", "iso", "Certification body", "QMS-000", 48), ("Factory licence — Perundurai store", "licence", "DISH", "FL/0000", -6)]:
        await C("compliance_items", {"name": nm, "category": cat, "authority": auth, "number": num, "valid_until": day(days), "remind_days": 30, "owner_id": acc_u["id"]})
    for a in (ACC[0], ACC[2]):
        await C("tasks", {"title": f"Collect TDS certificate from {a['name']}", "assigned_to": acc_u["id"], "due_on": day(R.randint(-2, 6)), "priority": "normal"})
    await C("tasks", {"title": "Prepare CEIG inspection file — Velavan Polymers", "assigned_to": U["liaison"]["id"], "due_on": day(2), "priority": "high", "project_id": PJ[3][0]["id"]})
    await C("tasks", {"title": "Update S-curve and send weekly report to Kaveri", "assigned_to": pm["id"], "due_on": day(1), "priority": "normal", "project_id": prj_main["id"]})
    await C("vendor_registrations", {"company": "Vetri Electricals", "vtype": "subcontractor", "trade": "HT jointing, cable laying", "phone": "+919443300011", "town": "Namakkal"})
    for nm, ph, exp_y, rl in [("Karthikeyan R", "+919876000111", 4, "Site engineer"), ("Sowmya M", "+919876000222", 2, "Estimation engineer")]:
        job = await db.jobs.find_one({"title": {"$regex": rl}}, {"_id": 0})
        await C("job_applications", {"job_id": job["id"] if job else None, "name": nm, "phone": ph, "experience_years": exp_y, "current_role": rl})

    # ------------------------------------------------------------------ portal logins
    client_acc = ACC[0]
    await mk_user("client", "Ganesan (Kaveri Spinning Mills)", "client", account_id=client_acc["id"], phone="+919000000201")
    await mk_user("consultant", consultant_contact["name"], "consultant", contact_id=consultant_contact["id"], phone="+919500000101")
    await mk_user("vendor", "Kongu Cables & Wires", "vendor", vendor_id=V["Kongu Cables & Wires"]["id"])
    await mk_user("subcontractor", "Karthik Electricals", "subcontractor", vendor_id=sub["id"])
    await mk_user("partner", partners[0]["name"], "partner", partner_id=partners[0]["id"])
    # a client payment notice and a client service request
    if inv_open:
        await db.receipts.insert_one({"id": new_id(), "code": "RCT-PENDING-1", "account_id": client_acc["id"], "date": day(0), "amount": round(float(inv_open.get("balance") or 0) / 2, 2), "mode": "neft",
                                      "reference": "UTR998877665", "allocations": [{"invoice_id": inv_open["id"], "amount": round(float(inv_open.get("balance") or 0) / 2, 2)}],
                                      "status": "pending", "notes": "Payment notice from the client portal", "created_at": now_iso(), "deleted": False, "branch_id": inv_open.get("branch_id")})
    # vault samples (only when VAULT_KEY is set)
    import routes_vault as RV
    if RV.configured():
        for preset, login, title in (("tnpdcl", "kaveri-ht-0421", "TNPDCL: Kaveri Spinning Mills HT service"), ("gem", "sapowerinfra-gem", "GeM seller account"),
                                     ("gst", "spi-gst-admin", "GST portal"), ("tntenders", "spi-tender-01", "Tamil Nadu tenders portal")):
            p_ = RV.PRESET[preset]
            iid = new_id()
            secret = {"password": f"Sample-{R.randint(1000, 9999)}!", "totp": "", "notes": "Sample login for the preview", "fields": []}
            await db.vault_items.insert_one({"id": iid, "title": title, "preset": preset, "category": p_["category"], "url": p_["url"], "username": login,
                                             "fields_public": [], "secret_labels": [], "secret": RV.encrypt(iid, secret), "has_password": True, "has_totp": False,
                                             "has_notes": True, "property_ids": [], "share_roles": ["director", "accounts", "liaison", "tender_exec"], "share_users": [],
                                             "rotate_days": p_.get("rotate_days"), "tags": ["sample"], "password_changed_at": (datetime.now(IST) - timedelta(days=R.randint(20, 120))).isoformat(),
                                             "created_by": boss["id"], "created_by_name": boss["name"], "created_at": now_iso(), "updated_at": now_iso(), "deleted": False})
    await seed_history(DONE, V, U, boss)
    await settle_created_at()
    clear_settings_cache()


async def seed_history(DONE, V, U, boss):
    """Earlier months: final bills and receipts for finished projects, their material bills and payments, and payroll,
    so cash flow, profit and receivables have a believable past."""
    acc_u = U["accounts"]
    sup = [V[n] for n in ("Kongu Cables & Wires", "Bhavani Transformers Pvt Ltd", "Annai Panel Builders", "Shakthi Switchgear Traders")]
    for k, (p, start_d, end_d) in enumerate(DONE):
        if (T - end_d).days > 205:
            continue
        cv = float(p["contract_value"])
        for frac, when, label_ in ((0.6, end_d - timedelta(days=40), "Supply and erection (60%)"), (0.4, end_d + timedelta(days=8), "Testing, commissioning and handover (40%)")):
            if when > T - timedelta(days=3):
                when = T - timedelta(days=3)
            inv = await C("invoices", {"itype": "tax_invoice", "account_id": p["account_id"], "project_id": p["id"], "date": when.isoformat(), "due_date": (when + timedelta(days=30)).isoformat(),
                                       "branch_id": p.get("branch_id"), "lines": [{"description": f"{p['name']}: {label_}", "hsn": "995461", "qty": 1, "unit": "ls", "rate": round(cv * frac, -2), "gst_rate": "18"}]}, acc_u)
            inv = await A("invoices", inv["id"], "issue", acc_u)
            paid_on = when + timedelta(days=R.randint(18, 40))
            if paid_on <= T - timedelta(days=1):
                await C("receipts", {"account_id": p["account_id"], "date": paid_on.isoformat(), "amount": inv["receivable"], "mode": "neft",
                                     "reference": f"UTR{R.randint(10 ** 9, 10 ** 10)}", "allocations": [{"invoice_id": inv["id"], "amount": inv["receivable"]}]}, acc_u)
        bill_d = start_d + timedelta(days=min(20, max(1, (end_d - start_d).days // 3)))
        v = sup[k % len(sup)]
        vb = await C("vendor_bills", {"vendor_id": v["id"], "project_id": p["id"], "bill_no": f"INV/{R.randint(1000, 9999)}", "bill_date": bill_d.isoformat(),
                                      "lines": [{"description": f"Material for {p['name']}", "qty": 1, "rate": round(cv * R.uniform(0.5, 0.6), -2), "gst_rate": "18"}], "tds_pct": 0}, acc_u)
        vb = await A("vendor_bills", vb["id"], "verify", acc_u)
        pay_d = bill_d + timedelta(days=R.randint(25, 45))
        if pay_d <= T - timedelta(days=1):
            pay = await C("vendor_payments", {"vendor_id": v["id"], "vendor_bill_id": vb["id"], "date": pay_d.isoformat(), "amount": vb["payable"], "mode": "neft"}, acc_u)
            pay = await approve("vendor_payments", pay, acc_u, boss)
            await A("vendor_payments", pay["id"], "pay", acc_u, {"reference": f"UTR{R.randint(10 ** 9, 10 ** 10)}"})
    # monthly progress snapshots (the scheduler records these at each month end; backfilled for the sample projects)
    import routes_ops as RO_
    for p in await db.projects.find({"status": {"$in": ["in_progress", "testing", "on_hold", "mobilising"]}}, {"_id": 0}).to_list(50):
        curve = await RO_.s_curve(p)
        now_mk = T.strftime("%Y-%m")
        plan_now = next((c["planned"] for c in curve if c["month"] == now_mk), None) or 1
        ratio = min(1.15, float(p.get("percent_complete") or 0) / plan_now) if plan_now else 1
        for c in curve:
            if c["month"] < now_mk and c["planned"] > 0:
                await db.project_progress.insert_one({"id": new_id(), "project_id": p["id"], "month": c["month"], "percent": round(min(c["planned"] * ratio * R.uniform(0.93, 1.03), 100), 1)})
    run = await db.payroll_runs.find_one({"status": "paid"}, {"_id": 0})
    if run:
        for back in range(2, 7):
            mk = (T.replace(day=1) - timedelta(days=30 * back - 15)).strftime("%Y-%m")
            if await db.payroll_runs.find_one({"month": mk}):
                continue
            await db.payroll_runs.insert_one({**run, "id": new_id(), "month": mk, "code": f"{run.get('code', 'PAY')}-{mk}", "created_at": f"{mk}-28T17:00:00+05:30", "updated_at": f"{mk}-28T17:00:00+05:30"})


async def settle_created_at():
    """Records made in one go all carry the same 'created' minute; move each to its own document date so lists read naturally."""
    from registry import E as REG_E
    keys = ("date", "bill_date", "from_date", "start", "start_date", "submitted_on", "period_to", "issued_on", "valid_from", "month")
    for key in REG_E:
        if key in ("leads", "tickets", "dprs"):
            continue
        async for d in db[key].find({}, {"_id": 0, "id": 1, "created_at": 1, **{k: 1 for k in keys}}):
            dv = next((d[k] for k in keys if isinstance(d.get(k), str) and len(d[k]) >= 7), None)
            if not dv:
                continue
            dv = dv + "-01" if len(dv) == 7 else dv[:10]
            if dv >= str(d.get("created_at") or "")[:10]:
                continue
            t = f"{dv}T{R.randint(9, 18):02d}:{R.randint(0, 59):02d}:00+05:30"
            await db[key].update_one({"id": d["id"]}, {"$set": {"created_at": t, "updated_at": t}})
    # requests waiting for approval were raised over the last few days, not all in the same minute
    async for a in db.approvals.find({"status": "pending"}, {"_id": 0, "id": 1, "doc_entity": 1, "doc_id": 1}):
        t = (datetime.now(IST) - timedelta(minutes=R.randint(90, 4 * 24 * 60))).isoformat()
        await db.approvals.update_one({"id": a["id"]}, {"$set": {"created_at": t}})
        await db[a["doc_entity"]].update_one({"id": a["doc_id"]}, {"$set": {"submitted_at": t}})


def item_by_id(items, iid):
    return next(i for i in items if i["id"] == iid)


def label(svc):
    from catalog import label_of
    return label_of("services", svc)
