// Answers every /api call in the browser for the hosted preview. Lists and records come from the sample database
// (changes you make stay until you reload); computed screens (CEO view, finance, reports) were recorded from the real server.
import { AxiosError } from "axios";
import { S, coll, ent, me, roleInfo, roleMeta, metaFor, isPortal, can, listRecords, getRecord, createRecord, updateRecord, setFields, audit, refs, titleOf,
  uid, nowIso, today, notifyRoles, actionsFor, strip } from "./store";

const PW = "Demo@12345";
const SEARCHABLE = ["leads", "accounts", "contacts", "projects", "proposals", "boqs", "tenders", "purchase_orders", "invoices", "vendors", "items", "tickets", "installed_assets", "employees", "documents", "liaisons", "drawings", "cable_drums", "workers"];
const LEAD_FORMS = { quote_wizard: "Website quote", survey_booking: "Survey booking", calculator: "Calculator result", bill_review: "Bill review", tender_invite: "Tender / BOQ invite", callback: "Call-back request", emergency: "Emergency", amc_enquiry: "AMC enquiry", download: "Guide download", contact_form: "Contact form", product_enquiry: "Product enquiry", service_enquiry: "Website quote", sector_enquiry: "Contact form", similar_project: "Website quote", referral: "Referral partner", existing_client: "Existing client" };

class HttpError extends Error { constructor(status, detail) { super(detail); this.status = status; this.detail = detail; } }
const fail = (status, detail) => { throw new HttpError(status, detail); };
const need = () => { if (!S.role) fail(401, "Please sign in"); return me(); };
const staff = () => { const u = need(); if (isPortal()) fail(403, "Staff only"); return u; };
const body = (cfg) => { if (!cfg.data) return {}; if (typeof cfg.data === "string") { try { return JSON.parse(cfg.data); } catch { return {}; } } return cfg.data; };
const delay = (ms) => new Promise((r) => setTimeout(r, ms));

function saveRole() { try { sessionStorage.setItem("spi_demo_role", S.role || ""); } catch { /* private mode */ } }
export function restoreRole() { try { const r = sessionStorage.getItem("spi_demo_role"); if (r && S.meta.by_role[r]) S.role = r; } catch { /* ignore */ } }
export function signInAs(role) { S.role = role; saveRole(); }

function screen(path) {
  const r = roleInfo();
  return r?.screens?.[path];
}
function recorded(path) {
  if (path in S.shared) return S.shared[path];
  if (path in S.public) return S.public[path];
  return undefined;
}

// ------------------------------------------------------------------ public website intake: becomes a real lead in the sample CRM
function newLead(b, source) {
  const branch = coll("branches").find((x) => /coimbatore|tiruppur|pollachi/i.test(b.town || "") ? x.code === "CBE" : x.is_head_office);
  const owner = coll("users").find((u) => u.role === "sales" && (u.branch_ids || []).includes(branch?.id)) || coll("users").find((u) => u.role === "sales");
  const prev = S.role; S.role = prev || null;
  const lead = createRecord("leads", { name: b.name, phone: b.phone, email: b.email || null, company: b.company || null, service: b.service || null, supply: b.supply || null,
    load_kva: b.load_kva ? Number(b.load_kva) : null, site_type: b.site_type || null, town: b.town || null, timeline: b.timeline || null, message: b.message || null,
    attachments: b.attachments || [], source, source_detail: LEAD_FORMS[b.form] || b.form, owner_id: owner?.id, consent: !!b.consent, calculator: b.calculator || null,
    partner_id: b.partner_id || null, utm_source: b.tracking?.utm_source || null, landing_page: b.tracking?.landing_page || null, branch_id: branch?.id }, { system: true });
  const due = new Date(Date.now() + 30 * 60e3).toISOString();
  setFields("leads", lead.id, { score: 40 + Math.min(40, Math.round((Number(b.load_kva) || 0) / 30)) + (b.supply === "HT" ? 10 : 0), response_due_at: due, probability: 5, consent_at: nowIso() });
  notifyRoles(["sales", "branch_manager"], `New lead: ${b.name}${b.company ? `, ${b.company}` : ""}`, `${LEAD_FORMS[b.form] || "Website"}. Respond within 30 working minutes.`, `/erp/e/leads/${lead.id}`);
  // the pipeline screen reads live data, so the new card shows up straight away
  return { ok: true, reference: lead.code, lead_id: lead.id };
}

