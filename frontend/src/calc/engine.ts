// TypeScript copy of backend/calc/engine.py — the same 24 calculators, for instant results in the browser.
// Both are run against backend/tests/calc_cases.json (scripts/calc-parity.mjs) so they never drift apart.
/* eslint-disable @typescript-eslint/no-explicit-any */
type Any = any;

const SQ3 = Math.sqrt(3);

export class CalcError extends Error {}

// ------------------------------------------------------------------ helpers (mirror engine.py)
function roundStr(str: string, n: number): number {
  const [ip, fp = ""] = str.split(".");
  if (fp.length <= n) return Number(str);
  const keep = fp.slice(0, n);
  const next = fp.charCodeAt(n) - 48;
  const digits = (ip + keep).split("").map(Number);
  if (next >= 5) {
    let i = digits.length - 1;
    while (i >= 0) {
      if (digits[i] === 9) { digits[i] = 0; i -= 1; } else { digits[i] += 1; break; }
    }
    if (i < 0) digits.unshift(1);
  }
  const all = digits.join("");
  const intLen = all.length - n;
  return Number(n > 0 ? `${all.slice(0, intLen)}.${all.slice(intLen)}` : all);
}

export function R(x: Any, n = 2): Any {
  if (x === null || x === undefined) return null;
  const v = Number(x);
  if (!Number.isFinite(v)) return v;
  const s = v < 0 ? -1 : 1;
  const a = Math.abs(v);
  const str = String(a);
  const r = str.includes("e") ? Number(a.toFixed(n)) : roundStr(str, n);
  return s * r || 0;
}

const pyRound = (x: number): number => { const f = Math.floor(x); const d = x - f; if (d > 0.5) return f + 1; if (d < 0.5) return f; return f % 2 === 0 ? f : f + 1; };

export function g(x: Any): string {
  const v = Number(x);
  if (v === 0) return "0";
  if (!Number.isFinite(v)) return String(v);
  const e = Number(v.toExponential(5).split("e")[1]);
  if (e < -4 || e >= 6) {
    const [m, ex] = v.toExponential(5).split("e");
    const mm = m.includes(".") ? m.replace(/\.?0+$/, "") : m;
    const sign = ex[0] === "-" ? "-" : "+";
    let dd = ex.replace(/^[+-]/, "");
    if (dd.length < 2) dd = `0${dd}`;
    return `${mm}e${sign}${dd}`;
  }
  const s = v.toPrecision(6);
  return s.includes(".") ? s.replace(/0+$/, "").replace(/\.$/, "") : s;
}

export function sci(x: Any): string {
  const [m, ex] = Number(x).toExponential(2).split("e");
  const sign = ex[0] === "-" ? "-" : "+";
  let dd = ex.replace(/^[+-]/, "");
  if (dd.length < 2) dd = `0${dd}`;
  return `${m}e${sign}${dd}`;
}

export function ind(x: Any, d = 0): string {
  const neg = Number(x) < 0;
  const s = Math.abs(Number(R(x, d))).toFixed(d);
  let [whole, frac] = s.split(".");
  if (whole.length > 3) {
    let head = whole.slice(0, -3);
    const tail = whole.slice(-3);
    const parts: string[] = [];
    while (head.length > 2) { parts.unshift(head.slice(-2)); head = head.slice(0, -2); }
    if (head) parts.unshift(head);
    whole = [...parts, tail].join(",");
  }
  return (neg ? "-" : "") + whole + (frac ? `.${frac}` : "");
}

function nextStd(val: number, ratings: number[]): Any {
  for (const r of ratings) if (r >= val - 1e-9) return r;
  return null;
}
function item(label: string, value: Any, unit?: Any, fmt?: Any, tone?: Any) {
  const d: Any = { label, value };
  if (unit) d.unit = unit;
  if (fmt) d.fmt = fmt;
  if (tone) d.tone = tone;
  return d;
}
function step(label: string, formula: string, value: Any, unit?: Any) {
  const d: Any = { label, formula, value };
  if (unit) d.unit = unit;
  return d;
}
function floorKey(table: Any, x: number) {
  const keys = Object.keys(table).sort((a, b) => parseFloat(a) - parseFloat(b));
  let best = keys[0];
  for (const k of keys) if (parseFloat(k) <= x + 1e-9) best = k;
  return table[best];
}
// the value for the smallest key at or above x (the last one past the end): a group of 7 cables uses the 8-cable factor
function ceilKey(table: Any, x: number) {
  const keys = Object.keys(table).filter((k) => !k.startsWith("_")).sort((a, b) => parseFloat(a) - parseFloat(b));
  for (const k of keys) if (parseFloat(k) >= x - 1e-9) return table[k];
  return table[keys[keys.length - 1]];
}
// one standard transformer, or several equal ones when one 2500 kVA unit isn't enough: [count, rating]
function txPlan(kvaNeeded: number, C: Any): [number, number] {
  const ratings = C.transformer_ratings;
  const one = nextStd(kvaNeeded, ratings);
  if (one !== null && one !== undefined) return [1, one];
  const n = Math.ceil(kvaNeeded / ratings[ratings.length - 1]);
  return [n, nextStd(kvaNeeded / n, ratings) ?? ratings[ratings.length - 1]];
}
function interp(pairs: number[][], x: number) {
  if (x <= pairs[0][0]) return pairs[0][1];
  for (let i = 0; i < pairs.length - 1; i += 1) {
    const [x0, y0] = pairs[i];
    const [x1, y1] = pairs[i + 1];
    if (x <= x1) return y0 + ((y1 - y0) * (x - x0)) / (x1 - x0);
  }
  return pairs[pairs.length - 1][1];
}
const sum = (a: number[]) => a.reduce((s, x) => s + x, 0);
const labelOf = (TOOLS: Any, slug: string, k: string) => TOOLS.tools.find((t: Any) => t.slug === slug).inputs.find((f: Any) => f.k === k).l;
const ucfirst = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

// With the form's values, a list that depends on another box narrows to match it (cable sizes follow the conductor).
export function optionsFrom(name: string, C: Any, vals?: Any) {
  if (name === "tariffs") return Object.entries(C.tariffs).map(([k, v]: Any) => ({ value: k, label: v.label }));
  if (name === "tariffs_ht") return Object.entries(C.tariffs).filter(([, v]: Any) => v.kind === "HT").map(([k, v]: Any) => ({ value: k, label: v.label }));
  if (name === "transformer_ratings") return C.transformer_ratings.map((k: number) => ({ value: String(k), label: `${k} kVA` }));
  if (name === "solar_towns") return Object.keys(C.solar.yield_kwh_per_kwp_day).map((k) => ({ value: k, label: k }));
  if (name === "cable_sizes") {
    const cond = vals?.conductor;
    const keys = (cond === "al" || cond === "cu" ? Object.keys(C.cable[`r20_${cond}`]) : Array.from(new Set([...Object.keys(C.cable.r20_al), ...Object.keys(C.cable.r20_cu)])))
      .sort((a, b) => parseFloat(a) - parseFloat(b));
    return keys.map((k) => ({ value: k, label: `${k} mm²` }));
  }
  return [];
}

export function mergedConstants(DEFAULTS: Any, overrides?: Any) {
  const C = JSON.parse(JSON.stringify(DEFAULTS));
  for (const [k, v] of Object.entries(overrides || {})) {
    if (v && typeof v === "object" && !Array.isArray(v) && C[k] && typeof C[k] === "object" && !Array.isArray(C[k])) C[k] = { ...C[k], ...(v as Any) };
    else C[k] = v;
  }
  return C;
}

// The form's visibility rules: a field that is hidden right now isn't asked for (mirrors engine.py shown()).
export function shown(f: Any, vals: Any) {
  const txt = (x: Any) => (x === null || x === undefined ? "" : String(x));
  if (f.show && !Object.entries(f.show).every(([k, x]) => txt(vals[k]) === txt(x))) return false;
  if (f.show_in && !Object.entries(f.show_in).every(([k, xs]: Any) => xs.map(txt).includes(txt(vals[k])))) return false;
  if (f.show_if_gt && !Object.entries(f.show_if_gt).every(([k, x]) => vals[k] !== null && vals[k] !== undefined && vals[k] !== "" && Number(vals[k]) > Number(x))) return false;
  return true;
}

const fmtLimit = (x: number) => (Number.isInteger(x) && Math.abs(x) >= 1000 ? ind(x, 0) : g(x));

// A number within the field's limits, or a plain message naming the field (mirrors engine.py _number()).
function numberIn(f: Any, v: Any) {
  if (typeof v === "boolean" || (typeof v === "string" && !v.trim())) throw new CalcError(`${f.l}: enter a number`);
  const n = Number(v);
  if (Number.isNaN(n) || !Number.isFinite(n)) throw new CalcError(`${f.l}: enter a number`);
  if (f.min !== undefined && f.min !== null && n < f.min) throw new CalcError(`${f.l}: must be at least ${fmtLimit(f.min)}`);
  if (f.max !== undefined && f.max !== null && n > f.max) throw new CalcError(`${f.l}: must be at most ${fmtLimit(f.max)}`);
  return n;
}

// a box's default; def_by makes it follow another box (single phase → 230 V, cable in air → 40 °C)
export function defaultOf(f: Any, raw: Any, spec: Any) {
  for (const [dep, table] of Object.entries(f.def_by || {}) as [string, Any][]) {
    const dv = raw[dep] !== undefined ? raw[dep] : spec.inputs.find((x: Any) => x.k === dep)?.def;
    const key = typeof dv === "boolean" ? String(dv) : dv === null || dv === undefined ? "" : String(dv);
    if (key in table) return table[key];
  }
  return f.def;
}
export function validate(spec: Any, raw: Any, C: Any) {
  const out: Any = {};
  raw = raw || {};
  const given: Any = Object.fromEntries(spec.inputs.map((f: Any) => [f.k, raw[f.k] !== undefined ? raw[f.k] : defaultOf(f, raw, spec)]));
  for (const f of spec.inputs) {
    const { k, t } = f;
    let v = given[k];
    if (t === "number") {
      const empty = v === null || v === undefined || v === "";
      if (!shown(f, given)) { // hidden: keep the value if it's usable, else the default
        const d = f.def === null || f.def === undefined ? null : Number(f.def);
        try { out[k] = empty ? d : numberIn(f, v); } catch { out[k] = d; }
        continue;
      }
      if (empty) {
        if (f.optional) { out[k] = null; continue; }
        throw new CalcError(`${f.l}: enter a value`);
      }
      out[k] = numberIn(f, v);
    } else if (t === "select") {
      const opts = f.opts || optionsFrom(f.opts_from, C);
      v = v === null || v === undefined ? null : String(v);
      if (!opts.some((o: Any) => o.value === v)) throw new CalcError(`${f.l}: choose one of the options`);
      out[k] = v;
    } else if (t === "bool") {
      out[k] = v === true || v === "true" || v === 1 || v === "1" || v === "yes";
    } else if (t === "series") {
      if (!Array.isArray(v) || !v.length) throw new CalcError(`${f.l}: enter the values`);
      const vals = v.filter((x: Any) => x !== null && x !== undefined && x !== "").map(Number);
      if (vals.some((x: number) => !Number.isFinite(x))) throw new CalcError(`${f.l}: numbers only`);
      if (!vals.length || vals.some((x: number) => x < 0) || vals.length > 24) throw new CalcError(`${f.l}: enter up to 24 positive values`);
      if (f.max !== undefined && f.max !== null && vals.some((x: number) => x > f.max)) throw new CalcError(`${f.l}: each value must be at most ${fmtLimit(f.max)}`);
      out[k] = vals;
    } else if (t === "lines") {
      const rows: Any[] = [];
      for (const row of (v || []).slice(0, 100)) {
        const r: Any = {};
        for (const sf of f.fields) {
          let x = row[sf.k];
          if (sf.t === "number") {
            x = x === null || x === undefined || x === "" ? 0 : Number(x);
            if (!Number.isFinite(x)) throw new CalcError(`${f.l}: ${sf.l} must be a number`);
            if (sf.min !== undefined && x < sf.min) throw new CalcError(`${f.l}: ${sf.l} must be at least ${fmtLimit(sf.min)}`);
            if (sf.max !== undefined && x > sf.max) throw new CalcError(`${f.l}: ${sf.l} must be at most ${fmtLimit(sf.max)}`);
          } else if (sf.t === "select") {
            if (!sf.opts.some((o: Any) => o.value === x)) throw new CalcError(`${f.l}: choose a ${sf.l.toLowerCase()}`);
          } else x = String(x || "").slice(0, 80);
          r[sf.k] = x;
        }
        rows.push(r);
      }
      out[k] = rows;
    } else out[k] = String(v || "").slice(0, 200);
  }
  return out;
}

