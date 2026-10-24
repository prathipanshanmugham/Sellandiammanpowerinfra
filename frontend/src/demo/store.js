// The preview's in-browser copy of the sample database, with the same list rules as the server:
// portal users see only their own records, hidden fields stay hidden, numbers and formulas are worked out the same way.
import { computeRecord } from "@/lib/expr";

export const S = { db: {}, meta: null, shared: {}, public: {}, role: null, log: [], fixed: null };

const PORTAL_KEY = { client: "account_id", consultant: "contact_id", vendor: "vendor_id", subcontractor: "vendor_id", partner: "partner_id" };
export const uid = () => (crypto?.randomUUID ? crypto.randomUUID() : `${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`);
export const nowIso = () => new Date().toISOString();
export const today = () => new Date(Date.now() + 5.5 * 3600e3).toISOString().slice(0, 10);

export function load({ db, meta, shared, pub }) {
  S.db = db; S.meta = meta; S.shared = shared; S.public = pub; S.fixed = meta.fixed_today;
}
export const reg = () => S.meta.registry;
export const ent = (k) => S.meta.registry.entities[k];
export const coll = (k) => (S.db[k] = S.db[k] || []);
export const roleInfo = (r = S.role) => S.meta.by_role[r];
export const me = () => (S.role ? roleInfo().user : null);
export const isPortal = () => S.meta.portal_roles.includes(S.role);

// /api/meta for the signed-in role, rebuilt from the registry and that role's differences
export function metaFor(role = S.role) {
  const R = reg();
  const info = roleInfo(role);
  const entities = {};
  for (const [k, d] of Object.entries(info.ents)) {
    const e = R.entities[k];
    const drop = new Set(d.drop || []);
    const fields = e.fields.filter((f) => !drop.has(f.k)).map((f) => (d.dropLines?.[f.k] ? { ...f, fields: f.fields.filter((x) => !d.dropLines[f.k].includes(x.k)) } : f));
    entities[k] = { ...e, fields, perm: d.perm, list: e.list.filter((x) => fields.some((f) => f.k === x) || ["code", "created_at", "status", "created_by"].includes(x)) };
  }
  return { ...R, entities };
}
let metaCache = {};
export const roleMeta = () => (metaCache[S.role] = metaCache[S.role] || metaFor());
export const can = (module, letter) => (me()?.permissions?.[module] || "").includes(letter);

// ------------------------------------------------------------------ helpers
export function titleOf(e, d) {
  if (!d) return "";
  const tk = e?.title || "name";
  let t = d[tk];
  const f = e?.fields.find((x) => x.k === tk);
  if (f?.t === "ref" && t) t = refTitle(f.ref, t);
  if (tk === "code" || !t) t = d.code || d.name || d.title || d.subject || d.id;
  return String(t ?? "");
}
export function refTitle(entity, id) {
  if (!id) return "";
  if (entity === "users") return coll("users").find((u) => u.id === id)?.name || "";
  if (entity === "branches") return coll("branches").find((b) => b.id === id)?.name || "";
  const d = coll(entity).find((x) => x.id === id);
  return d ? titleOf(ent(entity), d) : "";
}
export function refs(e, docs) {
  const want = {};
  const add = (ref, id) => { if (id) (want[ref] = want[ref] || new Set()).add(id); };
  for (const f of e.fields) {
    if (f.t === "ref" || f.t === "refs") for (const d of docs) { const v = d[f.k]; (Array.isArray(v) ? v : [v]).forEach((x) => add(f.ref, x)); }
    if (f.t === "lines") for (const sf of f.fields) if (sf.t === "ref") for (const d of docs) for (const ln of d[f.k] || []) add(sf.ref, ln?.[sf.k]);
  }
  for (const d of docs) { add("users", d.created_by); add("branches", d.branch_id); }
  const out = {};
  for (const [r, ids] of Object.entries(want)) { out[r] = {}; for (const id of ids) out[r][id] = refTitle(r, id); }
  return out;
}

function projectIdsFor(u) {
  if (u.role === "client") return new Set(coll("projects").filter((p) => !p.deleted && p.account_id === u.account_id).map((p) => p.id));
  if (u.role === "consultant") return new Set(coll("projects").filter((p) => !p.deleted && (p.consultant_ids || []).includes(u.contact_id)).map((p) => p.id));
  return new Set();
}
const CLIENT_STATUS = { proposals: ["sent", "accepted", "declined", "expired"], invoices: ["issued", "part_paid", "paid"], ra_bills: ["submitted", "certified", "invoiced", "paid"],
  variations: ["sent", "client_approved", "client_rejected"], test_reports: ["issued"] };