// ------------------------------------------------------------------ computed screens that follow your changes
function pipeline(params) {
  const L = coll("leads").filter((l) => !l.deleted && (!params.owner || l.owner_id === params.owner) && (!params.service || l.service === params.service));
  const states = ent("leads").status.states.filter((s) => s.value !== "lost");
  let weighted = 0;
  const columns = states.map((s) => {
    const items = L.filter((l) => l.stage === s.value).sort((a, b) => (b.score || 0) - (a.score || 0));
    const value = items.reduce((a, l) => a + (Number(l.value) || 0), 0);
    weighted += items.reduce((a, l) => a + (Number(l.value) || 0) * (Number(l.probability) || 0) / 100, 0);
    return { stage: s.value, label: s.label, items: items.map((l) => ({ id: l.id, code: l.code, name: l.name, company: l.company, service: l.service, supply: l.supply, load_kva: l.load_kva, town: l.town, value: l.value, score: l.score, owner_id: l.owner_id, next_follow_up: l.next_follow_up, response_due_at: l.response_due_at, first_response_at: l.first_response_at, source: l.source, created_at: l.created_at })), count: items.length, value };
  });
  return { columns, refs: refs(ent("leads"), L), weighted_value: Math.round(weighted) };
}
function inbox() {
  const u = me();
  const rows = coll("approvals").filter((a) => a.status === "pending").sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  const names = Object.fromEntries(coll("users").map((x) => [x.id, x.name]));
  const out = rows.map((a) => {
    const ok = (a.approver_roles || []).includes(u.role) && a.requested_by !== u.id;
    return { ...a, can_decide: ok, why_not: ok ? null : a.requested_by === u.id ? "You can't approve your own request" : "Needs a different role", entity_label: ent(a.doc_entity)?.label, requested_by_name: names[a.requested_by] };
  });
  return { to_decide: out.filter((a) => a.can_decide), my_requests: coll("approvals").filter((a) => a.requested_by === u.id).map((a) => ({ ...a, entity_label: ent(a.doc_entity)?.label })), count: out.filter((a) => a.can_decide).length };
}
function timeline(id) {
  const rec = recorded(`/crm/leads/${id}/timeline`);
  const extra = [];
  for (const k of ["activities", "surveys", "proposals"]) for (const d of coll(k).filter((x) => x.lead_id === id && x._demo)) extra.push({ at: d.created_at, kind: k === "activities" ? d.kind || "call" : k === "surveys" ? "survey" : "proposal", title: titleOf(ent(k), d), id: d.id, entity: k });
  const base = rec || [{ at: coll("leads").find((l) => l.id === id)?.created_at, kind: "created", title: "Lead created", by: "Website visitor" }];
  return [...extra, ...base].sort((a, b) => String(b.at).localeCompare(String(a.at)));
}
function search(q) {
  q = String(q || "").trim();
  if (q.length < 2) return [];
  const out = [];
  const M = roleMeta();
  for (const k of SEARCHABLE) {
    const e = M.entities[k];
    if (!e || !(e.perm || "").includes("r")) continue;
    for (const d of listRecords(k, { q, size: 5 }).items) out.push({ entity: k, entity_label: e.label, id: d.id, title: titleOf(ent(k), d), code: d.code, icon: e.icon });
  }
  return out.slice(0, 40);
}

// ------------------------------------------------------------------ record actions (status changes and approvals)
function runAction(k, id, action, b) {
  const u = staff();
  const e = ent(k);
  const d = coll(k).find((x) => x.id === id);
  if (!d) fail(404, "Record not found");
  const sf = e.status?.field;
  if (action === "submit") {
    const amount = e.approval?.amount ? Number(d[e.approval.amount] || d.total || 0) : 0;
    const rule = (S.shared["/settings"]?.approval_rules || []).find((r) => r.doc === k && (r.up_to === null || r.up_to === undefined || amount <= r.up_to));
    if (!rule) {
      setFields(k, id, { [sf]: e.approval.approved, approved_at: nowIso(), approval_note: "Within limits, approved automatically" });
      audit("auto_approved", k, id, { code: d.code });
    } else {
      const a = { id: uid(), doc_entity: k, doc_id: id, doc_code: d.code || titleOf(e, d), title: `${e.label}: ${titleOf(e, d)}`, amount, requested_by: u.id, approver_roles: rule.roles,
        branch_id: d.branch_id, status: "pending", created_at: nowIso(), created_by: u.id, module: e.module };
      coll("approvals").unshift(a);
      setFields(k, id, { [sf]: e.approval.pending, approval_id: a.id, submitted_at: nowIso(), submitted_by: u.id });
      audit("submitted", k, id, { code: d.code, approvers: rule.roles, amount });
      notifyRoles(rule.roles, `Approval needed: ${a.title}`, amount ? `Amount ₹${amount.toLocaleString("en-IN")}` : "", "/erp/approvals");
    }
  } else {
    const a = (e.actions || {})[action];
    if (!a) fail(404, "Unknown action");
    if (!a.from.includes(d[sf])) fail(409, `Not possible while the record is '${d[sf]}'`);
    if (a.not_self && d.created_by === u.id) fail(403, "Someone else has to approve a permit you raised");
    const patch = { [sf]: a.to };
    for (const nk of a.need || []) {
      const v = b[nk] ?? d[nk];
      if (v === null || v === undefined || v === "") fail(422, `Fill in '${e.fields.find((f) => f.k === nk)?.l || nk}' first`);
      if (nk in b) patch[nk] = b[nk];
    }
    if (a.reason) { if (!String(b.reason || "").trim()) fail(422, "Give a reason"); patch.status_reason = b.reason; }
    if (k === "invoices" && action === "issue") patch.due_date = d.due_date || new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10);
    setFields(k, id, patch);
    audit(action, k, id, { code: d.code, reason: b.reason });
  }
  return { ...getRecord(k, id) };
}
function decide(aid, decision, reason) {
  const u = staff();
  const a = coll("approvals").find((x) => x.id === aid);
  if (!a) fail(404, "Approval not found");
  if (a.status !== "pending") fail(409, "Already decided");
  if (a.requested_by === u.id) fail(403, "You can't approve your own request");
  if (decision === "reject" && !String(reason || "").trim()) fail(422, "Give a reason for rejecting");
  Object.assign(a, { status: decision === "approve" ? "approved" : "rejected", decided_by: u.id, decided_at: nowIso(), reason });
  const e = ent(a.doc_entity);
  setFields(a.doc_entity, a.doc_id, { [e.status.field]: decision === "approve" ? e.approval.approved : e.approval.rejected, decision_note: reason || "" });
  audit(decision, a.doc_entity, a.doc_id, { code: a.doc_code, reason });
  for (const sc of Object.values(S.meta.by_role)) {
    const ib = sc.screens?.["/approvals/inbox"];
    if (ib) { ib.to_decide = ib.to_decide.filter((x) => x.id !== aid); ib.count = ib.to_decide.length; }
    const db = sc.screens?.["/dashboard"];
    if (db?.approvals) db.approvals = db.approvals.filter((x) => x.id !== aid);
  }
  return a;
}