// ------------------------------------------------------------------ shared electrical pieces
// T.O. 6/2025: the rate of the band the PF falls in, for every 0.01 drop measured from the threshold
function pfPct(pf: number, thr: number, bands: Any[]) {
  pf = R(pf, 2);
  if (pf >= thr) return 0;
  const sorted = [...bands].sort((a: Any, b: Any) => b.to - a.to);
  const band = sorted.find((b: Any) => pf >= b.from - 1e-9) || sorted[sorted.length - 1];
  return R(pyRound((thr - pf) * 100) * band.pct_per_0_01, 2);
}
const pfPenaltyPct = (pf: number, C: Any) => pfPct(pf, C.pf_threshold, C.pf_penalty);
const ltPfPenaltyPct = (pf: number, C: Any) => pfPct(pf, C.lt_pf_threshold ?? 0.85, C.lt_pf_penalty || [{ from: 0, to: 0.85, pct_per_0_01: 1.0 }]);
function tariffHt(t: Any, units: number, md: number, cd: number, peak: number, night: number, pf: number, C: Any) {
  const energy = units * t.energy;
  let tod = 0;
  if (t.tod) tod = ((units * peak) / 100) * t.energy * C.tod.peak_surcharge_pct / 100 - ((units * night) / 100) * t.energy * C.tod.night_rebate_pct / 100;
  const floor = C.billing_demand_floor_pct / 100;
  const billed = Math.max(md, floor * cd);
  const excess = Math.max(md - cd, 0);
  const demand = billed * t.demand + excess * t.demand * (C.excess_demand_multiplier - 1);
  const penPct = pfPenaltyPct(pf, C);
  const pfPen = ((energy + tod) * penPct) / 100;
  const tax = ((energy + tod) * C.electricity_tax_pct) / 100;
  const meter = t.meter_rent || 0;
  return { energy, tod, demand, billed_kva: billed, excess_kva: excess, pf_penalty: pfPen, pf_penalty_pct: penPct, tax, meter_rent: meter, total: energy + tod + demand + pfPen + tax + meter };
}
function ltFixedRate(t: Any, kw: number) {
  for (const [limit, rate] of t.fixed_slabs) if (kw <= limit) return rate;
  return t.fixed_slabs[t.fixed_slabs.length - 1][1];
}
// LT bill per T.O. 6/2025: fixed charges per kW or part of a kW (cl. 3.2.1(g)); time-of-day on LT IIIB / LT V
// (cl. 3.2.1(c), and without a ToD meter 25% on 20% of units, cl. 3.2.1(d)); PF penalty below 0.85 (cl. 3.2.1(b))
function tariffLt(t: Any, units: number, loadKw: number, C: Any, peakShare: Any = null, nightShare: Any = null, pf: Any = null) {
  const rate = "energy_low" in t && units <= t.low_units ? t.energy_low : t.energy;
  const energy = units * rate;
  let tod = 0;
  if (t.tod) {
    const peak = peakShare === null || peakShare === undefined ? (C.tod.lt_no_meter_peak_share_pct ?? 20) : peakShare;
    const night = nightShare === null || nightShare === undefined ? 0 : nightShare;
    tod = ((units * peak) / 100) * rate * C.tod.peak_surcharge_pct / 100 - ((units * night) / 100) * rate * C.tod.night_rebate_pct / 100;
  }
  const kw = loadKw > 0 ? Math.ceil(loadKw - 1e-9) : 0;
  const fixedRate = ltFixedRate(t, kw);
  const fixed = kw * fixedRate;
  const penPct = pf === null || pf === undefined ? 0 : ltPfPenaltyPct(pf, C);
  const pfPen = ((energy + tod) * penPct) / 100;
  const tax = ((energy + tod) * C.electricity_tax_pct) / 100;
  return { energy, tod, fixed, fixed_rate: fixedRate, billed_kw: kw, pf_penalty: pfPen, pf_penalty_pct: penPct, tax, total: energy + tod + fixed + pfPen + tax };
}
function cableR90(C: Any, conductor: string, size: string) {
  const tab = C.cable[conductor === "al" ? "r20_al" : "r20_cu"];
  if (!(String(size) in tab)) throw new CalcError(`${size} mm² is not available in ${conductor === "al" ? "aluminium" : "copper"}`);
  const a = C.cable.alpha[conductor];
  return tab[String(size)] * (1 + a * (90 - 20));
}
function vdrop(current: number, lengthM: number, r: number, x: number, pf: number, phase3 = true, runs = 1) {
  const sin = Math.sqrt(Math.max(0, 1 - pf * pf));
  const k = phase3 ? SQ3 : 2;
  return (k * current * (lengthM / 1000) * (r * pf + x * sin)) / runs;
}
const sizesOf = (C: Any, key: string) => Object.keys(C.cable[key]).sort((a, b) => parseFloat(a) - parseFloat(b));
function derating(C: Any, laying: string, ambient: number, group: number, spacing: string, soil: string, depth: string, ht: boolean) {
  const cab = C.cable;
  const base = cab.base_temp[laying === "ground" ? "ground" : "air"];
  const tmax = cab.max_temp.xlpe;
  if (ambient >= tmax) throw new CalcError("Temperature too high for the cable");
  const kt = Math.sqrt((tmax - ambient) / (tmax - base));
  const n = Math.trunc(group);
  let kg; let kd; let ks;
  if (laying === "ground") {
    kg = ceilKey(cab[spacing === "touching" ? "group_ground_touching" : "group_ground_spaced"], n);
    kd = cab.depth[String(depth)] / (ht ? cab.depth["90"] : 1.0);
    ks = cab.soil[String(soil)];
  } else { kg = ceilKey(cab.group_air_tray, n); kd = 1.0; ks = 1.0; }
  return { temp: kt, group: kg, depth: kd, soil: ks, base, total: kt * kg * kd * ks };
}
function selectCable(C: Any, current: number, volts: number, pf: number, length: number, conductor: string, laying: string, ambient: number, group: number, spacing: string, soil: string, depth: string, vdLimit: number, faultKa: number, clearS: number) {
  const ht = volts >= 1000;
  const key = ht ? "al_xlpe_ht" : conductor === "al" ? "al_xlpe" : "cu_xlpe";
  const cond = ht ? "al" : conductor;
  const der = derating(C, laying, ambient, group, spacing, soil, depth, ht);
  const idx = laying === "ground" ? 0 : 1;
  const x = C.cable.x_ohm_km[ht ? "ht" : "lt"];
  const kSc = C.cable.k_short_circuit[`${cond === "al" ? "al" : "cu"}_xlpe`];
  const phase3 = volts !== 230;
  const rows: Any[] = [];
  let chosen: Any = null;
  let byCurrent: Any = null;
  for (let runs = 1; runs < 9; runs += 1) {
    for (const s of sizesOf(C, key)) {
      if (runs > 1 && parseFloat(s) < 95) continue;
      const rated = C.cable[key][s][idx] * der.total;
      const r = cableR90(C, cond, s);
      const vd = vdrop(current, length, r, x, pf, phase3, runs);
      const vdPct = (vd / volts) * 100;
      const sMin = faultKa ? (faultKa * 1000 * Math.sqrt(clearS)) / kSc / runs : 0;
      const okI = rated * runs >= current;
      const okV = vdPct <= vdLimit + 1e-9;
      const okS = parseFloat(s) >= sMin - 1e-9;
      if (okI && okV && byCurrent === null) byCurrent = { size: s, runs };
      if (runs === 1 || (chosen === null && runs > 1)) rows.push({ size: s, runs, rated: rated * runs, vd_pct: vdPct, s_min: sMin, ok: okI && okV && okS, ok_i: okI, ok_v: okV, ok_s: okS });
      if (okI && okV && okS) { chosen = { size: s, runs, rated: rated * runs, vd_pct: vdPct, vd, s_min: sMin, r, x }; break; }
    }
    if (chosen) break;
  }
  return { chosen, by_current: byCurrent, derating: der, rows: rows.slice(0, 16), key, cond, k_sc: kSc, x };
}
const motorEffPf = (C: Any, kw: number) => floorKey(C.motor_eff_pf, kw);
const fmtSize = (s: Any, runs: number) => (runs > 1 ? `${runs} × ${s} mm²` : `${s} mm²`);

// ------------------------------------------------------------------ 1
function tConnectedLoad(i: Any, C: Any) {
  const pf = i.pf;
  const steps: Any[] = [];
  let connKw = 0; let sumDmd = 0; let table: Any = null;
  if (i.method === "area") {
    const density = C.load_density_va_sqm[i.building];
    const connKva = (i.area * density) / 1000;
    connKw = connKva * pf;
    sumDmd = connKw;
    steps.push(step("Connected load", `${g(i.area)} m² × ${density} VA/m² × PF ${g(pf)}`, R(connKw, 1), "kW"));
  } else {
    const rows: Any[] = [];
    for (const ln of i.loads) {
      const tot = ln.qty * ln.kw;
      const dmd = tot * ln.df;
      connKw += tot; sumDmd += dmd;
      rows.push([ln.name || "Load", R(ln.qty, 2), R(ln.kw, 2), R(tot, 2), R(ln.df, 2), R(dmd, 2)]);
    }
    steps.push(step("Connected load", "Σ qty × kW", R(connKw, 2), "kW"));
    steps.push(step("Sum of individual demands", "Σ qty × kW × demand factor", R(sumDmd, 2), "kW"));
    table = { title: "Load list", columns: ["Load", "Qty", "kW each", "Total kW", "Demand factor", "Demand kW"], rows };
  }
  const mdKw = sumDmd * i.diversity;
  steps.push(step("Maximum demand now", `${g(R(sumDmd, 2))} × simultaneity ${g(i.diversity)}`, R(mdKw, 2), "kW"));
  const mdFuture = mdKw * (1 + i.growth / 100);
  steps.push(step("With growth", `${g(R(mdKw, 2))} × (1 + ${g(i.growth)}%)`, R(mdFuture, 2), "kW"));
  const mdKva = mdFuture / pf;
  steps.push(step("Maximum demand", `${g(R(mdFuture, 2))} kW ÷ PF ${g(pf)}`, R(mdKva, 2), "kVA"));
  const ltMax = C.lt_max_kw;
  let supply; let verdict; let sugg; let status;
  if (mdFuture <= ltMax) {
    supply = "LT";
    verdict = `LT supply works: your maximum demand of ${g(R(mdFuture, 1))} kW is within the ${ltMax} kW LT limit in Tamil Nadu.`;
    if (mdFuture > C.lt_ct_min_kw) verdict += " Expect CT-operated (LT-CT) metering at this size.";
    sugg = item("Suggested LT sanctioned load", Math.ceil(mdFuture - 1e-9), "kW", "int");
    status = "ok";
  } else {
    supply = "HT";
    verdict = `HT supply needed: ${g(R(mdFuture, 1))} kW is above the ${ltMax} kW LT limit in Tamil Nadu.`;
    sugg = item("Suggested contract demand", Math.trunc(Math.ceil(mdKva / 5) * 5), "kVA", "int");
    status = "warn";
  }
  const [nTx, tx] = txPlan(mdKva / 0.8, C);
  const items = [item("Connected load", R(connKw, 1), "kW", "1dp"), item("Maximum demand now", R(mdKw, 1), "kW", "1dp"),
    item("Maximum demand with growth", R(mdFuture, 1), "kW", "1dp"), item("Maximum demand", R(mdKva, 1), "kVA", "1dp"),
    item("Supply", supply, null, null, "accent"), sugg];
  if (supply === "HT") items.push(item("Transformer (≤80% loading)", nTx === 1 ? `${tx} kVA` : `${nTx} × ${tx} kVA`));
  return { headline: { label: "Maximum demand", value: R(mdKva, 1), unit: "kVA", sub: `${supply} supply` }, status, verdict, items, table, steps,
    notes: ["Demand and simultaneity factors are typical; your actual running pattern matters. A site survey firms this up.",
      "LT limit and metering per the TNERC supply code; verify for your area.",
      ...(supply === "LT" && connKw > mdFuture + 0.5 ? [`The suggestion is your maximum demand with growth. If the section office sanctions your connected load (${Math.ceil(connKw - 1e-9)} kW) instead, fixed charges are billed on that figure`
        + (connKw > ltMax ? `, and above ${ltMax} kW it needs an HT service.` : ".")] : [])] };
}

