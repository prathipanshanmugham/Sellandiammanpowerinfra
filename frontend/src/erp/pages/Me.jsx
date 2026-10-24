import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { MapPin, LogIn, LogOut, ShieldCheck, KeyRound, Monitor, CalendarPlus, FileText, Lock, Unlock, Copy, Eye, ExternalLink, Plus, Search, Timer } from "lucide-react";
import { api, errMsg, openFile } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { fmtDate, fmtDateTime, ago, inr, todayIST, num } from "@/lib/format";
import { Button, Badge, Skeleton, Input, Textarea, Select, Field, Switch, Alert, Dialog, Empty } from "@/components/ui/kit";
import { toast } from "sonner";
import { useApi } from "../lib";
import { PageHead, Panel, Table, usePageTitle } from "../ui";

function gps() {
  return new Promise((ok, no) => {
    if (!navigator.geolocation) { no(new Error("Location isn't available on this device")); return; }
    navigator.geolocation.getCurrentPosition((p) => ok({ lat: p.coords.latitude, lng: p.coords.longitude, accuracy: Math.round(p.coords.accuracy) }), (e) => no(new Error(e.message || "Allow location access to check in")), { enableHighAccuracy: true, timeout: 15000 });
  });
}

export default function Me() {
  const { user, refresh } = useAuth();
  const [sp] = useSearchParams();
  const { data, isLoading, refetch } = useApi("/hr/me");
  const [busy, setBusy] = useState("");
  const [leave, setLeave] = useState(false);
  usePageTitle("My profile");
  async function punch(kind) {
    setBusy(kind);
    try { const g = await gps(); await api.post(`/hr/check-${kind}`, { gps: g }); toast.success(kind === "in" ? "Checked in" : "Checked out"); refetch(); } catch (ex) { toast.error(ex.response ? errMsg(ex) : ex.message); } finally { setBusy(""); }
  }
  const today = data?.today;
  return (
    <div className="space-y-5 pb-10">
      <PageHead title={user.name} sub={`${user.role_label}, ${user.email}`} />
      {sp.get("setup") === "mfa" && <Alert tone="amber" icon={ShieldCheck} title="Set up 2-step sign-in to continue">Your role needs it. Use any authenticator app (Google Authenticator, Microsoft Authenticator, Authy).</Alert>}
      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="Today" className="lg:col-span-1">
          {isLoading ? <Skeleton className="h-24" /> : !data?.employee ? <p className="text-sm text-muted">No employee record is linked to your login. HR can link one.</p> : (
            <div className="space-y-3">
              <p className="text-sm text-muted">{new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", timeZone: "Asia/Kolkata" })}</p>
              {today ? (
                <dl className="grid grid-cols-2 gap-2 text-sm">
                  <div><dt className="text-xs text-muted">In</dt><dd className="font-semibold tabular">{today.check_in?.slice(11, 16)}</dd></div>
                  <div><dt className="text-xs text-muted">Out</dt><dd className="font-semibold tabular">{today.check_out?.slice(11, 16) || "—"}</dd></div>
                  {today.distance_m != null && <div className="col-span-2 text-xs text-muted"><MapPin className="mr-1 inline h-3.5 w-3.5" />{num(today.distance_m, 0)} m from the site{today.flag ? <Badge tone="amber" className="ml-2">{today.flag.replace(/_/g, " ")}</Badge> : null}</div>}
                </dl>
              ) : <p className="text-sm">You haven't checked in yet.</p>}
              <div className="flex gap-2">
                {!today && <Button loading={busy === "in"} onClick={() => punch("in")}><LogIn className="h-4 w-4" />Check in</Button>}
                {today && !today.check_out && <Button variant="dark" loading={busy === "out"} onClick={() => punch("out")}><LogOut className="h-4 w-4" />Check out</Button>}
                <Button variant="outline" onClick={() => setLeave(true)}><CalendarPlus className="h-4 w-4" />Apply for leave</Button>
              </div>
              <p className="text-xs text-muted">Check-in records your location once, to confirm you're at the site or office.</p>
            </div>
          )}
        </Panel>
        <Panel title="This month's attendance" className="lg:col-span-2" bodyClass="p-0">
          <Table dense columns={[{ label: "Date", render: (a) => fmtDate(a.date) }, { label: "In", render: (a) => a.check_in?.slice(11, 16) }, { label: "Out", render: (a) => a.check_out?.slice(11, 16) || "—" },
            { label: "Hours", right: true, render: (a) => (a.hours ? num(a.hours) : "—") }, { label: "", render: (a) => (a.flag ? <Badge tone="amber">{a.flag.replace(/_/g, " ")}</Badge> : null) }]} rows={data?.attendance || []} empty="No attendance this month" />
        </Panel>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Leave" bodyClass="p-0">
          <Table dense columns={[{ label: "From", render: (l) => fmtDate(l.from_date) }, { label: "To", render: (l) => fmtDate(l.to_date) }, { label: "Days", right: true, key: "days" }, { label: "Type", render: (l) => l.ltype },
            { label: "", render: (l) => <Badge tone={l.status === "approved" ? "green" : l.status === "rejected" ? "red" : "amber"}>{l.status === "pending_approval" ? "Waiting" : l.status}</Badge> }]} rows={data?.leaves || []} empty="No leave taken" />
        </Panel>
        <Panel title="Payslips" bodyClass="p-0">
          <Table dense columns={[{ label: "Month", key: "month" }, { label: "Days paid", right: true, key: "days_paid" }, { label: "Gross", right: true, render: (p) => inr(p.gross) }, { label: "Net", right: true, render: (p) => <span className="font-semibold">{inr(p.net)}</span> },
            { label: "", render: (p) => <Button size="sm" variant="ghost" onClick={() => openFile(`/e/payroll_runs/${p.run_id}/pdf?employee_id=${data.employee.id}`, { name: `payslip-${p.month}.pdf`, type: "application/pdf", kind: "payslip" })}><FileText className="h-3.5 w-3.5" />PDF</Button> }]} rows={data?.payslips || []} empty="No payslips yet" />
        </Panel>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Security />
        <Preferences />
      </div>
      <LeaveDialog open={leave} onClose={() => setLeave(false)} onDone={() => { setLeave(false); refetch(); }} />
    </div>
  );
}

function LeaveDialog({ open, onClose, onDone }) {
  const [v, setV] = useState({ ltype: "casual", from_date: todayIST(), to_date: todayIST(), reason: "" });
  const [busy, setBusy] = useState(false);
  return (
    <Dialog open={open} onOpenChange={(x) => !x && onClose()} title="Apply for leave" description="It goes to HR or your branch manager for approval."
      footer={<><Button variant="outline" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={async () => { setBusy(true); try { await api.post("/hr/my-leave", v); toast.success("Leave request sent"); onDone(); } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(false); } }}>Send request</Button></>}>
      <div className="space-y-3">
        <Field label="Type"><Select value={v.ltype} onChange={(e) => setV((s) => ({ ...s, ltype: e.target.value }))} options={[["casual", "Casual"], ["sick", "Sick"], ["earned", "Earned"], ["comp_off", "Comp-off"], ["unpaid", "Unpaid"]].map(([a, b]) => ({ value: a, label: b }))} /></Field>
        <div className="grid grid-cols-2 gap-3"><Field label="From"><Input type="date" value={v.from_date} onChange={(e) => setV((s) => ({ ...s, from_date: e.target.value }))} /></Field><Field label="To"><Input type="date" value={v.to_date} onChange={(e) => setV((s) => ({ ...s, to_date: e.target.value }))} /></Field></div>
        <Field label="Reason"><Textarea value={v.reason} onChange={(e) => setV((s) => ({ ...s, reason: e.target.value }))} /></Field>
      </div>
    </Dialog>
  );
}

function Security() {
  const { user, refresh } = useAuth();
  const { data: sessions, refetch } = useApi("/auth/sessions");
  const [setup, setSetup] = useState(null);
  const [code, setCode] = useState("");
  const [codes, setCodes] = useState(null);
  const [pw, setPw] = useState({ current: "", new: "" });
  const [busy, setBusy] = useState("");
  return (
    <Panel title="Sign-in and security">
      <div className="space-y-5">
        <div>
          <p className="flex items-center gap-2 text-sm font-medium"><ShieldCheck className={cn("h-4 w-4", user.mfa_enabled ? "text-good" : "text-muted")} />2-step sign-in {user.mfa_enabled ? <Badge tone="green">On</Badge> : <Badge>Off</Badge>}</p>
          {!user.mfa_enabled && !setup && <Button size="sm" variant="outline" className="mt-2" onClick={async () => { try { setSetup((await api.post("/auth/mfa/setup")).data); } catch (ex) { toast.error(errMsg(ex)); } }}>Set up 2-step sign-in</Button>}
          {setup && !codes && (
            <div className="mt-3 grid gap-3 sm:grid-cols-[160px_1fr]">
              <div className="rounded-lg bg-white p-2 [&_svg]:h-auto [&_svg]:w-full" dangerouslySetInnerHTML={{ __html: setup.qr_svg }} />
              <div className="space-y-2 text-sm">
                <p>Scan with your authenticator app, or type this key:</p>
                <p className="break-all rounded bg-canvas px-2 py-1 font-mono text-xs">{setup.secret}</p>
                <Field label="Then enter the 6-digit code"><Input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" className="w-40 text-center tracking-widest tabular" /></Field>
                <Button size="sm" loading={busy === "mfa"} onClick={async () => { setBusy("mfa"); try { setCodes((await api.post("/auth/mfa/enable", { code })).data.recovery_codes); refresh(); } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(""); } }}>Turn on</Button>
              </div>
            </div>
          )}
          {codes && <Alert tone="green" className="mt-3" title="Save these recovery codes">Each works once if you lose your phone.<p className="mt-2 font-mono text-xs leading-6">{codes.join("  ")}</p></Alert>}
        </div>
        <form className="grid gap-2 sm:grid-cols-[1fr_1fr_auto] sm:items-end" onSubmit={async (e) => { e.preventDefault(); setBusy("pw"); try { const r = (await api.post("/auth/password", pw)).data; toast.success(`Password changed${r.signed_out ? `; signed out ${r.signed_out} other session(s)` : ""}`); setPw({ current: "", new: "" }); } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(""); } }}>
          <Field label="Current password"><Input type="password" autoComplete="current-password" value={pw.current} onChange={(e) => setPw((s) => ({ ...s, current: e.target.value }))} /></Field>
          <Field label="New password"><Input type="password" autoComplete="new-password" value={pw.new} onChange={(e) => setPw((s) => ({ ...s, new: e.target.value }))} /></Field>
          <Button type="submit" variant="outline" loading={busy === "pw"} disabled={!pw.current || !pw.new}><KeyRound className="h-4 w-4" />Change</Button>
        </form>
        <div>
          <div className="flex items-center justify-between"><p className="text-sm font-medium">Signed in on</p>{sessions?.length > 1 && <Button size="sm" variant="ghost" onClick={async () => { await api.post("/auth/sessions/sign-out-others"); refetch(); toast.success("Signed out other devices"); }}>Sign out others</Button>}</div>
          <ul className="mt-2 space-y-1.5">{(sessions || []).map((s) => <li key={s.sid} className="flex items-center gap-2 text-sm"><Monitor className="h-4 w-4 text-muted" /><span className="truncate">{(s.agent || "Unknown device").slice(0, 60)}</span><span className="ml-auto shrink-0 text-xs text-muted">{s.current ? "This device" : ago(s.created_at)}</span></li>)}</ul>
        </div>
      </div>
    </Panel>
  );
}

