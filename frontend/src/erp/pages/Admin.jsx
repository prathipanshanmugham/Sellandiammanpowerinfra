import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Trash2, Save, Copy, ShieldCheck, ShieldAlert, Eye, Upload, RotateCcw, History, Link2, KeyRound, Search, CheckCircle2, XCircle } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { fmtDateTime, ago, inr } from "@/lib/format";
import { Button, Badge, Skeleton, Input, Textarea, Select, Field, Switch, Tabs, TabPanel, Alert, Dialog, Sheet, Checkbox, Empty } from "@/components/ui/kit";
import { toast } from "sonner";
import { useApi, useInvalidate } from "../lib";
import { RefPicker } from "../fields";
import { PageHead, Panel, Table, usePageTitle } from "../ui";

// ------------------------------------------------------------------ company settings
export function SettingsPage() {
  const { meta, can } = useAuth();
  const { data, isLoading, refetch } = useApi("/settings");
  const [v, setV] = useState(null);
  const [tab, setTab] = useState("company");
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (data) setV(JSON.parse(JSON.stringify(data))); }, [data]);
  usePageTitle("Company settings");
  if (isLoading || !v) return <Skeleton className="h-96" />;
  const set = (k) => (x) => setV((s) => ({ ...s, [k]: x?.target ? x.target.value : x }));
  const writable = can("settings", "w");
  async function save() {
    setBusy(true);
    try {
      const body = { ...v };
      delete body.integrations; delete body.roles;
      body.fy_start_month = Number(body.fy_start_month); body.first_response_minutes = Number(body.first_response_minutes); body.geofence_m = Number(body.geofence_m);
      await api.put("/settings", body); toast.success("Settings saved"); refetch();
    } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(false); }
  }
  const docs = Object.entries(meta.entities).filter(([, e]) => e.approval).map(([k, e]) => ({ value: k, label: e.plural }));
  const roles = (v.roles || meta.roles).filter((r) => !["client", "consultant", "vendor", "subcontractor", "partner"].includes(r.value));
  return (
    <div className="pb-10">
      <PageHead icon="cog" title="Company settings" actions={writable && <Button size="sm" loading={busy} onClick={save}><Save className="h-4 w-4" />Save changes</Button>} />
      <Tabs value={tab} onValueChange={setTab} tabs={[{ value: "company", label: "Company & numbering" }, { value: "approvals", label: "Approval limits" }, { value: "routing", label: "Lead routing" }, { value: "calc", label: "Calculator rates" }, { value: "integrations", label: "Connections" }]}>
        <TabPanel value="company">
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Numbering">
              <div className="space-y-3">
                <Field label="Company code" hint="First part of every document number"><Input value={v.company_code || ""} onChange={set("company_code")} /></Field>
                <Field label="Number format" hint={`{co} company, {br} branch, {doc} type, {fy} financial year, {seq} running number. Example: ${(v.number_format || "").replace("{co}", v.company_code || "SPI").replace("{br}", "PDR").replace("{doc}", "INV").replace("{fy}", "26-27").replace("{seq}", "0042")}`}>
                  <Input value={v.number_format || ""} onChange={set("number_format")} className="font-mono" /></Field>
                <Field label="Financial year starts in month"><Select value={String(v.fy_start_month)} onChange={set("fy_start_month")} options={["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"].map((m, i) => ({ value: String(i + 1), label: m }))} /></Field>
              </div>
            </Panel>
            <Panel title="Leads and attendance">
              <div className="space-y-3">
                <Field label="First reply target for new leads (working minutes)"><Input inputMode="numeric" value={v.first_response_minutes ?? ""} onChange={set("first_response_minutes")} /></Field>
                <Field label="Shown on the website as"><Input value={v.first_response_text || ""} onChange={set("first_response_text")} /></Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Working day starts"><Input type="time" value={v.working_hours?.start || ""} onChange={(e) => setV((s) => ({ ...s, working_hours: { ...s.working_hours, start: e.target.value } }))} /></Field>
                  <Field label="ends"><Input type="time" value={v.working_hours?.end || ""} onChange={(e) => setV((s) => ({ ...s, working_hours: { ...s.working_hours, end: e.target.value } }))} /></Field>
                </div>
                <Field label="Check-in allowed within (metres of the site or office)"><Input inputMode="numeric" value={v.geofence_m ?? ""} onChange={set("geofence_m")} /></Field>
              </div>
            </Panel>
            <Panel title="Collections">
              <div className="space-y-3">
                <Field label="UPI ID for the payment QR on invoices"><Input value={v.upi_id || ""} onChange={set("upi_id")} placeholder="name@bank" /></Field>
                <Field label="Bank details printed on invoices"><Textarea value={v.bank_details || ""} onChange={set("bank_details")} rows={2} /></Field>
                <Field label="Company name in Tally"><Input value={v.tally_company || ""} onChange={set("tally_company")} /></Field>
              </div>
            </Panel>
            <Panel title="Security and payroll">
              <div className="space-y-3">
                <Field label="Roles that must use 2-step sign-in">
                  <div className="flex flex-wrap gap-1.5">{roles.map((r) => { const on = (v.mfa_required_roles || []).includes(r.value); return <button key={r.value} type="button" onClick={() => setV((s) => ({ ...s, mfa_required_roles: on ? s.mfa_required_roles.filter((x) => x !== r.value) : [...(s.mfa_required_roles || []), r.value] }))} aria-pressed={on} className={cn("rounded px-2 py-1 text-xs", on ? "bg-ink text-white" : "bg-canvas text-fg/85")}>{r.label}</button>; })}</div>
                </Field>
                <Field label="Payroll deductions">
                  <div className="flex flex-wrap gap-4">{["pf", "esi", "pt", "tds"].map((k) => <Switch key={k} checked={!!v.payroll_statutory?.[k]} onChange={(x) => setV((s) => ({ ...s, payroll_statutory: { ...s.payroll_statutory, [k]: x } }))} label={k.toUpperCase()} />)}</div>
                </Field>
                <Switch checked={!!v.email_notifications} onChange={set("email_notifications")} label="Send notifications by email too" />
              </div>
            </Panel>
          </div>
        </TabPanel>
        <TabPanel value="approvals">
          <Panel title="Who approves what" sub="Rules are checked top to bottom; the first one that matches the document and amount applies. No rule means it's approved automatically. Nobody can approve their own request." bodyClass="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-[14px]">
                <thead className="border-b border-edge text-left text-xs text-muted"><tr><th className="px-3 py-2 font-medium">Document</th><th className="px-3 py-2 font-medium">Up to (₹)</th><th className="px-3 py-2 font-medium">Condition</th><th className="px-3 py-2 font-medium">Any of these roles</th><th /></tr></thead>
                <tbody className="divide-y divide-edge">
                  {(v.approval_rules || []).map((r, i) => (
                    <tr key={i} className="align-top">
                      <td className="px-3 py-2"><Select value={r.doc} onChange={(e) => setV((s) => ({ ...s, approval_rules: s.approval_rules.map((x, j) => (j === i ? { ...x, doc: e.target.value } : x)) }))} options={docs} className="h-9 w-48" /></td>
                      <td className="px-3 py-2"><Input value={r.up_to ?? ""} placeholder="No limit" inputMode="numeric" onChange={(e) => setV((s) => ({ ...s, approval_rules: s.approval_rules.map((x, j) => (j === i ? { ...x, up_to: e.target.value === "" ? null : Number(e.target.value.replace(/\D/g, "")) } : x)) }))} className="h-9 w-32 tabular" /></td>
                      <td className="px-3 py-2"><Input value={r.when || ""} placeholder="e.g. discount_pct > 5" onChange={(e) => setV((s) => ({ ...s, approval_rules: s.approval_rules.map((x, j) => (j === i ? { ...x, when: e.target.value } : x)) }))} className="h-9 w-52 font-mono text-xs" /></td>
                      <td className="px-3 py-2"><div className="flex max-w-md flex-wrap gap-1">{roles.filter((x) => !["employee", "auditor"].includes(x.value)).map((ro) => { const on = r.roles.includes(ro.value); return <button key={ro.value} type="button" onClick={() => setV((s) => ({ ...s, approval_rules: s.approval_rules.map((x, j) => (j === i ? { ...x, roles: on ? x.roles.filter((y) => y !== ro.value) : [...x.roles, ro.value] } : x)) }))} className={cn("rounded px-1.5 py-0.5 text-[12px]", on ? "bg-ink text-white" : "bg-canvas text-muted")}>{ro.label.split(" (")[0]}</button>; })}</div></td>
                      <td className="px-3 py-2"><button type="button" onClick={() => setV((s) => ({ ...s, approval_rules: s.approval_rules.filter((_, j) => j !== i) }))} className="rounded p-1.5 text-muted hover:bg-bad/10 hover:text-bad" aria-label="Remove rule"><Trash2 className="h-4 w-4" /></button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="border-t border-edge p-3"><Button size="sm" variant="outline" onClick={() => setV((s) => ({ ...s, approval_rules: [...(s.approval_rules || []), { doc: docs[0]?.value, up_to: null, roles: ["director"] }] }))}><Plus className="h-4 w-4" />Add a rule</Button></div>
          </Panel>
        </TabPanel>
        <TabPanel value="routing"><Routing /></TabPanel>
        <TabPanel value="calc"><CalcConstants /></TabPanel>
        <TabPanel value="integrations">
          <Panel title="Connections" sub="Set in the server's environment file; see the deployment guide.">
            <ul className="grid gap-2 sm:grid-cols-2">
              {Object.entries({ email: "Email (SMTP)", whatsapp: "WhatsApp Business messages", turnstile: "Spam protection on forms (Cloudflare Turnstile)", lead_webhooks: "Lead webhooks (IndiaMART, JustDial, Meta and Google ads)", vault: "Password vault encryption key", ga4: "Google Analytics" }).map(([k, l]) => (
                <li key={k} className="flex items-center gap-2.5 rounded-lg border border-edge px-3 py-2.5 text-sm">{v.integrations?.[k] ? <CheckCircle2 className="h-4 w-4 text-good" /> : <XCircle className="h-4 w-4 text-muted" />}{l}<span className="ml-auto text-xs text-muted">{v.integrations?.[k] ? "Connected" : "Not set"}</span></li>
              ))}
            </ul>
          </Panel>
        </TabPanel>
      </Tabs>
    </div>
  );
}

function Routing() {
  const { data, refetch } = useApi("/crm/routing");
  const [rules, setRules] = useState(null);
  const [refs, setRefs] = useState({ users: {}, branches: {} });
  const { data: br } = useApi("/branches/all");
  const { data: users } = useApi("/users/lookup");
  useEffect(() => { if (data) setRules(JSON.parse(JSON.stringify(data.rules || []))); }, [data]);
  useEffect(() => { if (users) setRefs((r) => ({ ...r, users: Object.fromEntries(users.map((u) => [u.id, u.name])) })); }, [users]);
  if (!rules) return <Skeleton className="h-40" />;
  async function save() { try { await api.put("/crm/routing", { rules }); toast.success("Routing saved"); refetch(); } catch (ex) { toast.error(errMsg(ex)); } }
  return (
    <Panel title="Where new leads go" sub="By the town on the enquiry. Within a team, leads go round-robin. Unmatched leads go to the head office sales team." actions={<Button size="sm" onClick={save}><Save className="h-4 w-4" />Save routing</Button>}>
      <div className="space-y-3">
        {rules.map((r, i) => (
          <div key={i} className="grid gap-3 rounded-lg border border-edge p-3 md:grid-cols-[1fr_1.4fr_1fr_1.4fr_auto]">
            <Field label="Name"><Input value={r.name} onChange={(e) => setRules(rules.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} /></Field>
            <Field label="Towns (comma separated)"><Input value={(r.towns || []).join(", ")} onChange={(e) => setRules(rules.map((x, j) => (j === i ? { ...x, towns: e.target.value.split(",").map((t) => t.trim()).filter(Boolean) } : x)))} /></Field>
            <Field label="Branch"><Select value={r.branch_id || ""} onChange={(e) => setRules(rules.map((x, j) => (j === i ? { ...x, branch_id: e.target.value } : x)))} options={(br || []).map((b) => ({ value: b.id, label: b.name }))} /></Field>
            <Field label="Team">
              <div className="flex flex-wrap gap-1">{(r.team || []).map((u) => <Badge key={u} tone="blue">{refs.users[u] || "…"}<button type="button" onClick={() => setRules(rules.map((x, j) => (j === i ? { ...x, team: x.team.filter((y) => y !== u) } : x)))} aria-label="Remove">×</button></Badge>)}</div>
              <RefPicker f={{ ref: "users" }} value={null} onChange={(u) => u && setRules(rules.map((x, j) => (j === i ? { ...x, team: [...new Set([...(x.team || []), u])] } : x)))} refs={refs} onRefTitle={(e, id, t) => setRefs((s) => ({ ...s, users: { ...s.users, [id]: t } }))} placeholder="Add a person" className="mt-1 h-9" />
            </Field>
            <button type="button" onClick={() => setRules(rules.filter((_, j) => j !== i))} className="self-end rounded p-2 text-muted hover:bg-bad/10 hover:text-bad" aria-label="Remove"><Trash2 className="h-4 w-4" /></button>
          </div>
        ))}
        <Button size="sm" variant="outline" onClick={() => setRules([...rules, { name: "New area", towns: [], branch_id: br?.[0]?.id, team: [] }])}><Plus className="h-4 w-4" />Add an area</Button>
      </div>
    </Panel>
  );
}

function CalcConstants() {
  const { data, refetch } = useApi("/settings/calc-constants");
  const [text, setText] = useState("");
  const [ref, setRef] = useState("");
  const [from, setFrom] = useState("");
  useEffect(() => { if (data) { setText(JSON.stringify(data.overrides || {}, null, 2)); setRef(data.reference || ""); setFrom(data.effective_from || ""); } }, [data]);
  if (!data) return <Skeleton className="h-40" />;
  const t = data.merged.tariffs || {};
  async function save() {
    let values;
    try { values = JSON.parse(text || "{}"); } catch { toast.error("That isn't valid JSON"); return; }
    try { await api.put("/settings/calc-constants", { values, reference: ref, effective_from: from }); toast.success("Rates saved; every calculator checked"); refetch(); } catch (ex) { toast.error(errMsg(ex)); }
  }
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
      <Panel title="Tariffs in use" sub={`Rates as of ${data.merged.rates_as_of}`} bodyClass="p-0">
        <Table dense columns={[{ label: "Tariff", render: (r) => r.label }, { label: "Energy ₹/kWh", right: true, render: (r) => r.energy ?? r.energy_rate ?? "—" }, { label: "Demand / fixed", right: true, render: (r) => (r.demand ? `₹${r.demand}/kVA` : r.fixed_slabs ? `₹${r.fixed_slabs[0][1]}–${r.fixed_slabs[r.fixed_slabs.length - 1][1]}/kW` : "—") }]}
          rows={Object.entries(t).map(([k, x]) => ({ id: k, ...x }))} />
      </Panel>
      <Panel title="Change rates" sub="Enter only the values that differ from the bundled defaults (TNERC order). Saving runs every calculator to check nothing breaks." actions={<Button size="sm" onClick={save}><Save className="h-4 w-4" />Save</Button>}>
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Tariff order / reference"><Input value={ref} onChange={(e) => setRef(e.target.value)} placeholder="e.g. TNERC T.O. No. 6 of 2025" /></Field>
            <Field label="Effective from"><Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></Field>
          </div>
          <Field label="Overrides (JSON)"><Textarea value={text} onChange={(e) => setText(e.target.value)} rows={12} className="font-mono text-xs" /></Field>
          {data.history?.length > 0 && <p className="text-xs text-muted">Last changed {ago(data.history[0].at)} by {data.history[0].by}</p>}
        </div>
      </Panel>
    </div>
  );
}

// ------------------------------------------------------------------ users
const LINK = { client: ["account_id", "accounts", "Client"], consultant: ["contact_id", "contacts", "Contact"], vendor: ["vendor_id", "vendors", "Vendor"], subcontractor: ["vendor_id", "vendors", "Subcontractor"], partner: ["partner_id", "partners", "Referral partner"] };
export function UsersPage() {
  const { can, user: me } = useAuth();
  const [q, setQ] = useState("");
  const [portal, setPortal] = useState("staff");
  const { data, isLoading, refetch } = useApi("/users", { portal: portal === "portal" });
  const { data: roles } = useApi("/roles");
  const { data: br } = useApi("/branches/all");
  const [edit, setEdit] = useState(null);
  const [link, setLink] = useState(null);
  usePageTitle("Users & roles");
  const rows = (data || []).filter((u) => !q || `${u.name} ${u.email}`.toLowerCase().includes(q.toLowerCase()));
  const brName = Object.fromEntries((br || []).map((b) => [b.id, b.name]));
  return (
    <div className="pb-10">
      <PageHead icon="users-round" title="Users & roles" sub="Staff logins and client, vendor and partner portal logins. A new login gets a 7-day link to set a password."
        actions={can("users", "w") && <Button size="sm" onClick={() => setEdit({ role: portal === "portal" ? "client" : "employee", branch_ids: [], active: true })}><Plus className="h-4 w-4" />Add a login</Button>} />
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="flex rounded-md border border-edge bg-surface p-0.5">{[["staff", "Staff"], ["portal", "Portal logins"]].map(([k, l]) => <button key={k} type="button" onClick={() => setPortal(k)} className={cn("rounded px-3 py-1.5 text-sm", portal === k ? "bg-ink text-white" : "text-muted")}>{l}</button>)}</div>
        <label className="relative"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" /><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search" className="h-9 w-56 pl-9" /></label>
      </div>
      {isLoading ? <Skeleton className="h-64" /> : (
        <div className="overflow-hidden rounded-xl border border-edge bg-surface">
          <Table columns={[
            { label: "Name", render: (u) => <span><span className="block font-medium">{u.name}</span><span className="text-xs text-muted">{u.email}</span></span> },
            { label: "Role", render: (u) => u.role_label },
            { label: "Branches", render: (u) => (u.branch_ids?.length ? u.branch_ids.map((b) => brName[b] || "…").join(", ") : <span className="text-muted">All</span>) },
            { label: "2-step", render: (u) => (u.mfa_enabled ? <Badge tone="green">On</Badge> : <span className="text-muted">Off</span>) },
            { label: "Last sign-in", render: (u) => (u.last_login ? ago(u.last_login) : <span className="text-muted">Never</span>) },
            { label: "", render: (u) => <Badge tone={u.active ? "gray" : "red"}>{u.active ? "Active" : "Off"}</Badge> },
          ]} rows={rows} onRow={can("users", "w") ? (u) => setEdit(u) : undefined} />
        </div>
      )}
      {edit && <UserSheet u={edit} roles={roles?.roles || []} branches={br || []} me={me} onClose={() => setEdit(null)} onSaved={(r) => { setEdit(null); refetch(); if (r?.set_password_link) setLink(r.set_password_link); }} onLink={setLink} />}
      <Dialog open={!!link} onOpenChange={(x) => !x && setLink(null)} title="Set-password link" description="Valid for 7 days. It has also been emailed if email is set up.">
        <div className="flex gap-2"><Input readOnly value={link || ""} className="font-mono text-xs" /><Button variant="outline" onClick={() => { navigator.clipboard?.writeText(link); toast.success("Copied"); }}><Copy className="h-4 w-4" /></Button></div>
      </Dialog>
    </div>
  );
}

function UserSheet({ u, roles, branches, onClose, onSaved, onLink, me }) {
  const [v, setV] = useState({ ...u });
  const [refs, setRefs] = useState({});
  const [busy, setBusy] = useState(false);
  const isNew = !u.id;
  const lk = LINK[v.role];
  async function save() {
    setBusy(true);
    try {
      const body = { name: v.name, email: v.email, role: v.role, phone: v.phone, branch_ids: v.branch_ids || [], designation: v.designation, active: v.active, ...(lk ? { [lk[0]]: v[lk[0]] } : {}) };
      const r = isNew ? (await api.post("/users", body)).data : (await api.patch(`/users/${u.id}`, body)).data;
      toast.success(isNew ? "Login added" : "Saved");
      onSaved(r);
    } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(false); }
  }
  return (
    <Sheet open onOpenChange={(x) => !x && onClose()} title={isNew ? "Add a login" : v.name} description={!isNew ? v.email : undefined}
      footer={<><Button variant="outline" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={save}>{isNew ? "Add and create link" : "Save"}</Button></>}>
      <div className="space-y-3">
        <Field label="Name" required><Input value={v.name || ""} onChange={(e) => setV((s) => ({ ...s, name: e.target.value }))} /></Field>
        <Field label="Email" required><Input type="email" value={v.email || ""} disabled={!isNew} onChange={(e) => setV((s) => ({ ...s, email: e.target.value }))} /></Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Role"><Select value={v.role} onChange={(e) => setV((s) => ({ ...s, role: e.target.value }))} options={roles.filter((r) => r.value !== "super_admin" || me.role === "super_admin")} /></Field>
          <Field label="Phone"><Input value={v.phone || ""} onChange={(e) => setV((s) => ({ ...s, phone: e.target.value }))} /></Field>
        </div>
        {lk ? <Field label={`Linked ${lk[2].toLowerCase()}`} required hint="The portal shows only this record's projects, bills and requests"><RefPicker f={{ ref: lk[1] }} value={v[lk[0]] || null} onChange={(x) => setV((s) => ({ ...s, [lk[0]]: x }))} refs={refs} onRefTitle={(e, id, t) => setRefs((r) => ({ ...r, [e]: { ...(r[e] || {}), [id]: t } }))} /></Field> : (
          <>
            <Field label="Designation"><Input value={v.designation || ""} onChange={(e) => setV((s) => ({ ...s, designation: e.target.value }))} /></Field>
            <Field label="Branches" hint="None ticked means all branches (only for directors and auditors)">
              <div className="space-y-1.5">{branches.map((b) => <Checkbox key={b.id} checked={(v.branch_ids || []).includes(b.id)} onChange={(x) => setV((s) => ({ ...s, branch_ids: x ? [...(s.branch_ids || []), b.id] : s.branch_ids.filter((y) => y !== b.id) }))} label={b.name} />)}</div>
            </Field>
          </>
        )}
        <Switch checked={v.active !== false} onChange={(x) => setV((s) => ({ ...s, active: x }))} label={v.active !== false ? "Login active" : "Login switched off"} />
        {!isNew && (
          <div className="flex flex-wrap gap-2 border-t border-edge pt-3">
            <Button size="sm" variant="outline" onClick={async () => { try { onLink((await api.post(`/users/${u.id}/link`)).data.set_password_link); } catch (ex) { toast.error(errMsg(ex)); } }}><Link2 className="h-4 w-4" />New set-password link</Button>
            {u.mfa_enabled && <Button size="sm" variant="outline" onClick={async () => { try { await api.post(`/users/${u.id}/reset-mfa`); toast.success("2-step sign-in reset"); } catch (ex) { toast.error(errMsg(ex)); } }}><KeyRound className="h-4 w-4" />Reset 2-step sign-in</Button>}
          </div>
        )}
      </div>
    </Sheet>
  );
}

// ------------------------------------------------------------------ activity log
export function AuditPage() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const { data, isLoading } = useApi("/audit", { q: q || undefined, page });
  const [check, setCheck] = useState(null);
  usePageTitle("Activity log");
  return (
    <div className="pb-10">
      <PageHead icon="list-checks" title="Activity log" sub="Every add, change, delete, approval, sign-in and export. Each entry carries a fingerprint of the one before it, so a changed or removed entry shows up."
        actions={<Button size="sm" variant="outline" onClick={async () => { try { setCheck((await api.get("/audit/verify")).data); } catch (ex) { toast.error(errMsg(ex)); } }}><ShieldCheck className="h-4 w-4" />Check the chain</Button>} />
      {check && <Alert tone={check.ok ? "green" : "red"} icon={check.ok ? ShieldCheck : ShieldAlert} className="mb-3" title={check.ok ? "The log is intact" : `The chain breaks at entry ${check.broken_at}`}>{check.entries} entries checked.</Alert>}
      <div className="mb-3"><label className="relative"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" /><Input value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} placeholder="Person, action or document number" className="h-9 w-72 pl-9" /></label></div>
      {isLoading ? <Skeleton className="h-64" /> : (
        <div className="overflow-hidden rounded-xl border border-edge bg-surface">
          <Table dense columns={[
            { label: "#", key: "seq", className: "tabular text-muted" }, { label: "When", render: (r) => <span className="whitespace-nowrap tabular">{fmtDateTime(r.at)}</span> },
            { label: "Who", render: (r) => <span>{r.user_name}<span className="block text-xs text-muted">{r.role}</span></span> },
            { label: "Action", render: (r) => r.action.replace(/_/g, " ") },
            { label: "Record", render: (r) => (r.entity && r.entity_id && !["users", "settings", "alerts"].includes(r.entity) ? <Link to={`/erp/e/${r.entity}/${r.entity_id}`} className="hover:underline">{r.details?.code || r.details?.title || r.entity}</Link> : r.details?.code || r.entity || "—") },
            { label: "IP", key: "ip", className: "text-xs text-muted tabular" },
          ]} rows={data.items} />
          <div className="flex items-center justify-end gap-2 border-t border-edge px-3 py-2 text-sm"><span className="text-muted">{data.total} entries</span>
            <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>Newer</Button><Button size="sm" variant="outline" disabled={page * 100 >= data.total} onClick={() => setPage(page + 1)}>Older</Button></div>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ website editor
const LIST_FIELDS = { trust: [["value", "Number"], ["label", "What it means"]], process: [["step", "Step"], ["text", "Description"]], values: [["title", "Title"], ["text", "Text"]], group_companies: [["name", "Name"], ["text", "What they do"], ["url", "Website"]] };
export function WebsiteEditor() {
  const { can } = useAuth();
  const { data, isLoading, refetch } = useApi("/cms/site");
  const { data: versions, refetch: rv } = useApi("/cms/versions");
  const [v, setV] = useState(null);
  const [busy, setBusy] = useState("");
  useEffect(() => { if (data) setV(JSON.parse(JSON.stringify(data.draft))); }, [data]);
  usePageTitle("Website editor");
  if (isLoading || !v) return <Skeleton className="h-96" />;
  const set = (k, sub) => (e) => { const x = e?.target ? (e.target.type === "checkbox" ? e.target.checked : e.target.value) : e; setV((s) => (sub ? { ...s, [k]: { ...(s[k] || {}), [sub]: x } } : { ...s, [k]: x })); };
  const dirty = JSON.stringify(v) !== JSON.stringify(data.draft);
  async function saveDraft() { setBusy("save"); try { await api.put("/cms/site", { values: v }); toast.success("Draft saved"); refetch(); } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(""); } }
  async function publish() { setBusy("pub"); try { if (dirty) await api.put("/cms/site", { values: v }); await api.post("/cms/publish"); toast.success("Published to the website"); refetch(); rv(); } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(""); } }
  const ListEditor = ({ k }) => (
    <div className="space-y-2">
      {(v[k] || []).map((row, i) => (
        <div key={i} className="flex gap-2">
          {LIST_FIELDS[k].map(([f, l]) => <Input key={f} value={row[f] || ""} placeholder={l} aria-label={l} onChange={(e) => setV((s) => ({ ...s, [k]: s[k].map((x, j) => (j === i ? { ...x, [f]: e.target.value } : x)) }))} className={f === "text" ? "flex-[2]" : "flex-1"} />)}
          <button type="button" onClick={() => setV((s) => ({ ...s, [k]: s[k].filter((_, j) => j !== i) }))} className="rounded p-2 text-muted hover:text-bad" aria-label="Remove"><Trash2 className="h-4 w-4" /></button>
        </div>
      ))}
      <Button size="sm" variant="outline" onClick={() => setV((s) => ({ ...s, [k]: [...(s[k] || []), {}] }))}><Plus className="h-4 w-4" />Add</Button>
    </div>
  );
  return (
    <div className="pb-10">
      <PageHead icon="newspaper" title="Website editor" sub={data.has_draft ? `Unpublished draft saved ${ago(data.draft_at)} by ${data.draft_by}` : "Changes are saved as a draft. Preview, then publish. The last 15 versions are kept."}
        actions={<>
          <Button size="sm" variant="outline" as="a" href="/?preview=1" target="_blank" rel="noreferrer"><Eye className="h-4 w-4" />Preview</Button>
          {can("cms", "w") && <Button size="sm" variant="outline" loading={busy === "save"} disabled={!dirty} onClick={saveDraft}><Save className="h-4 w-4" />Save draft</Button>}
          {can("cms", "p") && <Button size="sm" loading={busy === "pub"} disabled={!dirty && !data.has_draft} onClick={publish}><Upload className="h-4 w-4" />Publish</Button>}
        </>} />
      <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          <Panel title="Announcement bar">
            <div className="grid gap-3 sm:grid-cols-[1fr_200px_auto] sm:items-end">
              <Field label="Text"><Input value={v.announcement?.text || ""} onChange={set("announcement", "text")} /></Field>
              <Field label="Link (optional)"><Input value={v.announcement?.link || ""} onChange={set("announcement", "link")} placeholder="/amc" /></Field>
              <Switch checked={!!v.announcement?.active} onChange={set("announcement", "active")} label="Show" />
            </div>
          </Panel>
          <Panel title="Home page hero">
            <div className="space-y-3">
              <Field label="Small line above the title"><Input value={v.hero?.eyebrow || ""} onChange={set("hero", "eyebrow")} /></Field>
              <Field label="Title"><Input value={v.hero?.title || ""} onChange={set("hero", "title")} /></Field>
              <Field label="Text"><Textarea value={v.hero?.text || ""} onChange={set("hero", "text")} rows={3} /></Field>
            </div>
          </Panel>
          <Panel title="Numbers under the hero" sub="Only facts you can stand behind"><ListEditor k="trust" /></Panel>
          <Panel title="Contact details">
            <div className="grid gap-3 sm:grid-cols-2">
              {[["phone", "Phone"], ["whatsapp", "WhatsApp"], ["emergency_phone", "24×7 breakdown line"], ["email", "Email"], ["gstin", "GSTIN"], ["elb_licence", "Electrical contractor licence"]].map(([k, l]) => <Field key={k} label={l}><Input value={v[k] || ""} onChange={set(k)} /></Field>)}
              <Field label="Address" className="sm:col-span-2"><Textarea value={v.address || ""} onChange={set("address")} rows={2} /></Field>
            </div>
          </Panel>
          <Panel title="About us">
            <div className="space-y-3">
              <Field label="Our story"><Textarea value={v.about?.story || ""} onChange={set("about", "story")} rows={5} /></Field>
              <Field label="Mission"><Textarea value={v.about?.mission || ""} onChange={set("about", "mission")} rows={2} /></Field>
              <Field label="How we work"><ListEditor k="values" /></Field>
              <Field label="Group companies"><ListEditor k="group_companies" /></Field>
            </div>
          </Panel>
          <Panel title="How a project runs"><ListEditor k="process" /></Panel>
        </div>
        <div className="space-y-4">
          <Panel title="Pages and content" bodyClass="p-0">
            <ul className="divide-y divide-edge text-sm">
              {[["services", "Services"], ["products", "Products"], ["industries", "Industries"], ["projects?publish=true", "Published projects"], ["testimonials", "Testimonials"], ["gallery", "Gallery"], ["insights", "Insights (blog)"], ["faqs", "FAQs"], ["downloads", "Guides & downloads"], ["jobs", "Job openings"], ["town_pages", "Town pages"]].map(([k, l]) => (
                <li key={k}><Link to={`/erp/e/${k}`} className="block px-4 py-2.5 hover:bg-canvas">{l}</Link></li>
              ))}
            </ul>
          </Panel>
          <Panel title="Earlier versions" bodyClass="p-0">
            {!versions?.length ? <p className="px-4 py-4 text-sm text-muted">No earlier versions yet</p> : (
              <ul className="divide-y divide-edge">
                {versions.map((x) => (
                  <li key={x.id} className="flex items-center justify-between gap-2 px-4 py-2.5 text-sm"><span><span className="block">{fmtDateTime(x.at)}</span><span className="text-xs text-muted">{x.by}</span></span>
                    {can("cms", "p") && <Button size="sm" variant="ghost" onClick={async () => { try { const r = await api.post(`/cms/versions/${x.id}/restore`); toast.success(r.data.message); refetch(); } catch (ex) { toast.error(errMsg(ex)); } }}><RotateCcw className="h-3.5 w-3.5" />Load</Button>}</li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}

export { History, Empty, inr, useMemo };