// ------------------------------------------------------------------ 2
function tLtVsHt(i: Any, C: Any) {
  const [ltKey, htKey] = i.category === "industrial" ? ["LT_IIIB", "HT_I"] : ["LT_V", "HT_III"];
  const ltT = C.tariffs[ltKey]; const htT = C.tariffs[htKey];
  const { md_kva: mdKva, units, pf } = i;
  const mdKw = mdKva * pf;
  const [nTx, tx] = txPlan(mdKva / 0.8, C);
  const [nll, ll] = C.transformer_losses[String(tx)] || [0, 0];
  const avgKva = units / 720 / pf;
  const frac = avgKva / (tx * nTx);
  const lossKwh = (nTx * (nll + ll * frac * frac) * 720) / 1000;
  const ht = tariffHt(htT, units + lossKwh, mdKva, mdKva, i.peak_share, i.night_share, pf, C);
  const ltOk = mdKw <= C.lt_max_kw;
  const lt = ltOk ? tariffLt(ltT, units, mdKw, C, i.peak_share, i.night_share, pf) : null;
  let cost = i.substation_cost;
  let costNote;
  const txTxt = nTx === 1 ? `${tx} kVA` : `${nTx} × ${tx} kVA`;
  if (cost === null || cost === undefined) {
    const rate = C.substation_cost_per_kva.find(([lim]: number[]) => tx <= lim)[1];
    cost = nTx * tx * rate;
    costNote = `typical ${txTxt} substation at ₹${ind(rate)}/kVA`;
  } else costNote = "your figure";
  const steps = [step("Transformer for HT", `${g(R(mdKva, 1))} kVA ÷ 0.8 → next standard`, txTxt),
    step("Transformer losses billed on HT side", `${nTx > 1 ? `${nTx} × ` : ""}(${nll} + ${ll} × ${g(R(frac, 3))}²) W × 720 h`, R(lossKwh, 0), "kWh/month"),
    step("HT monthly bill", "energy + ToD + demand + tax + meter rent", R(ht.total, 0), "₹")];
  const dash = "—";
  const rows = [["Energy", lt ? R(lt.energy, 0) : dash, R(ht.energy, 0)], ["Fixed / demand charges", lt ? R(lt.fixed, 0) : dash, R(ht.demand, 0)],
    ["Time-of-day (peak +, night −)", lt ? R(lt.tod, 0) : dash, R(ht.tod, 0)], ["PF penalty", lt ? R(lt.pf_penalty, 0) : dash, R(ht.pf_penalty, 0)],
    ["Electricity tax", lt ? R(lt.tax, 0) : dash, R(ht.tax, 0)],
    ["Meter rent", lt ? 0 : dash, R(ht.meter_rent, 0)], ["Monthly total", lt ? R(lt.total, 0) : dash, R(ht.total, 0)],
    ["Yearly total", lt ? R(lt.total * 12, 0) : dash, R(ht.total * 12, 0)]];
  const items: Any[] = [item("HT yearly bill", R(ht.total * 12, 0), "₹", "inr")];
  let verdict; let status;
  if (ltOk && lt) {
    const saving = (lt.total - ht.total) * 12;
    steps.unshift(step("LT monthly bill", "energy + ToD + fixed (per kW slab) + PF penalty + tax", R(lt.total, 0), "₹"));
    items.unshift(item("LT yearly bill", R(lt.total * 12, 0), "₹", "inr"));
    items.push(item("Yearly difference (LT − HT)", R(saving, 0), "₹", "inr", saving > 0 ? "good" : "bad"));
    items.push(item("Substation cost", R(cost, 0), "₹", "inr"));
    if (saving > 0) {
      const payback = cost / saving;
      items.push(item("Payback", R(payback, 1), "years", "1dp", payback <= 5 ? "good" : null));
      steps.push(step("Payback", `₹${ind(R(cost, 0))} ÷ ₹${ind(R(saving, 0))} per year`, R(payback, 1), "years"));
      verdict = `HT saves about ₹${g(R(saving / 100000, 2))} lakh a year; the substation pays back in ${g(R(payback, 1))} years.`;
      status = payback <= 5 ? "ok" : "warn";
    } else { verdict = "LT is cheaper to run at this load; HT doesn't pay back."; status = "warn"; }
  } else {
    verdict = `HT is required: ${g(R(mdKw, 1))} kW is above the ${C.lt_max_kw} kW LT limit.`;
    status = "warn";
    items.push(item("Substation cost", R(cost, 0), "₹", "inr"));
  }
  const diffY = ltOk && lt ? (lt.total - ht.total) * 12 : 0;
  const headLabel = ltOk ? (diffY > 0 ? "HT saves per year" : "LT saves per year") : "HT yearly bill";
  return { headline: { label: headLabel, value: R(ltOk ? Math.abs(diffY) : ht.total * 12, 0), unit: "₹", fmt: "inr" }, status, verdict, items,
    table: { title: `Monthly bill: ${ltT.label.split(" —")[0]} vs ${htT.label.split(" —")[0]}`, columns: ["", "LT ₹", "HT ₹"], rows },
    steps, notes: [`Substation cost: ${costNote}.`, `Rates: ${C.tariff_order}.`, "HT is metered on the HT side, so transformer losses are added to HT units.",
      `Time-of-day applies to both LT and HT: +${C.tod.peak_surcharge_pct}% on peak-hour units (${C.tod.peak_hours}), −${C.tod.night_rebate_pct}% at night (${C.tod.night_hours}).`] };
}

// ------------------------------------------------------------------ 3
function tBillEstimator(i: Any, C: Any) {
  const t = C.tariffs[i.tariff];
  let b: Any; let rows; let notes: string[] = []; let status = "ok"; let unitRate;
  if (t.kind === "HT") {
    b = tariffHt(t, i.units, i.md_kva, i.cd_kva, i.peak_share, i.night_share, i.pf, C);
    rows = [["Energy", `${ind(i.units)} kWh × ₹${t.energy}`, R(b.energy, 0)],
      ["Time-of-day", `peak +${C.tod.peak_surcharge_pct}% on ${g(i.peak_share)}%, night −${C.tod.night_rebate_pct}% on ${g(i.night_share)}%`, R(b.tod, 0)],
      ["Demand charges", `${g(R(b.billed_kva, 1))} kVA × ₹${t.demand}${b.excess_kva ? ` + excess ${g(R(b.excess_kva, 1))} kVA` : ""}`, R(b.demand, 0)],
      ["PF penalty", b.pf_penalty_pct ? `PF ${g(i.pf)}: ${g(b.pf_penalty_pct)}% of energy charges` : `PF ${g(i.pf)}: none (starts below ${g(C.pf_threshold)})`, R(b.pf_penalty, 0)],
      ["Electricity tax", `${C.electricity_tax_pct}% of energy + ToD`, R(b.tax, 0)], ["Meter rent", "", R(b.meter_rent, 0)], ["Total", "", R(b.total, 0)]];
    if (b.excess_kva) notes.push(`Demand exceeded the contract demand by ${g(R(b.excess_kva, 1))} kVA — excess is charged at ${C.excess_demand_multiplier}× the rate.`);
    if (b.pf_penalty_pct) notes.push("Improve power factor to 0.90 or above to avoid the penalty — see the Power factor correction tool.");
    status = b.excess_kva || b.pf_penalty_pct ? "warn" : "ok";
    unitRate = i.units ? b.total / i.units : 0;
  } else {
    const meter = i.tod_meter;
    b = tariffLt(t, i.units, i.load_kw, C, meter ? i.peak_share : null, meter ? i.night_share : null, i.pf);
    const ltThr = C.lt_pf_threshold ?? 0.85;
    const noMeter = C.tod.lt_no_meter_peak_share_pct ?? 20;
    rows = [["Energy", `${ind(i.units)} kWh`, R(b.energy, 0)],
      ["Time-of-day", meter ? `peak +${C.tod.peak_surcharge_pct}% on ${g(i.peak_share)}%, night −${C.tod.night_rebate_pct}% on ${g(i.night_share)}%` : `no ToD meter: +${C.tod.peak_surcharge_pct}% on ${noMeter}% of units`, R(b.tod, 0)],
      ["Fixed charges", `${g(b.billed_kw)} kW × ₹${b.fixed_rate}`, R(b.fixed, 0)],
      ["PF penalty", b.pf_penalty_pct ? `PF ${g(i.pf)}: ${g(b.pf_penalty_pct)}% of energy charges (three-phase services)` : `PF ${g(i.pf)}: none (starts below ${g(ltThr)})`, R(b.pf_penalty, 0)],
      ["Electricity tax", `${C.electricity_tax_pct}% of energy + ToD`, R(b.tax, 0)], ["Total", "", R(b.total, 0)]];
    notes = meter ? [`Without a ToD meter TNPDCL may bill the ${C.tod.peak_surcharge_pct}% peak charge on ${noMeter}% of units instead — switch off "ToD meter fitted" to see that.`] : []; status = "ok";
    if (b.pf_penalty_pct) { notes.push(`Improve power factor to ${g(ltThr)} or above to avoid the penalty — see the Power factor correction tool.`); status = "warn"; }
    if (i.load_kw > C.lt_max_kw) { notes.push(`LT supply is limited to ${C.lt_max_kw} kW; above this an HT connection is needed.`); status = "warn"; }
    unitRate = i.units ? b.total / i.units : 0;
  }
  notes.push(`Rates: ${C.tariff_order}. Fuel and other surcharges, if any, are not included.`);
  return { headline: { label: "Estimated monthly bill", value: R(b.total, 0), unit: "₹", fmt: "inr" }, status, verdict: `About ₹${g(R(unitRate, 2))} per unit all-in.`,
    items: [item("Monthly bill", R(b.total, 0), "₹", "inr"), item("Average cost per unit", R(unitRate, 2), "₹/kWh", "2dp")],
    table: { title: t.label, columns: ["Charge", "How", "₹"], rows }, steps: [], notes };
}

// ------------------------------------------------------------------ 4
function tContractDemand(i: Any, C: Any, TOOLS: Any) {
  const t = C.tariffs[i.tariff];
  const rate = t.demand; const floor = C.billing_demand_floor_pct / 100; const mult = C.excess_demand_multiplier;
  const mds: number[] = i.md;
  const cost = (cd: number) => sum(mds.map((m) => Math.max(m, floor * cd) * rate + Math.max(m - cd, 0) * rate * (mult - 1)));
  const peak = Math.max(...mds);
  if (peak <= 0) throw new CalcError(`${labelOf(TOOLS, "contract-demand", "md")}: enter at least one month above 0`);
  const lo = Math.trunc(Math.floor((peak * 0.7) / 5) * 5) || 5;
  const hi = Math.max(Math.trunc(Math.ceil((peak * 1.3) / 5) * 5), lo);
  let bestCd: Any = null; let best: Any = null;
  for (let cd = lo; cd <= hi; cd += 5) {
    const c = cost(cd);
    if (best === null || c < best - 0.5) { bestCd = cd; best = c; } else if (c <= best + 0.5) bestCd = cd; // same cost at a higher demand: the headroom is free
  }
  const now = cost(i.cd_kva);
  const saving = now - best;
  const rows = mds.map((m, n) => [`Month ${n + 1}`, R(m, 1), R(Math.max(m, floor * i.cd_kva), 1), R(Math.max(m, floor * bestCd), 1), R(Math.max(m - bestCd, 0), 1)]);
  const over = mds.filter((m) => m > bestCd).length;
  return { headline: { label: "Best contract demand", value: bestCd, unit: "kVA" }, status: "ok",
    verdict: saving > 1 ? `Changing the contract demand from ${g(i.cd_kva)} to ${bestCd} kVA saves about ₹${ind(R(saving, 0))} a year in demand charges.` : `Your present contract demand of ${g(i.cd_kva)} kVA is already close to the best.`,
    items: [item("Present yearly demand charges", R(now, 0), "₹", "inr"), item("At the best contract demand", R(best, 0), "₹", "inr"),
      item("Yearly saving", R(saving, 0), "₹", "inr", saving > 0 ? "good" : null), item("Highest recorded demand", R(peak, 1), "kVA", "1dp"),
      item("Months above the new CD", over, null, "int", over ? "warn" : null), item("Demand charge rate", `₹${g(rate)}/kVA (${t.label.split(" — ")[0]})`)],
    table: { title: "Billing demand by month (kVA)", columns: ["Month", "Recorded", `Billed at ${g(i.cd_kva)}`, `Billed at ${bestCd}`, "Excess at new CD"], rows },
    steps: [step("Billing demand", `higher of recorded MD or ${C.billing_demand_floor_pct}% of CD`, "per month"),
      step("Excess demand", `above CD, charged at ${mult}× ₹${rate}/kVA`, "per month"), step("Search", `CD from ${lo} to ${hi} kVA in 5 kVA steps`, `${bestCd} kVA`)],
    notes: ["Keep some margin for growth; repeated excess demand can also lead to notices from TNPDCL.",
      "A change of contract demand needs an application and may have a minimum period. We can file it for you."] };
}

