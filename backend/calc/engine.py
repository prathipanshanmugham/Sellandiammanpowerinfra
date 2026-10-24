"""The 24 customer calculators (section 6 of the brief), as pure functions.

Every tool takes (inputs, constants) and returns:
    {"headline": {...}, "status": ok|warn|bad, "verdict": str, "items": [...], "table": {...}|None,
     "steps": [{"label", "formula", "value"}], "notes": [...], "basis": str}
The same functions exist in TypeScript (frontend/src/calc/engine.ts) for instant results in the browser; both are
run against backend/tests/calc_cases.json so they never drift apart. Specs and default constants live in
tools.json and constants.json beside this file (copied to frontend/src/shared/ by scripts/sync_shared.py).
"""
import json
import math
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

HERE = Path(__file__).parent
TOOLS = json.loads((HERE / "tools.json").read_text())
DEFAULTS = json.loads((HERE / "constants.json").read_text())
SPEC = {t["slug"]: t for t in TOOLS["tools"]}
SQ3 = math.sqrt(3)


class CalcError(ValueError):
    pass


# ------------------------------------------------------------------ helpers (mirrored in engine.ts)
def R(x, n=2):
    """Round half away from zero on the shortest decimal form (same as the TypeScript copy)."""
    if x is None:
        return None
    x = float(x)
    if math.isinf(x) or math.isnan(x):
        return x
    s = -1 if x < 0 else 1
    q = Decimal(1).scaleb(-n)
    return s * float(Decimal(repr(abs(x))).quantize(q, rounding=ROUND_HALF_UP))


def next_std(val, ratings):
    for r in ratings:
        if r >= val - 1e-9:
            return r
    return None


def ind(x, d=0):
    """Indian digit grouping: 12,34,567."""
    neg = x < 0
    s = f"{abs(float(R(x, d))):.{d}f}"
    whole, _, frac = s.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    return ("-" if neg else "") + whole + ("." + frac if frac else "")


def g(x):
    """Python's general number format (used in sentences)."""
    return f"{float(x):g}"


def sci(x):
    return "%.2e" % float(x)


def item(label, value, unit=None, fmt=None, tone=None):
    d = {"label": label, "value": value}
    if unit:
        d["unit"] = unit
    if fmt:
        d["fmt"] = fmt
    if tone:
        d["tone"] = tone
    return d


def step(label, formula, value, unit=None):
    d = {"label": label, "formula": formula, "value": value}
    if unit:
        d["unit"] = unit
    return d


def floor_key(table, x):
    """Value for the largest numeric key <= x (or the smallest key)."""
    keys = sorted(table, key=lambda k: float(k))
    best = keys[0]
    for k in keys:
        if float(k) <= x + 1e-9:
            best = k
    return table[best]