// Same rules as engine.portal_filter on the server
function portalRows(k, e, rows, u) {
  const cfg = (e.portal || {})[u.role];
  if (!cfg) return [];
  const pids = projectIdsFor(u);
  if (u.role === "client") {
    const acc = u.account_id;
    rows = rows.filter((d) => (cfg === "id" ? d.id === acc : cfg === "account_id" ? d.account_id === acc : cfg === "project" ? pids.has(d.project_id)
      : cfg === "account_id_or_project" ? d.account_id === acc || pids.has(d.project_id) : false));
    if (["dprs", "drawings", "documents", "liaisons"].includes(k)) rows = rows.filter((d) => d.share_with_client === true);
    if (CLIENT_STATUS[k]) rows = rows.filter((d) => CLIENT_STATUS[k].includes(d.status));
    return rows;
  }
  if (u.role === "consultant") {
    rows = rows.filter((d) => (cfg === "consultant_ids" ? (d.consultant_ids || []).includes(u.contact_id) : pids.has(d.project_id)));
    if (["dprs", "drawings"].includes(k)) rows = rows.filter((d) => d.share_with_client === true);
    return rows;
  }
  if (u.role === "vendor" || u.role === "subcontractor") {
    const v = u.vendor_id;
    if (cfg === "id") return rows.filter((d) => d.id === v);
    if (cfg === "vendor_ids") return rows.filter((d) => (d.vendor_ids || []).includes(v));
    if (cfg === "worker") { const ws = new Set(coll("workers").filter((w) => w.contractor_id === v).map((w) => w.id)); return rows.filter((d) => ws.has(d.worker_id)); }
    return rows.filter((d) => d[cfg] === v);
  }
  return [];
}
export function visibleRows(k, e) {
  const u = me();
  let rows = coll(k).filter((d) => !d.deleted);
  if (isPortal()) rows = portalRows(k, e, rows, u);
  return rows;
}

export function strip(k, d) {
  const e = roleMeta().entities[k];
  if (!e) return d;
  const full = ent(k);
  const keep = new Set(e.fields.map((f) => f.k));
  const out = { ...d };
  for (const f of full.fields) if (!keep.has(f.k)) delete out[f.k];
  return out;
}

const NUM = ["number", "money", "percent"];
function coerce(f, v) {
  if (v === "" || v === undefined) return null;
  if (NUM.includes(f.t)) return v === null ? null : Number(v);
  if (f.t === "bool") return v === true || v === "true";
  return v;
}
export function listRecords(k, params = {}) {
  const e = ent(k);
  let rows = visibleRows(k, e);
  const fmap = Object.fromEntries(e.fields.map((f) => [f.k, f]));
  const sf = e.status?.field;
  for (const [pk, pv] of Object.entries(params)) {
    if (pv === null || pv === undefined || pv === "" || pv === "all") continue;
    const key = pk === "status" && sf ? sf : pk;
    if (!(key in fmap) && !["status", "branch_id", "created_by", "id"].includes(key)) continue;
    const f = fmap[key] || { t: "select" };
    const vals = String(pv).includes(",") && !["text", "textarea"].includes(f.t) ? String(pv).split(",") : null;
    rows = rows.filter((d) => {
      const v = d[key];
      if (pv === "__empty") return v === null || v === undefined || v === "";
      if (f.t === "refs" || f.t === "multiselect") return (v || []).includes(pv);
      if (vals) return vals.map((x) => String(coerce(f, x))).includes(String(v));
      if (f.t === "text" && key === "town") return String(v || "").toLowerCase() === String(pv).toLowerCase();
      return String(v) === String(coerce(f, pv));
    });
  }
  if (params.from || params.to) {
    const dk = params.date_field || (fmap.date ? "date" : "created_at");
    rows = rows.filter((d) => (!params.from || String(d[dk] || "") >= params.from) && (!params.to || String(d[dk] || "").slice(0, 10) <= params.to));
  }
  const q = String(params.q || "").trim().toLowerCase();
  if (q) {
    const keys = [...(e.search || []), ...(e.number ? ["code"] : [])];
    rows = rows.filter((d) => keys.some((x) => String(d[x] ?? "").toLowerCase().includes(q)));
  }
  const sort = params.sort || e.sort || "-created_at";
  const dir = sort.startsWith("-") ? -1 : 1;
  const sk = sort.replace(/^-/, "");
  rows = [...rows].sort((a, b) => {
    const x = a[sk]; const y = b[sk];
    if (x === y) return String(b.created_at || "").localeCompare(String(a.created_at || ""));
    if (x === null || x === undefined) return 1;
    if (y === null || y === undefined) return -1;
    return (typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y))) * dir;
  });
  const size = Math.min(500, Number(params.size || 50));
  const page = Math.max(1, Number(params.page || 1));
  const items = rows.slice((page - 1) * size, page * size).map((d) => strip(k, d));
  return { items, total: rows.length, page, size, refs: refs(e, items) };
}

export function getRecord(k, id) {
  const e = ent(k);
  const d = visibleRows(k, e).find((x) => x.id === id);
  if (!d) return null;
  const out = strip(k, d);
  out._refs = refs(e, [d]);
  out._actions = isPortal() ? [] : actionsFor(k, d);
  if (d.approval_id) out._approval = coll("approvals").find((a) => a.id === d.approval_id) || null;
  return out;
}