// ------------------------------------------------------------------ 5
function tHtRoadmap(i: Any, C: Any, TOOLS: Any) {
  const w = C.ht_roadmap_weeks;
  const stepsList: [string, number[]][] = [["Application to TNPDCL and feasibility / field inspection", w.application_to_feasibility],
    ["Estimate issued and paid (line extension, supervision charges, deposit)", w.estimate_payment], ["CEIG drawing approval for the substation", w.ceig_drawing_approval],
    ["Substation works: transformer, HT panel / RMU, cabling, earthing, LT panel", w.works], ["Testing, CEIG inspection, meter fixing and energisation", w.inspection_energisation]];
  const lo = sum(stepsList.map((s) => s[1][0])); const hi = sum(stepsList.map((s) => s[1][1]));
  const [nTx, tx] = txPlan(i.kva / 0.8, C);
  const rate = C.substation_cost_per_kva.find(([lim]: number[]) => tx <= lim)[1];
  const subCost = nTx * tx * rate;
  const rows = stepsList.map((s, n) => [n + 1, s[0], `${s[1][0]}–${s[1][1]} weeks`]);
  const small = i.kva * 0.9 <= C.lt_max_kw;
  return { headline: { label: "Typical time to energise", value: `${lo}–${hi}`, unit: "weeks" }, status: small ? "warn" : "ok",
    verdict: `A ${g(i.kva)} kVA ${i.voltage.replace("kV", " kV")} service typically takes ${lo}–${hi} weeks from application to energisation, with the steps one after another; works can start while approvals are pending, which shortens it.`
      + (small ? ` At this size an LT service (up to ${C.lt_max_kw} kW) may be enough — check with the LT vs HT tool.` : ""),
    items: [item("Transformer (≤80% loading)", nTx === 1 ? `${tx} kVA` : `${nTx} × ${tx} kVA`), item("Indicative substation cost (our scope)", R(subCost, 0), "₹", "inr"), item("Time", `${lo}–${hi} weeks`)],
    table: { title: "Steps", columns: ["#", "Step", "Typical time"], rows }, checklist: TOOLS.checklists[i.kind !== "load_increase" ? "new_ht" : "load_change"],
    steps: [], notes: ["Times depend on the TNPDCL section office, line distance and CEIG workload.", "TNPDCL line extension and deposits are billed by TNPDCL and are not in the substation cost."] };
}

// ------------------------------------------------------------------ 6
function tTransformerSizing(i: Any, C: Any) {
  const mdKw = i.load_kw * i.demand_factor; const mdKva = mdKw / i.pf;
  const fut = mdKva * (1 + i.growth / 100); const need = fut / (i.max_loading / 100);
  const rating = nextStd(need, C.transformer_ratings);
  const steps = [step("Maximum demand", `${g(i.load_kw)} kW × ${g(i.demand_factor)} ÷ PF ${g(i.pf)}`, R(mdKva, 1), "kVA"),
    step("With growth", `× (1 + ${g(i.growth)}%)`, R(fut, 1), "kVA"), step("Rating needed", `÷ ${g(i.max_loading)}% loading`, R(need, 1), "kVA")];
  if (rating === null) {
    const n = Math.ceil(need / 2500);
    return { headline: { label: "Transformers", value: `${n} × 2500`, unit: "kVA" }, status: "warn",
      verdict: `${g(R(need, 0))} kVA is beyond one standard distribution transformer; use ${n} units or a power transformer.`, items: [item("Rating needed", R(need, 0), "kVA", "int")], steps, notes: [] };
  }
  const loadNow = (mdKva / rating) * 100; const loadFut = (fut / rating) * 100;
  const [nll, ll] = C.transformer_losses[String(rating)] || [0, 0];
  const lossNow = nll + ll * (loadNow / 100) ** 2;
  const ttype = i.location === "indoor" ? "Dry type (cast resin)" : "Oil-filled (ONAN)";
  return { headline: { label: "Transformer", value: rating, unit: "kVA", sub: ttype }, status: "ok",
    verdict: `${rating} kVA ${i.location === "indoor" ? "dry-type" : "oil-filled"} transformer: ${g(R(loadNow, 0))}% loaded today and ${g(R(loadFut, 0))}% after growth.`,
    items: [item("Maximum demand", R(mdKva, 1), "kVA", "1dp"), item("With growth", R(fut, 1), "kVA", "1dp"), item("Standard rating", rating, "kVA", "int", "accent"),
      item("Loading today", R(loadNow, 0), "%", "int"), item("Loading after growth", R(loadFut, 0), "%", "int"), item("Type", ttype), item("Losses at today's load (typical)", R(lossNow, 0), "W", "int")],
    steps, notes: ["Indoor transformers inside buildings are normally dry type for fire safety.", "Ratings per IS 1180 up to 2500 kVA; choose an energy-efficiency level by total owning cost.",
      ...(i.location === "indoor" ? ["Losses shown are typical oil-type (IS 1180) values; dry-type (IS 11171) losses differ — use the maker's figures."] : [])] };
}

// ------------------------------------------------------------------ 7
function tTransformerLosses(i: Any, C: Any) {
  void C;
  const load = i.avg_load / 100; const h = i.hours;
  const rows: Any[] = []; let best: Any = null;
  const a = (h * i.tariff * i.years) / 1000; const b = a * load * load;
  for (const o of i.options) {
    const kwh = (o.nll * h + o.ll * load * load * h) / 1000;
    const yearly = kwh * i.tariff; const toc = o.price + yearly * i.years;
    rows.push([o.name || "Offer", R(o.price, 0), R(kwh, 0), R(yearly, 0), R(toc, 0)]);
    if (best === null || toc < best[1]) best = [o.name || "Offer", toc];
  }
  if (!rows.length) throw new CalcError("Add at least one offer");
  rows.sort((x, y) => x[4] - y[4]);
  const gap = rows.length > 1 ? rows[1][4] - rows[0][4] : 0;
  return { headline: { label: "Lowest total owning cost", value: best[0], sub: `₹${ind(R(best[1], 0))} over ${g(i.years)} years` }, status: "ok",
    verdict: gap ? `${best[0]} costs ₹${ind(R(gap, 0))} less over ${g(i.years)} years than the next best (${rows[1][0]}) once losses are counted.`
      : rows.length > 1 ? `${best[0]} and ${rows[1][0]} cost the same over ${g(i.years)} years.` : `${best[0]}.`,
    items: [item("Capitalised no-load loss (A)", R(a, 2), "₹ per W", "2dp"), item("Capitalised load loss (B)", R(b, 2), "₹ per W", "2dp")],
    table: { title: `${i.kva} kVA offers`, columns: ["Offer", "Price ₹", "Losses kWh/yr", "Loss cost ₹/yr", "Total owning cost ₹"], rows },
    steps: [step("Yearly loss energy", "(no-load W × hours + load W × loading² × hours) ÷ 1000", "kWh"), step("Total owning cost", `price + loss cost × ${g(i.years)} years`, "₹"),
      step("Equivalent", "TOC = price + A × no-load W + B × load W", `A = ₹${g(R(a, 2))}, B = ₹${g(R(b, 2))}`)],
    notes: ["Simple (undiscounted) comparison. Use the maker's guaranteed losses from the offer."] };
}

// ------------------------------------------------------------------ 8
function tDgSizing(i: Any, C: Any) {
  const runKva = i.running_kw / i.pf; const mKw = i.motor_kw;
  let eff = 0; let mpf = 0; let mRunKva = 0; let mStart = 0; let mult = 0;
  if (mKw > 0) { [eff, mpf] = motorEffPf(C, mKw); mRunKva = mKw / (eff * mpf); mult = C.motor_start_multiple[i.starter]; mStart = mRunKva * mult; }
  const others = Math.max(runKva - mRunKva, 0);
  const eqKva = Math.max(runKva, i.running_kw / 0.8); // a set gives 0.8 kW per kVA, so a high-PF load is limited by kW
  const req1 = eqKva / 0.8; const req2 = mKw > 0 ? (others + mStart) / i.transient : 0;
  const need = Math.max(req1, req2);
  const rating = nextStd(need, C.dg_ratings);
  const fuelLph = i.running_kw * C.dg_fuel_l_per_kwh; const monthlyL = fuelLph * i.hours; const monthlyCost = monthlyL * C.diesel_price;
  const kwBound = i.running_kw / 0.8 > runKva + 1e-9;
  const governs = req1 >= req2 ? (kwBound ? "running kW (a DG gives 0.8 kW per kVA)" : "running load") : "motor starting";
  const steps = [step("Running load", `${g(i.running_kw)} kW ÷ PF ${g(i.pf)}`, R(runKva, 1), "kVA")];
  if (kwBound) steps.push(step("kW limit of the set", `${g(i.running_kw)} kW ÷ 0.8 (sets are rated at PF 0.8)`, R(eqKva, 1), "kVA"));
  steps.push(step("For ≤80% loading", `${g(R(eqKva, 1))} ÷ 0.8`, R(req1, 1), "kVA"));
  if (mKw > 0) {
    steps.push(step("Largest motor running", `${g(mKw)} kW ÷ (η ${g(eff)} × PF ${g(mpf)})`, R(mRunKva, 1), "kVA"),
      step("Its starting kVA", `× ${g(mult)} (${i.starter.replaceAll("_", "-")})`, R(mStart, 1), "kVA"),
      step("Step-load check", `(${g(R(others, 1))} + ${g(R(mStart, 1))}) ÷ ${g(i.transient)}`, R(req2, 1), "kVA"));
  }
  if (rating === null) return { headline: { label: "DG needed", value: R(need, 0), unit: "kVA" }, status: "warn", verdict: "Larger than single standard sets — consider sets in parallel.", items: [], steps, notes: [] };
  return { headline: { label: "DG set", value: rating, unit: "kVA" }, status: "ok",
    verdict: `A ${rating} kVA DG set (${g(R(rating * 0.8, 1))} kW) covers the load; sizing is set by ${governs}. It runs at ${g(R((eqKva / rating) * 100, 0))}% loading.`,
    items: [item("Running load", R(runKva, 1), "kVA", "1dp"), item("Size needed", R(need, 1), "kVA", "1dp"),
      ...(mKw > 0 ? [item("Largest motor starting", R(mStart, 1), "kVA", "1dp"), item("Size for motor starting", R(req2, 1), "kVA", "1dp")] : []),
      item("Standard DG rating", rating, "kVA", null, "accent"), item("kW rating (at PF 0.8)", R(rating * 0.8, 1), "kW", "1dp"),
      item("Loading", R((eqKva / rating) * 100, 0), "%", "int"), item("Fuel at this load", R(fuelLph, 1), "litres/hour", "1dp"),
      item("Fuel per month", R(monthlyL, 0), "litres", "int"), item("Diesel cost per month", R(monthlyCost, 0), "₹", "inr")],
    steps, notes: [`Fuel at ${C.dg_fuel_l_per_kwh} L/kWh and ₹${C.diesel_price}/L (typical; check the maker's curve).`, "Stagger large motor starts and keep DG loading above 30% to avoid wet stacking."] };
}

// ------------------------------------------------------------------ 9
function tUpsBattery(i: Any, C: Any) {
  const kva = (i.load_kw / i.pf) * (1 + i.growth / 100);
  let ups = nextStd(kva, C.ups_ratings);
  let nUps = 1;
  if (ups === null) { nUps = Math.ceil(kva / C.ups_ratings[C.ups_ratings.length - 1]); ups = nextStd(kva / nUps, C.ups_ratings); }
  const upsTxt = nUps === 1 ? `${ups} kVA` : `${nUps} × ${ups} kVA (parallel)`;
  const v = parseFloat(i.bank_v);
  const mins = Math.max(i.backup_min, 5); // lead-acid ratings start at 5 minutes; a shorter backup still needs a 5-minute battery
  const wh = (i.load_kw * 1000 * mins) / 60;
  const rateF = interp(C.battery_rate_factor || [[0, 1.0], [1, 1.0]], mins);
  const usable = Math.min(i.dod, rateF);
  const ah = (wh / (v * i.eff * usable)) * i.ageing;
  let block; let strings;
  if (ah <= C.battery_ah[C.battery_ah.length - 1]) { block = nextStd(ah, C.battery_ah); strings = 1; } else { block = C.battery_ah[C.battery_ah.length - 1]; strings = Math.ceil(ah / block); }
  const perString = Math.trunc(v / 12);
  const steps = [step("UPS rating", `${g(i.load_kw)} kW ÷ PF ${g(i.pf)} × (1 + ${g(i.growth)}%)`, R(kva, 2), "kVA"),
    step("Energy for backup", `${g(i.load_kw)} kW × ${g(mins)} min${i.backup_min < 5 ? " (sized as a 5-minute backup, the shortest batteries are rated for)" : ""}`, R(wh, 0), "Wh"),
    step("Usable share of capacity", `lower of depth of discharge ${g(i.dod)} and ${g(R(rateF, 2))} at a ${g(mins)}-minute rate`, R(usable, 2)),
    step("Battery capacity", `${g(R(wh, 0))} ÷ (${g(v)} V × ${g(i.eff)} × ${g(R(usable, 2))}) × ${g(i.ageing)}`, R(ah, 1), "Ah")];
  const notes = ["Capacity at short backups follows typical 12 V VRLA discharge tables to 1.75 V per cell; confirm with the chosen battery's constant-power table.",
    "Keep the battery room ventilated and at 25 °C for full life."];
  if (strings > 4) notes.unshift(`${strings} strings in parallel is a lot to balance and maintain — a higher-voltage bank, 2 V cells or lithium-ion would be neater.`);
  return { headline: { label: "UPS", value: nUps === 1 ? ups : `${nUps} × ${ups}`, unit: "kVA", sub: `${perString * strings} × 12 V ${block} Ah batteries` }, status: strings > 4 || nUps > 1 ? "warn" : "ok",
    verdict: `${upsTxt} UPS with ${strings} string${strings > 1 ? "s" : ""} of ${perString} × 12 V ${block} Ah batteries (${g(v)} V bank)${nUps > 1 ? " in total, shared or split between the units." : "."}`,
    items: [item("Size needed", R(kva, 2), "kVA", "2dp"), item("UPS rating", upsTxt), item("Battery capacity needed", R(ah, 1), "Ah", "1dp"), item("Battery block", `12 V ${block} Ah`),
      item("Batteries per string", perString, null, "int"), item("Strings in parallel", strings, null, "int"), item("Total batteries", perString * strings, null, "int")],
    steps, notes };
}

