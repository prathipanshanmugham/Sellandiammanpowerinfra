// The registry's formula language (same rules as backend/expr.py) — totals update while typing and the
// hosted preview computes exactly what the server stores.
const TOKEN = /\s*(?:(\d+\.\d*|\.\d+|\d+)|('(?:[^'\\]|\\.)*')|([A-Za-z_][\w.]*)|(==|!=|<=|>=|[-+*/%(),<>!]))/y;
const PREC = { or: 1, and: 2, "==": 3, "!=": 3, "<": 4, "<=": 4, ">": 4, ">=": 4, "+": 5, "-": 5, "*": 6, "/": 6, "%": 6 };

function tokenize(src) {
  const out = [];
  const s = src.trim();
  let pos = 0;
  while (pos < s.length) {
    TOKEN.lastIndex = pos;
    const m = TOKEN.exec(s);
    if (!m || m.index !== pos) throw new Error(`Bad formula near: ${s.slice(pos, pos + 10)}`);
    const [, numT, str, name, op] = m;
    if (numT !== undefined) out.push(["num", parseFloat(numT)]);
    else if (str !== undefined) out.push(["str", str.slice(1, -1).replace(/\\'/g, "'")]);
    else if (name !== undefined) {
      if (["and", "or", "not"].includes(name)) out.push(["op", name]);
      else if (name === "true" || name === "false") out.push(["num", name === "true" ? 1 : 0]);
      else out.push(["name", name]);
    } else out.push(["op", op]);
    pos = TOKEN.lastIndex;
    while (pos < s.length && /\s/.test(s[pos])) pos += 1;
  }
  out.push(["end", null]);
  return out;
}

function parse(src) {
  const t = tokenize(src);
  let i = 0;
  const peek = () => t[i];
  const take = () => t[i++];
  const isOp = (tok, v) => tok[0] === "op" && tok[1] === v;
  function expr(minp) {
    let left = unary();
    for (;;) {
      const [k, v] = peek();
      if (k !== "op" || !(v in PREC) || PREC[v] < minp) return left;
      take();
      const right = expr(PREC[v] + 1);
      left = ["bin", v, left, right];
    }
  }
  function unary() {
    const [k, v] = peek();
    if (k === "op" && (v === "-" || v === "not" || v === "!")) { take(); return [v === "-" ? "neg" : "not", unary()]; }
    if (k === "op" && v === "+") { take(); return unary(); }
    return primary();
  }
  function primary() {
    const [k, v] = take();
    if (k === "num") return ["num", v];
    if (k === "str") return ["str", v];
    if (k === "op" && v === "(") { const n = expr(0); if (!isOp(take(), ")")) throw new Error("Expected )"); return n; }
    if (k === "name") {
      if (isOp(peek(), "(")) {
        take();
        const args = [];
        if (!isOp(peek(), ")")) {
          for (;;) { args.push(expr(0)); if (isOp(peek(), ",")) { take(); continue; } break; }
        }
        if (!isOp(take(), ")")) throw new Error("Expected )");
        return ["call", v, args];
      }
      return ["name", v];
    }
    throw new Error("Bad formula");
  }
  const node = expr(0);
  if (peek()[0] !== "end") throw new Error("Unexpected text at end of formula");
  return node;
}

const cache = new Map();
const compile = (src) => { if (!cache.has(src)) cache.set(src, parse(src)); return cache.get(src); };
const num = (x) => (typeof x === "boolean" ? (x ? 1 : 0) : typeof x === "number" ? x : typeof x === "string" ? (x.trim() && !Number.isNaN(Number(x)) ? Number(x) : 0) : 0);
const truthy = (x) => (typeof x === "string" ? x !== "" : Array.isArray(x) ? x.length > 0 : Boolean(x));

export function roundHalfUp(x, n = 0) {
  const v = num(x);
  const s = v < 0 ? -1 : 1;
  const r = Number(`${Math.round(Number(`${Math.abs(v)}e${n}`))}e-${n}`);
  return s * r;
}

function resolve(ctx, path) {
  const parts = path.split(".");
  let cur = ctx;
  for (let i = 0; i < parts.length; i += 1) {
    if (Array.isArray(cur)) { const rest = parts.slice(i).join("."); return cur.map((it) => resolve(it, rest)); }
    if (cur === null || typeof cur !== "object") return null;
    cur = cur[parts[i]];
  }
  return cur === undefined ? null : cur;
}

const days = (a, b) => { const x = Date.parse(`${String(a).slice(0, 10)}T00:00:00Z`); const y = Date.parse(`${String(b).slice(0, 10)}T00:00:00Z`); return Number.isNaN(x) || Number.isNaN(y) ? 0 : Math.round((x - y) / 864e5); };

function ev(node, ctx) {
  const k = node[0];
  if (k === "num" || k === "str") return node[1];
  if (k === "name") { const v = resolve(ctx, node[1]); return v === null ? 0 : v; }
  if (k === "neg") return -num(ev(node[1], ctx));
  if (k === "not") return truthy(ev(node[1], ctx)) ? 0 : 1;
  if (k === "bin") {
    const op = node[1];
    if (op === "and") return truthy(ev(node[2], ctx)) && truthy(ev(node[3], ctx)) ? 1 : 0;
    if (op === "or") return truthy(ev(node[2], ctx)) || truthy(ev(node[3], ctx)) ? 1 : 0;
    const a = ev(node[2], ctx);
    const b = ev(node[3], ctx);
    if (op === "==" || op === "!=") {
      let eq;
      if (typeof a === "string" || typeof b === "string") {
        eq = String(a ?? "") === String(b ?? "");
        if (typeof a === "number" && a === 0 && b === "") eq = true;
      } else eq = num(a) === num(b);
      return (op === "==" ? eq : !eq) ? 1 : 0;
    }
    if (["<", "<=", ">", ">="].includes(op)) {
      let x = typeof a === "string" ? a : num(a);
      let y = typeof b === "string" ? b : num(b);
      if (typeof x !== typeof y) { x = String(x); y = String(y); }
      return ({ "<": x < y, "<=": x <= y, ">": x > y, ">=": x >= y })[op] ? 1 : 0;
    }
    const x = num(a); const y = num(b);
    if (op === "+") return x + y;
    if (op === "-") return x - y;
    if (op === "*") return x * y;
    if (op === "/") return y ? x / y : 0;
    if (op === "%") return y ? x % y : 0;
  }
  if (k === "call") {
    const [, fn, args] = node;
    if (fn === "if") return truthy(ev(args[0], ctx)) ? ev(args[1], ctx) : args.length > 2 ? ev(args[2], ctx) : 0;
    const vals = args.map((a) => ev(a, ctx));
    if (fn === "sum") { const v = vals[0]; return Array.isArray(v) ? v.reduce((s, x) => s + num(x), 0) : num(v); }
    if (fn === "count") { const v = vals[0]; return Array.isArray(v) ? v.length : truthy(v) ? 1 : 0; }
    if (fn === "round") return roundHalfUp(vals[0], vals.length > 1 ? num(vals[1]) : 0);
    if (fn === "min") return Math.min(...vals.map(num));
    if (fn === "max") return Math.max(...vals.map(num));
    if (fn === "abs") return Math.abs(num(vals[0]));
    if (fn === "ceil") return Math.ceil(num(vals[0]) - 1e-9);
    if (fn === "floor") return Math.floor(num(vals[0]) + 1e-9);
    if (fn === "coalesce") { for (const x of vals) if (truthy(x)) return x; return 0; }
    if (fn === "days") return days(vals[0], vals[1]);
    throw new Error(`Unknown function ${fn}`);
  }
  throw new Error("Bad formula");
}

export function evaluate(src, ctx) { return ev(compile(src), ctx); }

const money = (v) => roundHalfUp(v, 2);
const roundF = (f, v) => (typeof v === "number" ? (f.t === "money" ? money(v) : Math.round(v * 1e6) / 1e6) : v);

// Line formulas, then record formulas (twice, so later fields can feed earlier ones) — as backend/engine.compute.
export function computeRecord(entity, doc) {
  const out = { ...doc };
  for (const f of entity.fields) {
    if (f.t === "lines" && Array.isArray(out[f.k])) {
      out[f.k] = out[f.k].map((ln) => {
        const row = { ...ln };
        for (const sf of f.fields) if (sf.calc) { try { row[sf.k] = roundF(sf, evaluate(sf.calc, { ...out, ...row })); } catch { /* ignore */ } }
        return row;
      });
    }
  }
  for (let pass = 0; pass < 2; pass += 1) {
    for (const f of entity.fields) if (f.calc && f.t !== "lines") { try { out[f.k] = roundF(f, evaluate(f.calc, out)); } catch { /* ignore */ } }
  }
  return out;
}