def interp(pairs, x):
    if x <= pairs[0][0]:
        return pairs[0][1]
    for (x0, y0), (x1, y1) in zip(pairs, pairs[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pairs[-1][1]


def options_from(name, C):
    if name == "tariffs":
        return [{"value": k, "label": v["label"]} for k, v in C["tariffs"].items()]
    if name == "tariffs_ht":
        return [{"value": k, "label": v["label"]} for k, v in C["tariffs"].items() if v["kind"] == "HT"]
    if name == "transformer_ratings":
        return [{"value": str(k), "label": f"{k} kVA"} for k in C["transformer_ratings"]]
    if name == "solar_towns":
        return [{"value": k, "label": k} for k in C["solar"]["yield_kwh_per_kwp_day"]]
    if name == "cable_sizes":
        keys = sorted(set(C["cable"]["r20_al"]) | set(C["cable"]["r20_cu"]), key=float)
        return [{"value": k, "label": f"{k} mm²"} for k in keys]
    return []


def validate(slug, raw, C):
    spec = SPEC.get(slug)
    if not spec:
        raise CalcError("Unknown calculator")
    out = {}
    raw = raw or {}
    for f in spec["inputs"]:
        k, t = f["k"], f["t"]
        v = raw.get(k, f.get("def"))
        if t == "number":
            if v in (None, ""):
                out[k] = None
                continue
            try:
                v = float(v)
            except (TypeError, ValueError):
                raise CalcError(f"{f['l']}: enter a number")
            if math.isnan(v) or math.isinf(v):
                raise CalcError(f"{f['l']}: enter a number")
            if f.get("min") is not None and v < f["min"]:
                raise CalcError(f"{f['l']}: must be at least {f['min']}")
            if f.get("max") is not None and v > f["max"]:
                raise CalcError(f"{f['l']}: must be at most {f['max']}")
            out[k] = v
        elif t == "select":
            opts = f.get("opts") or options_from(f.get("opts_from"), C)
            v = str(v) if v is not None else None
            if v not in [o["value"] for o in opts]:
                raise CalcError(f"{f['l']}: choose one of the options")
            out[k] = v
        elif t == "bool":
            out[k] = v in (True, "true", 1, "1", "yes")
        elif t == "series":
            if not isinstance(v, list) or not v:
                raise CalcError(f"{f['l']}: enter the values")
            try:
                vals = [float(x) for x in v if x not in (None, "")]
            except (TypeError, ValueError):
                raise CalcError(f"{f['l']}: numbers only")
            if not vals or any(x < 0 for x in vals) or len(vals) > 24:
                raise CalcError(f"{f['l']}: enter up to 24 positive values")
            out[k] = vals
        elif t == "lines":
            rows = []
            for row in (v or [])[:100]:
                r = {}
                for sf in f["fields"]:
                    x = row.get(sf["k"])
                    if sf["t"] == "number":
                        try:
                            x = float(x) if x not in (None, "") else 0.0
                        except (TypeError, ValueError):
                            raise CalcError(f"{f['l']}: {sf['l']} must be a number")
                        if sf.get("min") is not None and x < sf["min"]:
                            raise CalcError(f"{f['l']}: {sf['l']} must be at least {sf['min']}")
                        if sf.get("max") is not None and x > sf["max"]:
                            raise CalcError(f"{f['l']}: {sf['l']} must be at most {sf['max']}")
                    elif sf["t"] == "select":
                        if x not in [o["value"] for o in sf["opts"]]:
                            raise CalcError(f"{f['l']}: choose a {sf['l'].lower()}")
                    else:
                        x = str(x or "")[:80]
                    r[sf["k"]] = x
                rows.append(r)
            out[k] = rows
        else:
            out[k] = str(v or "")[:200]
    return out


def merged_constants(overrides=None):
    C = json.loads(json.dumps(DEFAULTS))
    for k, v in (overrides or {}).items():
        if isinstance(v, dict) and isinstance(C.get(k), dict):
            C[k] = {**C[k], **v}
        else:
            C[k] = v
    return C


def run(slug, raw, overrides=None):
    C = merged_constants(overrides)
    inp = validate(slug, raw, C)
    fn = FUNCS[slug]
    res = fn(inp, C)
    res.setdefault("status", "ok")
    res.setdefault("notes", [])
    res.setdefault("steps", [])
    res.setdefault("items", [])
    res.setdefault("table", None)
    res["basis"] = SPEC[slug]["basis"]
    res["slug"] = slug
    res["title"] = SPEC[slug]["title"]
    res["inputs"] = inp
    res["rates_as_of"] = C.get("rates_as_of")
    return res


# ------------------------------------------------------------------ shared electrical pieces
def tariff_ht_bill(t, units, md, cd, peak_share, night_share, pf, C):
    energy = units * t["energy"]
    tod = 0.0
    if t.get("tod"):
        tod = units * peak_share / 100 * t["energy"] * C["tod"]["peak_surcharge_pct"] / 100 \
            - units * night_share / 100 * t["energy"] * C["tod"]["night_rebate_pct"] / 100
    floor = C["billing_demand_floor_pct"] / 100
    billed = max(md, floor * cd)
    excess = max(md - cd, 0)
    demand = billed * t["demand"] + excess * t["demand"] * (C["excess_demand_multiplier"] - 1)
    pen_pct = pf_penalty_pct(pf, C)
    pf_pen = (energy + tod) * pen_pct / 100
    tax = (energy + tod) * C["electricity_tax_pct"] / 100
    meter = t.get("meter_rent", 0)
    total = energy + tod + demand + pf_pen + tax + meter
    return {"energy": energy, "tod": tod, "demand": demand, "billed_kva": billed, "excess_kva": excess,
            "pf_penalty": pf_pen, "pf_penalty_pct": pen_pct, "tax": tax, "meter_rent": meter, "total": total}


def lt_fixed_rate(t, kw):
    for limit, rate in t["fixed_slabs"]:
        if kw <= limit:
            return rate
    return t["fixed_slabs"][-1][1]


def tariff_lt_bill(t, units, load_kw, C):
    if "energy_low" in t and units <= t["low_units"]:
        energy = units * t["energy_low"]
    else:
        energy = units * t["energy"]
    fixed = load_kw * lt_fixed_rate(t, load_kw)
    tax = energy * C["electricity_tax_pct"] / 100
    total = energy + fixed + tax
    return {"energy": energy, "fixed": fixed, "fixed_rate": lt_fixed_rate(t, load_kw), "tax": tax, "total": total}


def pf_penalty_pct(pf, C):
    pf = R(pf, 2)
    thr = C["pf_threshold"]
    if pf >= thr:
        return 0.0
    pct = 0.0
    for band in sorted(C["pf_penalty"], key=lambda b: -b["to"]):
        hi, lo = band["to"], band["from"]
        if pf >= hi:
            continue
        low = max(pf, lo)
        steps_ = round((hi - low) * 100)
        pct += steps_ * band["pct_per_0_01"]
    return pct


def cable_r90(C, conductor, size):
    tab = C["cable"]["r20_al" if conductor == "al" else "r20_cu"]
    if str(size) not in tab:
        raise CalcError(f"{size} mm² is not available in {'aluminium' if conductor == 'al' else 'copper'}")
    a = C["cable"]["alpha"][conductor]
    return tab[str(size)] * (1 + a * (90 - 20))


def vdrop(current, length_m, r, x, pf, phase3=True, runs=1):
    sin = math.sqrt(max(0.0, 1 - pf * pf))
    k = SQ3 if phase3 else 2
    return k * current * (length_m / 1000) * (r * pf + x * sin) / runs


def sizes_of(C, key):
    return sorted(C["cable"][key].keys(), key=float)


def derating(C, laying, ambient, group, spacing, soil, depth, ht):
    cab = C["cable"]
    base = cab["base_temp"]["ground" if laying == "ground" else "air"]
    tmax = cab["max_temp"]["xlpe"]
    if ambient >= tmax:
        raise CalcError("Temperature too high for the cable")
    kt = math.sqrt((tmax - ambient) / (tmax - base))
    n = int(group)
    if laying == "ground":
        kg = floor_key(cab["group_ground_touching" if spacing == "touching" else "group_ground_spaced"], n)
        kd = cab["depth"][str(depth)] / (cab["depth"]["90"] if ht else 1.0)
        ks = cab["soil"][str(soil)]
    else:
        kg = floor_key(cab["group_air_tray"], n)
        kd = 1.0
        ks = 1.0
    if n > 1 and kg == 1.0:
        kg = floor_key(cab["group_air_tray"], n)
    return {"temp": kt, "group": kg, "depth": kd, "soil": ks, "total": kt * kg * kd * ks}


def select_cable(C, current, volts, pf, length, conductor, laying, ambient, group, spacing, soil, depth, vd_limit, fault_ka, clear_s):
    ht = volts >= 1000
    key = "al_xlpe_ht" if ht else ("al_xlpe" if conductor == "al" else "cu_xlpe")
    cond = "al" if ht else conductor
    der = derating(C, laying, ambient, group, spacing, soil, depth, ht)
    idx = 0 if laying == "ground" else 1
    x = C["cable"]["x_ohm_km"]["ht" if ht else "lt"]
    k_sc = C["cable"]["k_short_circuit"][("al" if cond == "al" else "cu") + "_xlpe"]
    phase3 = volts != 230
    rows = []
    chosen = None
    for runs in range(1, 9):
        for s in sizes_of(C, key):
            if runs > 1 and float(s) < 95:
                continue
            rated = C["cable"][key][s][idx] * der["total"]
            r = cable_r90(C, cond, s)
            vd = vdrop(current, length, r, x, pf, phase3, runs)
            vd_pct = vd / volts * 100
            s_min = fault_ka * 1000 * math.sqrt(clear_s) / k_sc / runs if fault_ka else 0
            ok_i = rated * runs >= current
            ok_v = vd_pct <= vd_limit + 1e-9
            ok_s = float(s) >= s_min - 1e-9
            if runs == 1 or (chosen is None and runs > 1):
                rows.append({"size": s, "runs": runs, "rated": rated * runs, "vd_pct": vd_pct, "s_min": s_min,
                             "ok": ok_i and ok_v and ok_s, "ok_i": ok_i, "ok_v": ok_v, "ok_s": ok_s})
            if ok_i and ok_v and ok_s:
                chosen = {"size": s, "runs": runs, "rated": rated * runs, "vd_pct": vd_pct, "vd": vd, "s_min": s_min, "r": r, "x": x}
                break
        if chosen:
            break
    return {"chosen": chosen, "derating": der, "rows": rows[:16], "key": key, "cond": cond, "k_sc": k_sc, "x": x}


def motor_eff_pf(C, kw):
    e, p = floor_key(C["motor_eff_pf"], kw)
    return e, p


def fmt_size(s, runs):
    return f"{runs} × {s} mm²" if runs > 1 else f"{s} mm²"


# ------------------------------------------------------------------ 1 connected load & maximum demand
def t_connected_load(i, C):
    pf = i["pf"]
    steps = []
    if i["method"] == "area":
        density = C["load_density_va_sqm"][i["building"]]
        conn_kva = i["area"] * density / 1000
        conn_kw = conn_kva * pf
        sum_dmd = conn_kw
        steps.append(step("Connected load", f"{i['area']:g} m² × {density} VA/m² × PF {g(pf)}", R(conn_kw, 1), "kW"))
        table = None
    else:
        conn_kw = 0.0
        sum_dmd = 0.0
        rows = []
        for ln in i["loads"]:
            tot = ln["qty"] * ln["kw"]
            dmd = tot * ln["df"]
            conn_kw += tot
            sum_dmd += dmd
            rows.append([ln["name"] or "Load", R(ln["qty"], 2), R(ln["kw"], 2), R(tot, 2), R(ln["df"], 2), R(dmd, 2)])
        steps.append(step("Connected load", "Σ qty × kW", R(conn_kw, 2), "kW"))
        steps.append(step("Sum of individual demands", "Σ qty × kW × demand factor", R(sum_dmd, 2), "kW"))
        table = {"title": "Load list", "columns": ["Load", "Qty", "kW each", "Total kW", "Demand factor", "Demand kW"], "rows": rows}
    md_kw = sum_dmd * i["diversity"]
    steps.append(step("Maximum demand now", f"{g(R(sum_dmd, 2))} × simultaneity {g(i['diversity'])}", R(md_kw, 2), "kW"))
    md_future = md_kw * (1 + i["growth"] / 100)
    steps.append(step("With growth", f"{g(R(md_kw, 2))} × (1 + {i['growth']:g}%)", R(md_future, 2), "kW"))
    md_kva = md_future / pf
    steps.append(step("Maximum demand", f"{g(R(md_future, 2))} kW ÷ PF {g(pf)}", R(md_kva, 2), "kVA"))
    lt_max = C["lt_max_kw"]
    if md_future <= lt_max:
        supply = "LT"
        verdict = f"LT supply works: your maximum demand of {R(md_future, 1):g} kW is within the {lt_max} kW LT limit in Tamil Nadu."
        if md_future > C["lt_ct_min_kw"]:
            verdict += " Expect CT-operated (LT-CT) metering at this size."
        sugg = item("Suggested LT sanctioned load", math.ceil(conn_kw), "kW", "int")
        status = "ok"
    else:
        supply = "HT"
        verdict = f"HT supply needed: {R(md_future, 1):g} kW is above the {lt_max} kW LT limit in Tamil Nadu."
        sugg = item("Suggested contract demand", int(math.ceil(md_kva / 5) * 5), "kVA", "int")
        status = "warn"
    tx = next_std(md_kva / 0.8, C["transformer_ratings"])
    items = [item("Connected load", R(conn_kw, 1), "kW", "1dp"), item("Maximum demand now", R(md_kw, 1), "kW", "1dp"),
             item("Maximum demand with growth", R(md_future, 1), "kW", "1dp"), item("Maximum demand", R(md_kva, 1), "kVA", "1dp"),
             item("Supply", supply, tone="accent"), sugg]
    if supply == "HT":
        items.append(item("Transformer (≤80% loading)", f"{tx} kVA" if tx else "More than 2500 kVA — split across transformers"))
    return {"headline": {"label": "Maximum demand", "value": R(md_kva, 1), "unit": "kVA", "sub": f"{supply} supply"},
            "status": status, "verdict": verdict, "items": items, "table": table, "steps": steps,
            "notes": ["Demand and simultaneity factors are typical; your actual running pattern matters. A site survey firms this up.",
                      "LT limit and metering per the TNERC supply code; verify for your area."]}


# ------------------------------------------------------------------ 2 LT vs HT
def t_lt_vs_ht(i, C):
    lt_key, ht_key = ("LT_IIIB", "HT_I") if i["category"] == "industrial" else ("LT_V", "HT_III")
    lt_t, ht_t = C["tariffs"][lt_key], C["tariffs"][ht_key]
    md_kva, units, pf = i["md_kva"], i["units"], i["pf"]
    md_kw = md_kva * pf
    tx = next_std(md_kva / 0.8, C["transformer_ratings"]) or C["transformer_ratings"][-1]
    nll, ll = C["transformer_losses"].get(str(tx), [0, 0])
    avg_kva = units / 720 / pf
    frac = avg_kva / tx
    loss_kwh = (nll + ll * frac * frac) * 720 / 1000
    ht = tariff_ht_bill(ht_t, units + loss_kwh, md_kva, md_kva, i["peak_share"], i["night_share"], pf, C)
    lt_ok = md_kw <= C["lt_max_kw"]
    lt = tariff_lt_bill(lt_t, units, md_kw, C) if lt_ok else None
    cost = i["substation_cost"]
    if cost is None:
        rate = next(r for lim, r in C["substation_cost_per_kva"] if tx <= lim)
        cost = tx * rate
        cost_note = f"typical {tx} kVA substation at ₹{ind(rate)}/kVA"
    else:
        cost_note = "your figure"
    steps = [step("Transformer for HT", f"{R(md_kva, 1):g} kVA ÷ 0.8 → next standard", tx, "kVA"),
             step("Transformer losses billed on HT side", f"({nll} + {ll} × {g(R(frac, 3))}²) W × 720 h", R(loss_kwh, 0), "kWh/month"),
             step("HT monthly bill", "energy + ToD + demand + tax + meter rent", R(ht["total"], 0), "₹")]
    rows = [["Energy", R(lt["energy"], 0) if lt else "—", R(ht["energy"], 0)],
            ["Fixed / demand charges", R(lt["fixed"], 0) if lt else "—", R(ht["demand"], 0)],
            ["Time-of-day (peak +, night −)", 0 if lt else "—", R(ht["tod"], 0)],
            ["Electricity tax", R(lt["tax"], 0) if lt else "—", R(ht["tax"], 0)],
            ["Meter rent", 0 if lt else "—", R(ht["meter_rent"], 0)],
            ["Monthly total", R(lt["total"], 0) if lt else "—", R(ht["total"], 0)],
            ["Yearly total", R(lt["total"] * 12, 0) if lt else "—", R(ht["total"] * 12, 0)]]
    items = [item("HT yearly bill", R(ht["total"] * 12, 0), "₹", "inr")]
    if lt_ok:
        saving = (lt["total"] - ht["total"]) * 12
        steps.insert(0, step("LT monthly bill", "energy + fixed (per kW slab) + tax", R(lt["total"], 0), "₹"))
        items.insert(0, item("LT yearly bill", R(lt["total"] * 12, 0), "₹", "inr"))
        items.append(item("Yearly difference (LT − HT)", R(saving, 0), "₹", "inr", "good" if saving > 0 else "bad"))
        items.append(item("Substation cost", R(cost, 0), "₹", "inr"))
        if saving > 0:
            payback = cost / saving
            items.append(item("Payback", R(payback, 1), "years", "1dp", "good" if payback <= 5 else None))
            steps.append(step("Payback", f"₹{ind(R(cost, 0))} ÷ ₹{ind(R(saving, 0))} per year", R(payback, 1), "years"))
            verdict = f"HT saves about ₹{g(R(saving / 100000, 2))} lakh a year; the substation pays back in {g(R(payback, 1))} years."
            status = "ok" if payback <= 5 else "warn"
        else:
            verdict = "LT is cheaper to run at this load; HT doesn't pay back."
            status = "warn"
    else:
        verdict = f"HT is required: {R(md_kw, 1):g} kW is above the {C['lt_max_kw']} kW LT limit."
        status = "warn"
        items.append(item("Substation cost", R(cost, 0), "₹", "inr"))
    diff_y = (lt["total"] - ht["total"]) * 12 if lt_ok else 0
    head_label = ("HT saves per year" if diff_y > 0 else "LT saves per year") if lt_ok else "HT yearly bill"
    return {"headline": {"label": head_label, "value": R(abs(diff_y) if lt_ok else ht["total"] * 12, 0), "unit": "₹", "fmt": "inr"},
            "status": status, "verdict": verdict, "items": items,
            "table": {"title": f"Monthly bill: {lt_t['label'].split(' —')[0]} vs {ht_t['label'].split(' —')[0]}", "columns": ["", "LT ₹", "HT ₹"], "rows": rows},
            "steps": steps, "notes": [f"Substation cost: {cost_note}.", f"Rates: {C['tariff_order']}.",
                                      "HT is metered on the HT side, so transformer losses are added to HT units."]}


# ------------------------------------------------------------------ 3 bill estimator
def t_bill_estimator(i, C):
    t = C["tariffs"][i["tariff"]]
    if t["kind"] == "HT":
        b = tariff_ht_bill(t, i["units"], i["md_kva"], i["cd_kva"], i["peak_share"], i["night_share"], i["pf"], C)
        rows = [["Energy", f"{ind(i['units'])} kWh × ₹{t['energy']}", R(b["energy"], 0)],
                ["Time-of-day", f"peak +{C['tod']['peak_surcharge_pct']}% on {i['peak_share']:g}%, night −{C['tod']['night_rebate_pct']}% on {i['night_share']:g}%", R(b["tod"], 0)],
                ["Demand charges", f"{R(b['billed_kva'], 1):g} kVA × ₹{t['demand']}" + (f" + excess {R(b['excess_kva'], 1):g} kVA" if b["excess_kva"] else ""), R(b["demand"], 0)],
                ["PF penalty", f"{b['pf_penalty_pct']:g}% of energy charges" if b["pf_penalty_pct"] else "PF ≥ 0.90 — none", R(b["pf_penalty"], 0)],
                ["Electricity tax", f"{C['electricity_tax_pct']}% of energy + ToD", R(b["tax"], 0)],
                ["Meter rent", "", R(b["meter_rent"], 0)],
                ["Total", "", R(b["total"], 0)]]
        notes = []
        if b["excess_kva"]:
            notes.append(f"Demand exceeded the contract demand by {R(b['excess_kva'], 1):g} kVA — excess is charged at {C['excess_demand_multiplier']}× the rate.")
        if b["pf_penalty_pct"]:
            notes.append("Improve power factor to 0.90 or above to avoid the penalty — see the Power factor correction tool.")
        status = "warn" if (b["excess_kva"] or b["pf_penalty_pct"]) else "ok"
        unit_rate = b["total"] / i["units"] if i["units"] else 0
    else:
        b = tariff_lt_bill(t, i["units"], i["load_kw"], C)
        rows = [["Energy", f"{ind(i['units'])} kWh", R(b["energy"], 0)],
                ["Fixed charges", f"{i['load_kw']:g} kW × ₹{b['fixed_rate']}", R(b["fixed"], 0)],
                ["Electricity tax", f"{C['electricity_tax_pct']}% of energy", R(b["tax"], 0)],
                ["Total", "", R(b["total"], 0)]]
        notes, status = [], "ok"
        if i["load_kw"] > C["lt_max_kw"]:
            notes.append(f"LT supply is limited to {C['lt_max_kw']} kW; above this an HT connection is needed.")
            status = "warn"
        unit_rate = b["total"] / i["units"] if i["units"] else 0
    notes.append(f"Rates: {C['tariff_order']}. Fuel and other surcharges, if any, are not included.")
    return {"headline": {"label": "Estimated monthly bill", "value": R(b["total"], 0), "unit": "₹", "fmt": "inr"},
            "status": status, "verdict": f"About ₹{g(R(unit_rate, 2))} per unit all-in.",
            "items": [item("Monthly bill", R(b["total"], 0), "₹", "inr"), item("Average cost per unit", R(unit_rate, 2), "₹/kWh", "2dp")],
            "table": {"title": t["label"], "columns": ["Charge", "How", "₹"], "rows": rows}, "steps": [], "notes": notes}


# ------------------------------------------------------------------ 4 contract demand optimiser
def t_contract_demand(i, C):
    t = C["tariffs"][i["tariff"]]
    rate = t["demand"]
    floor = C["billing_demand_floor_pct"] / 100
    mult = C["excess_demand_multiplier"]
    mds = i["md"]

    def cost(cd):
        return sum(max(m, floor * cd) * rate + max(m - cd, 0) * rate * (mult - 1) for m in mds)

    peak = max(mds)
    lo = int(math.floor(peak * 0.7 / 5) * 5) or 5
    hi = int(math.ceil(peak * 1.3 / 5) * 5)
    best_cd, best = None, None
    for cd in range(lo, hi + 1, 5):
        c = cost(cd)
        if best is None or c < best - 1e-6:
            best_cd, best = cd, c
    now = cost(i["cd_kva"])
    saving = now - best
    rows = []
    for n, m in enumerate(mds, 1):
        rows.append([f"Month {n}", R(m, 1), R(max(m, floor * i["cd_kva"]), 1), R(max(m, floor * best_cd), 1),
                     R(max(m - best_cd, 0), 1)])
    over = sum(1 for m in mds if m > best_cd)
    return {"headline": {"label": "Best contract demand", "value": best_cd, "unit": "kVA"},
            "status": "ok" if saving > 0 else "ok",
            "verdict": (f"Changing the contract demand from {i['cd_kva']:g} to {best_cd} kVA saves about ₹{ind(R(saving, 0))} a year in demand charges."
                        if saving > 1 else f"Your present contract demand of {i['cd_kva']:g} kVA is already close to the best."),
            "items": [item("Present yearly demand charges", R(now, 0), "₹", "inr"), item("At the best contract demand", R(best, 0), "₹", "inr"),
                      item("Yearly saving", R(saving, 0), "₹", "inr", "good" if saving > 0 else None),
                      item("Highest recorded demand", R(peak, 1), "kVA", "1dp"), item("Months above the new CD", over, None, "int", "warn" if over else None)],
            "table": {"title": "Billing demand by month (kVA)", "columns": ["Month", "Recorded", f"Billed at {i['cd_kva']:g}", f"Billed at {best_cd}", "Excess at new CD"], "rows": rows},
            "steps": [step("Billing demand", f"higher of recorded MD or {C['billing_demand_floor_pct']}% of CD", "per month"),
                      step("Excess demand", f"above CD, charged at {g(mult)}× ₹{rate}/kVA", "per month"),
                      step("Search", f"CD from {lo} to {hi} kVA in 5 kVA steps", f"{best_cd} kVA")],
            "notes": ["Keep some margin for growth; repeated excess demand can also lead to notices from TNPDCL.",
                      "A change of contract demand needs an application and may have a minimum period. We can file it for you."]}


# ------------------------------------------------------------------ 5 HT roadmap
def t_ht_roadmap(i, C):
    w = C["ht_roadmap_weeks"]
    steps_list = [("Application to TNPDCL and feasibility / field inspection", w["application_to_feasibility"]),
                  ("Estimate issued and paid (line extension, supervision charges, deposit)", w["estimate_payment"]),
                  ("CEIG drawing approval for the substation", w["ceig_drawing_approval"]),
                  ("Substation works: transformer, HT panel / RMU, cabling, earthing, LT panel", w["works"]),
                  ("Testing, CEIG inspection, meter fixing and energisation", w["inspection_energisation"])]
    lo = sum(s[1][0] for s in steps_list)
    hi = sum(s[1][1] for s in steps_list)
    tx = next_std(i["kva"] / 0.8, C["transformer_ratings"]) or C["transformer_ratings"][-1]
    rate = next(r for lim, r in C["substation_cost_per_kva"] if tx <= lim)
    sub_cost = tx * rate
    rows = [[n + 1, s[0], f"{s[1][0]}–{s[1][1]} weeks"] for n, s in enumerate(steps_list)]
    return {"headline": {"label": "Typical time to energise", "value": f"{lo}–{hi}", "unit": "weeks"},
            "verdict": f"A {i['kva']:g} kVA {i['voltage'].replace('kV', ' kV')} service typically takes {lo}–{hi} weeks from application to energisation; some steps run in parallel.",
            "items": [item("Transformer (≤80% loading)", f"{tx} kVA"), item("Indicative substation cost (our scope)", R(sub_cost, 0), "₹", "inr"),
                      item("Time", f"{lo}–{hi} weeks")],
            "table": {"title": "Steps", "columns": ["#", "Step", "Typical time"], "rows": rows},
            "checklist": TOOLS["checklists"]["new_ht" if i["kind"] != "load_increase" else "load_change"],
            "steps": [], "notes": ["Times depend on the TNPDCL section office, line distance and CEIG workload.",
                                   "TNPDCL line extension and deposits are billed by TNPDCL and are not in the substation cost."]}


# ------------------------------------------------------------------ 6 transformer sizing
def t_transformer_sizing(i, C):
    md_kw = i["load_kw"] * i["demand_factor"]
    md_kva = md_kw / i["pf"]
    fut = md_kva * (1 + i["growth"] / 100)
    need = fut / (i["max_loading"] / 100)
    rating = next_std(need, C["transformer_ratings"])
    steps = [step("Maximum demand", f"{i['load_kw']:g} kW × {g(i['demand_factor'])} ÷ PF {g(i['pf'])}", R(md_kva, 1), "kVA"),
             step("With growth", f"× (1 + {i['growth']:g}%)", R(fut, 1), "kVA"),
             step("Rating needed", f"÷ {i['max_loading']:g}% loading", R(need, 1), "kVA")]
    if rating is None:
        n = math.ceil(need / 2500)
        return {"headline": {"label": "Transformers", "value": f"{n} × 2500", "unit": "kVA"}, "status": "warn",
                "verdict": f"{R(need, 0):g} kVA is beyond one standard distribution transformer; use {n} units or a power transformer.",
                "items": [item("Rating needed", R(need, 0), "kVA", "int")], "steps": steps, "notes": []}
    load_now = md_kva / rating * 100
    load_fut = fut / rating * 100
    nll, ll = C["transformer_losses"].get(str(rating), [0, 0])
    loss_now = nll + ll * (load_now / 100) ** 2
    ttype = "Dry type (cast resin)" if i["location"] == "indoor" else "Oil-filled (ONAN)"
    return {"headline": {"label": "Transformer", "value": rating, "unit": "kVA", "sub": ttype},
            "verdict": f"{rating} kVA {'dry-type' if i['location'] == 'indoor' else 'oil-filled'} transformer: {R(load_now, 0):g}% loaded today and {R(load_fut, 0):g}% after growth.",
            "items": [item("Maximum demand", R(md_kva, 1), "kVA", "1dp"), item("With growth", R(fut, 1), "kVA", "1dp"),
                      item("Standard rating", rating, "kVA", "int", "accent"), item("Loading today", R(load_now, 0), "%", "int"),
                      item("Loading after growth", R(load_fut, 0), "%", "int"), item("Type", ttype),
                      item("Losses at today's load (typical)", R(loss_now, 0), "W", "int")],
            "steps": steps, "notes": ["Indoor transformers inside buildings are normally dry type for fire safety.",
                                      "Ratings per IS 1180 up to 2500 kVA; choose an energy-efficiency level by total owning cost."]}


# ------------------------------------------------------------------ 7 transformer losses / TOC
def t_transformer_losses(i, C):
    load = i["avg_load"] / 100
    h = i["hours"]
    rows = []
    best = None
    a = h * i["tariff"] * i["years"] / 1000
    b = a * load * load
    for o in i["options"]:
        kwh = (o["nll"] * h + o["ll"] * load * load * h) / 1000
        yearly = kwh * i["tariff"]
        toc = o["price"] + yearly * i["years"]
        rows.append([o["name"] or "Offer", R(o["price"], 0), R(kwh, 0), R(yearly, 0), R(toc, 0)])
        if best is None or toc < best[1]:
            best = (o["name"] or "Offer", toc)
    if not rows:
        raise CalcError("Add at least one offer")
    rows.sort(key=lambda r: r[4])
    gap = rows[-1][4] - rows[0][4] if len(rows) > 1 else 0
    return {"headline": {"label": "Lowest total owning cost", "value": best[0], "sub": f"₹{ind(R(best[1], 0))} over {i['years']:g} years"},
            "verdict": (f"{best[0]} costs ₹{ind(R(gap, 0))} less over {i['years']:g} years once losses are counted." if gap else f"{best[0]}."),
            "items": [item("Capitalised no-load loss (A)", R(a, 2), "₹ per W", "2dp"), item("Capitalised load loss (B)", R(b, 2), "₹ per W", "2dp")],
            "table": {"title": f"{i['kva']} kVA offers", "columns": ["Offer", "Price ₹", "Losses kWh/yr", "Loss cost ₹/yr", "Total owning cost ₹"], "rows": rows},
            "steps": [step("Yearly loss energy", "(no-load W × hours + load W × loading² × hours) ÷ 1000", "kWh"),
                      step("Total owning cost", f"price + loss cost × {i['years']:g} years", "₹"),
                      step("Equivalent", "TOC = price + A × no-load W + B × load W", f"A = ₹{g(R(a, 2))}, B = ₹{g(R(b, 2))}")],
            "notes": ["Simple (undiscounted) comparison. Use the maker's guaranteed losses from the offer."]}


# ------------------------------------------------------------------ 8 DG sizing
def t_dg_sizing(i, C):
    run_kva = i["running_kw"] / i["pf"]
    m_kw = i["motor_kw"]
    if m_kw > 0:
        eff, mpf = motor_eff_pf(C, m_kw)
        m_run_kva = m_kw / (eff * mpf)
        mult = C["motor_start_multiple"][i["starter"]]
        m_start = m_run_kva * mult
    else:
        eff = mpf = m_run_kva = m_start = mult = 0
    others = max(run_kva - m_run_kva, 0)
    req1 = run_kva / 0.8
    req2 = (others + m_start) / i["transient"] if m_kw > 0 else 0
    need = max(req1, req2)
    rating = next_std(need, C["dg_ratings"])
    fuel_lph = i["running_kw"] * C["dg_fuel_l_per_kwh"]
    monthly_l = fuel_lph * i["hours"]
    monthly_cost = monthly_l * C["diesel_price"]
    governs = "running load" if req1 >= req2 else "motor starting"
    steps = [step("Running load", f"{i['running_kw']:g} kW ÷ PF {g(i['pf'])}", R(run_kva, 1), "kVA"),
             step("For ≤80% loading", f"{g(R(run_kva, 1))} ÷ 0.8", R(req1, 1), "kVA")]
    if m_kw > 0:
        steps += [step("Largest motor running", f"{m_kw:g} kW ÷ (η {g(eff)} × PF {g(mpf)})", R(m_run_kva, 1), "kVA"),
                  step("Its starting kVA", f"× {g(mult)} ({i['starter'].replace('_', '-')})", R(m_start, 1), "kVA"),
                  step("Step-load check", f"({g(R(others, 1))} + {g(R(m_start, 1))}) ÷ {g(i['transient'])}", R(req2, 1), "kVA")]
    if rating is None:
        return {"headline": {"label": "DG needed", "value": R(need, 0), "unit": "kVA"}, "status": "warn",
                "verdict": "Larger than single standard sets — consider sets in parallel.", "items": [], "steps": steps, "notes": []}
    return {"headline": {"label": "DG set", "value": rating, "unit": "kVA"},
            "verdict": f"A {rating} kVA DG set covers the load; sizing is set by {governs}. It runs at {R(run_kva / rating * 100, 0):g}% loading.",
            "items": [item("Running load", R(run_kva, 1), "kVA", "1dp"), item("Size needed", R(need, 1), "kVA", "1dp"),
                      item("Standard DG rating", rating, "kVA", None, "accent"), item("Loading", R(run_kva / rating * 100, 0), "%", "int"),
                      item("Fuel at this load", R(fuel_lph, 1), "litres/hour", "1dp"), item("Fuel per month", R(monthly_l, 0), "litres", "int"),
                      item("Diesel cost per month", R(monthly_cost, 0), "₹", "inr")],
            "steps": steps, "notes": [f"Fuel at {C['dg_fuel_l_per_kwh']} L/kWh and ₹{C['diesel_price']}/L (typical; check the maker's curve).",
                                      "Stagger large motor starts and keep DG loading above 30% to avoid wet stacking."]}


# ------------------------------------------------------------------ 9 UPS & battery
def t_ups_battery(i, C):
    kva = i["load_kw"] / i["pf"] * (1 + i["growth"] / 100)
    ups = next_std(kva, C["ups_ratings"])
    v = float(i["bank_v"])
    wh = i["load_kw"] * 1000 * i["backup_min"] / 60
    ah = wh / (v * i["eff"] * i["dod"]) * i["ageing"]
    if ah <= C["battery_ah"][-1]:
        block = next_std(ah, C["battery_ah"])
        strings = 1
    else:
        block = C["battery_ah"][-1]
        strings = math.ceil(ah / block)
    per_string = int(v / 12)
    steps = [step("UPS rating", f"{i['load_kw']:g} kW ÷ PF {g(i['pf'])} × (1 + {i['growth']:g}%)", R(kva, 2), "kVA"),
             step("Energy for backup", f"{i['load_kw']:g} kW × {i['backup_min']:g} min", R(wh, 0), "Wh"),
             step("Battery capacity", f"{g(R(wh, 0))} ÷ ({v:g} V × {g(i['eff'])} × {g(i['dod'])}) × {g(i['ageing'])}", R(ah, 1), "Ah")]
    return {"headline": {"label": "UPS", "value": ups or R(kva, 0), "unit": "kVA", "sub": f"{per_string * strings} × 12 V {block} Ah batteries"},
            "verdict": f"{ups} kVA UPS with {strings} string{'s' if strings > 1 else ''} of {per_string} × 12 V {block} Ah batteries ({v:g} V bank).",
            "items": [item("UPS rating", ups, "kVA"), item("Battery capacity needed", R(ah, 1), "Ah", "1dp"),
                      item("Battery block", f"12 V {block} Ah"), item("Batteries per string", per_string, None, "int"),
                      item("Strings in parallel", strings, None, "int"), item("Total batteries", per_string * strings, None, "int")],
            "steps": steps, "notes": ["For backups under an hour, check the maker's constant-power discharge table: batteries deliver less at high rates.",
                                      "Keep the battery room ventilated and at 25 °C for full life."]}


# ------------------------------------------------------------------ 10 solar rooftop
def t_solar_rooftop(i, C):
    s = C["solar"]
    y = s["yield_kwh_per_kwp_day"][i["town"]]
    need = i["monthly_units"] * 12
    k_need = need / (y * 365) if y else 0
    k_roof = i["roof_area"] / s["area_per_kwp_sqm"]
    k_cap = i["sanctioned_kw"]
    limits = [("consumption", k_need), ("roof area", k_roof), ("sanctioned load", k_cap)]
    lim_name, kwp = min(limits, key=lambda x: x[1])
    kwp = math.floor(kwp * 10) / 10 if kwp < 10 else math.floor(kwp)
    gen = kwp * y * 365
    if i["metering"] == "gross":
        saving = gen * i["export_rate"]
        rate_used = i["export_rate"]
    else:
        saving = min(gen, need) * i["tariff"] + max(gen - need, 0) * 0
        rate_used = i["tariff"]
    cost = kwp * i["cost_per_kwp"]
    payback = cost / saving if saving > 0 else None
    life = 0.0
    for yr in range(int(s["life_years"])):
        gy = gen * (1 - s["degradation_pct"] / 100) ** yr
        if i["metering"] == "gross":
            life += gy * rate_used
        else:
            life += min(gy, need) * rate_used * (1 + s["tariff_escalation_pct"] / 100) ** yr
    co2 = gen * C["co2_kg_per_kwh"] / 1000
    steps = [step("Size for your consumption", f"{ind(need)} kWh ÷ ({g(y)} × 365)", R(k_need, 1), "kWp"),
             step("Size your roof allows", f"{i['roof_area']:g} m² ÷ {s['area_per_kwp_sqm']} m²/kWp", R(k_roof, 1), "kWp"),
             step("Allowed by sanctioned load", "≤ sanctioned load", R(k_cap, 1), "kWp"),
             step("Yearly generation", f"{kwp:g} kWp × {g(y)} × 365", R(gen, 0), "kWh")]
    return {"headline": {"label": "Solar plant", "value": kwp, "unit": "kWp", "sub": f"limited by {lim_name}"},
            "verdict": (f"A {kwp:g} kWp plant makes about {R(gen / 1000, 1):g} MWh a year, saving ₹{R(saving / 100000, 2):g} lakh a year with a {R(payback, 1):g}-year payback."
                        if payback else "No savings at these inputs."),
            "items": [item("Plant size", kwp, "kWp", "1dp", "accent"), item("Yearly generation", R(gen, 0), "kWh", "int"),
                      item("Share of your consumption", R(min(gen / need * 100, 100) if need else 0, 0), "%", "int"),
                      item("Yearly saving", R(saving, 0), "₹", "inr"), item("Investment", R(cost, 0), "₹", "inr"),
                      item("Payback", R(payback, 1) if payback else "—", "years", "1dp"), item("25-year savings", R(life, 0), "₹", "inr"),
                      item("CO₂ avoided", R(co2, 1), "tonnes/year", "1dp"), item("Roof area used", R(kwp * s["area_per_kwp_sqm"], 0), "m²", "int")],
            "steps": steps, "notes": [f"Yield for {i['town']}: {g(y)} kWh/kWp/day (typical). Tamil Nadu metering rules and charges change — verify the current order.",
                                      f"CO₂ at {C['co2_kg_per_kwh']} kg/kWh ({C['co2_basis']}).", "Delivered with Sensoper Controls and Renewables, our group's solar company."]}


# ------------------------------------------------------------------ 11 EV chargers
def t_ev_charger_load(i, C):
    tot = 0.0
    rows = []
    for ch in i["chargers"]:
        kw = C["ev_chargers_kw"][ch["type"]]
        rows.append([ch["type"].replace("_", " ").upper().replace(" 3 3", " 3.3").replace(" 7 4", " 7.4"), R(ch["qty"], 0), kw, R(kw * ch["qty"], 1)])
        tot += kw * ch["qty"]
    added_kw = tot * i["diversity"]
    added_kva = added_kw / 0.95
    spare = i["sanctioned_kva"] - i["existing_md"]
    new_md = i["existing_md"] + added_kva
    upgrade = added_kva > spare
    sugg = int(math.ceil(new_md * 1.1 / 5) * 5)
    return {"headline": {"label": "Added demand", "value": R(added_kva, 1), "unit": "kVA", "sub": "upgrade needed" if upgrade else "fits your connection"},
            "status": "warn" if upgrade else "ok",
            "verdict": (f"Your chargers add about {R(added_kva, 0):g} kVA but only {R(spare, 0):g} kVA is spare — apply to raise the load to about {sugg} kVA."
                        if upgrade else f"The chargers fit within your present connection ({R(spare, 0):g} kVA spare)."),
            "items": [item("Charger capacity installed", R(tot, 1), "kW", "1dp"), item("Added demand with diversity", R(added_kw, 1), "kW", "1dp"),
                      item("Added demand", R(added_kva, 1), "kVA", "1dp"), item("Spare on present connection", R(spare, 1), "kVA", "1dp"),
                      item("New maximum demand", R(new_md, 1), "kVA", "1dp"), item("Suggested new sanction", sugg if upgrade else "No change", "kVA" if upgrade else None)],
            "table": {"title": "Chargers", "columns": ["Charger", "Qty", "kW each", "kW total"], "rows": rows},
            "steps": [step("Added demand", f"{g(R(tot, 1))} kW × diversity {g(i['diversity'])} ÷ PF 0.95", R(added_kva, 1), "kVA")],
            "notes": ["Public charging stations can take a separate EV tariff connection (HT V / LT EV) — ask us about separate metering.",
                      "A load management (smart charging) controller can cap the demand without an upgrade."]}


# ------------------------------------------------------------------ 12 cable size
def t_cable_size(i, C):
    v = float(i["voltage"])
    p = i["load_kw"] * 1000
    current = p / (SQ3 * v * i["pf"]) if v != 230 else p / (v * i["pf"])
    sel = select_cable(C, current, v, i["pf"], i["length"], i["conductor"], i["laying"], i["ambient"], i["group"],
                       i["spacing"], i["soil"], i["depth"], i["vd_limit"], i["fault_ka"], i["clear_s"])
    d = sel["derating"]
    ch = sel["chosen"]
    rows = [[f"{r['size']} mm²" + (f" × {r['runs']}" if r["runs"] > 1 else ""), R(r["rated"], 0), R(r["vd_pct"], 2), R(r["s_min"], 1),
             "OK" if r["ok"] else ("Current" if not r["ok_i"] else ("Voltage drop" if not r["ok_v"] else "Short circuit"))] for r in sel["rows"]]
    steps = [step("Design current", "P ÷ (√3 × V × PF)" if v != 230 else "P ÷ (V × PF)", R(current, 1), "A"),
             step("Temperature factor", f"√((90 − {i['ambient']:g}) ÷ (90 − base))", R(d["temp"], 3)),
             step("Grouping factor", f"{int(i['group'])} cable(s)", R(d["group"], 2)),
             step("Depth × soil factors", "", R(d["depth"] * d["soil"], 3)),
             step("Total derating", "product of the factors", R(d["total"], 3))]
    if not ch:
        return {"headline": {"label": "Cable", "value": "Not found"}, "status": "bad",
                "verdict": "No standard size meets all three checks — shorten the route, raise the voltage or split the load.",
                "items": [item("Design current", R(current, 1), "A", "1dp")], "table": {"title": "Sizes checked", "columns": ["Size", "Derated A", "VD %", "Min mm² (SC)", "Result"], "rows": rows},
                "steps": steps, "notes": []}
    cond_l = "aluminium" if sel["cond"] == "al" else "copper"
    cores = "3 core" if v >= 1000 else ("3.5 core" if v != 230 else "2 core")
    desc = f"{fmt_size(ch['size'], ch['runs'])} {cond_l} XLPE armoured, {cores}"
    steps += [step("Voltage drop", "k × I × L × (R cos φ + X sin φ) ÷ runs", R(ch["vd_pct"], 2), "%"),
              step("Short-circuit minimum", f"I × √t ÷ k ({sel['k_sc']})", R(ch["s_min"], 1), "mm²")]
    return {"headline": {"label": "Cable", "value": fmt_size(ch["size"], ch["runs"]), "sub": f"{cond_l} XLPE armoured"},
            "verdict": f"Use {desc}. It carries {R(ch['rated'], 0):g} A after derating against {R(current, 0):g} A needed, with {g(R(ch['vd_pct'], 2))}% voltage drop.",
            "items": [item("Design current", R(current, 1), "A", "1dp"), item("Derating factor", R(d["total"], 3), None, "3dp"),
                      item("Cable", desc, tone="accent"), item("Derated rating", R(ch["rated"], 0), "A", "int"),
                      item("Voltage drop", R(ch["vd_pct"], 2), "%", "2dp", "good" if ch["vd_pct"] <= i["vd_limit"] else "bad"),
                      item("Minimum size for fault", R(ch["s_min"], 1), "mm²", "1dp")],
            "table": {"title": "Sizes checked", "columns": ["Size", "Derated A", "VD %", "Min mm² (SC)", "Result"], "rows": rows},
            "steps": steps, "notes": ["Ratings are typical catalogue values; confirm with the chosen maker's table.",
                                      "Glands, lugs and termination size follow the cable chosen."]}


# ------------------------------------------------------------------ 13 voltage drop
def t_voltage_drop(i, C):
    phase3 = i["phase"] == "3"
    v = 415.0 if phase3 else 230.0
    r = cable_r90(C, i["conductor"], i["size"])
    x = C["cable"]["x_ohm_km"]["lt"]
    vd = vdrop(i["current"], i["length"], r, x, i["pf"], phase3, i["runs"])
    pct = vd / v * 100
    limit = C["cable"]["vd_limit_pct"][i["purpose"]]
    per_m = vdrop(i["current"], 1, r, x, i["pf"], phase3, i["runs"])
    max_len = limit / 100 * v / per_m if per_m else 0
    sin = math.sqrt(1 - i["pf"] ** 2)
    ok = pct <= limit + 1e-9
    return {"headline": {"label": "Voltage drop", "value": R(pct, 2), "unit": "%", "sub": f"{g(R(vd, 2))} V"},
            "status": "ok" if ok else "bad",
            "verdict": (f"Within the {limit}% limit." if ok else f"Above the {limit}% limit — use a bigger cable or more runs.") + f" Longest run at this current: {R(max_len, 0):g} m.",
            "items": [item("Voltage drop", R(vd, 2), "V", "2dp"), item("Voltage drop", R(pct, 2), "%", "2dp", "good" if ok else "bad"),
                      item("Limit", limit, "%"), item("Resistance at 90 °C", R(r, 4), "Ω/km", "4dp"), item("Reactance", x, "Ω/km"),
                      item("Longest length within limit", R(max_len, 0), "m", "int")],
            "steps": [step("Resistance at 90 °C", "R20 × (1 + α × 70)", R(r, 4), "Ω/km"),
                      step("Voltage drop", f"{'√3' if phase3 else '2'} × {i['current']:g} A × {i['length'] / 1000:g} km × ({g(R(r, 4))} × {g(i['pf'])} + {g(x)} × {g(R(sin, 3))}) ÷ {int(i['runs'])}", R(vd, 2), "V"),
                      step("As a percentage", f"{g(R(vd, 2))} ÷ {v:g} V", R(pct, 2), "%")],
            "notes": ["Limits used: 3% lighting, 5% power, measured from the supply point (typical practice under IS 732)."]}


# ------------------------------------------------------------------ 14 fault level
def t_fault_level(i, C):
    v = i["lv"]
    c = 1.05
    z_src = v * v / (i["source_mva"] * 1e6)
    x_src = z_src / math.sqrt(1 + 0.1 ** 2)
    r_src = 0.1 * x_src
    z_tx = i["z_pct"] / 100 * v * v / (i["kva"] * 1000)
    r_tx = z_tx / math.sqrt(1 + i["xr"] ** 2)
    x_tx = r_tx * i["xr"]
    tab = C["cable"]["r20_al" if i["conductor"] == "al" else "r20_cu"]
    if str(i["cable_size"]) not in tab:
        raise CalcError(f"{i['cable_size']} mm² is not available in {'aluminium' if i['conductor'] == 'al' else 'copper'}")
    r_c = tab[str(i["cable_size"])] * i["cable_m"] / 1000 / i["runs"]
    x_c = C["cable"]["x_ohm_km"]["lt"] * i["cable_m"] / 1000 / i["runs"]
    r1, x1 = r_src + r_tx, x_src + x_tx
    r2, x2 = r1 + r_c, x1 + x_c
    ik1 = c * v / (SQ3 * math.hypot(r1, x1)) / 1000
    ik2 = c * v / (SQ3 * math.hypot(r2, x2)) / 1000
    kappa = 1.02 + 0.98 * math.exp(-3 * r2 / x2)
    ip = kappa * math.sqrt(2) * ik2
    lst = C["breakers"]["acb_ka"] if ik2 > 50 else C["breakers"]["mccb_ka"]
    bc = next_std(ik2, sorted(set(C["breakers"]["mccb_ka"] + C["breakers"]["acb_ka"])))
    flc = i["kva"] * 1000 / (SQ3 * v)
    return {"headline": {"label": "Fault level at the panel", "value": R(ik2, 1), "unit": "kA"},
            "verdict": f"About {R(ik1, 1):g} kA at the transformer terminals and {R(ik2, 1):g} kA at the panel. Breakers there need at least {bc} kA breaking capacity.",
            "items": [item("At transformer LV terminals", R(ik1, 2), "kA", "2dp"), item("At the panel", R(ik2, 2), "kA", "2dp", "accent"),
                      item("Peak (making) current", R(ip, 1), "kA", "1dp"), item("Breaking capacity needed", bc, "kA"),
                      item("Transformer full-load current", R(flc, 0), "A", "int")],
            "steps": [step("Source impedance at LV", f"{v:g}² ÷ {i['source_mva']:g} MVA", R(z_src * 1000, 3), "mΩ"),
                      step("Transformer impedance", f"{g(i['z_pct'])}% × {v:g}² ÷ {i['kva']:g} kVA", R(z_tx * 1000, 3), "mΩ"),
                      step("Cable impedance", f"{i['cable_m']:g} m of {int(i['runs'])} × {i['cable_size']} mm²", R(math.hypot(r_c, x_c) * 1000, 3), "mΩ"),
                      step("Fault current", "c × V ÷ (√3 × |Z|), c = 1.05", R(ik2, 2), "kA"),
                      step("Peak factor κ", "1.02 + 0.98 e^(−3R/X)", R(kappa, 3))],
            "notes": ["Motor contribution is not included; add it for large motor loads.", "Simplified IEC 60909 method; a full study uses actual network data."]}


# ------------------------------------------------------------------ 15 breaker selector
FUSES = [2, 4, 6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250]


def t_breaker_selector(i, C):
    v = float(i["voltage"])
    phase3 = v != 230
    if i["input"] == "kw":
        ib = i["value"] * 1000 / ((SQ3 if phase3 else 1) * v * i["pf"])
    elif i["input"] == "kva":
        ib = i["value"] * 1000 / ((SQ3 if phase3 else 1) * v)
    else:
        ib = i["value"]
    factor = {"lighting": 1.0, "mixed": 1.25, "motor": 1.25, "capacitor": 1.43, "transformer": 1.0}[i["load_type"]]
    need = ib * factor
    b = C["breakers"]
    steps = [step("Load current", "P ÷ (√3 × V × PF)" if i["input"] == "kw" else ("S ÷ (√3 × V)" if i["input"] == "kva" else "given"), R(ib, 1), "A"),
             step("Rating needed", f"× {g(factor)} ({i['load_type']})", R(need, 1), "A")]
    notes = []
    if v >= 1000:
        rating = next_std(max(need, 1), b["vcb_a"])
        bc = next_std(i["fault_ka"], b["vcb_ka"])
        kind = "VCB (vacuum circuit breaker)"
        detail = f"{rating} A, {bc} kA, with numerical relay (50/51, 50N/51N)"
        notes.append("Set relay pick-up and time for grading with the upstream TNPDCL breaker.")
    else:
        if need <= b["mcb"][-1] and i["fault_ka"] <= b["mcb_ka"][-1] and i["load_type"] not in ("transformer",):
            rating = next_std(need, b["mcb"])
            bc = next_std(i["fault_ka"], b["mcb_ka"])
            curve = {"lighting": "B", "mixed": "C", "motor": "D", "capacitor": "C"}[i["load_type"]]
            kind = f"MCB, curve {curve}"
            detail = f"{rating} A {'4' if phase3 else '2'}-pole, {bc} kA"
        elif need <= b["mccb"][-1] and not (i["load_type"] == "transformer" and need > 630):
            rating = next_std(need, b["mccb"])
            bc = next_std(i["fault_ka"], b["mccb_ka"])
            kind = "MCCB" + (" with motor-protection release" if i["load_type"] == "motor" else "")
            detail = f"{rating} A frame / set at ≈{R(need, 0):g} A, {bc} kA (Icu)"
        else:
            rating = next_std(need, b["acb"])
            bc = next_std(i["fault_ka"], b["acb_ka"])
            kind = "ACB (draw-out)"
            detail = f"{rating} A, {bc} kA, with microprocessor release (LSIG)"
        if bc is None:
            bc = "above standard — use current-limiting or cascading"
        if rating is None:
            rating = "above standard — split the feeder"
        if i["load_type"] == "motor":
            notes.append("For motors, coordinate with the contactor and overload relay (Type 2 coordination).")
        if i["load_type"] == "capacitor":
            notes.append("Capacitor feeders are rated 1.43× the capacitor current for harmonics and tolerance.")
    fuse = next_std(need, FUSES) if v < 1000 else None
    items = [item("Load current", R(ib, 1), "A", "1dp"), item("Rating needed", R(need, 1), "A", "1dp"), item("Breaker", kind, tone="accent"),
             item("Selection", detail)]
    if fuse:
        items.append(item("Equivalent HRC fuse", fuse, "A"))
    return {"headline": {"label": kind, "value": f"{rating} A" if isinstance(rating, (int, float)) else rating, "sub": f"{bc} kA" if isinstance(bc, (int, float)) else str(bc)},
            "verdict": f"Use {kind}: {detail}.", "items": items, "steps": steps,
            "notes": notes + ["Check that the cable's derated rating is at least the breaker setting (Iz ≥ In)."]}


# ------------------------------------------------------------------ 16 motor
def t_motor(i, C):
    kw = i["rating"] * 0.746 if i["unit"] == "hp" else i["rating"]
    e_t, p_t = motor_eff_pf(C, kw)
    eff = i["eff"] or e_t
    pf = i["pf"] or p_t
    v = i["voltage"]
    flc = kw * 1000 / (SQ3 * v * eff * pf)
    if i["duty"] == "variable":
        starter = "vfd"
    elif i["duty"] == "conveyor":
        starter = "dol" if kw <= 7.5 else "soft_starter"
    elif kw <= 7.5:
        starter = "dol"
    elif kw <= 75:
        starter = "star_delta"
    else:
        starter = "soft_starter"
    names = {"dol": "Direct on line (DOL)", "star_delta": "Star-delta", "soft_starter": "Soft starter", "vfd": "Variable frequency drive (VFD)"}
    mult = C["motor_start_multiple"][starter]
    i_start = flc * mult
    design = flc * 1.25
    cond = "cu" if design <= 60 else "al"
    sel = select_cable(C, design, v, pf, i["length"], cond, "air", 40, 1, "touching", "150", "75", 5, 0, 0.1)
    ch = sel["chosen"]
    cab = f"{fmt_size(ch['size'], ch['runs'])} {'copper' if cond == 'cu' else 'aluminium'} XLPE armoured" if ch else "Check manually"
    brk = next_std(design, C["breakers"]["mccb"] if design > 63 else C["breakers"]["mcb"]) or "—"
    return {"headline": {"label": "Full-load current", "value": R(flc, 1), "unit": "A", "sub": names[starter]},
            "verdict": f"A {R(kw, 2):g} kW motor draws about {R(flc, 1):g} A. Use a {names[starter].lower()} starter (≈{R(i_start, 0):g} A while starting) and {cab}.",
            "items": [item("Rating", R(kw, 2), "kW", "2dp"), item("Efficiency used", eff), item("Power factor used", pf),
                      item("Full-load current", R(flc, 1), "A", "1dp", "accent"), item("Starter", names[starter]),
                      item("Starting current", R(i_start, 0), "A", "int"), item("Cable (125% of FLC)", cab), item("Motor protection breaker", f"{brk} A")],
            "steps": [step("Full-load current", f"{R(kw * 1000, 0):g} W ÷ (√3 × {v:g} × {g(eff)} × {g(pf)})", R(flc, 2), "A"),
                      step("Starting current", f"× {g(mult)} for {names[starter].lower()}", R(i_start, 0), "A")],
            "notes": ["Typical IE3 4-pole efficiency and PF are used when you leave them blank; use the nameplate if you have it."]}


# ------------------------------------------------------------------ 17 PF correction
def t_pf_correction(i, C):
    if i["pf_target"] <= i["pf_now"]:
        raise CalcError("Target power factor must be higher than the present one")
    t1 = math.tan(math.acos(i["pf_now"]))
    t2 = math.tan(math.acos(i["pf_target"]))
    kvar = i["kw"] * (t1 - t2)
    bank = math.ceil(kvar / 25) * 25
    caps = C["capacitor_steps_kvar"]
    s = next_std(bank / 10, caps) or caps[-1]
    steps_ = [s, s]
    while sum(steps_) < bank:
        steps_.append(2 * s)
    detuned = i["nonlinear"] > 15
    kva1 = i["kw"] / i["pf_now"]
    kva2 = i["kw"] / i["pf_target"]
    pen_pct = pf_penalty_pct(i["pf_now"], C) if i["ht"] else 0
    pen = i["energy_bill"] * pen_pct / 100
    demand_save = (kva1 - kva2) * C["tariffs"]["HT_I"]["demand"] if i["ht"] else 0
    monthly = pen + demand_save
    cost = bank * (2000 if detuned else 1200)
    payback_m = cost / monthly if monthly > 0 else None
    return {"headline": {"label": "Capacitors needed", "value": R(kvar, 1), "unit": "kVAR", "sub": f"APFC panel {bank} kVAR"},
            "verdict": f"Add about {R(kvar, 0):g} kVAR (an APFC panel of {bank} kVAR)" + (f"; it saves about ₹{ind(R(monthly, 0))} a month." if monthly > 0 else "."),
            "items": [item("kVAR needed", R(kvar, 1), "kVAR", "1dp"), item("APFC panel", bank, "kVAR", None, "accent"),
                      item("Steps", " + ".join(f"{x:g}" for x in steps_) + " kVAR"),
                      item("Reactors", "7% detuned reactors" if detuned else "Not needed (low harmonics)", tone="warn" if detuned else None),
                      item("Demand before → after", f"{R(kva1, 0):g} → {R(kva2, 0):g} kVA"),
                      item("PF penalty avoided", R(pen, 0), "₹/month", "inr"), item("Demand charge saved", R(demand_save, 0), "₹/month", "inr"),
                      item("Indicative panel cost", R(cost, 0), "₹", "inr"), item("Payback", R(payback_m, 1) if payback_m else "—", "months", "1dp")],
            "steps": [step("kVAR", f"{i['kw']:g} × (tan(acos {g(i['pf_now'])}) − tan(acos {g(i['pf_target'])})) = {i['kw']:g} × ({g(R(t1, 4))} − {g(R(t2, 4))})", R(kvar, 2), "kVAR"),
                      step("PF penalty now", f"{pen_pct:g}% of energy charges", R(pen, 0), "₹/month")],
            "notes": (["With more than 15% VFD / UPS / LED load, plain capacitors can resonate — use detuned reactors."] if detuned else [])
            + ["Panel cost is indicative; we quote after a power-quality measurement."]}


# ------------------------------------------------------------------ 18 harmonics
def t_harmonics(i, C):
    isc_kva = i["kva"] / (i["z_pct"] / 100)
    ratio = isc_kva / i["load_kva"]
    tdd = next(l for lim, l in C["harmonics_tdd_limits"] if ratio < lim)
    nl = i["nonlinear"]
    est_thd = nl * 0.4
    if nl < 15:
        risk, status = "Low", "ok"
    elif nl <= 30:
        risk, status = "Medium", "warn"
    else:
        risk, status = "High", "bad"
    recs = []
    if nl >= 15:
        recs.append("Measure with a power-quality analyser for 7 days (we can do this).")
        recs.append("Use 7% detuned reactors in the APFC panel.")
    if nl > 30:
        recs.append("Consider an active harmonic filter at the main LT panel, and DC chokes / line reactors on large VFDs.")
        recs.append("Check neutral sizing and transformer heating (consider K-rated transformers for new projects).")
    if i["capacitors"] and nl >= 15:
        recs.append("Plain capacitors with this much non-linear load risk resonance — replace or add reactors.")
        status = "bad"
    if not recs:
        recs.append("No action needed now; recheck when adding drives, UPS or EV chargers.")
    return {"headline": {"label": "Harmonic risk", "value": risk, "sub": f"{nl:g}% non-linear load"}, "status": status,
            "verdict": f"{risk} risk. Your current distortion limit (TDD) at this short-circuit ratio is {tdd}% per IEEE 519.",
            "items": [item("Short-circuit ratio Isc/IL", R(ratio, 1), None, "1dp"), item("Current TDD limit", tdd, "%"),
                      item("Voltage THD limit (below 1 kV)", 8, "%"), item("Indicative current THD", R(est_thd, 0), "%", "int", "warn" if est_thd > tdd else None)],
            "table": {"title": "What to do", "columns": ["Recommendation"], "rows": [[r] for r in recs]},
            "steps": [step("Short-circuit kVA", f"{i['kva']:g} ÷ {g(i['z_pct'])}%", R(isc_kva, 0), "kVA"),
                      step("Ratio", f"{R(isc_kva, 0):g} ÷ {i['load_kva']:g}", R(ratio, 1))],
            "notes": ["Indicative only — six-pulse drives produce about 30–45% current THD on their own current."]}


# ------------------------------------------------------------------ 19 energy savings
def t_energy_savings(i, C):
    h = i["hours"]
    if i["measure"] == "led":
        old = i["fixtures"] * i["old_w"] * h / 1000
        new = i["fixtures"] * i["new_w"] * h / 1000
        steps = [step("Present use", f"{i['fixtures']:g} × {i['old_w']:g} W × {h:g} h", R(old, 0), "kWh/yr"),
                 step("With LED", f"{i['fixtures']:g} × {i['new_w']:g} W × {h:g} h", R(new, 0), "kWh/yr")]
        name = "LED retrofit"
    elif i["measure"] == "vfd":
        f = i["flow"] / 100
        p_thr = i["motor_kw"] * (0.55 + 0.45 * f) / 0.92
        p_vfd = i["motor_kw"] * f ** 3 / 0.97 / 0.92
        old, new = p_thr * h, p_vfd * h
        steps = [step("With throttle valve / damper", f"{i['motor_kw']:g} kW × (0.55 + 0.45 × {f:g}) ÷ 0.92", R(p_thr, 2), "kW"),
                 step("With VFD (affinity law)", f"{i['motor_kw']:g} kW × {f:g}³ ÷ 0.97 ÷ 0.92", R(p_vfd, 2), "kW")]
        name = "VFD"
    else:
        out = i["motor_kw"] * i["load_pct"] / 100
        old, new = out / i["eff_old"] * h, out / i["eff_new"] * h
        steps = [step("Output power", f"{i['motor_kw']:g} kW × {i['load_pct']:g}%", R(out, 2), "kW"),
                 step("Input saved", f"{g(R(out, 2))} × (1/{g(i['eff_old'])} − 1/{g(i['eff_new'])})", R(out / i["eff_old"] - out / i["eff_new"], 3), "kW")]
        name = "Efficient motor"
    save = old - new
    rupees = save * i["tariff"]
    payback = i["cost"] / rupees if rupees > 0 else None
    co2 = save * C["co2_kg_per_kwh"] / 1000
    return {"headline": {"label": "Yearly saving", "value": R(rupees, 0), "unit": "₹", "fmt": "inr", "sub": f"{ind(R(save, 0))} kWh"},
            "verdict": f"{name} saves about {ind(R(save, 0))} kWh (₹{ind(R(rupees, 0))}) a year" + (f" and pays back in {R(payback, 1):g} years." if payback else "."),
            "items": [item("Energy before", R(old, 0), "kWh/yr", "int"), item("Energy after", R(new, 0), "kWh/yr", "int"),
                      item("Saved", R(save, 0), "kWh/yr", "int", "good"), item("Saved", R(rupees, 0), "₹/yr", "inr", "good"),
                      item("Payback", R(payback, 1) if payback else "—", "years", "1dp"), item("CO₂ avoided", R(co2, 2), "tonnes/yr", "2dp")],
            "steps": steps, "notes": [f"CO₂ at {C['co2_kg_per_kwh']} kg/kWh ({C['co2_basis']})."]}


# ------------------------------------------------------------------ 20 earthing
def t_earthing(i, C):
    rho = i["rho"]
    if i["electrode"] == "pipe":
        L, d = i["length"], i["diameter"] / 1000
        r1 = rho / (2 * math.pi * L) * math.log(4 * L / d)
        f = f"ρ ÷ (2πL) × ln(4L/d) = {rho:g} ÷ (2π × {L:g}) × ln(4 × {L:g} ÷ {d:g})"
    elif i["electrode"] == "plate":
        A = i["plate_w"] * i["plate_h"]
        r1 = rho / 4 * math.sqrt(math.pi / A)
        f = f"(ρ ÷ 4) × √(π ÷ A) = ({rho:g} ÷ 4) × √(π ÷ {R(A, 3):g})"
    else:
        L, w, t = i["length"], i["strip_w"] / 1000, i["strip_depth"]
        r1 = rho / (2 * math.pi * L) * math.log(2 * L * L / (w * t))
        f = f"ρ ÷ (2πL) × ln(2L² ÷ (w × t))"

    def eta(n):
        return 1.0 if n == 1 else (0.85 if n <= 3 else (0.75 if n <= 6 else (0.65 if n <= 12 else 0.55)))

    n = 1
    while r1 / (n * eta(n)) > i["target"] and n < 50:
        n += 1
    rn = r1 / (n * eta(n))
    reached = rn <= i["target"] + 1e-9
    k = C["earthing_k"][i["material"]]
    s = i["fault_ka"] * 1000 * math.sqrt(i["duration"]) / k
    s_allow = s * 1.25 if i["material"] == "gi" else s
    if i["material"] == "gi":
        strip = next(([w, t] for w, t in C["earth_strips_mm"] if w * t >= s_allow), None)
        cond = f"{strip[0]} × {strip[1]} mm GI strip" if strip else "Larger than 75 × 10 mm — use multiple strips"
    else:
        sizes = [16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300]
        sz = next_std(s_allow, sizes)
        cond = f"{sz} mm² {i['material']}" if sz else "Above 300 mm² — use multiple conductors"
    return {"headline": {"label": "Earth pits needed", "value": n, "sub": f"≈ {g(R(rn, 2))} Ω combined"},
            "status": "ok" if reached else "warn",
            "verdict": (f"{n} pit{'s' if n > 1 else ''} of this type, spaced at least twice the electrode length apart, give about {g(R(rn, 2))} Ω." if reached
                        else f"Even 50 pits don't reach {i['target']:g} Ω in this soil — use soil treatment, longer rods, a ring earth or chemical earthing."),
            "items": [item("One electrode", R(r1, 2), "Ω", "2dp"), item("Pits", n, None, "int", "accent"), item("Combined", R(rn, 2), "Ω", "2dp"),
                      item("Conductor size needed", R(s_allow, 0), "mm²", "int"), item("Earthing conductor", cond)],
            "steps": [step("One electrode", f, R(r1, 2), "Ω"),
                      step("Several in parallel", "R1 ÷ (n × utilisation)", R(rn, 2), "Ω"),
                      step("Conductor", f"I × √t ÷ k = {i['fault_ka']:g} kA × √{i['duration']:g} ÷ {k}" + (" + 25% corrosion allowance" if i["material"] == "gi" else ""), R(s_allow, 0), "mm²")],
            "notes": ["Measure soil resistivity on site (Wenner four-pin method) — it can vary 10× across a plot and with the season.",
                      "Typical targets: ≤1 Ω for HT substations, ≤5 Ω for LT equipment earths."]}


# ------------------------------------------------------------------ 21 lightning
def t_lightning_risk(i, C):
    L, W, H = i["l"], i["w"], i["h"]
    lc = C["lightning"]
    ac = L * W + 2 * L * H + 2 * W * H + math.pi * H * H
    p = i["ng"] * ac * 1e-6
    a, b, c, d, e = lc["a"][i["use"]], lc["b"][i["construction"]], lc["c"][i["contents"]], lc["d"][i["isolation"]], lc["e"][i["terrain"]]
    overall = p * a * b * c * d * e
    ad = L * W + 2 * 3 * H * (L + W) + math.pi * (3 * H) ** 2
    cd = {"surrounded": 0.5, "few": 1.0, "isolated": 2.0}[i["isolation"]]
    nd = i["ng"] * ad * cd * 1e-6
    ratio = overall / lc["threshold"]
    needed = ratio > 1
    lpl = "Not needed" if not needed else ("Class IV" if ratio <= 100 else ("Class III" if ratio <= 1000 else ("Class II" if ratio <= 10000 else "Class I")))
    return {"headline": {"label": "Lightning protection", "value": "Needed" if needed else "Not required", "sub": lpl if needed else None},
            "status": "warn" if needed else "ok",
            "verdict": (f"Protection is recommended: the weighted risk ({sci(overall)}) is {R(ratio, 1):g}× the acceptable 1 × 10⁻⁵. Start with {lpl}."
                        if needed else f"The weighted risk ({sci(overall)}) is below 1 × 10⁻⁵ — protection is not required by this method."),
            "items": [item("Collection area", R(ac, 0), "m²", "int"), item("Probable strikes per year", f"{sci(p)}"),
                      item("Weighted risk", f"{sci(overall)}", tone="warn" if needed else "good"), item("Starting class", lpl),
                      item("IEC 62305 dangerous events (Nd)", f"{sci(nd)}", "per year")],
            "steps": [step("Collection area", "LW + 2LH + 2WH + πH²", R(ac, 0), "m²"),
                      step("Probability", f"Ng {i['ng']:g} × Ac × 10⁻⁶", f"{sci(p)}"),
                      step("Weighting", f"A {g(a)} × B {g(b)} × C {g(c)} × D {g(d)} × E {g(e)}", R(a * b * c * d * e, 4)),
                      step("Overall risk", "probability × weighting", f"{sci(overall)}")],
            "notes": ["Quick method per IS 2309. A full IS/IEC 62305-2 risk assessment fixes the final class, surge protection and earthing."]}


# ------------------------------------------------------------------ 22 lux
def t_lighting_lux(i, C):
    E = i["lux"] or C["lux_targets"][i["space"]]
    A = i["length"] * i["width"]
    k = A / (i["height"] * (i["length"] + i["width"]))
    uf = interp(C["uf_table"], k)
    n = math.ceil(E * A / (i["lumens"] * uf * i["mf"]) - 1e-9)
    achieved = n * i["lumens"] * uf * i["mf"] / A
    lpd = n * i["watts"] / A
    cols = max(1, round(math.sqrt(n * i["length"] / i["width"])))
    rows = math.ceil(n / cols)
    return {"headline": {"label": "Fixtures", "value": n, "sub": f"{R(achieved, 0):g} lux achieved"},
            "verdict": f"{n} fixtures in about {rows} rows × {cols} give {R(achieved, 0):g} lux at {R(lpd, 1):g} W/m².",
            "items": [item("Target", E, "lux"), item("Room index", R(k, 2), None, "2dp"), item("Utilisation factor", R(uf, 2), None, "2dp"),
                      item("Fixtures", n, None, "int", "accent"), item("Layout", f"{rows} rows × {cols}"), item("Achieved", R(achieved, 0), "lux", "int"),
                      item("Lighting power density", R(lpd, 2), "W/m²", "2dp"), item("Spacing", f"≈ {R(i['length'] / cols, 1):g} m × {R(i['width'] / rows, 1):g} m")],
            "steps": [step("Room index", f"L × W ÷ (Hm × (L + W)) = {i['length']:g} × {i['width']:g} ÷ ({i['height']:g} × {i['length'] + i['width']:g})", R(k, 2)),
                      step("Fixtures", f"E × A ÷ (lumens × UF × MF) = {E:g} × {R(A, 1):g} ÷ ({i['lumens']:g} × {g(R(uf, 2))} × {g(i['mf'])})", n)],
            "notes": ["Utilisation factor for typical reflectances (ceiling 70%, walls 50%, floor 20%); use the fixture's photometric data for final design."]}


# ------------------------------------------------------------------ 23 units
def t_units(i, C):
    v, pf, eff = i["voltage"], i["pf"], i["eff"]
    k = SQ3 if i["phase"] == "3" else 1.0
    x = i["value"]
    if i["from"] == "kw":
        kw = x
    elif i["from"] == "kva":
        kw = x * pf
    elif i["from"] == "hp":
        kw = x * 0.746 / eff
    else:
        kw = k * v * x * pf / 1000
    kva = kw / pf
    amps = kva * 1000 / (k * v)
    hp = kw * eff / 0.746
    kvar = math.sqrt(max(kva * kva - kw * kw, 0))
    return {"headline": {"label": "Current", "value": R(amps, 2), "unit": "A"},
            "verdict": f"{R(kw, 3):g} kW = {R(kva, 3):g} kVA = {R(hp, 2):g} HP = {R(amps, 2):g} A at {v:g} V, PF {g(pf)}.",
            "items": [item("Active power", R(kw, 3), "kW", "3dp"), item("Apparent power", R(kva, 3), "kVA", "3dp"),
                      item("Reactive power", R(kvar, 3), "kVAR", "3dp"), item("Horsepower (output)", R(hp, 2), "HP", "2dp"),
                      item("Current", R(amps, 2), "A", "2dp", "accent")],
            "steps": [step("Three phase" if i["phase"] == "3" else "Single phase", "P = √3 × V × I × cos φ" if i["phase"] == "3" else "P = V × I × cos φ", ""),
                      step("Ohm's law", "V = I × R; P = V × I = I² × R", "")],
            "notes": ["1 HP = 0.746 kW (output). Motor input kW = HP × 0.746 ÷ efficiency."]}


# ------------------------------------------------------------------ 24 checklists
def t_checklists(i, C):
    names = {"new_lt": "New LT service", "load_change": "Load change", "new_ht": "New HT service", "ceig": "CEIG drawing approval & inspection",
             "name_transfer": "Name transfer", "solar": "Solar net metering"}
    lst = TOOLS["checklists"][i["kind"]]
    return {"headline": {"label": names[i["kind"]], "value": len(lst), "unit": "documents"},
            "verdict": f"Keep these {len(lst)} documents ready. Our liaison team can prepare and file them for you.",
            "items": [], "checklist": lst, "table": {"title": "Checklist", "columns": ["#", "Document"], "rows": [[n + 1, d] for n, d in enumerate(lst)]},
            "steps": [], "notes": ["Requirements change from time to time and between offices; we confirm the current list when we take up your case."]}


FUNCS = {
    "connected-load": t_connected_load, "lt-vs-ht": t_lt_vs_ht, "bill-estimator": t_bill_estimator,
    "contract-demand": t_contract_demand, "ht-connection-roadmap": t_ht_roadmap, "transformer-sizing": t_transformer_sizing,
    "transformer-losses": t_transformer_losses, "dg-sizing": t_dg_sizing, "ups-battery": t_ups_battery,
    "solar-rooftop": t_solar_rooftop, "ev-charger-load": t_ev_charger_load, "cable-size": t_cable_size,
    "voltage-drop": t_voltage_drop, "fault-level": t_fault_level, "breaker-selector": t_breaker_selector, "motor": t_motor,
    "pf-correction": t_pf_correction, "harmonics": t_harmonics, "energy-savings": t_energy_savings, "earthing": t_earthing,
    "lightning-risk": t_lightning_risk, "lighting-lux": t_lighting_lux, "units-formulas": t_units, "document-checklists": t_checklists,
}
assert set(FUNCS) == set(SPEC), set(SPEC) ^ set(FUNCS)