// ------------------------------------------------------------------ 10
function tSolarRooftop(i: Any, C: Any) {
  const s = C.solar; const y = s.yield_kwh_per_kwp_day[i.town];
  const need = i.monthly_units * 12;
  const kNeed = y ? need / (y * 365) : 0; const kRoof = i.roof_area / s.area_per_kwp_sqm; const kCap = i.sanctioned_kw;
  const limits: [string, number][] = [["consumption", kNeed], ["roof area", kRoof], ["sanctioned load", kCap]];
  let [limName, kwp] = limits[0];
  for (const l of limits.slice(1)) if (l[1] < kwp) { [limName, kwp] = l; }
  kwp = kwp < 10 ? Math.floor(kwp * 10) / 10 : Math.floor(kwp);
  const gen = kwp * y * 365;
  let saving; let rateUsed;
  if (i.metering === "gross") { saving = gen * i.export_rate; rateUsed = i.export_rate; } else { saving = Math.min(gen, need) * i.tariff + Math.max(gen - need, 0) * 0; rateUsed = i.tariff; }
  const cost = kwp * i.cost_per_kwp;
  const payback = saving > 0 ? cost / saving : null;
  let life = 0;
  for (let yr = 0; yr < Math.trunc(s.life_years); yr += 1) {
    const gy = gen * (1 - s.degradation_pct / 100) ** yr;
    if (i.metering === "gross") life += gy * rateUsed; else life += Math.min(gy, need) * rateUsed * (1 + s.tariff_escalation_pct / 100) ** yr;
  }
  const co2 = (gen * C.co2_kg_per_kwh) / 1000;
  const steps = [step("Size for your consumption", `${ind(need)} kWh ÷ (${g(y)} × 365)`, R(kNeed, 1), "kWp"),
    step("Size your roof allows", `${g(i.roof_area)} m² ÷ ${s.area_per_kwp_sqm} m²/kWp`, R(kRoof, 1), "kWp"),
    step("Allowed by sanctioned load", "≤ sanctioned load", R(kCap, 1), "kWp"), step("Yearly generation", `${g(kwp)} kWp × ${g(y)} × 365`, R(gen, 0), "kWh")];
  return { headline: { label: "Solar plant", value: kwp, unit: "kWp", sub: `limited by ${limName}` }, status: "ok",
    verdict: payback ? `A ${g(kwp)} kWp plant makes about ${g(R(gen / 1000, 1))} MWh a year, saving ₹${g(R(saving / 100000, 2))} lakh a year with a ${g(R(payback, 1))}-year payback.` : "No savings at these inputs.",
    items: [item("Plant size", kwp, "kWp", "1dp", "accent"), item("Yearly generation", R(gen, 0), "kWh", "int"),
      item("Share of your consumption", R(need ? Math.min((gen / need) * 100, 100) : 0, 0), "%", "int"), item("Yearly saving", R(saving, 0), "₹", "inr"),
      item("Investment", R(cost, 0), "₹", "inr"), item("Payback", payback ? R(payback, 1) : "—", "years", "1dp"), item("25-year savings", R(life, 0), "₹", "inr"),
      item("CO₂ avoided", R(co2, 1), "tonnes/year", "1dp"), item("Roof area used", R(kwp * s.area_per_kwp_sqm, 0), "m²", "int"),
      item("Size for your consumption", R(kNeed, 1), "kWp", "1dp"), item("Size your roof allows", R(kRoof, 1), "kWp", "1dp"), item("Allowed by sanctioned load", R(kCap, 1), "kWp", "1dp")],
    steps, notes: [`Yield for ${i.town}: ${g(y)} kWh/kWp/day (typical). Tamil Nadu metering rules and charges change — verify the current order.`,
      `CO₂ at ${C.co2_kg_per_kwh} kg/kWh (${C.co2_basis}).`, "Delivered with Sensoper Controls and Renewables, our group's solar company."] };
}

// ------------------------------------------------------------------ 11
function tEvChargerLoad(i: Any, C: Any) {
  let tot = 0; const rows: Any[] = [];
  for (const ch of i.chargers) {
    const kw = C.ev_chargers_kw[ch.type];
    rows.push([ch.type.replaceAll("_", " ").toUpperCase().replaceAll(" 3 3", " 3.3").replaceAll(" 7 4", " 7.4"), R(ch.qty, 0), kw, R(kw * ch.qty, 1)]);
    tot += kw * ch.qty;
  }
  const addedKw = tot * i.diversity; const addedKva = addedKw / 0.95;
  const spare = i.sanctioned_kva - i.existing_md; const newMd = i.existing_md + addedKva;
  const upgrade = addedKva > spare; const sugg = Math.trunc(Math.ceil((newMd * 1.1) / 5) * 5);
  return { headline: { label: "Added demand", value: R(addedKva, 1), unit: "kVA", sub: upgrade ? "upgrade needed" : "fits your connection" }, status: upgrade ? "warn" : "ok",
    verdict: upgrade ? `Your chargers add about ${g(R(addedKva, 0))} kVA but only ${g(R(spare, 0))} kVA is spare — apply to raise the load to about ${sugg} kVA.` : `The chargers fit within your present connection (${g(R(spare, 0))} kVA spare).`,
    items: [item("Charger capacity installed", R(tot, 1), "kW", "1dp"), item("Added demand with diversity", R(addedKw, 1), "kW", "1dp"), item("Added demand", R(addedKva, 1), "kVA", "1dp"),
      item("Spare on present connection", R(spare, 1), "kVA", "1dp"), item("New maximum demand", R(newMd, 1), "kVA", "1dp"), item("Suggested new sanction", upgrade ? sugg : "No change", upgrade ? "kVA" : null)],
    table: { title: "Chargers", columns: ["Charger", "Qty", "kW each", "kW total"], rows },
    steps: [step("Added demand", `${g(R(tot, 1))} kW × diversity ${g(i.diversity)} ÷ PF 0.95`, R(addedKva, 1), "kVA")],
    notes: [...(upgrade && sugg * 0.95 > C.lt_max_kw ? [`About ${sugg} kVA is above the ${C.lt_max_kw} kW LT limit, so on an LT service this needs an HT connection (or a separate EV service).`] : []),
      "Public charging stations can take a separate EV tariff connection (HT V / LT EV) — ask us about separate metering.", "A load management (smart charging) controller can cap the demand without an upgrade."] };
}

// ------------------------------------------------------------------ 12
function tCableSize(i: Any, C: Any) {
  const v = parseFloat(i.voltage); const p = i.load_kw * 1000;
  const current = v !== 230 ? p / (SQ3 * v * i.pf) : p / (v * i.pf);
  const sel = selectCable(C, current, v, i.pf, i.length, i.conductor, i.laying, i.ambient, i.group, i.spacing, i.soil, i.depth, i.vd_limit, i.fault_ka, i.clear_s);
  const d = sel.derating; const ch = sel.chosen;
  const rows = sel.rows.map((r: Any) => [`${r.size} mm²${r.runs > 1 ? ` × ${r.runs}` : ""}`, R(r.rated, 0), R(r.vd_pct, 2), R(r.s_min, 1),
    r.ok ? "OK" : !r.ok_i ? "Current" : !r.ok_v ? "Voltage drop" : "Short circuit"]);
  const steps = [step("Design current", v !== 230 ? "P ÷ (√3 × V × PF)" : "P ÷ (V × PF)", R(current, 1), "A"),
    step("Temperature factor", `√((90 − ${g(i.ambient)}) ÷ (90 − ${g(d.base)})), rated at ${g(d.base)} °C ${i.laying === "ground" ? "in ground" : "in air"}`, R(d.temp, 3)), step("Grouping factor", `${Math.trunc(i.group)} cable(s)`, R(d.group, 2)),
    step("Depth × soil factors", "", R(d.depth * d.soil, 3)), step("Total derating", "product of the factors", R(d.total, 3))];
  const table = { title: "Sizes checked", columns: ["Size", "Derated A", "VD %", "Min mm² (SC)", "Result"], rows };
  if (!ch) return { headline: { label: "Cable", value: "Not found" }, status: "bad", verdict: "No standard size meets all three checks — shorten the route, raise the voltage or split the load.",
    items: [item("Design current", R(current, 1), "A", "1dp")], table, steps, notes: [] };
  const condL = sel.cond === "al" ? "aluminium" : "copper";
  const cores = v >= 1000 ? "3 core" : v !== 230 ? "3.5 core" : "2 core";
  const desc = `${fmtSize(ch.size, ch.runs)} ${condL} XLPE armoured, ${cores}`;
  steps.push(step("Voltage drop", "k × I × L × (R cos φ + X sin φ) ÷ runs", R(ch.vd_pct, 2), "%"), step("Short-circuit minimum", `I × √t ÷ k (${sel.k_sc})`, R(ch.s_min, 1), "mm²"));
  const bc = sel.by_current;
  const scSets = !!bc && (bc.runs !== ch.runs || parseFloat(bc.size) !== parseFloat(ch.size)) && ch.s_min > parseFloat(bc.size) - 1e-9;
  const notes = ["Ratings are typical catalogue values; confirm with the chosen maker's table.", "Glands, lugs and termination size follow the cable chosen."];
  if (v >= 1000 && i.conductor === "cu") notes.unshift("HT cables are sized here in aluminium, which is what is normally laid; ask us if you need a copper HT cable.");
  if (v > 11000) notes.unshift(`${g(v / 1000)} kV cables use the 11 kV current ratings here (within a few per cent); confirm with the maker's table.`);
  return { headline: { label: "Cable", value: fmtSize(ch.size, ch.runs), sub: `${condL} XLPE armoured` }, status: "ok",
    verdict: `Use ${desc}. It carries ${g(R(ch.rated, 0))} A after derating against ${g(R(current, 0))} A needed, with ${g(R(ch.vd_pct, 2))}% voltage drop.`
      + (scSets ? ` The short-circuit check (${g(i.fault_ka)} kA for ${g(i.clear_s)} s) sets this size; for current and voltage drop alone ${fmtSize(bc.size, bc.runs)} would do`
        + (i.clear_s >= 0.1 ? " — a faster-clearing breaker allows the smaller cable." : " — below 0.1 s, check against the breaker's let-through energy (I²t) instead.") : ""),
    items: [item("Design current", R(current, 1), "A", "1dp"), item("Derating factor", R(d.total, 3), null, "3dp"), item("Cable", desc, null, null, "accent"),
      item("Derated rating", R(ch.rated, 0), "A", "int"), item("Voltage drop", R(ch.vd_pct, 2), "%", "2dp", ch.vd_pct <= i.vd_limit ? "good" : "bad"), item("Voltage-drop limit", i.vd_limit, "%"),
      item("Minimum size for fault", R(ch.s_min, 1), "mm²", "1dp")],
    table, steps, notes };
}

// ------------------------------------------------------------------ 13
function tVoltageDrop(i: Any, C: Any) {
  const phase3 = i.phase === "3"; const v = phase3 ? 415.0 : 230.0;
  const r = cableR90(C, i.conductor, i.size); const x = C.cable.x_ohm_km.lt;
  const vd = vdrop(i.current, i.length, r, x, i.pf, phase3, i.runs); const p = (vd / v) * 100;
  const limit = C.cable.vd_limit_pct[i.purpose];
  const perM = vdrop(i.current, 1, r, x, i.pf, phase3, i.runs);
  const maxLen = perM ? ((limit / 100) * v) / perM : 0;
  const sin = Math.sqrt(1 - i.pf ** 2); const ok = p <= limit + 1e-9;
  return { headline: { label: "Voltage drop", value: R(p, 2), unit: "%", sub: `${g(R(vd, 2))} V` }, status: ok ? "ok" : "bad",
    verdict: `${ok ? `Within the ${limit}% limit.` : `Above the ${limit}% limit — use a bigger cable or more runs.`} Longest run at this current: ${g(R(maxLen, 0))} m.`,
    items: [item("Voltage drop", R(vd, 2), "V", "2dp"), item("Voltage drop", R(p, 2), "%", "2dp", ok ? "good" : "bad"), item("Limit", limit, "%"),
      item("Resistance at 90 °C", R(r, 4), "Ω/km", "4dp"), item("Reactance", x, "Ω/km"), item("Longest length within limit", R(maxLen, 0), "m", "int")],
    steps: [step("Resistance at 90 °C", "R20 × (1 + α × 70)", R(r, 4), "Ω/km"),
      step("Voltage drop", `${phase3 ? "√3" : "2"} × ${g(i.current)} A × ${g(i.length / 1000)} km × (${g(R(r, 4))} × ${g(i.pf)} + ${g(x)} × ${g(R(sin, 3))}) ÷ ${Math.trunc(i.runs)}`, R(vd, 2), "V"),
      step("As a percentage", `${g(R(vd, 2))} ÷ ${g(v)} V`, R(p, 2), "%")],
    notes: ["Limits used: 3% lighting, 5% power, measured from the supply point (typical practice under IS 732)."] };
}