// ------------------------------------------------------------------ the router
async function route(method, path, params, b, cfg) {
  const m = (re) => path.match(re);
  let x;
  // ---- sign-in
  if (path === "/auth/me") { const u = need(); return { user: u }; }
  if (path === "/auth/login" && method === "post") {
    const email = String(b.email || "").trim().toLowerCase();
    const role = Object.entries(S.meta.logins).find(([, v]) => v === email)?.[0];
    if (!role || b.password !== PW) fail(401, "Email or password is wrong. In this preview use a demo login, password Demo@12345.");
    const portal = S.meta.portal_roles.includes(role);
    if (b.portal === true && !portal) fail(403, "Staff sign in from the staff login page (link at the bottom of the website)");
    if (b.portal === false && portal) fail(403, "Customers and partners sign in from the Login button at the top of the website");
    signInAs(role);
    return { user: me() };
  }
  if (path === "/auth/logout") { S.role = null; saveRole(); return { ok: true }; }
  if (path === "/auth/refresh") return { ok: true };
  if (path === "/auth/forgot") return { ok: true, message: "If that email has an account, a link to set a new password is on its way. (The preview doesn't send emails.)" };
  if (path === "/auth/set-password") return { ok: true, portal: false };
  if (path === "/auth/password") { need(); if (b.current !== PW) fail(401, "Current password is wrong"); return { signed_out: 0 }; }
  if (path === "/auth/mfa/setup") return { secret: "JBSWY3DPEHPK3PXP", otpauth_uri: "otpauth://totp/demo", qr_svg: QR_SVG };
  if (path === "/auth/mfa/enable") { if (!/^\d{6}$/.test(String(b.code || ""))) fail(422, "That code didn't match"); Object.assign(me(), { mfa_enabled: true }); return { ok: true, recovery_codes: ["a1b2c3d4", "e5f6a7b8", "c9d0e1f2", "a3b4c5d6", "e7f8a9b0", "c1d2e3f4", "a5b6c7d8", "e9f0a1b2"] }; }
  if (path === "/auth/sessions") return [{ sid: "preview1", current: true, created_at: nowIso(), ip: "—", agent: navigator.userAgent.slice(0, 80) }];
  if (path === "/auth/sessions/sign-out-others") return { ok: true };
  if (path === "/meta") { need(); return roleMeta(); }
  if (path === "/me/preferences") { Object.assign(me(), b); return { ok: true }; }

  // ---- notifications, approvals, search
  if (path === "/notifications") { need(); return screen("/notifications") || { items: [], unread: 0 }; }
  if (path === "/notifications/read") { const n = screen("/notifications"); if (n) { n.items.forEach((i) => { if (!b.ids || b.ids.includes(i.id)) i.read = true; }); n.unread = n.items.filter((i) => !i.read).length; } return { ok: true }; }
  if (path === "/approvals/inbox") { staff(); return inbox(); }
  if ((x = m(/^\/approvals\/([^/]+)\/decide$/))) return decide(x[1], b.decision, b.reason);
  if (path === "/search") { staff(); return search(params.q); }
  if (path === "/users/lookup") { staff(); return coll("users").filter((u) => !S.meta.portal_roles.includes(u.role) && u.active !== false && (!params.q || u.name.toLowerCase().includes(String(params.q).toLowerCase()))).map((u) => ({ id: u.id, name: u.name, role: u.role, role_label: S.meta.roles[u.role], designation: u.designation, branch_ids: u.branch_ids })); }
  if (path === "/users" && method === "get") { staff(); const pr = S.meta.portal_roles; return coll("users").filter((u) => (params.portal === true || params.portal === "true" ? pr.includes(u.role) : !pr.includes(u.role))).map((u) => ({ ...u, role_label: S.meta.roles[u.role] })); }
  if (path === "/users" && method === "post") { staff(); const u = { id: uid(), ...b, email: String(b.email || "").toLowerCase(), active: true, created_at: nowIso(), mfa_enabled: false, role_label: S.meta.roles[b.role] }; coll("users").push(u); return { user: u, set_password_link: `${location.origin}/set-password?token=preview-${u.id.slice(0, 8)}` }; }
  if ((x = m(/^\/users\/([^/]+)$/)) && method === "patch") { const u = coll("users").find((y) => y.id === x[1]); Object.assign(u, b); return { ...u, role_label: S.meta.roles[u.role] }; }
  if ((x = m(/^\/users\/([^/]+)\/link$/))) return { set_password_link: `${location.origin}/set-password?token=preview-${x[1].slice(0, 8)}` };
  if ((x = m(/^\/users\/([^/]+)\/reset-mfa$/))) return { ok: true };
  if (path === "/branches/all") { need(); return coll("branches").filter((y) => !y.deleted); }
  if (path === "/views/" || m(/^\/views\//)) return method === "get" ? [] : { ok: true, id: uid() };

  // ---- files
  if (path === "/files" || path === "/portal/files" || path === "/public/upload") {
    const f = cfg.data instanceof FormData ? cfg.data.get("file") : null;
    const rec = { id: uid(), name: f?.name || "file", type: f?.type || "application/octet-stream", size: f?.size || 0, url: f ? URL.createObjectURL(f) : null };
    coll("files").push(rec);
    await delay(250);
    return rec;
  }
  if ((x = m(/^\/files\/([^/]+)\/link$/))) return { url: `/files/get/${x[1]}` };

  // ---- generic records
  if ((x = m(/^\/e\/([a-z_]+)\/bulk$/))) { staff(); let done = 0; for (const id of b.ids || []) { if (b.op === "delete") setFields(x[1], id, { deleted: true }); else updateRecord(x[1], id, b.values || {}); done += 1; } return { done, errors: [] }; }
  if ((x = m(/^\/e\/([a-z_]+)\/([^/]+)\/action\/([a-z_]+)$/))) return { ...runAction(x[1], x[2], x[3], b), _actions: actionsFor(x[1], coll(x[1]).find((y) => y.id === x[2])) };
  if ((x = m(/^\/e\/([a-z_]+)\/([^/]+)\/history$/))) { staff(); return coll("audit_logs").filter((a) => a.entity === x[1] && a.entity_id === x[2]).sort((p, q) => (q.seq || 0) - (p.seq || 0)); }
  if ((x = m(/^\/e\/([a-z_]+)$/))) {
    const k = x[1];
    const e = roleMeta().entities[k];
    need();
    if (!e) fail(403, "You do not have permission to view this");
    if (method === "get") { if (!isPortal() && !(e.perm || "").includes("r")) fail(403, "You do not have permission to view this"); return listRecords(k, params); }
    if (method === "post") { staff(); if (!(e.perm || "").includes("w")) fail(403, "You do not have permission to add this"); const missing = ent(k).fields.filter((f) => f.req && !f.ro && !f.calc && (b[f.k] === undefined || b[f.k] === null || b[f.k] === "")); if (missing.length) fail(422, `Fill in: ${missing.map((f) => f.l).join(", ")}`); return createRecord(k, b); }
  }
  if ((x = m(/^\/e\/([a-z_]+)\/([^/]+)$/))) {
    const [, k, id] = x;
    need();
    if (!roleMeta().entities[k]) fail(403, "You do not have permission to view this");
    if (method === "get") { const d = getRecord(k, id); if (!d) fail(404, "Record not found"); return d; }
    if (method === "patch") { staff(); const d = updateRecord(k, id, b); if (!d) fail(404, "Record not found"); return strip(k, d); }
    if (method === "delete") { staff(); setFields(k, id, { deleted: true, deleted_reason: params.reason }); audit("delete", k, id, { reason: params.reason }); return { ok: true }; }
  }

  // ---- CRM
  if (path === "/crm/pipeline") { staff(); return pipeline(params); }
  if ((x = m(/^\/crm\/leads\/([^/]+)\/move$/))) { staff(); const patch = { stage: b.stage }; for (const k of ["lost_reason", "lost_note", "hold_until"]) if (b[k]) patch[k] = b[k]; const prob = { new: 5, contacted: 10, survey_scheduled: 20, survey_done: 30, estimating: 40, quoted: 50, negotiation: 70, won: 100, lost: 0, on_hold: 10 }[b.stage]; return updateRecord("leads", x[1], { ...patch }) && setFields("leads", x[1], { probability: prob, first_response_at: coll("leads").find((l) => l.id === x[1]).first_response_at || nowIso() }); }
  if ((x = m(/^\/crm\/leads\/([^/]+)\/convert$/))) {
    staff();
    const l = coll("leads").find((y) => y.id === x[1]);
    let acc = b.account_id;
    if (!acc) acc = createRecord("accounts", { name: b.account_name || l.company || l.name, phone: l.phone, email: l.email, town: l.town, sector: l.site_type, owner_id: l.owner_id, branch_id: l.branch_id }).id;
    const c = createRecord("contacts", { name: l.name, account_id: acc, phone: l.phone, email: l.email, is_primary: true });
    const p = createRecord("projects", { name: b.project_name || `${l.company || l.name} — ${l.service || "project"}`, account_id: acc, contact_id: c.id, lead_id: l.id, service: l.service, sector: l.site_type, supply: ["LT", "HT"].includes(l.supply) ? l.supply : null, capacity_kva: l.load_kva, town: l.town, contract_value: l.value, manager_id: b.manager_id, branch_id: l.branch_id, start_date: b.start_date });
    setFields("leads", l.id, { stage: "won", probability: 100, account_id: acc, project_id: p.id });
    return { account_id: acc, contact_id: c.id, project_id: p.id };
  }
  if ((x = m(/^\/crm\/leads\/([^/]+)\/timeline$/))) { staff(); return timeline(x[1]); }
  if ((x = m(/^\/crm\/leads\/([^/]+)\/whatsapp$/))) { const l = coll("leads").find((y) => y.id === x[1]); return { url: `https://wa.me/${String(l?.phone || "").replace(/\D/g, "")}?text=${encodeURIComponent(`Hello ${l?.name}, this is Sellandiamman Power Infra about your enquiry ${l?.code}.`)}` }; }
  if (path === "/crm/routing" && method === "put") { S.shared["/crm/routing"].rules = b.rules; return S.shared["/crm/routing"]; }
  if ((x = m(/^\/crm\/partners\/([^/]+)\/statement$/))) return recorded(path) || { rows: [], commission_total: 0 };

  // ---- project, procurement, HR actions
  if ((x = m(/^\/projects\/([^/]+)\/ra-from-mb$/))) { staff(); const p = coll("projects").find((y) => y.id === x[1]); const mbs = coll("mb_entries").filter((y) => y.project_id === x[1] && y.status === "checked"); if (!mbs.length) fail(409, "No checked measurements to bill yet"); return createRecord("ra_bills", { project_id: x[1], period_to: today(), lines: mbs.map((y) => ({ description: y.description, unit: y.unit, this_qty: y.qty || y.nos || 1, rate: y.rate })), branch_id: p?.branch_id }); }
  if ((x = m(/^\/purchase_requests\/([^/]+)\/to-rfq$/))) { staff(); const pr = coll("purchase_requests").find((y) => y.id === x[1]); return createRecord("rfqs", { pr_id: pr.id, project_id: pr.project_id, vendor_ids: [], lines: (pr.lines || []).map((l) => ({ item_id: l.item_id, description: l.description, qty: l.qty, unit: l.unit })), due_on: new Date(Date.now() + 3 * 864e5).toISOString().slice(0, 10) }); }
  if ((x = m(/^\/rfqs\/([^/]+)\/award$/))) { staff(); const q = coll("vendor_quotes").find((y) => y.id === b.quote_id); const r = coll("rfqs").find((y) => y.id === x[1]); setFields("rfqs", x[1], { status: "closed", awarded_to: q.vendor_id }); return createRecord("purchase_orders", { vendor_id: q.vendor_id, project_id: r.project_id, rfq_id: r.id, date: today(), lines: (q.lines || []).map((l) => ({ item_id: l.item_id, description: l.description, make: l.make, qty: l.qty, rate: l.rate, gst_rate: l.gst_rate || "18" })) }); }
  if (path === "/hr/check-in" || path === "/hr/check-out") {
    staff();
    const hr = screen("/hr/me");
    if (!hr?.employee) fail(409, "No employee record is linked to your login");
    const t = new Date(Date.now() + 5.5 * 3600e3).toISOString().slice(0, 19) + "+05:30";
    if (path.endsWith("in")) { if (hr.today) fail(409, "Already checked in today"); hr.today = { id: uid(), date: today(), check_in: t, in_gps: b.gps, distance_m: 120, flag: "" }; hr.attendance.unshift(hr.today); }
    else { if (!hr.today) fail(409, "Check in first"); hr.today.check_out = t; hr.today.hours = Math.round(((Date.parse(t) - Date.parse(hr.today.check_in)) / 36e5) * 10) / 10; }
    return hr.today;
  }
  if (path === "/hr/my-leave") { const hr = screen("/hr/me"); const l = { id: uid(), ...b, days: Math.round((Date.parse(b.to_date) - Date.parse(b.from_date)) / 864e5) + 1, status: "pending_approval" }; hr?.leaves.unshift(l); return l; }
  if (path === "/hr/payroll/generate") fail(409, "Payroll for this month is already prepared in the sample data");

  // ---- CEO alerts, CMS, settings
  if ((x = m(/^\/ceo\/alerts\/([^/]+)$/))) { const a = (S.shared["/ceo"]?.alerts || []).find((y) => y.id === x[1]); if (a) a.status = b.status; return { ok: true }; }
  if (path === "/cms/site" && method === "put") { const c = S.shared["/cms/site"]; c.draft = b.values; c.has_draft = true; c.draft_by = me().name; c.draft_at = nowIso(); return { ok: true }; }
  if (path === "/cms/publish") {
    const c = S.shared["/cms/site"];
    (S.shared["/cms/versions"] = S.shared["/cms/versions"] || []).unshift({ id: uid(), at: nowIso(), by: me().name, note: "Before publish" });
    c.live = { ...c.draft }; c.has_draft = false;
    Object.assign(S.public["/public/site"].settings, c.draft);
    return { ok: true };
  }
  if (path === "/cms/draft") { const c = S.shared["/cms/site"]; c.draft = { ...c.live }; c.has_draft = false; return { ok: true }; }
  if (path === "/cms/preview") return { ...(S.shared["/cms/site"]?.live || {}), ...(S.shared["/cms/site"]?.draft || {}) };
  if ((x = m(/^\/cms\/versions\/([^/]+)\/restore$/))) return { ok: true, message: "Loaded into the draft — check it and publish." };
  if (path === "/settings" && method === "put") { Object.assign(S.shared["/settings"], b); return S.shared["/settings"]; }
  if (path === "/settings/calc-constants" && method === "put") { const c = S.shared["/settings/calc-constants"]; c.overrides = b.values; c.reference = b.reference; c.effective_from = b.effective_from; return c; }

  // ---- vault
  if (path === "/vault/status") { staff(); return { ...(S.shared["/vault/status"] || { configured: true }), unlocked: !!S.vault, until: S.vault }; }
  if (path === "/vault/unlock") { if (b.password !== PW) fail(401, "That password is not right"); S.vault = Math.floor(Date.now() / 1000) + 900; return { ok: true, until: S.vault }; }
  if (path === "/vault/lock") { S.vault = null; return { ok: true }; }
  if (path === "/vault/items" && method === "get") { if (!S.vault) fail(423, "vault_locked"); const q = String(params.q || "").toLowerCase(); return coll("vault_items").filter((i) => !i.deleted && (!q || `${i.title} ${i.username}`.toLowerCase().includes(q))).map((i) => { const { secret, ...rest } = i; return { ...rest, category_label: (S.shared["/vault/meta"]?.categories || []).find((c) => c.key === i.category)?.label || "Other", rotate_due: false, can_edit: true }; }); }
  if (path === "/vault/items" && method === "post") { if (!S.vault) fail(423, "vault_locked"); const it = { id: uid(), title: b.title, preset: b.preset, category: (S.shared["/vault/meta"]?.presets || []).find((p) => p.key === b.preset)?.category || "other", url: b.url, username: b.username, has_password: !!b.password, has_totp: false, _pw: b.password, created_at: nowIso(), deleted: false }; coll("vault_items").push(it); return it; }
  if ((x = m(/^\/vault\/items\/([^/]+)\/reveal$/))) { if (!S.vault) fail(423, "vault_locked"); const it = coll("vault_items").find((i) => i.id === x[1]); return { value: it?._pw || `Sample-${(it?.id || "0000").slice(0, 4)}!` }; }
  if ((x = m(/^\/vault\/items\/([^/]+)\/code$/))) return { code: String(Math.floor(Math.random() * 1e6)).padStart(6, "0"), seconds_left: 30 - (Math.floor(Date.now() / 1000) % 30) };

  // ---- portals
  if (path === "/portal/summary") { need(); return portalSummary(); }
  if (path === "/portal/otp") return { sent_to: String(me().phone || "").slice(-4), status: "preview" };
  if ((x = m(/^\/portal\/approve\/([a-z_]+)\/([^/]+)$/))) {
    if (!/^\d{6}$/.test(String(b.otp || "")) || b.otp === "000000") fail(422, "That code didn't work or has expired. Ask for a new one.");
    const [, k, id] = x;
    const map = { drawings: { approve: "approved", approve_with_comments: "approved_with_comments", reject: "rejected" }, variations: { approve: "client_approved", reject: "client_rejected" }, proposals: { approve: "accepted", reject: "declined" }, snags: { approve: "verified", reject: "open" } };
    const st = map[k]?.[b.decision];
    if (!st) fail(422, "Choose approve or reject");
    if (b.decision !== "approve" && !String(b.comment || "").trim() && k === "drawings") fail(422, "Add your comments");
    setFields(k, id, { status: st, comments: b.comment || undefined, reviewed_by: `${me().name} (${me().role})` });
    audit(`portal_${b.decision}`, k, id, { comment: b.comment, otp: true });
    notifyRoles(["project_manager"], `Client ${b.decision.replace(/_/g, " ")}: ${coll(k).find((y) => y.id === id)?.code || ""}`, b.comment || "", `/erp/e/${k}/${id}`);
    return { ok: true, status: st };
  }
  if ((x = m(/^\/portal\/pay\/([^/]+)$/))) return recorded(`/finance/upi/${x[1]}`) || fail(409, "UPI is not set up yet");
  if (path === "/portal/payment-notice") { const r = createRecord("receipts", { account_id: me().account_id, date: b.date || today(), amount: Number(b.amount), mode: b.mode, reference: b.reference, allocations: [{ invoice_id: b.invoice_id, amount: Number(b.amount) }], notes: "Payment notice from the client portal" }, { system: true }); setFields("receipts", r.id, { status: "pending" }); notifyRoles(["accounts"], `Client says they paid ₹${Number(b.amount).toLocaleString("en-IN")}`, b.reference, `/erp/e/receipts/${r.id}`); return { ok: true, reference: r.code }; }
  if (path === "/portal/tickets") { if (!String(b.title || "").trim()) fail(422, "Describe the problem"); const t = createRecord("tickets", { account_id: me().account_id, channel: "portal", category: b.category || "breakdown", priority: b.priority || "normal", title: b.title, description: b.description, photos: b.photos || [], contact_name: me().name, contact_phone: me().phone }, { system: true }); notifyRoles(["service_manager"], `New service request: ${b.title}`, me().name, `/erp/e/tickets/${t.id}`); return { ok: true, reference: t.code, id: t.id }; }
  if ((x = m(/^\/portal\/tickets\/([^/]+)\/rate$/))) { setFields("tickets", x[1], { rating: b.rating, feedback: b.feedback, ...(b.reopen ? { status: "reopened" } : {}) }); return { ok: true }; }
  if (path === "/portal/requirement") return newLead({ ...b, form: "existing_client", name: me().name, phone: me().phone, company: coll("accounts").find((a) => a.id === me().account_id)?.name, consent: true }, "existing_client");
  if ((x = m(/^\/portal\/rfis\/([^/]+)\/answer$/))) { if (!String(b.answer || "").trim()) fail(422, "Write the answer"); setFields("rfis", x[1], { answer: b.answer, status: "answered", answered_on: today(), answered_by: me().name }); return { ok: true }; }
  if ((x = m(/^\/portal\/rfqs\/([^/]+)\/quote$/))) { const r = coll("rfqs").find((y) => y.id === x[1]); const lines = (r.lines || []).map((l, i) => ({ item_id: l.item_id, description: l.description, qty: l.qty, ...(b.lines?.[i] || {}) })); const q = createRecord("vendor_quotes", { rfq_id: r.id, vendor_id: me().vendor_id, lines, freight: b.freight, payment_terms: b.payment_terms, valid_until: b.valid_until }, { system: true }); notifyRoles(["purchase"], `Quote received for ${r.code}`, "", `/erp/e/rfqs/${r.id}`); return { ok: true, id: q.id, total: q.total }; }
  if (path === "/portal/vendor-bills") { const po = coll("purchase_orders").find((y) => y.id === b.po_id); if (!String(b.bill_no || "").trim()) fail(422, "Enter your bill number"); const vb = createRecord("vendor_bills", { vendor_id: me().vendor_id, po_id: po.id, project_id: po.project_id, bill_no: b.bill_no, bill_date: b.bill_date, lines: (po.lines || []).map((l) => ({ description: l.description, qty: l.received_qty || l.qty, rate: l.rate, gst_rate: l.gst_rate })), file: b.file }, { system: true }); notifyRoles(["accounts", "purchase"], `Vendor bill uploaded: ${b.bill_no}`, "", `/erp/e/vendor_bills/${vb.id}`); return { ok: true, reference: vb.code }; }
  if (path === "/portal/sc-bills") { const wo = coll("work_orders").find((y) => y.id === b.work_order_id); const lines = (b.lines || []).filter((l) => Number(l.this_qty) > 0).map((l) => ({ description: wo.lines[l.line].description, unit: wo.lines[l.line].unit, this_qty: Number(l.this_qty), rate: wo.lines[l.line].rate })); if (!lines.length) fail(422, "Enter the quantity done for at least one item"); const sb = createRecord("sc_bills", { work_order_id: wo.id, vendor_id: me().vendor_id, project_id: wo.project_id, period_to: b.period_to, lines, retention_pct: wo.retention_pct, tds_pct: wo.tds_pct }, { system: true }); notifyRoles(["project_manager"], `Subcontractor bill ${sb.code}`, "", `/erp/e/sc_bills/${sb.id}`); return { ok: true, reference: sb.code }; }
  if (path === "/portal/labour-attendance") return { ok: true, saved: (b.rows || []).length };
  if (path === "/portal/referrals") { if (!String(b.name || "").trim()) fail(422, "Enter the customer's name"); if (!b.consent) fail(422, "Confirm the customer agreed to be contacted"); return newLead({ ...b, form: "referral", partner_id: me().partner_id }, "referral"); }

  // ---- public website
  if (path === "/public/leads") { if (!b.consent) fail(422, "Please tick the consent box so we can contact you"); return newLead(b, LEAD_SOURCE[b.form] || "contact_form"); }
  if (path === "/public/survey-booking") {
    const r = newLead({ ...b, form: "survey_booking" }, "survey_booking");
    const eng = coll("users").find((u) => u.role === "sales");
    const s = createRecord("surveys", { lead_id: r.lead_id, scheduled_at: b.slot, survey_type: b.survey_type, address: b.address, engineer_id: eng?.id }, { system: true });
    setFields("leads", r.lead_id, { stage: "survey_scheduled" });
    return { ok: true, reference: r.reference, when: b.slot, engineer: eng?.name, ics: "#", survey: s.code };
  }
  if ((x = m(/^\/public\/calc\/([a-z-]+)\/lead$/))) { const r = newLead({ ...b, form: "calculator", calculator: { slug: x[1], inputs: b.inputs, want: b.want }, message: `Calculator: ${x[1].replace(/-/g, " ")}${b.want === "review" ? ". Wants an engineer to check this." : ""}` }, "calculator"); return { ok: true, reference: r.reference, pdf: `/api/public/calc-report/${x[1]}` }; }
  if ((x = m(/^\/public\/download\/([a-z0-9-]+)$/)) && method === "post") { newLead({ ...b, form: "download", message: `Downloaded: ${x[1]}` }, "download"); return { url: `/api/public/download/${x[1]}` }; }
  if (path === "/public/emergency") { const r = newLead({ ...b, form: "emergency", consent: true }, "emergency"); const t = createRecord("tickets", { channel: "website", category: "breakdown", priority: "urgent", title: `Breakdown: ${b.equipment || "electrical"} at ${b.town || b.company || b.name}`, description: b.message, contact_name: b.name, contact_phone: b.phone }, { system: true }); notifyRoles(["service_manager", "technician"], `Breakdown call: ${b.company || b.name}`, b.message || "", `/erp/e/tickets/${t.id}`); return { ok: true, reference: t.code, lead: r.reference }; }
  if (path === "/public/newsletter") { if (!b.consent) fail(422, "Please tick the box to agree to receive updates"); return { ok: true }; }
  if ((x = m(/^\/public\/careers\/([^/]+)\/apply$/))) { if (!b.consent) fail(422, "Please tick the consent box"); createRecord("job_applications", { job_id: x[1], name: b.name, phone: b.phone, email: b.email, experience_years: b.experience_years, current_role: b.current_role, cv: b.cv, message: b.message }, { system: true }); return { ok: true }; }
  if (path === "/public/vendor-registration") { if (!b.consent) fail(422, "Please tick the consent box"); createRecord("vendor_registrations", { company: b.company, vtype: b.vtype, trade: b.trade, gstin: b.gstin, contact_person: b.contact_person, phone: b.phone, email: b.email, town: b.town, documents: b.documents }, { system: true }); return { ok: true }; }
  if ((x = m(/^\/public\/asset\/([^/]+)\/request$/))) { const a = coll("installed_assets").find((y) => y.qr_token === x[1]); const t = createRecord("tickets", { account_id: a?.account_id, asset_id: a?.id, channel: "qr", category: "breakdown", priority: b.priority, title: `${a?.code}: ${String(b.issue).slice(0, 80)}`, description: b.issue, contact_name: b.name, contact_phone: b.phone }, { system: true }); return { ok: true, reference: t.code }; }
  if (path === "/public/projects" && Object.keys(params).length) return filterProjects(params);
  if (path === "/public/gallery" && params.category) return (recorded("/public/gallery") || []).filter((g) => g.category === params.category);
  if (path === "/public/insights" && params.tag) return (recorded("/public/insights") || []).filter((g) => (g.tags || []).includes(params.tag));
  if (path === "/public/assistant") return { answers: [], handover: true };

  // ---- recorded screens (CEO view, hub, finance, reports…) and the rest
  if (method === "get") {
    const own = screen(path);
    if (own !== undefined) return own;
    if (path === "/dashboard" || path === "/hr/me" || path === "/service/my-jobs") return path === "/hr/me" ? { employee: null } : path === "/service/my-jobs" ? { tickets: [], visits: [], accounts: {} } : { kpis: [], lists: [], approvals: [] };
    const r = recorded(path);
    if (r !== undefined) return params.fmt && params.fmt !== "json" ? r : r;
    if (path.startsWith("/public/")) fail(404, "Not found");
    if (m(/^\/projects\/[^/]+\/(hub|gantt|materials)$/)) return projectFallback(path);
    if (m(/^\/rfqs\/[^/]+\/comparison$/)) return { rfq: {}, rows: [], totals: [], vendors: {} };
    return {};
  }
  return { ok: true };
}

const LEAD_SOURCE = { quote_wizard: "quote_wizard", survey_booking: "survey_booking", calculator: "calculator", bill_review: "bill_review", tender_invite: "tender_invite", callback: "callback", emergency: "emergency", amc_enquiry: "amc_enquiry", download: "download", contact_form: "contact_form", product_enquiry: "product_enquiry", service_enquiry: "quote_wizard", sector_enquiry: "contact_form", similar_project: "quote_wizard" };

function filterProjects(params) {
  const all = recorded("/public/projects");
  let items = all.items;
  for (const k of ["sector", "service", "supply", "voltage", "year"]) if (params[k]) items = items.filter((p) => String(p[k]) === String(params[k]));
  if (params.town) items = items.filter((p) => String(p.town).toLowerCase() === String(params.town).toLowerCase());
  if (params.state === "ongoing") items = items.filter((p) => p.ongoing);
  if (params.state === "completed") items = items.filter((p) => !p.ongoing);
  if (params.limit) items = items.slice(0, Number(params.limit));
  return { items, facets: all.facets };
}
function projectFallback(path) {
  const id = path.split("/")[2];
  const p = coll("projects").find((x) => x.id === id);
  if (path.endsWith("/gantt")) return coll("milestones").filter((x) => x.project_id === id);
  if (path.endsWith("/materials")) return [];
  return { project: p, numbers: { contract_value: p?.contract_value || 0, percent_complete: p?.percent_complete || 0, earned_value: 0, billed: 0, received: 0, retention_held: 0, over_under_billed: 0 }, counts: {}, upcoming: coll("milestones").filter((x) => x.project_id === id), dprs: [], liaison: [], risks: [], s_curve: [] };
}

function portalSummary() {
  const base = screen("/portal/summary");
  if (!base) return {};
  const u = me();
  // keep the parts people change in the preview in step with the store
  if (u.role === "client") {
    const pids = new Set(coll("projects").filter((p) => p.account_id === u.account_id).map((p) => p.id));
    base.approvals = (base.approvals || []).filter((a) => { const d = coll(a.entity).find((y) => y.id === a.id); return d && ["submitted", "sent", "fixed"].includes(d.status); });
    base.tickets = coll("tickets").filter((t) => t.account_id === u.account_id && !["resolved", "closed"].includes(t.status) && !t.deleted);
    base.invoices_due = coll("invoices").filter((i) => i.account_id === u.account_id && ["issued", "part_paid"].includes(i.status));
    base.outstanding = base.invoices_due.reduce((a, i) => a + (Number(i.balance) || 0), 0);
    base.projects = base.projects.map((p) => coll("projects").find((y) => y.id === p.id) || p).filter((p) => pids.has(p.id));
  }
  if (u.role === "consultant") {
    base.drawings_to_review = (base.drawings_to_review || []).filter((d) => coll("drawings").find((y) => y.id === d.id)?.status === "submitted");
    base.rfis = (base.rfis || []).filter((d) => coll("rfis").find((y) => y.id === d.id)?.status === "open");
  }
  if (u.role === "vendor") base.bills = coll("vendor_bills").filter((v) => v.vendor_id === u.vendor_id && !v.deleted);
  if (u.role === "subcontractor") base.bills = coll("sc_bills").filter((v) => v.vendor_id === u.vendor_id && !v.deleted);
  if (u.role === "partner") {
    const pct = base.partner?.commission_pct || 0;
    base.referrals = coll("leads").filter((l) => l.partner_id === u.partner_id && !l.deleted).map((l) => ({ code: l.code, name: l.name, company: l.company, service: l.service, status: l.stage === "won" ? "Won" : l.stage === "lost" ? "Closed" : "In progress", created_at: String(l.created_at).slice(0, 10), commission: l.stage === "won" ? Math.round((Number(l.value) || 0) * pct / 100) : 0 }));
    base.commission_total = base.referrals.reduce((a, r) => a + r.commission, 0);
  }
  return base;
}

// A tiny stand-in QR (the real server draws a scannable one)
const QR_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 29 29" shape-rendering="crispEdges"><rect width="29" height="29" fill="#fff"/><path fill="#0A1626" d="M2 2h7v7H2zM3 3v5h5V3zM4 4h3v3H4zM20 2h7v7h-7zM21 3v5h5V3zM22 4h3v3h-3zM2 20h7v7H2zM3 21v5h5v-5zM4 22h3v3H4zM11 2h2v2h-2zM14 4h2v2h-2zM11 7h3v2h-3zM16 9h2v3h-2zM11 11h3v2h-3zM2 11h3v2H2zM7 13h2v2H7zM20 11h2v2h-2zM24 13h3v2h-3zM13 15h3v3h-3zM18 16h2v2h-2zM11 20h2v3h-2zM15 21h3v2h-3zM20 20h3v3h-3zM24 18h3v2h-3zM14 25h2v2h-2zM19 24h2v3h-2zM24 23h3v4h-3z"/></svg>`;

// ------------------------------------------------------------------ axios adapter
export async function demoAdapter(config) {
  const url = new URL(config.url, "http://x");
  const path = url.pathname.replace(/^\/api/, "");
  const params = { ...Object.fromEntries(url.searchParams.entries()), ...(config.params || {}) };
  for (const k of Object.keys(params)) if (params[k] === undefined) delete params[k];
  const method = (config.method || "get").toLowerCase();
  await delay(method === "get" ? 60 : 180);
  try {
    const data = await route(method, path, params, body(config), config);
    return { data: JSON.parse(JSON.stringify(data ?? {})), status: 200, statusText: "OK", headers: {}, config, request: {} };
  } catch (e) {
    if (!(e instanceof HttpError)) { console.error("[preview]", method, path, e); }
    const status = e instanceof HttpError ? e.status : 500;
    const response = { data: { detail: e instanceof HttpError ? e.detail : "Something went wrong in the preview." }, status, statusText: "Error", headers: {}, config, request: {} };
    throw new AxiosError(response.data.detail, status >= 500 ? AxiosError.ERR_BAD_RESPONSE : AxiosError.ERR_BAD_REQUEST, config, {}, response);
  }
}
export { metaFor, can, today };