function Preferences() {
  const { user, refresh } = useAuth();
  const [p, setP] = useState(user.notify_prefs || { email: true, whatsapp: true, digest: true });
  const [del, setDel] = useState({ delegate_to: user.delegate_to || "", delegate_until: user.delegate_until || "" });
  const { data: people } = useApi("/users/lookup");
  async function save() { try { await api.put("/me/preferences", { notify_prefs: p, ...del }); toast.success("Saved"); refresh(); } catch (ex) { toast.error(errMsg(ex)); } }
  return (
    <Panel title="Notifications and cover" actions={<Button size="sm" onClick={save}>Save</Button>}>
      <div className="space-y-4">
        <div className="space-y-2">
          <Switch checked={!!p.email} onChange={(x) => setP((s) => ({ ...s, email: x }))} label="Email me about approvals, assignments and alerts" />
          <Switch checked={!!p.whatsapp} onChange={(x) => setP((s) => ({ ...s, whatsapp: x }))} label="WhatsApp me for urgent items" />
          <Switch checked={!!p.digest} onChange={(x) => setP((s) => ({ ...s, digest: x }))} label="Daily summary at 9 am" />
        </div>
        <div className="border-t border-edge pt-3">
          <p className="text-sm font-medium">Going on leave?</p>
          <p className="mb-2 text-xs text-muted">Someone else can approve on your behalf until the date you set.</p>
          <div className="grid gap-2 sm:grid-cols-2">
            <Select value={del.delegate_to} onChange={(e) => setDel((s) => ({ ...s, delegate_to: e.target.value }))} options={(people || []).filter((x) => x.id !== user.id).map((x) => ({ value: x.id, label: `${x.name} (${x.role_label})` }))} placeholder="No one" />
            <Input type="date" value={del.delegate_until} onChange={(e) => setDel((s) => ({ ...s, delegate_until: e.target.value }))} aria-label="Until" />
          </div>
        </div>
      </div>
    </Panel>
  );
}