export function actionsFor(k, d) {
  const e = ent(k);
  const sf = e.status?.field;
  if (!sf) return [];
  const cur = d[sf];
  const out = [];
  if (e.approval && e.approval.from.includes(cur) && can(e.module, "w")) out.push({ key: "submit", label: "Submit for approval", tone: "primary" });
  for (const [key, a] of Object.entries(e.actions || {})) if (a.from.includes(cur) && can(e.module, a.perm || "w")) out.push({ key, label: a.label, confirm: a.confirm, reason: a.reason, need: a.need || [] });
  return out;
}

// ------------------------------------------------------------------ writes
function fyOf(d) { const y = Number(d.slice(0, 4)); const m = Number(d.slice(5, 7)); const s = m >= 4 ? y : y - 1; return `${String(s).slice(2)}-${String(s + 1).slice(2)}`; }
function nextCode(k, e, doc) {
  const n = e.number;
  if (!n) return null;
  const seq = coll(k).length + 1;
  if (n.prefix) return n.kind === "year" ? `${n.prefix}-${today().slice(0, 4)}-${String(seq).padStart(4, "0")}` : `${n.prefix}-${String(seq).padStart(5, "0")}`;
  const br = coll("branches").find((b) => b.id === doc.branch_id)?.code || "PDR";
  return `SPI/${br}/${n.doc}/${fyOf(today())}/${String(seq).padStart(4, "0")}`;
}
const NUMT = new Set(["number", "money", "percent"]);
export function clean(e, data) {
  const out = {};
  for (const f of e.fields) {
    if (!(f.k in data) || f.ro || f.calc) continue;
    let v = data[f.k];
    if (NUMT.has(f.t)) v = v === "" || v === null || v === undefined ? null : Number(v);
    if (f.t === "lines") v = (v || []).map((r) => { const row = { ...r }; for (const sf of f.fields) if (NUMT.has(sf.t) && row[sf.k] !== null && row[sf.k] !== undefined && row[sf.k] !== "") row[sf.k] = Number(row[sf.k]); return row; });
    out[f.k] = v;
  }
  return out;
}
export function audit(action, k, id, details = {}) {
  const u = me();
  coll("audit_logs").push({ id: uid(), seq: coll("audit_logs").length + 1, user_id: u?.id || null, user_name: u?.name || "Website visitor", role: u?.role, action, entity: k, entity_id: id, details, at: nowIso() });
}
export function createRecord(k, data, { system = false } = {}) {
  const e = ent(k);
  const u = me();
  const doc = { id: uid(), ...clean(e, data) };
  for (const f of e.fields) if (doc[f.k] === undefined && f.default !== undefined) doc[f.k] = f.default;
  if (e.status?.field && !doc[e.status.field]) doc[e.status.field] = e.status.default;
  if (e.branch && !doc.branch_id) doc.branch_id = u?.branch_ids?.[0] || coll("branches").find((b) => b.is_head_office)?.id;
  const done = computeRecord(e, doc);
  done.code = done.code || nextCode(k, e, done);
  Object.assign(done, { created_at: nowIso(), created_by: system ? null : u?.id || null, updated_at: nowIso(), deleted: false, _demo: true });
  coll(k).unshift(done);
  audit("create", k, done.id, { code: done.code, title: titleOf(e, done) });
  return done;
}
export function updateRecord(k, id, data) {
  const e = ent(k);
  const i = coll(k).findIndex((x) => x.id === id);
  if (i < 0) return null;
  const old = coll(k)[i];
  const next = computeRecord(e, { ...old, ...clean(e, data), updated_at: nowIso(), updated_by: me()?.id });
  const changes = {};
  for (const f of e.fields) if (JSON.stringify(old[f.k]) !== JSON.stringify(next[f.k]) && f.k in data) changes[f.k] = ["lines", "textarea", "markdown", "files", "json"].includes(f.t) ? "changed" : [old[f.k] ?? null, next[f.k] ?? null];
  coll(k)[i] = next;
  if (Object.keys(changes).length) audit("update", k, id, { code: next.code, changes });
  return next;
}
export function setFields(k, id, patch) {
  const i = coll(k).findIndex((x) => x.id === id);
  if (i < 0) return null;
  coll(k)[i] = { ...coll(k)[i], ...patch, updated_at: nowIso() };
  return coll(k)[i];
}
export function notifyRoles(roles, title, body, link) {
  for (const u of coll("users").filter((x) => roles.includes(x.role))) coll("notifications").unshift({ id: uid(), user_id: u.id, title, body, link, kind: "info", read: false, created_at: nowIso() });
  for (const r of roles) {
    const sc = S.meta.by_role[r]?.screens?.["/notifications"];
    if (sc) { sc.items.unshift({ id: uid(), title, body, link, kind: "info", read: false, created_at: nowIso() }); sc.unread += 1; }
  }
}