// ------------------------------------------------------------------ 14
function tFaultLevel(i: Any, C: Any) {
  const v = i.lv; const c = 1.05;
  const zSrc = (v * v) / (i.source_mva * 1e6); const xSrc = zSrc / Math.sqrt(1 + 0.1 ** 2); const rSrc = 0.1 * xSrc;
  const zTx = ((i.z_pct / 100) * v * v) / (i.kva * 1000); const rTx = zTx / Math.sqrt(1 + i.xr ** 2); const xTx = rTx * i.xr;
  const tab = C.cable[i.conductor === "al" ? "r20_al" : "r20_cu"];
  if (!(String(i.cable_size) in tab)) throw new CalcError(`${i.cable_size} mm² is not available in ${i.conductor === "al" ? "aluminium" : "copper"}`);
  const rC = (tab[String(i.cable_size)] * i.cable_m) / 1000 / i.runs; const xC = (C.cable.x_ohm_km.lt * i.cable_m) / 1000 / i.runs;
  const r1 = rSrc + rTx; const x1 = xSrc + xTx; const r2 = r1 + rC; const x2 = x1 + xC;
  const ik1 = (c * v) / (SQ3 * Math.hypot(r1, x1)) / 1000; const ik2 = (c * v) / (SQ3 * Math.hypot(r2, x2)) / 1000;
  const kappa = 1.02 + 0.98 * Math.exp((-3 * r2) / x2); const ip = kappa * Math.sqrt(2) * ik2;
  const bc = nextStd(ik2, Array.from(new Set([...C.breakers.mccb_ka, ...C.breakers.acb_ka])).sort((a: Any, b: Any) => a - b) as number[]);
  const flc = (i.kva * 1000) / (SQ3 * v);
  return { headline: { label: "Fault level at the panel", value: R(ik2, 1), unit: "kA" }, status: bc ? "ok" : "warn",
    verdict: `About ${g(R(ik1, 1))} kA at the transformer terminals and ${g(R(ik2, 1))} kA at the panel. `
      + (bc ? `Breakers there need at least ${bc} kA breaking capacity.` : "That is above standard breakers — use current-limiting breakers or fuses, or split the bus across transformers."),
    items: [item("At transformer LV terminals", R(ik1, 2), "kA", "2dp"), item("At the panel", R(ik2, 2), "kA", "2dp", "accent"), item("Peak (making) current", R(ip, 1), "kA", "1dp"),
      item("Breaking capacity needed", bc ? bc : "Above 100 kA", bc ? "kA" : null), item("Transformer full-load current", R(flc, 0), "A", "int")],
    steps: [step("Source impedance at LV", `${g(v)}² ÷ ${g(i.source_mva)} MVA`, R(zSrc * 1000, 3), "mΩ"),
      step("Transformer impedance", `${g(i.z_pct)}% × ${g(v)}² ÷ ${g(i.kva)} kVA`, R(zTx * 1000, 3), "mΩ"),
      step("Cable impedance", `${g(i.cable_m)} m of ${Math.trunc(i.runs)} × ${i.cable_size} mm²`, R(Math.hypot(rC, xC) * 1000, 3), "mΩ"),
      step("Fault current", "c × V ÷ (√3 × |Z|), c = 1.05", R(ik2, 2), "kA"), step("Peak factor κ", "1.02 + 0.98 e^(−3R/X)", R(kappa, 3))],
    notes: ["Motor contribution is not included; add it for large motor loads.", "Simplified IEC 60909 method; a full study uses actual network data."] };
}

// ------------------------------------------------------------------ 15
const FUSES = [2, 4, 6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250];
const MCCB_RELEASES = [16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250]; // thermal-magnetic In
function tBreakerSelector(i: Any, C: Any) {
  const v = parseFloat(i.voltage); const phase3 = v !== 230;
  let ib;
  if (i.input === "kw") ib = (i.value * 1000) / ((phase3 ? SQ3 : 1) * v * i.pf);
  else if (i.input === "kva") ib = (i.value * 1000) / ((phase3 ? SQ3 : 1) * v);
  else ib = i.value;
  const factor = ({ lighting: 1.0, mixed: 1.25, motor: 1.25, capacitor: 1.43, transformer: 1.0 } as Any)[i.load_type];
  const need = ib * factor; const b = C.breakers;
  const sq = phase3 ? "√3 × " : "";
  const steps = [step("Load current", i.input === "kw" ? `P ÷ (${sq}V × PF)` : i.input === "kva" ? `S ÷ (${sq}V)`.replace("(V)", "V") : "given", R(ib, 1), "A"),
    step("Rating needed", `× ${g(factor)} (${i.load_type})`, R(need, 1), "A")];
  const notes: string[] = [];
  let rating: Any; let bc: Any; let kind; let detail;
  const last = (a: Any[]) => a[a.length - 1];
  const poles = !phase3 ? 2 : i.load_type === "motor" || i.load_type === "capacitor" ? 3 : 4;
  if (v >= 1000) {
    rating = nextStd(Math.max(need, 1), b.vcb_a); bc = nextStd(i.fault_ka, b.vcb_ka);
    kind = "VCB (vacuum circuit breaker)";
    const rTxt = rating ? `${rating} A` : `above ${last(b.vcb_a)} A — split the load or use a special breaker`;
    const bcTxt = bc ? `${bc} kA` : `above ${last(b.vcb_ka)} kA — check the fault level with TNPDCL`;
    detail = `${rTxt}, ${bcTxt}, with numerical relay (50/51, 50N/51N)`;
    notes.push("Set relay pick-up and time for grading with the upstream TNPDCL breaker.");
  } else {
    if (need <= last(b.mcb) && i.fault_ka <= last(b.mcb_ka) && i.load_type !== "transformer") {
      rating = nextStd(need, b.mcb); bc = nextStd(i.fault_ka, b.mcb_ka);
      const curve = ({ lighting: "B", mixed: "C", motor: "D", capacitor: "C" } as Any)[i.load_type];
      kind = `MCB, curve ${curve}`; detail = `${rating} A ${poles}-pole, ${bc} kA`;
    } else if (need <= last(b.mccb) && !(i.load_type === "transformer" && need > 630)) {
      const frame = nextStd(need, b.mccb); const rel = nextStd(need, MCCB_RELEASES);
      rating = rel && rel < frame ? rel : frame; bc = nextStd(i.fault_ka, b.mccb_ka);
      kind = `MCCB${i.load_type === "motor" ? " with motor-protection release" : ""}`;
      const bcTxt = bc ? `${bc} kA (Icu)` : `above ${last(b.mccb_ka)} kA — use current-limiting breakers or cascading`;
      const art = String(rating).startsWith("8") || rating === 11 || rating === 18 ? "an" : "a";
      detail = `${rating < frame ? `${frame} A frame with ${art} ${rating} A release` : `${frame} A`}, ${poles}-pole, ${bcTxt}`;
    } else {
      rating = nextStd(need, b.acb); bc = nextStd(i.fault_ka, b.acb_ka);
      kind = "ACB (draw-out)";
      const rTxt = rating ? `${rating} A` : `above ${last(b.acb)} A — split the feeder`;
      const bcTxt = bc ? `${bc} kA` : `above ${last(b.acb_ka)} kA — use current-limiting or cascading`;
      detail = `${rTxt}, ${bcTxt}, with microprocessor release (LSIG)`;
    }
    if (i.load_type === "motor") notes.push("For motors, coordinate with the contactor and overload relay (Type 2 coordination).");
    if (i.load_type === "capacitor") notes.push("Capacitor feeders are rated 1.43× the capacitor current for harmonics and tolerance.");
  }
  const fuse = v < 1000 ? nextStd(need, FUSES) : null;
  const items = [item("Load current", R(ib, 1), "A", "1dp"), item("Rating needed", R(need, 1), "A", "1dp"), item("Breaker", kind, null, null, "accent"), item("Selection", detail)];
  if (fuse) items.push(item("Equivalent HRC fuse", fuse, "A"));
  return { headline: { label: kind, value: rating ? `${rating} A` : "Above standard", sub: bc ? `${bc} kA` : "above standard kA" }, status: rating && bc ? "ok" : "warn",
    verdict: `Use ${kind}: ${detail}.`, items, steps, notes: [...notes, "Check that the cable's derated rating is at least the breaker setting (Iz ≥ In)."] };
}

// ------------------------------------------------------------------ 16
function tMotor(i: Any, C: Any) {
  const kw = i.unit === "hp" ? i.rating * 0.746 : i.rating;
  const [eT, pT] = motorEffPf(C, kw);
  const eff = i.eff || eT; const pf = i.pf || pT; const v = i.voltage;
  const flc = (kw * 1000) / (SQ3 * v * eff * pf);
  let starter;
  if (i.duty === "variable") starter = "vfd"; else if (i.duty === "conveyor") starter = kw <= 7.5 ? "dol" : "vfd"; // a soft starter cuts torque with current; heavy loads need a VFD
  else if (kw <= 7.5) starter = "dol"; else if (kw <= 75) starter = "star_delta"; else starter = "soft_starter";
  const names: Any = { dol: "Direct on line (DOL)", star_delta: "Star-delta", soft_starter: "Soft starter", vfd: "Variable frequency drive (VFD)" };
  const use: Any = { dol: "a direct-on-line (DOL) starter", star_delta: "a star-delta starter", soft_starter: "a soft starter", vfd: "a VFD" };
  const mult = C.motor_start_multiple[starter]; const iStart = flc * mult; const design = flc * 1.25;
  const ht = v >= 1000;
  let brkTxt; let cableI;
  if (ht) { brkTxt = "VCB with motor protection relay"; cableI = design; } else {
    let brk; let brkKind;
    if (design <= C.breakers.mcb[C.breakers.mcb.length - 1]) { brk = nextStd(design, C.breakers.mcb); brkKind = "MCB"; }
    else if (design <= MCCB_RELEASES[MCCB_RELEASES.length - 1]) { brk = nextStd(design, MCCB_RELEASES); brkKind = "MCCB"; }
    else { brk = nextStd(design, C.breakers.acb); brkKind = "ACB"; }
    brkTxt = brk ? `${brk} A ${brkKind}` : "Above standard ratings — split the drive";
    cableI = Math.max(design, brk || design); // the cable must carry at least the breaker rating (Iz ≥ In)
  }
  const cond = cableI <= 60 ? "cu" : "al";
  const sel = selectCable(C, cableI, v, pf, i.length, cond, "air", 40, 1, "touching", "150", "75", 5, 0, 0.1);
  const ch = sel.chosen;
  const cab = ch ? `${fmtSize(ch.size, ch.runs)} ${sel.cond === "cu" ? "copper" : "aluminium"} XLPE armoured` : "a cable sized by detailed design (beyond the standard table)";
  return { headline: { label: "Full-load current", value: R(flc, 1), unit: "A", sub: names[starter] }, status: "ok",
    verdict: `A ${g(R(kw, 2))} kW motor draws about ${g(R(flc, 1))} A. Use ${use[starter]} (≈${g(R(iStart, 0))} A while starting) and ${cab}.`,
    items: [item("Rating", R(kw, 2), "kW", "2dp"), item("Efficiency used", eff), item("Power factor used", pf), item("Full-load current", R(flc, 1), "A", "1dp", "accent"),
      item("Starter", names[starter]), item("Starting current", R(iStart, 0), "A", "int"), item("Cable (≥125% of FLC and the breaker rating)", cab), item("Motor protection breaker", brkTxt)],
    steps: [step("Full-load current", `${g(R(kw * 1000, 0))} W ÷ (√3 × ${g(v)} × ${g(eff)} × ${g(pf)})`, R(flc, 2), "A"),
      step("Starting current", `× ${g(mult)} for ${names[starter].toLowerCase()}`, R(iStart, 0), "A")],
    notes: ["IE3 4-pole minimum efficiency (IEC 60034-30-1) and typical PF are used when you leave them blank; use the nameplate if you have it.",
      ...(i.duty === "conveyor" && kw > 7.5 ? ["Heavy-start loads (conveyors, crushers) need a VFD or DOL starting; a soft starter lowers the starting torque along with the current."] : [])] };
}