// ------------------------------------------------------------------ password vault
export function Vault() {
  const { user } = useAuth();
  const { data: st, refetch: rs } = useApi("/vault/status");
  const { data: vm } = useApi("/vault/meta");
  const [q, setQ] = useState("");
  const { data: items, refetch } = useApi(st?.configured ? "/vault/items" : null, { q: q || undefined });
  const [pw, setPw] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [shown, setShown] = useState({});
  const [add, setAdd] = useState(false);
  usePageTitle("Password vault");
  if (!st) return <Skeleton className="h-64" />;
  async function unlock(e) {
    e.preventDefault(); setBusy(true);
    try { await api.post("/vault/unlock", { password: pw, code: code || undefined }); setPw(""); setCode(""); rs(); toast.success("Vault open for 15 minutes"); } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(false); }
  }
  async function reveal(it, purpose = "view") {
    try {
      const r = (await api.post(`/vault/items/${it.id}/reveal`, { field: "password", purpose })).data;
      if (purpose === "copy") { await navigator.clipboard?.writeText(r.value); toast.success("Password copied; the clipboard isn't cleared automatically"); return; }
      setShown((s) => ({ ...s, [it.id]: r.value }));
      setTimeout(() => setShown((s) => { const n = { ...s }; delete n[it.id]; return n; }), 20000);
    } catch (ex) { if (ex.response?.data?.detail === "vault_locked") rs(); toast.error(ex.response?.data?.detail === "vault_locked" ? "The vault locked itself; open it again" : errMsg(ex)); }
  }
  const groups = {};
  (items || []).forEach((i) => { (groups[i.category_label] = groups[i.category_label] || []).push(i); });
  return (
    <div className="space-y-5 pb-10">
      <PageHead icon="file-lock-2" title="Password vault" sub="Company logins for TNPDCL, CEIG, tender portals, GST, PF and ESI, shared by role. Passwords are encrypted; every view and copy is logged."
        actions={st.unlocked ? <><Button size="sm" variant="outline" onClick={async () => { await api.post("/vault/lock"); rs(); }}><Lock className="h-4 w-4" />Lock now</Button>{st.can_add && <Button size="sm" onClick={() => setAdd(true)}><Plus className="h-4 w-4" />Add a login</Button>}</> : null} />
      {!st.configured ? <Alert tone="amber" title="The vault is switched off">Set VAULT_KEY on the server (32 random bytes) to use it. See the deployment guide.</Alert> : !st.unlocked ? (
        <form onSubmit={unlock} className="max-w-sm space-y-3 rounded-xl border border-edge bg-surface p-5">
          <p className="flex items-center gap-2 font-medium"><Lock className="h-4 w-4" />Enter your password to open the vault</p>
          <Field label="Your sign-in password"><Input type="password" value={pw} onChange={(e) => setPw(e.target.value)} autoFocus /></Field>
          {st.mfa && <Field label="6-digit code from your app"><Input inputMode="numeric" value={code} onChange={(e) => setCode(e.target.value)} /></Field>}
          <Button type="submit" loading={busy}><Unlock className="h-4 w-4" />Open for 15 minutes</Button>
        </form>
      ) : (
        <>
          <label className="relative block max-w-xs"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" /><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search logins" className="h-9 pl-9" /></label>
          {!items?.length ? <Empty title="No logins shared with you yet" /> : Object.entries(groups).map(([g, list]) => (
            <Panel key={g} title={g} bodyClass="p-0">
              <ul className="divide-y divide-edge">
                {list.map((it) => (
                  <li key={it.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="flex items-center gap-2 text-sm font-medium">{it.title}{it.rotate_due && <Badge tone="amber">Change due</Badge>}</p>
                      <p className="flex items-center gap-1.5 text-xs text-muted">{it.username}{it.username && <button type="button" onClick={() => { navigator.clipboard?.writeText(it.username); toast.success("Username copied"); }} aria-label="Copy username"><Copy className="h-3 w-3" /></button>}
                        {it.url && <a href={it.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 hover:underline"><ExternalLink className="h-3 w-3" />Open site</a>}</p>
                    </div>
                    {shown[it.id] ? <span className="rounded bg-canvas px-2 py-1 font-mono text-sm">{shown[it.id]}</span> : null}
                    {it.has_password && <><Button size="sm" variant="ghost" onClick={() => reveal(it)}><Eye className="h-3.5 w-3.5" />Show</Button><Button size="sm" variant="outline" onClick={() => reveal(it, "copy")}><Copy className="h-3.5 w-3.5" />Copy</Button></>}
                    {it.has_totp && <TotpButton id={it.id} />}
                  </li>
                ))}
              </ul>
            </Panel>
          ))}
        </>
      )}
      {add && <AddLogin presets={vm?.presets || []} roles={vm?.roles || []} onClose={() => setAdd(false)} onDone={() => { setAdd(false); refetch(); }} />}
    </div>
  );
}

function TotpButton({ id }) {
  const [c, setC] = useState(null);
  return c ? <span className="flex items-center gap-1 rounded bg-signal-soft px-2 py-1 font-mono text-sm tabular"><Timer className="h-3.5 w-3.5" />{c.code} <span className="text-xs text-muted">{c.seconds_left}s</span></span>
    : <Button size="sm" variant="ghost" onClick={async () => { try { setC((await api.post(`/vault/items/${id}/code`)).data); } catch (ex) { toast.error(errMsg(ex)); } }}>2-step code</Button>;
}

function AddLogin({ presets, roles, onClose, onDone }) {
  const [v, setV] = useState({ preset: "other", title: "", url: "", username: "", password: "", notes: "", share_roles: ["director"], share_users: [], fields: [], property_ids: [], tags: [] });
  const [busy, setBusy] = useState(false);
  const pick = (k) => { const p = presets.find((x) => x.key === k); setV((s) => ({ ...s, preset: k, title: s.title || p?.name || "", url: p?.url || s.url })); };
  return (
    <Dialog open onOpenChange={(x) => !x && onClose()} title="Add a login" wide
      footer={<><Button variant="outline" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={async () => { setBusy(true); try { await api.post("/vault/items", v); toast.success("Saved"); onDone(); } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(false); } }}>Save</Button></>}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Site"><Select value={v.preset} onChange={(e) => pick(e.target.value)} options={presets.map((p) => ({ value: p.key, label: p.name }))} /></Field>
        <Field label="Name in the vault" required><Input value={v.title} onChange={(e) => setV((s) => ({ ...s, title: e.target.value }))} /></Field>
        <Field label="Web address"><Input value={v.url} onChange={(e) => setV((s) => ({ ...s, url: e.target.value }))} /></Field>
        <Field label={presets.find((p) => p.key === v.preset)?.hint || "Username"}><Input value={v.username} onChange={(e) => setV((s) => ({ ...s, username: e.target.value }))} /></Field>
        <Field label="Password"><Input type="password" value={v.password} onChange={(e) => setV((s) => ({ ...s, password: e.target.value }))} autoComplete="new-password" /></Field>
        <Field label="Notes"><Input value={v.notes} onChange={(e) => setV((s) => ({ ...s, notes: e.target.value }))} /></Field>
        <Field label="Who can see it" className="sm:col-span-2">
          <div className="flex flex-wrap gap-1.5">{roles.map((r) => { const on = v.share_roles.includes(r.key); return <button key={r.key} type="button" onClick={() => setV((s) => ({ ...s, share_roles: on ? s.share_roles.filter((x) => x !== r.key) : [...s.share_roles, r.key] }))} className={cn("rounded px-2 py-1 text-xs", on ? "bg-ink text-white" : "bg-canvas text-fg/75")}>{r.label}</button>; })}</div>
        </Field>
      </div>
    </Dialog>
  );
}

export { Link, useEffect };