// ------------------------------------------------------------------ 17
function tPfCorrection(i: Any, C: Any) {
  if (i.pf_target <= i.pf_now) throw new CalcError("Target power factor must be higher than the present one");
  const t1 = Math.tan(Math.acos(i.pf_now)); const t2 = Math.tan(Math.acos(i.pf_target));
  const kvar = i.kw * (t1 - t2);
  const caps = C.capacitor_steps_kvar; const big = caps[caps.length - 1];
  const panels = Math.max(1, Math.ceil(Math.ceil(kvar / 25) * 25 / (2 * big + 10 * 2 * big))); // two small + ten double steps of the largest unit
  const panel = Math.ceil(Math.ceil(kvar / 25) * 25 / panels / 25) * 25;
  const s = nextStd(panel / 10, caps) || big;
  // two small steps, then double steps, then whatever is left, so the steps add up to the panel (counted, not looped)
  const k = Math.max(0, Math.floor((panel - 2 * s) / (2 * s)));
  const rest = panel - 2 * s - 2 * s * k;
  const steps_: number[] = [s, s, ...Array(k).fill(2 * s), ...(rest > 1e-9 ? [rest] : [])];
  const bank = panel * panels;
  const detuned = i.nonlinear > 15;
  const kva1 = i.kw / i.pf_now; const kva2 = i.kw / i.pf_target;
  const penPct = i.ht ? pfPenaltyPct(i.pf_now, C) : ltPfPenaltyPct(i.pf_now, C); const pen = (i.energy_bill * penPct) / 100;
  const demandSave = i.ht ? (kva1 - kva2) * C.tariffs.HT_I.demand : 0;
  const monthly = pen + demandSave; const cost = bank * (detuned ? 2000 : 1200);
  const paybackM = monthly > 0 ? cost / monthly : null;
  return { headline: { label: "Capacitors needed", value: R(kvar, 1), unit: "kVAR", sub: panels === 1 ? `APFC panel ${panel} kVAR` : `${panels} APFC panels of ${panel} kVAR` }, status: "ok",
    verdict: `Add about ${g(R(kvar, 0))} kVAR (${panels === 1 ? "an APFC panel" : `${panels} APFC panels`} of ${panel} kVAR)${monthly > 0 ? `; it saves about ₹${ind(R(monthly, 0))} a month.` : "."}`,
    items: [item("kVAR needed", R(kvar, 1), "kVAR", "1dp"), item("APFC panel", panels === 1 ? panel : `${panels} × ${panel}`, "kVAR", null, "accent"),
      item(`Steps${panels > 1 ? " (each panel)" : ""}`, `${steps_.map((x) => g(x)).join(" + ")} = ${g(panel)} kVAR`),
      item("Reactors", detuned ? `7% detuned reactors (${g(i.nonlinear)}% non-linear load)` : `Not needed (${g(i.nonlinear)}% non-linear load)`, null, null, detuned ? "warn" : null),
      item("Demand before → after", `${g(R(kva1, 0))} → ${g(R(kva2, 0))} kVA`), item("PF penalty avoided", R(pen, 0), "₹/month", "inr"),
      item("Demand charge saved", R(demandSave, 0), "₹/month", "inr"), item("Indicative panel cost", R(cost, 0), "₹", "inr"), item("Payback", paybackM ? R(paybackM, 1) : "—", "months", "1dp")],
    steps: [step("kVAR", `${g(i.kw)} × (tan(acos ${g(i.pf_now)}) − tan(acos ${g(i.pf_target)})) = ${g(i.kw)} × (${g(R(t1, 4))} − ${g(R(t2, 4))})`, R(kvar, 2), "kVAR"),
      step("PF penalty now", `${g(penPct)}% of energy charges`, R(pen, 0), "₹/month")],
    notes: [...(detuned ? ["With more than 15% VFD / UPS / LED load, plain capacitors can resonate — use detuned reactors."] : []), "Panel cost is indicative; we quote after a power-quality measurement.",
      i.ht ? `The PF penalty follows ${C.tariff_order}: the band's rate for every 0.01 below ${g(C.pf_threshold)}. The demand saving assumes this load sets your maximum demand and that it is above ${C.billing_demand_floor_pct}% of the contract demand.`
        : `LT IIIB and LT V three-phase services pay a PF penalty below ${g(C.lt_pf_threshold ?? 0.85)} (${C.tariff_order}); there is no demand charge to save on LT.`] };
}

// ------------------------------------------------------------------ 18
function tHarmonics(i: Any, C: Any) {
  const iscKva = i.kva / (i.z_pct / 100); const ratio = iscKva / i.load_kva;
  const tdd = C.harmonics_tdd_limits.find(([lim]: number[]) => ratio < lim)[1];
  const nl = i.nonlinear; const estThd = nl * 0.4;
  let risk; let status;
  if (nl < 15) { risk = "Low"; status = "ok"; } else if (nl <= 30) { risk = "Medium"; status = "warn"; } else { risk = "High"; status = "bad"; }
  const recs: string[] = [];
  if (nl >= 15) { recs.push("Measure with a power-quality analyser for 7 days (we can do this)."); recs.push("Use 7% detuned reactors in the APFC panel."); }
  if (nl > 30) { recs.push("Consider an active harmonic filter at the main LT panel, and DC chokes / line reactors on large VFDs."); recs.push("Check neutral sizing and transformer heating (consider K-rated transformers for new projects)."); }
  if (i.capacitors && nl >= 15) { recs.push("Plain capacitors with this much non-linear load risk resonance — replace or add reactors."); status = "bad"; }
  if (R(estThd, 1) > tdd) {
    if (risk === "Low") { risk = "Medium"; status = "warn"; }
    recs.unshift(`The indicative distortion (${g(R(estThd, 1))}%) is above the ${tdd}% limit for this short-circuit ratio — measure it, and plan filtering if confirmed.`);
  }
  if (!recs.length) recs.push("No action needed now; recheck when adding drives, UPS or EV chargers.");
  return { headline: { label: "Harmonic risk", value: risk, sub: `${g(nl)}% non-linear load` }, status,
    verdict: `${risk} risk. Your current distortion limit (TDD) at this short-circuit ratio is ${tdd}% per IEEE 519.`,
    items: [item("Short-circuit ratio Isc/IL", R(ratio, 1), null, "1dp"), item("Current TDD limit", tdd, "%"), item("Voltage THD limit (below 1 kV)", 8, "%"),
      item("Indicative current THD", R(estThd, 1), "%", "1dp", R(estThd, 1) > tdd ? "warn" : null)],
    table: { title: "What to do", columns: ["Recommendation"], rows: recs.map((r) => [r]) },
    steps: [step("Short-circuit kVA", `${g(i.kva)} ÷ ${g(i.z_pct)}%`, R(iscKva, 0), "kVA"), step("Ratio", `${g(R(iscKva, 0))} ÷ ${g(i.load_kva)}`, R(ratio, 1))],
    notes: ["Indicative only — six-pulse drives produce about 30–45% current THD on their own current."] };
}

// ------------------------------------------------------------------ 19
function tEnergySavings(i: Any, C: Any) {
  const h = i.hours; let old; let nw; let steps; let name;
  if (i.measure === "led") {
    old = (i.fixtures * i.old_w * h) / 1000; nw = (i.fixtures * i.new_w * h) / 1000;
    steps = [step("Present use", `${g(i.fixtures)} × ${g(i.old_w)} W × ${g(h)} h`, R(old, 0), "kWh/yr"), step("With LED", `${g(i.fixtures)} × ${g(i.new_w)} W × ${g(h)} h`, R(nw, 0), "kWh/yr")];
    name = "LED retrofit";
  } else if (i.measure === "vfd") {
    const f = i.flow / 100;
    const pThr = (i.motor_kw * (0.55 + 0.45 * f)) / 0.92; const pVfd = (i.motor_kw * f ** 3) / 0.97 / 0.92;
    old = pThr * h; nw = pVfd * h;
    steps = [step("With throttle valve / damper", `${g(i.motor_kw)} kW × (0.55 + 0.45 × ${g(f)}) ÷ 0.92`, R(pThr, 2), "kW"), step("With VFD (affinity law)", `${g(i.motor_kw)} kW × ${g(f)}³ ÷ 0.97 ÷ 0.92`, R(pVfd, 2), "kW")];
    name = "VFD";
  } else {
    const out = (i.motor_kw * i.load_pct) / 100;
    old = (out / i.eff_old) * h; nw = (out / i.eff_new) * h;
    steps = [step("Output power", `${g(i.motor_kw)} kW × ${g(i.load_pct)}%`, R(out, 2), "kW"), step("Input saved", `${g(R(out, 2))} × (1/${g(i.eff_old)} − 1/${g(i.eff_new)})`, R(out / i.eff_old - out / i.eff_new, 3), "kW")];
    name = "Efficient motor";
  }
  const save = old - nw; const rupees = save * i.tariff;
  const mid = ({ "LED retrofit": "LED retrofit", VFD: "VFD", "Efficient motor": "efficient motor" } as Any)[name]; const payback = rupees > 0 ? i.cost / rupees : null; const co2 = (save * C.co2_kg_per_kwh) / 1000;
  let verdict;
  if (save > 0.5) verdict = `${name} saves about ${ind(R(save, 0))} kWh (₹${ind(R(rupees, 0))}) a year${payback ? ` and pays back in ${g(R(payback, 1))} years.` : "."}`;
  else if (save < -0.5) verdict = `At these inputs the ${mid} uses about ${ind(R(-save, 0))} kWh (₹${ind(R(-rupees, 0))}) a year more, so it doesn't pay.`
    + (i.measure === "vfd" ? " At full flow a VFD only adds its own losses; it saves when the flow is reduced." : "");
  else verdict = `At these inputs the ${mid} makes no real difference to energy use.`;
  const worse = save < -0.5;
  return { headline: { label: worse ? "Yearly extra cost" : "Yearly saving", value: R(worse ? -rupees : rupees, 0), unit: "₹", fmt: "inr",
    sub: `${ind(R(worse ? -save : save, 0))} kWh ${worse ? "more" : "saved"}` }, status: save > 0.5 ? "ok" : "warn",
    verdict,
    items: [item("Energy before", R(old, 0), "kWh/yr", "int"), item("Energy after", R(nw, 0), "kWh/yr", "int"), item("Saved", R(save, 0), "kWh/yr", "int", save > 0 ? "good" : "bad"),
      item("Saved", R(rupees, 0), "₹/yr", "inr", save > 0 ? "good" : "bad"), item("Payback", payback ? R(payback, 1) : "—", "years", "1dp"), item("CO₂ avoided", R(co2, 2), "tonnes/yr", "2dp")],
    steps, notes: [`CO₂ at ${C.co2_kg_per_kwh} kg/kWh (${C.co2_basis}).`] };
}

// ------------------------------------------------------------------ 20
function tEarthing(i: Any, C: Any, TOOLS: Any) {
  const rho = i.rho; let r1; let f;
  if (i.electrode === "pipe") {
    const L = i.length; const d = i.diameter / 1000;
    r1 = (rho / (2 * Math.PI * L)) * Math.log((4 * L) / d);
    f = `ρ ÷ (2πL) × ln(4L/d) = ${g(rho)} ÷ (2π × ${g(L)}) × ln(4 × ${g(L)} ÷ ${g(d)})`;
  } else if (i.electrode === "plate") {
    const A = 2 * i.plate_w * i.plate_h; r1 = (rho / 4) * Math.sqrt(Math.PI / A); // IS 3043: A is the area of both faces of the plate
    f = `(ρ ÷ 4) × √(π ÷ A), A = both faces = 2 × ${g(i.plate_w)} × ${g(i.plate_h)} = ${g(R(A, 3))} m²`;
  } else {
    const L = i.length; const w = i.strip_w / 1000; const t = i.strip_depth;
    const arg = (2 * L * L) / (w * t);
    const minL = Math.max(4 * t, Math.sqrt(w * t) + 0.1); // the IS 3043 strip formula holds for a strip much longer than its depth
    if (L < minL - 1e-9) throw new CalcError(`${labelOf(TOOLS, "earthing", "length")}: too short for a strip buried ${g(t)} m deep; use at least ${g(R(minL, 1))} m`);
    r1 = (rho / (2 * Math.PI * L)) * Math.log(arg); f = "ρ ÷ (2πL) × ln(2L² ÷ (w × t))";
  }
  // several electrodes in a line, spaced s apart: R = R1 × (1 + λα) ÷ n, α = ρ ÷ (2π R1 s), λ ≈ 2 × (1/2 + … + 1/n)
  const space = i.electrode === "plate" ? Math.max(4.0, 2 * Math.max(i.plate_w, i.plate_h)) : Math.max(2 * i.length, 2.0);
  const alpha = rho / (2 * Math.PI * r1 * space);
  const combined = (m: number) => { let lam = 0; for (let q = 2; q <= m; q += 1) lam += 1 / q; lam *= 2; return (r1 * (1 + lam * alpha)) / m; };
  let n = 1;
  while (combined(n) > i.target && n < 50) n += 1;
  const rn = combined(n); const reached = rn <= i.target + 1e-9;
  const k = C.earthing_k[i.material];
  const s = (i.fault_ka * 1000 * Math.sqrt(i.duration)) / k; const sAllow = i.material === "gi" ? s * 1.25 : s;
  let cond;
  if (i.material === "gi") {
    const strip = C.earth_strips_mm.find(([w, t]: number[]) => w * t >= sAllow);
    cond = strip ? `${strip[0]} × ${strip[1]} mm GI strip` : "Larger than 75 × 10 mm — use multiple strips";
  } else {
    const sz = nextStd(sAllow, [16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300]);
    cond = sz ? `${sz} mm² ${i.material}` : "Above 300 mm² — use multiple conductors";
  }
  return { headline: { label: "Earth pits needed", value: n, sub: `≈ ${g(R(rn, 2))} Ω combined` }, status: reached ? "ok" : "warn",
    verdict: reached ? `${n} pit${n > 1 ? "s" : ""} of this type${n > 1 ? `, ${g(R(space, 1))} m apart in a line,` : ""} give about ${g(R(rn, 2))} Ω.` : `Even 50 pits don't reach ${g(i.target)} Ω in this soil — use soil treatment, longer rods, a ring earth or chemical earthing.`,
    items: [item("One electrode", R(r1, 2), "Ω", "2dp"), item("Pits", n, null, "int", "accent"), item("Combined", R(rn, 2), "Ω", "2dp"), item("Conductor size needed", R(sAllow, 0), "mm²", "int"), item("Earthing conductor", cond)],
    steps: [step("One electrode", f, R(r1, 2), "Ω"), step("Several in parallel", `R1 × (1 + λα) ÷ n, α = ρ ÷ (2π × R1 × ${g(R(space, 1))} m) = ${g(R(alpha, 4))}, n = ${n}`, R(rn, 2), "Ω"),
      step("Conductor", `I × √t ÷ k = ${g(i.fault_ka)} kA × √${g(i.duration)} ÷ ${k}${i.material === "gi" ? " + 25% corrosion allowance" : ""}`, R(sAllow, 0), "mm²")],
    notes: ["Measure soil resistivity on site (Wenner four-pin method) — it can vary 10× across a plot and with the season.", "Typical targets: ≤1 Ω for HT substations, ≤5 Ω for LT equipment earths."] };
}

// ------------------------------------------------------------------ 21
function tLightningRisk(i: Any, C: Any) {
  const { l: L, w: W, h: H } = i; const lc = C.lightning;
  const ac = L * W + 2 * L * H + 2 * W * H + Math.PI * H * H; const p = i.ng * ac * 1e-6;
  const a = lc.a[i.use]; const b = lc.b[i.construction]; const c = lc.c[i.contents]; const d = lc.d[i.isolation]; const e = lc.e[i.terrain];
  const overall = p * a * b * c * d * e;
  const ad = L * W + 2 * 3 * H * (L + W) + Math.PI * (3 * H) ** 2;
  const cds = lc.cd || { surrounded: 0.5, few: 1.0, isolated: 1.0, isolated_hill: 2.0 };
  const cd = i.isolation === "isolated" && i.terrain !== "flat" ? cds.isolated_hill : cds[i.isolation];
  const nd = i.ng * ad * cd * 1e-6;
  const ratio = overall / lc.threshold; const needed = ratio > 1;
  const classes: [number, string][] = lc.classes || [[5, "Class IV"], [10, "Class III"], [20, "Class II"], [50, "Class I"]];
  const lpl = !needed ? "Not needed" : (classes.find(([lim]) => ratio <= lim)?.[1] ?? "Class I with extra measures");
  const effNeeded = needed ? 1 - 1 / ratio : 0;
  return { headline: { label: "Lightning protection", value: needed ? "Needed" : "Not required", sub: needed ? lpl : null }, status: needed ? "warn" : "ok",
    verdict: needed ? `Protection is recommended: the weighted risk (${sci(overall)}) is ${g(R(ratio, 1))}× the acceptable 1 × 10⁻⁵. Start with ${lpl}.` : `The weighted risk (${sci(overall)}) is below 1 × 10⁻⁵ — protection is not required by this method.`,
    items: [item("Collection area", R(ac, 0), "m²", "int"), item("Probable strikes per year", sci(p)), item("Weighted risk", sci(overall), null, null, needed ? "warn" : "good"),
      item("Starting class", lpl), item("IEC 62305 dangerous events (Nd)", sci(nd), "per year")],
    steps: [step("Collection area", "LW + 2LH + 2WH + πH²", R(ac, 0), "m²"), step("Probability", `Ng ${g(i.ng)} × Ac × 10⁻⁶`, sci(p)),
      step("Weighting", `A ${g(a)} × B ${g(b)} × C ${g(c)} × D ${g(d)} × E ${g(e)}`, R(a * b * c * d * e, 4)), step("Overall risk", "probability × weighting", sci(overall)),
      ...(needed ? [step("Protection efficiency needed", `1 − 1 ÷ ${g(R(ratio, 1))}`, R(effNeeded, 3)),
        step("Class", "E ≤ 0.80 IV, ≤ 0.90 III, ≤ 0.95 II, ≤ 0.98 I, above I + extra measures", lpl)] : [])],
    notes: ["Risk per IS 2309; class from the protection efficiency needed (IEC 62305). A full IS/IEC 62305-2 risk assessment fixes the final class, surge protection and earthing.",
      ...(needed && ratio > classes[classes.length - 1][0] ? ["Class I with extra measures means Class I plus surge protection and, where needed, mesh and down-conductor spacing tighter than Class I."] : [])] };
}

// ------------------------------------------------------------------ 22
function tLightingLux(i: Any, C: Any) {
  const E = i.lux || C.lux_targets[i.space]; const A = i.length * i.width;
  const k = A / (i.height * (i.length + i.width)); const uf = interp(C.uf_table, k);
  const need = Math.ceil((E * A) / (i.lumens * uf * i.mf) - 1e-9);
  // the smallest grid of at least `need` fixtures; prefer spacings within 2:1 of each other, then the squarest
  let best: Any = null;
  for (let r = 1; r <= Math.min(need, 2000); r += 1) {
    const c = Math.ceil(need / r);
    const sx = i.length / c; const sy = i.width / r;
    const ratio = Math.max(sx / sy, sy / sx);
    const key = [ratio <= 2 + 1e-9 ? 0 : 1, r * c, ratio];
    if (best === null || key[0] < best.key[0] || (key[0] === best.key[0] && (key[1] < best.key[1] || (key[1] === best.key[1] && key[2] < best.key[2])))) best = { key, r, c };
  }
  const rows = best.r; const cols = best.c;
  const n = rows * cols; // fill the grid so the spacing is even
  const achieved = (n * i.lumens * uf * i.mf) / A; const lpd = (n * i.watts) / A;
  return { headline: { label: "Fixtures", value: n, sub: `${g(R(achieved, 0))} lux achieved` }, status: "ok",
    verdict: `${n} fixtures in ${rows} row${rows > 1 ? "s" : ""} × ${cols} give ${g(R(achieved, 0))} lux at ${g(R(lpd, 1))} W/m²` + (n > need ? ` (${need} are needed; ${n} fill the grid evenly).` : "."),
    items: [item("Target", E, "lux"), item("Room index", R(k, 2), null, "2dp"), item("Utilisation factor", R(uf, 2), null, "2dp"),
      item("Fixtures needed", need, null, "int"), item("Fixtures in the layout", n, null, "int", "accent"),
      item("Layout", `${rows} row${rows > 1 ? "s" : ""} × ${cols}`), item("Achieved", R(achieved, 0), "lux", "int"), item("Lighting power density", R(lpd, 2), "W/m²", "2dp"),
      item("Spacing", `≈ ${g(R(i.length / cols, 1))} m × ${g(R(i.width / rows, 1))} m`)],
    steps: [step("Room index", `L × W ÷ (Hm × (L + W)) = ${g(i.length)} × ${g(i.width)} ÷ (${g(i.height)} × ${g(i.length + i.width)})`, R(k, 2)),
      step("Fixtures", `E × A ÷ (lumens × UF × MF) = ${g(E)} × ${g(R(A, 1))} ÷ (${g(i.lumens)} × ${g(R(uf, 2))} × ${g(i.mf)})`, need),
      step("Layout", `${rows} row${rows > 1 ? "s" : ""} × ${cols} in ${g(i.length)} × ${g(i.width)} m`, n)],
    ...(() => { const sp = Math.max(i.length / cols, i.width / rows); const wide = sp > 1.5 * i.height + 1e-9;
      return { status: wide ? "warn" : "ok", notes: [...(wide ? [`The spacing (${g(R(sp, 1))} m) is more than 1.5 × the mounting height (${g(i.height)} m), so the light won't be even — use more fixtures in that direction, or wider-beam fittings.`] : []),
        "Utilisation factor for typical reflectances (ceiling 70%, walls 50%, floor 20%); use the fixture's photometric data for final design."] }; })() };
}

// ------------------------------------------------------------------ 23
function tUnits(i: Any, C: Any) {
  void C;
  const { voltage: v, pf, eff } = i; const k = i.phase === "3" ? SQ3 : 1.0; const x = i.value;
  let kw;
  if (i.from === "kw") kw = x; else if (i.from === "kva") kw = x * pf; else if (i.from === "hp") kw = (x * 0.746) / eff; else kw = (k * v * x * pf) / 1000;
  const kva = kw / pf; const amps = (kva * 1000) / (k * v); const hp = (kw * eff) / 0.746; const kvar = Math.sqrt(Math.max(kva * kva - kw * kw, 0));
  return { headline: { label: "Current", value: R(amps, 2), unit: "A" }, status: "ok",
    verdict: `${g(R(kw, 3))} kW = ${g(R(kva, 3))} kVA = ${g(R(hp, 2))} HP = ${g(R(amps, 2))} A at ${g(v)} V, PF ${g(pf)}.`,
    items: [item("Active power", R(kw, 3), "kW", "3dp"), item("Apparent power", R(kva, 3), "kVA", "3dp"), item("Reactive power", R(kvar, 3), "kVAR", "3dp"),
      item("Horsepower (output)", R(hp, 2), "HP", "2dp"), item("Current", R(amps, 2), "A", "2dp", "accent")],
    steps: [step(i.phase === "3" ? "Three phase" : "Single phase", i.phase === "3" ? "P = √3 × V × I × cos φ" : "P = V × I × cos φ", ""), step("Ohm's law", "V = I × R; P = V × I = I² × R", "")],
    notes: ["1 HP = 0.746 kW (output). Motor input kW = HP × 0.746 ÷ efficiency."] };
}

// ------------------------------------------------------------------ 24
function tChecklists(i: Any, C: Any, TOOLS: Any) {
  void C;
  const names: Any = { new_lt: "New LT service", load_change: "Load change", new_ht: "New HT service", ceig: "CEIG drawing approval & inspection", name_transfer: "Name transfer", solar: "Solar net metering" };
  const lst: string[] = TOOLS.checklists[i.kind];
  return { headline: { label: names[i.kind], value: lst.length, unit: "documents" }, status: "ok",
    verdict: `Keep these ${lst.length} documents ready. Our liaison team can prepare and file them for you.`,
    items: [], checklist: lst, table: { title: "Checklist", columns: ["#", "Document"], rows: lst.map((d, n) => [n + 1, d]) }, steps: [],
    notes: ["Requirements change from time to time and between offices; we confirm the current list when we take up your case."] };
}

const FUNCS: Any = {
  "connected-load": tConnectedLoad, "lt-vs-ht": tLtVsHt, "bill-estimator": tBillEstimator, "contract-demand": tContractDemand,
  "ht-connection-roadmap": tHtRoadmap, "transformer-sizing": tTransformerSizing, "transformer-losses": tTransformerLosses, "dg-sizing": tDgSizing,
  "ups-battery": tUpsBattery, "solar-rooftop": tSolarRooftop, "ev-charger-load": tEvChargerLoad, "cable-size": tCableSize, "voltage-drop": tVoltageDrop,
  "fault-level": tFaultLevel, "breaker-selector": tBreakerSelector, motor: tMotor, "pf-correction": tPfCorrection, harmonics: tHarmonics,
  "energy-savings": tEnergySavings, earthing: tEarthing, "lightning-risk": tLightningRisk, "lighting-lux": tLightingLux, "units-formulas": tUnits,
  "document-checklists": tChecklists,
};

export function makeEngine(TOOLS: Any, DEFAULTS: Any) {
  const SPEC: Any = Object.fromEntries(TOOLS.tools.map((t: Any) => [t.slug, t]));
  function run(slug: string, raw: Any, overrides?: Any) {
    const C = mergedConstants(DEFAULTS, overrides);
    const spec = SPEC[slug];
    if (!spec) throw new CalcError("Unknown calculator");
    const inp = validate(spec, raw, C);
    const res: Any = FUNCS[slug](inp, C, TOOLS);
    res.status = res.status || "ok";
    res.notes = res.notes || [];
    res.steps = res.steps || [];
    res.items = res.items || [];
    if (res.table === undefined) res.table = null;
    res.basis = spec.basis;
    res.slug = slug;
    res.title = spec.title;
    res.inputs = inp;
    res.rates_as_of = C.rates_as_of;
    return res;
  }
  return { run, SPEC, TOOLS, constants: (o?: Any) => mergedConstants(DEFAULTS, o), optionsFrom, defaultOf };
}
export { ucfirst };
