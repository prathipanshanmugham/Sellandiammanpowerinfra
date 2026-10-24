import { useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate, useParams } from "react-router-dom";
import ErrorBoundary from "@/components/ErrorBoundary";
import { LogOut, Check, X, FileText, Wrench, IndianRupee, Plus, Star, MessageSquare, ShieldCheck, Send, CalendarCheck, ArrowLeft, Phone, MapPin, ClipboardCheck, Receipt, Users, HandCoins, Upload } from "lucide-react";
import { api, errMsg, openFile, IS_DEMO } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { inr, num, pct, fmtDate, fmtDateTime, ago, todayIST, telLink } from "@/lib/format";
import { Logo } from "@/components/brand/Logo";
import { Button, Badge, Skeleton, Empty, Dialog, Sheet, Field, Input, Textarea, Select, Alert, Progress, Tabs, TabPanel, Checkbox } from "@/components/ui/kit";
import { toast } from "sonner";
import { useApi, useInvalidate, stateOf } from "@/erp/lib";
import { FilesInput, FieldValue } from "@/erp/fields";
import { Details } from "@/erp/EntityDetail";
import { EntityList } from "@/erp/EntityList";
import { Panel, Table, usePageTitle } from "@/erp/ui";
import { useSite } from "@/components/public/site";

let demoBar = null;
export const setPortalDemoBar = (C) => { demoBar = C; };

const NAVS = {
  client: [["/client", "Overview", true], ["/client/projects", "Projects"], ["/client/bills", "Bills"], ["/client/service", "Service"], ["/client/new", "New requirement"]],
  consultant: [["/consultant", "Overview", true]],
  vendor: [["/vendor", "Overview", true]],
  subcontractor: [["/subcontractor", "Overview", true]],
  partner: [["/partner", "Referrals", true]],
};

export function PortalLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const site = useSite();
  const loc = useLocation();
  const DemoBar = IS_DEMO ? demoBar : null;
  return (
    <div className={cn("min-h-screen bg-canvas", DemoBar && "pt-10")}>
      {DemoBar && <DemoBar />}
      <header className="border-b border-white/10 bg-ink text-white">
        <div className="container flex h-14 items-center justify-between gap-3">
          <Link to="/" aria-label="Website"><Logo theme="dark" compact /></Link>
          <div className="flex items-center gap-3 text-sm">
            <span className="hidden text-white/80 sm:inline">{user?.name}</span>
            <button type="button" onClick={async () => { await logout(); nav("/login"); }} className="flex items-center gap-1.5 rounded-md px-2 py-1.5 text-white/85 hover:bg-white/10 hover:text-white"><LogOut className="h-4 w-4" />Sign out</button>
          </div>
        </div>
        <nav className="container scrollbar-thin flex gap-1 overflow-x-auto" aria-label="Portal">
          {(NAVS[user?.role] || []).map(([to, l, end]) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => cn("shrink-0 border-b-2 px-3 py-2.5 text-sm", isActive ? "border-signal font-semibold text-white" : "border-transparent text-white/75 hover:text-white")}>{l}</NavLink>
          ))}
        </nav>
      </header>
      <main id="main" className="container py-6"><ErrorBoundary resetKey={loc.pathname}><Outlet /></ErrorBoundary></main>
      <footer className="container pb-10 pt-4 text-sm text-muted">
        Need help? {site.settings?.phone && <a href={telLink(site.settings.phone)} className="font-medium text-fg hover:underline">{site.settings.phone}</a>}{site.settings?.emergency_phone && <> or the breakdown line <a href={telLink(site.settings.emergency_phone)} className="font-medium text-bad hover:underline">{site.settings.emergency_phone}</a></>}
      </footer>
    </div>
  );
}

function Head({ title, sub, actions }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div><h1 className="text-[24px] font-extrabold leading-tight md:text-[28px]">{title}</h1>{sub && <p className="mt-1 text-sm text-muted">{sub}</p>}</div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

// OTP-confirmed approval (drawings, variations, proposals, snags)
function ApproveDialog({ item, onClose, onDone, allowComments = true }) {
  const [step, setStep] = useState("choose");
  const [decision, setDecision] = useState("approve");
  const [comment, setComment] = useState("");
  const [otp, setOtp] = useState("");
  const [sent, setSent] = useState(null);
  const [busy, setBusy] = useState(false);
  if (!item) return null;
  const options = item.entity === "drawings" ? [["approve", "Approve"], ["approve_with_comments", "Approve with comments"], ["reject", "Return for changes"]] : item.entity === "snags" ? [["approve", "It's fixed"], ["reject", "Not fixed yet"]] : [["approve", "Approve"], ["reject", "Reject"]];
  async function sendOtp() {
    setBusy(true);
    try { setSent((await api.post("/portal/otp")).data); setStep("otp"); } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(false); }
  }
  async function confirm() {
    setBusy(true);
    try { await api.post(`/portal/approve/${item.entity}/${item.id}`, { decision, comment, otp }); toast.success("Thank you, recorded"); onDone(); } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(false); }
  }
  return (
    <Dialog open onOpenChange={(x) => !x && onClose()} title={item.title} description={item.amount ? `Amount ${inr(item.amount)}` : "Your decision is recorded with a one-time code sent to your phone."}
      footer={step === "choose" ? <><Button variant="outline" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={sendOtp} disabled={decision !== "approve" && !comment.trim()}>Continue</Button></>
        : <><Button variant="outline" onClick={() => setStep("choose")}>Back</Button><Button loading={busy} onClick={confirm} disabled={otp.length !== 6}>Confirm</Button></>}>
      {step === "choose" ? (
        <div className="space-y-3">
          <div className="grid gap-2">{options.map(([k, l]) => (
            <label key={k} className={cn("flex cursor-pointer items-center gap-3 rounded-md border px-3 py-2.5 text-sm", decision === k ? "border-ink bg-ink text-white" : "border-edge hover:border-fg/30")}>
              <input type="radio" className="sr-only" checked={decision === k} onChange={() => setDecision(k)} />{l}
            </label>
          ))}</div>
          {allowComments && <Field label={decision === "approve" ? "Comments (optional)" : "Comments"} required={decision !== "approve"}><Textarea value={comment} onChange={(e) => setComment(e.target.value)} /></Field>}
          {item.entity === "drawings" && <Button size="sm" variant="ghost" onClick={() => openFile(`/e/drawings/${item.id}/pdf`, { name: "drawing.pdf", type: "application/pdf", kind: "generic" })}><FileText className="h-4 w-4" />Open the drawing sheet</Button>}
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm">We sent a 6-digit code {sent?.sent_to ? `to the phone ending ${sent.sent_to}` : "to your registered phone"}{IS_DEMO ? " (in this preview, any 6 digits work)" : ""}.</p>
          <Input inputMode="numeric" value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))} className="w-44 text-center text-lg tracking-[0.3em] tabular" autoFocus aria-label="One-time code" />
        </div>
      )}
    </Dialog>
  );
}

function RecordSheet({ entity, id, onClose }) {
  const { meta } = useAuth();
  const e = meta?.entities?.[entity];
  const { data } = useApi(id ? `/e/${entity}/${id}` : null, null, { keep: false });
  if (!id || !e) return null;
  return (
    <Sheet open onOpenChange={(x) => !x && onClose()} title={data ? (data.code || data.name || data.title || e.label) : e.label}
      footer={<Button variant="outline" onClick={() => openFile(`/e/${entity}/${id}/pdf`, { name: `${data?.code || entity}.pdf`, type: "application/pdf", kind: entity })}><FileText className="h-4 w-4" />PDF</Button>}>
      {!data ? <Skeleton className="h-64" /> : <Details e={e} doc={data} />}
    </Sheet>
  );
}

// ------------------------------------------------------------------ client
export function ClientHome() {
  const { user } = useAuth();
  const { data, isLoading, refetch } = useApi("/portal/summary");
  const [appr, setAppr] = useState(null);
  usePageTitle("Your portal");
  if (isLoading || !data) return <Skeleton className="h-96" />;
  const live = data.projects.filter((p) => !["handed_over", "closed", "cancelled"].includes(p.status));
  return (
    <div className="space-y-5">
      <Head title={data.account?.name || "Welcome"} sub={`Signed in as ${user.name}`} actions={<Button as={Link} to="/client/service?new=1" variant="outline"><Wrench className="h-4 w-4" />Report a problem</Button>} />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[["Live projects", live.length, "/client/projects"], ["Waiting for you", data.approvals.length, null], ["Outstanding", inr(data.outstanding), "/client/bills"], ["Open service requests", data.tickets.length, "/client/service"]].map(([l, v, to]) => {
          const body = <div className={cn("rounded-xl border border-edge bg-surface p-4 shadow-card", to && "hover:border-fg/25")}><p className="text-[14px] text-muted">{l}</p><p className="mt-1 font-display text-[24px] font-extrabold tabular">{v}</p></div>;
          return to ? <Link key={l} to={to}>{body}</Link> : <div key={l}>{body}</div>;
        })}
      </div>
      {data.approvals.length > 0 && (
        <Panel title="Waiting for your OK" sub="Approve with a one-time code sent to your phone" bodyClass="p-0">
          <ul className="divide-y divide-edge">
            {data.approvals.map((a) => (
              <li key={`${a.entity}:${a.id}`} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <ShieldCheck className="h-5 w-5 shrink-0 text-signal-deep" />
                <div className="min-w-0 flex-1"><p className="text-sm font-medium">{a.title}</p>{a.amount ? <p className="text-xs text-muted">{inr(a.amount)}</p> : null}</div>
                <Button size="sm" onClick={() => setAppr(a)}>Review</Button>
              </li>
            ))}
          </ul>
        </Panel>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        {live.map((p) => <ProjectCard key={p.id} p={p} refs={data.refs} />)}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {data.approvals_tracker?.length > 0 && (
          <Panel title="TNPDCL and CEIG approvals" bodyClass="p-0">
            <ul className="divide-y divide-edge">{data.approvals_tracker.map((l) => <li key={l.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm"><span><span className="block font-medium">{l.authority}: {(l.kind || "").replace(/_/g, " ")}</span><span className="text-xs text-muted">{l.application_no}{l.office ? `, ${l.office}` : ""}</span></span><Badge tone="blue">{(l.stage || "").replace(/_/g, " ")}</Badge></li>)}</ul>
          </Panel>
        )}
        <Panel title="Maintenance" bodyClass="p-0">
          {!data.amc.length ? <p className="px-4 py-6 text-sm text-muted">No active maintenance contract. <Link to="/amc" className="text-cable underline">See AMC plans</Link></p> : (
            <ul className="divide-y divide-edge">
              {data.amc.map((a) => <li key={a.id} className="px-4 py-3 text-sm"><p className="font-medium">{a.title}</p><p className="text-xs text-muted">Valid until {fmtDate(a.end)}, {a.visits_per_year} visits a year, {data.assets} items of equipment covered</p></li>)}
              {data.next_visits.map((v) => <li key={v.id} className="flex items-center gap-2 px-4 py-2.5 text-sm"><CalendarCheck className="h-4 w-4 text-cable" />Next visit {fmtDate(v.scheduled_on)}</li>)}
            </ul>
          )}
        </Panel>
      </div>
      {appr && <ApproveDialog item={appr} onClose={() => setAppr(null)} onDone={() => { setAppr(null); refetch(); }} />}
    </div>
  );
}

function ProjectCard({ p, refs }) {
  return (
    <Link to={`/client/projects/${p.id}`} className="block rounded-xl border border-edge bg-surface p-5 shadow-card hover:border-fg/25">
      <div className="flex items-start justify-between gap-3"><p className="font-display text-[17px] font-bold leading-snug">{p.name}</p><Badge tone="blue">{(p.status || "").replace(/_/g, " ")}</Badge></div>
      <p className="mt-1 text-sm text-muted">{p.code}{refs?.users?.[p.manager_id] ? `, project manager ${refs.users[p.manager_id]}` : ""}</p>
      <div className="mt-4 flex items-center gap-3"><Progress value={p.percent_complete || 0} tone="signal" className="h-2" /><span className="shrink-0 text-sm font-semibold tabular">{pct(p.percent_complete || 0, 0)}</span></div>
      <p className="mt-2 text-xs text-muted">{p.end_date ? `Planned finish ${fmtDate(p.end_date)}` : ""}</p>
    </Link>
  );
}

export function ClientProjects() {
  const { data } = useApi("/portal/summary");
  usePageTitle("Projects");
  if (!data) return <Skeleton className="h-64" />;
  return (
    <div>
      <Head title="Your projects" />
      {!data.projects.length ? <Empty title="No projects yet" /> : <div className="grid gap-4 lg:grid-cols-2">{data.projects.map((p) => <ProjectCard key={p.id} p={p} refs={data.refs} />)}</div>}
    </div>
  );
}

const CLIENT_TABS = [["milestones", "Schedule"], ["dprs", "Daily progress"], ["drawings", "Drawings"], ["variations", "Variations"], ["ra_bills", "RA bills"], ["invoices", "Invoices"], ["test_reports", "Test reports"], ["snags", "Snags"], ["liaisons", "Approvals"], ["handovers", "Handover"], ["documents", "Documents"]];
export function ClientProject() {
  const { id } = useParams();
  const { meta } = useAuth();
  const { data: p } = useApi(`/e/projects/${id}`);
  const [tab, setTab] = useState("milestones");
  const [open, setOpen] = useState(null);
  usePageTitle(p?.name || "Project");
  if (!p || !meta) return <Skeleton className="h-96" />;
  const tabs = CLIENT_TABS.filter(([k]) => meta.entities[k]);
  return (
    <div>
      <Link to="/client/projects" className="mb-2 inline-flex items-center gap-1 text-sm text-muted hover:text-fg"><ArrowLeft className="h-3.5 w-3.5" />All projects</Link>
      <Head title={p.name} sub={[p.code, p.town, p._refs?.users?.[p.manager_id] ? `Project manager ${p._refs.users[p.manager_id]}` : null].filter(Boolean).join(", ")} />
      <div className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="rounded-xl border border-edge bg-surface p-4"><p className="text-xs text-muted">Work done</p><p className="mt-1 font-display text-[22px] font-extrabold tabular">{pct(p.percent_complete || 0, 0)}</p><Progress value={p.percent_complete || 0} tone="signal" className="mt-2" /></div>
        <div className="rounded-xl border border-edge bg-surface p-4"><p className="text-xs text-muted">Contract value</p><p className="mt-1 font-display text-[22px] font-extrabold tabular">{inr(p.contract_value, { compact: true })}</p></div>
        <div className="rounded-xl border border-edge bg-surface p-4"><p className="text-xs text-muted">Started</p><p className="mt-1 font-display text-[18px] font-bold">{fmtDate(p.start_date)}</p></div>
        <div className="rounded-xl border border-edge bg-surface p-4"><p className="text-xs text-muted">Planned finish</p><p className="mt-1 font-display text-[18px] font-bold">{fmtDate(p.end_date)}</p></div>
      </div>
      <Tabs value={tab} onValueChange={setTab} tabs={tabs.map(([k, l]) => ({ value: k, label: l }))}>
        {tabs.map(([k]) => <TabPanel key={k} value={k}>{tab === k && <EntityList entityKey={k} fixed={{ project_id: id }} embedded onOpen={(d) => setOpen({ entity: k, id: d.id })} />}</TabPanel>)}
      </Tabs>
      {open && <RecordSheet entity={open.entity} id={open.id} onClose={() => setOpen(null)} />}
    </div>
  );
}

export function ClientBills() {
  const { data, refetch } = useApi("/portal/summary");
  const [pay, setPay] = useState(null);
  const [notice, setNotice] = useState(null);
  const [open, setOpen] = useState(null);
  usePageTitle("Bills");
  if (!data) return <Skeleton className="h-64" />;
  return (
    <div className="space-y-5">
      <Head title="Bills and payments" sub={`Outstanding ${inr(data.outstanding)}`} />
      <Panel title="Due for payment" bodyClass="p-0">
        <Table columns={[
          { label: "Invoice", render: (i) => <button type="button" onClick={() => setOpen(i.id)} className="font-medium text-cable hover:underline">{i.code}</button> },
          { label: "Date", render: (i) => fmtDate(i.date) }, { label: "Due", render: (i) => <span className={cn(i.due_date < todayIST() && "font-semibold text-bad")}>{fmtDate(i.due_date)}</span> },
          { label: "Total", right: true, render: (i) => inr(i.total) }, { label: "Balance", right: true, render: (i) => <span className="font-semibold">{inr(i.balance)}</span> },
          { label: "", render: (i) => <div className="flex justify-end gap-2"><Button size="sm" onClick={async () => { try { setPay({ inv: i, ...(await api.get(`/portal/pay/${i.id}`)).data }); } catch (ex) { toast.error(errMsg(ex)); } }}><IndianRupee className="h-3.5 w-3.5" />Pay by UPI</Button><Button size="sm" variant="outline" onClick={() => setNotice(i)}>I've paid</Button></div> },
        ]} rows={data.invoices_due} empty="Nothing due. Thank you." />
      </Panel>
      <Panel title="All invoices" bodyClass="p-3"><EntityList entityKey="invoices" embedded onOpen={(d) => setOpen(d.id)} /></Panel>
      <Dialog open={!!pay} onOpenChange={(x) => !x && setPay(null)} title={`Pay ${inr(pay?.amount)}`} description={pay?.inv?.code}>
        {pay && <div className="space-y-3 text-center"><div className="mx-auto w-56 [&_svg]:h-auto [&_svg]:w-full" dangerouslySetInnerHTML={{ __html: pay.qr_svg }} /><p className="text-sm">Scan with any UPI app. After paying, tap "I've paid" so accounts can match it.</p>{pay.bank_details && <p className="text-xs text-muted">Or transfer to: {pay.bank_details}</p>}</div>}
      </Dialog>
      {notice && <PaymentNotice inv={notice} onClose={() => setNotice(null)} onDone={() => { setNotice(null); refetch(); }} />}
      {open && <RecordSheet entity="invoices" id={open} onClose={() => setOpen(null)} />}
    </div>
  );
}

function PaymentNotice({ inv, onClose, onDone }) {
  const [v, setV] = useState({ amount: inv.balance, reference: "", date: todayIST(), mode: "neft", proof: null });
  const [busy, setBusy] = useState(false);
  return (
    <Dialog open onOpenChange={(x) => !x && onClose()} title={`Payment for ${inv.code}`} description="Accounts confirm it when it reaches the bank."
      footer={<><Button variant="outline" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={async () => { setBusy(true); try { const r = (await api.post("/portal/payment-notice", { invoice_id: inv.id, ...v })).data; toast.success(`Thanks, noted as ${r.reference}`); onDone(); } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(false); } }}>Send</Button></>}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Amount paid (₹)"><Input inputMode="decimal" value={v.amount} onChange={(e) => setV((s) => ({ ...s, amount: e.target.value }))} /></Field>
        <Field label="Date"><Input type="date" value={v.date} onChange={(e) => setV((s) => ({ ...s, date: e.target.value }))} /></Field>
        <Field label="Paid by"><Select value={v.mode} onChange={(e) => setV((s) => ({ ...s, mode: e.target.value }))} options={[["neft", "NEFT / RTGS"], ["upi", "UPI"], ["cheque", "Cheque"]].map(([a, b]) => ({ value: a, label: b }))} /></Field>
        <Field label="UTR / cheque number" required><Input value={v.reference} onChange={(e) => setV((s) => ({ ...s, reference: e.target.value }))} /></Field>
        <Field label="Proof (optional)" className="sm:col-span-2"><FilesInput value={v.proof ? [v.proof] : []} onChange={(x) => setV((s) => ({ ...s, proof: x[0] || null }))} max={1} portal /></Field>
      </div>
    </Dialog>
  );
}

export function ClientService() {
  const { data, refetch } = useApi("/portal/summary");
  const [raise, setRaise] = useState(new URLSearchParams(window.location.search).get("new") === "1");
  const [rate, setRate] = useState(null);
  const [open, setOpen] = useState(null);
  usePageTitle("Service");
  return (
    <div className="space-y-5">
      <Head title="Service requests" sub="Breakdowns, maintenance and anything that needs a visit" actions={<Button onClick={() => setRaise(true)}><Plus className="h-4 w-4" />Report a problem</Button>} />
      <Panel title="All requests" bodyClass="p-3"><EntityList entityKey="tickets" embedded onOpen={(d) => (["resolved", "closed"].includes(d.status) && !d.rating ? setRate(d) : setOpen(d.id))} /></Panel>
      {raise && <RaiseTicket onClose={() => setRaise(false)} onDone={() => { setRaise(false); refetch(); }} />}
      {rate && <RateTicket t={rate} onClose={() => setRate(null)} />}
      {open && <RecordSheet entity="tickets" id={open} onClose={() => setOpen(null)} />}
    </div>
  );
}

function RaiseTicket({ onClose, onDone }) {
  const [v, setV] = useState({ title: "", description: "", priority: "normal", category: "breakdown", photos: [] });
  const [busy, setBusy] = useState(false);
  const invalidate = useInvalidate();
  return (
    <Dialog open onOpenChange={(x) => !x && onClose()} title="Report a problem" description="For an outage, also call the breakdown line."
      footer={<><Button variant="outline" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={async () => { setBusy(true); try { const r = (await api.post("/portal/tickets", v)).data; toast.success(`Logged as ${r.reference}`); invalidate("/e/tickets"); onDone(); } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(false); } }}>Send</Button></>}>
      <div className="space-y-3">
        <Field label="What's wrong?" required><Input value={v.title} onChange={(e) => setV((s) => ({ ...s, title: e.target.value }))} placeholder="e.g. LT panel ACB tripping" /></Field>
        <Field label="Details"><Textarea value={v.description} onChange={(e) => setV((s) => ({ ...s, description: e.target.value }))} /></Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="How urgent?"><Select value={v.priority} onChange={(e) => setV((s) => ({ ...s, priority: e.target.value }))} options={[["urgent", "Urgent: supply is down"], ["high", "High: running, at risk"], ["normal", "Normal"], ["low", "Low"]].map(([a, b]) => ({ value: a, label: b }))} /></Field>
          <Field label="Type"><Select value={v.category} onChange={(e) => setV((s) => ({ ...s, category: e.target.value }))} options={[["breakdown", "Breakdown"], ["maintenance", "Maintenance"], ["modification", "Change or addition"], ["other", "Something else"]].map(([a, b]) => ({ value: a, label: b }))} /></Field>
        </div>
        <Field label="Photos"><FilesInput value={v.photos} onChange={(x) => setV((s) => ({ ...s, photos: x }))} max={6} portal /></Field>
      </div>
    </Dialog>
  );
}

function RateTicket({ t, onClose }) {
  const [r, setR] = useState(5);
  const [fb, setFb] = useState("");
  const invalidate = useInvalidate();
  const send = async (reopen) => { try { await api.post(`/portal/tickets/${t.id}/rate`, { rating: r, feedback: fb, reopen }); toast.success(reopen ? "Reopened; we'll call you" : "Thanks for the feedback"); invalidate("/e/tickets"); onClose(); } catch (ex) { toast.error(errMsg(ex)); } };
  return (
    <Dialog open onOpenChange={(x) => !x && onClose()} title={`How did we do? ${t.code}`} description={t.title}
      footer={<><Button variant="outline" onClick={() => send(true)}>Still not fixed</Button><Button onClick={() => send(false)}>Send rating</Button></>}>
      <div className="space-y-3">
        <div className="flex gap-1" role="radiogroup" aria-label="Rating">{[1, 2, 3, 4, 5].map((n) => <button key={n} type="button" role="radio" aria-checked={r === n} onClick={() => setR(n)} aria-label={`${n} stars`}><Star className={cn("h-7 w-7", n <= r ? "fill-signal text-signal-bright" : "text-steel")} /></button>)}</div>
        <Field label="Anything to add?"><Textarea value={fb} onChange={(e) => setFb(e.target.value)} /></Field>
      </div>
    </Dialog>
  );
}

export function ClientNew() {
  const { meta } = useAuth();
  const [v, setV] = useState({ service: "", supply: "", load_kva: "", message: "", attachments: [] });
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(null);
  usePageTitle("New requirement");
  return (
    <div className="max-w-2xl">
      <Head title="Tell us about a new requirement" sub="An addition, a new site, solar, an upgrade. It goes straight to your account manager." />
      {done ? <Alert tone="green" title="Thank you">Reference {done}. We'll call you to discuss.</Alert> : (
        <div className="space-y-3 rounded-xl border border-edge bg-surface p-5">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="What do you need?"><Select value={v.service} onChange={(e) => setV((s) => ({ ...s, service: e.target.value }))} options={meta?.options?.services || []} placeholder="Choose" /></Field>
            <Field label="Approximate load (kVA)"><Input inputMode="decimal" value={v.load_kva} onChange={(e) => setV((s) => ({ ...s, load_kva: e.target.value }))} /></Field>
          </div>
          <Field label="Details"><Textarea value={v.message} onChange={(e) => setV((s) => ({ ...s, message: e.target.value }))} rows={4} /></Field>
          <Field label="Drawings or photos"><FilesInput value={v.attachments} onChange={(x) => setV((s) => ({ ...s, attachments: x }))} portal /></Field>
          <Button loading={busy} onClick={async () => { setBusy(true); try { setDone((await api.post("/portal/requirement", { ...v, load_kva: v.load_kva ? Number(v.load_kva) : null })).data.reference); } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(false); } }}><Send className="h-4 w-4" />Send</Button>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ consultant
export function ConsultantHome() {
  const { user } = useAuth();
  const { data, refetch } = useApi("/portal/summary");
  const [appr, setAppr] = useState(null);
  const [rfi, setRfi] = useState(null);
  const [open, setOpen] = useState(null);
  usePageTitle("Consultant portal");
  if (!data) return <Skeleton className="h-96" />;
  return (
    <div className="space-y-5">
      <Head title={`Welcome, ${user.name.split(" ")[0]}`} sub="Projects where you're the consultant or architect" />
      <div className="grid gap-4 lg:grid-cols-2">{data.projects.map((p) => (
        <div key={p.id} className="rounded-xl border border-edge bg-surface p-5"><p className="font-display text-[17px] font-bold">{p.name}</p><p className="text-sm text-muted">{p.code}, {p.town}</p>
          <div className="mt-3 flex items-center gap-3"><Progress value={p.percent_complete || 0} tone="signal" className="h-2" /><span className="text-sm font-semibold tabular">{pct(p.percent_complete || 0, 0)}</span></div></div>
      ))}</div>
      <Panel title="Drawings for your review" bodyClass="p-0">
        <Table columns={[{ label: "Drawing", render: (d) => <span><span className="block font-medium">{d.number} {d.title}</span><span className="text-xs text-muted">Revision {d.revision}, sent {fmtDate(d.submitted_on)}</span></span> },
          { label: "", render: (d) => <div className="flex justify-end"><Button size="sm" onClick={() => setAppr({ entity: "drawings", id: d.id, title: `Drawing ${d.number} ${d.title} (rev ${d.revision})` })}>Review</Button></div> }]} rows={data.drawings_to_review} empty="Nothing to review" />
      </Panel>
      <Panel title="Questions for you (RFIs)" bodyClass="p-0">
        <Table columns={[{ label: "Question", render: (r) => <span><span className="block font-medium">{r.subject}</span><span className="text-xs text-muted">{r.question}</span></span> }, { label: "Reply by", render: (r) => <span className={cn(r.due_on < todayIST() && "font-semibold text-bad")}>{fmtDate(r.due_on)}</span> },
          { label: "", render: (r) => <div className="flex justify-end"><Button size="sm" variant="outline" onClick={() => setRfi(r)}><MessageSquare className="h-3.5 w-3.5" />Answer</Button></div> }]} rows={data.rfis} empty="No open questions" />
      </Panel>
      <Panel title="Test reports" bodyClass="p-0">
        <Table columns={[{ label: "Test", render: (t) => <button type="button" className="font-medium text-cable hover:underline" onClick={() => setOpen(t.id)}>{t.equipment}</button> }, { label: "Type", render: (t) => (t.test_type || "").replace(/_/g, " ") }, { label: "Date", render: (t) => fmtDate(t.date) },
          { label: "Result", render: (t) => <Badge tone={t.result === "pass" ? "green" : t.result === "fail" ? "red" : "gray"}>{t.result || t.status}</Badge> }]} rows={data.tests} empty="No test reports yet" />
      </Panel>
      {appr && <ApproveDialog item={appr} onClose={() => setAppr(null)} onDone={() => { setAppr(null); refetch(); }} />}
      {rfi && <AnswerRfi r={rfi} onClose={() => setRfi(null)} onDone={() => { setRfi(null); refetch(); }} />}
      {open && <RecordSheet entity="test_reports" id={open} onClose={() => setOpen(null)} />}
    </div>
  );
}

function AnswerRfi({ r, onClose, onDone }) {
  const [a, setA] = useState("");
  return (
    <Dialog open onOpenChange={(x) => !x && onClose()} title={r.subject} description={r.question}
      footer={<><Button variant="outline" onClick={onClose}>Cancel</Button><Button disabled={!a.trim()} onClick={async () => { try { await api.post(`/portal/rfis/${r.id}/answer`, { answer: a }); toast.success("Answer sent"); onDone(); } catch (ex) { toast.error(errMsg(ex)); } }}>Send answer</Button></>}>
      <Field label="Your answer"><Textarea value={a} onChange={(e) => setA(e.target.value)} rows={5} autoFocus /></Field>
    </Dialog>
  );
}

// ------------------------------------------------------------------ vendor
export function VendorHome() {
  const { data, refetch } = useApi("/portal/summary");
  const [quote, setQuote] = useState(null);
  const [bill, setBill] = useState(null);
  usePageTitle("Vendor portal");
  if (!data) return <Skeleton className="h-96" />;
  return (
    <div className="space-y-5">
      <Head title={data.vendor?.name || "Vendor portal"} sub="Requests for quotation, purchase orders, bills and payments" />
      <Panel title="Requests for quotation" bodyClass="p-0">
        <Table columns={[{ label: "RFQ", render: (r) => <span><span className="block font-medium">{r.code}</span><span className="text-xs text-muted">{r.lines?.length} items</span></span> }, { label: "Quote by", render: (r) => fmtDate(r.due_on) },
          { label: "Status", render: (r) => <Badge tone={r.status === "closed" ? "gray" : "blue"}>{r.status === "closed" ? (r.awarded_to === data.vendor?.id ? "Awarded to you" : "Closed") : "Open"}</Badge> },
          { label: "", render: (r) => r.status !== "closed" && <div className="flex justify-end"><Button size="sm" onClick={() => setQuote(r)}><Send className="h-3.5 w-3.5" />Quote</Button></div> }]} rows={data.rfqs} empty="No RFQs right now" />
      </Panel>
      <Panel title="Purchase orders" bodyClass="p-0">
        <Table columns={[{ label: "PO", render: (p) => <button type="button" className="font-medium text-cable hover:underline" onClick={() => openFile(`/e/purchase_orders/${p.id}/pdf`, { name: `${p.code}.pdf`, type: "application/pdf", kind: "purchase_order" })}>{p.code}</button> },
          { label: "Date", render: (p) => fmtDate(p.date) }, { label: "Deliver by", render: (p) => fmtDate(p.delivery_by) }, { label: "Value", right: true, render: (p) => inr(p.total) }, { label: "Status", render: (p) => <Badge>{(p.status || "").replace(/_/g, " ")}</Badge> },
          { label: "", render: (p) => ["received", "partly_received", "sent", "acknowledged"].includes(p.status) && <div className="flex justify-end"><Button size="sm" variant="outline" onClick={() => setBill(p)}><Upload className="h-3.5 w-3.5" />Send bill</Button></div> }]} rows={data.pos} empty="No purchase orders" />
      </Panel>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Your bills" bodyClass="p-0"><Table dense columns={[{ label: "Bill", key: "bill_no" }, { label: "Date", render: (b) => fmtDate(b.bill_date) }, { label: "Amount", right: true, render: (b) => inr(b.total) }, { label: "Status", render: (b) => <Badge tone={b.status === "paid" ? "green" : "gray"}>{(b.status || "").replace(/_/g, " ")}</Badge> }]} rows={data.bills} empty="No bills yet" /></Panel>
        <Panel title="Payments received" bodyClass="p-0"><Table dense columns={[{ label: "Date", render: (p) => fmtDate(p.date) }, { label: "Reference", key: "code" }, { label: "Amount", right: true, render: (p) => inr(p.amount) }]} rows={data.payments} empty="No payments yet" /></Panel>
      </div>
      {quote && <QuoteDialog rfq={quote} onClose={() => setQuote(null)} onDone={() => { setQuote(null); refetch(); }} />}
      {bill && <BillDialog po={bill} onClose={() => setBill(null)} onDone={() => { setBill(null); refetch(); }} />}
    </div>
  );
}

function QuoteDialog({ rfq, onClose, onDone }) {
  const [lines, setLines] = useState(rfq.lines.map(() => ({ rate: "", make: "", delivery_days: "", gst_rate: "18" })));
  const [v, setV] = useState({ freight: "", payment_terms: "30 days", valid_until: "" });
  const total = rfq.lines.reduce((a, ln, i) => a + (Number(lines[i].rate) || 0) * (Number(ln.qty) || 0), 0);
  return (
    <Dialog open wide onOpenChange={(x) => !x && onClose()} title={`Quote for ${rfq.code}`} description="Rates without GST. You can change your quote until the RFQ closes."
      footer={<><span className="mr-auto text-sm">Total before GST <span className="font-semibold tabular">{inr(total)}</span></span><Button variant="outline" onClick={onClose}>Cancel</Button><Button onClick={async () => { try { await api.post(`/portal/rfqs/${rfq.id}/quote`, { lines: lines.map((l) => ({ ...l, rate: Number(l.rate) || null, delivery_days: Number(l.delivery_days) || null })), ...v, freight: Number(v.freight) || null }); toast.success("Quote sent"); onDone(); } catch (ex) { toast.error(errMsg(ex)); } }}>Send quote</Button></>}>
      <div className="space-y-3">
        {rfq.lines.map((ln, i) => (
          <div key={i} className="rounded-lg border border-edge p-3">
            <p className="text-sm font-medium">{ln.description}</p><p className="text-xs text-muted">{num(ln.qty)} {ln.unit}</p>
            <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Input placeholder="Rate ₹" inputMode="decimal" value={lines[i].rate} onChange={(e) => setLines(lines.map((x, j) => (j === i ? { ...x, rate: e.target.value } : x)))} aria-label="Rate" />
              <Input placeholder="Make" value={lines[i].make} onChange={(e) => setLines(lines.map((x, j) => (j === i ? { ...x, make: e.target.value } : x)))} aria-label="Make" />
              <Input placeholder="Delivery days" inputMode="numeric" value={lines[i].delivery_days} onChange={(e) => setLines(lines.map((x, j) => (j === i ? { ...x, delivery_days: e.target.value } : x)))} aria-label="Delivery days" />
              <Select value={lines[i].gst_rate} onChange={(e) => setLines(lines.map((x, j) => (j === i ? { ...x, gst_rate: e.target.value } : x)))} options={["0", "5", "12", "18", "28"].map((g) => ({ value: g, label: `GST ${g}%` }))} aria-label="GST" />
            </div>
          </div>
        ))}
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Freight (₹)"><Input inputMode="decimal" value={v.freight} onChange={(e) => setV((s) => ({ ...s, freight: e.target.value }))} /></Field>
          <Field label="Payment terms"><Input value={v.payment_terms} onChange={(e) => setV((s) => ({ ...s, payment_terms: e.target.value }))} /></Field>
          <Field label="Valid until"><Input type="date" value={v.valid_until} onChange={(e) => setV((s) => ({ ...s, valid_until: e.target.value }))} /></Field>
        </div>
      </div>
    </Dialog>
  );
}

function BillDialog({ po, onClose, onDone }) {
  const [v, setV] = useState({ bill_no: "", bill_date: todayIST(), eway_bill_no: "", file: null });
  return (
    <Dialog open onOpenChange={(x) => !x && onClose()} title={`Send your bill for ${po.code}`} description="Lines are taken from the PO and what we received; accounts match it with the GRN."
      footer={<><Button variant="outline" onClick={onClose}>Cancel</Button><Button onClick={async () => { try { const r = (await api.post("/portal/vendor-bills", { po_id: po.id, ...v })).data; toast.success(`Bill received: ${r.reference}`); onDone(); } catch (ex) { toast.error(errMsg(ex)); } }}>Send bill</Button></>}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Your bill number" required><Input value={v.bill_no} onChange={(e) => setV((s) => ({ ...s, bill_no: e.target.value }))} /></Field>
        <Field label="Bill date"><Input type="date" value={v.bill_date} onChange={(e) => setV((s) => ({ ...s, bill_date: e.target.value }))} /></Field>
        <Field label="E-way bill number"><Input value={v.eway_bill_no} onChange={(e) => setV((s) => ({ ...s, eway_bill_no: e.target.value }))} /></Field>
        <Field label="Bill copy (PDF)"><FilesInput value={v.file ? [v.file] : []} onChange={(x) => setV((s) => ({ ...s, file: x[0] || null }))} max={1} portal /></Field>
      </div>
    </Dialog>
  );
}

// ------------------------------------------------------------------ subcontractor
export function SubcontractorHome() {
  const { data, refetch } = useApi("/portal/summary");
  const [bill, setBill] = useState(null);
  usePageTitle("Subcontractor portal");
  if (!data) return <Skeleton className="h-96" />;
  return (
    <div className="space-y-5">
      <Head title={data.vendor?.name || "Subcontractor portal"} sub="Work orders, running bills and payments" />
      <Panel title="Work orders" bodyClass="p-0">
        <Table columns={[{ label: "Work order", render: (w) => <span><span className="block font-medium">{w.code}</span><span className="text-xs text-muted">{w.scope}</span></span> }, { label: "Period", render: (w) => `${fmtDate(w.start)} to ${fmtDate(w.end)}` },
          { label: "Value", right: true, render: (w) => inr(w.total) }, { label: "Status", render: (w) => <Badge tone={w.status === "active" ? "blue" : "gray"}>{w.status}</Badge> },
          { label: "", render: (w) => ["approved", "active"].includes(w.status) && <div className="flex justify-end"><Button size="sm" onClick={() => setBill(w)}><Receipt className="h-3.5 w-3.5" />Raise a bill</Button></div> }]} rows={data.work_orders} empty="No work orders" />
      </Panel>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Your bills" bodyClass="p-0"><Table dense columns={[{ label: "Bill", key: "code" }, { label: "Up to", render: (b) => fmtDate(b.period_to) }, { label: "Gross", right: true, render: (b) => inr(b.gross) }, { label: "Net payable", right: true, render: (b) => inr(b.net) }, { label: "Status", render: (b) => <Badge>{(b.status || "").replace(/_/g, " ")}</Badge> }]} rows={data.bills} empty="No bills yet" /></Panel>
        <Panel title="Payments" bodyClass="p-0"><Table dense columns={[{ label: "Date", render: (p) => fmtDate(p.date) }, { label: "Reference", key: "code" }, { label: "Amount", right: true, render: (p) => inr(p.amount) }]} rows={data.payments} empty="No payments yet" /></Panel>
      </div>
      {bill && <ScBill wo={bill} onClose={() => setBill(null)} onDone={() => { setBill(null); refetch(); }} />}
    </div>
  );
}

function ScBill({ wo, onClose, onDone }) {
  const [q, setQ] = useState(wo.lines.map(() => ""));
  const [to, setTo] = useState(todayIST());
  const gross = wo.lines.reduce((a, ln, i) => a + (Number(q[i]) || 0) * (Number(ln.rate) || 0), 0);
  return (
    <Dialog open onOpenChange={(x) => !x && onClose()} title={`Running bill on ${wo.code}`} description={`Retention ${wo.retention_pct}% and TDS ${wo.tds_pct}% are deducted when it's approved.`}
      footer={<><span className="mr-auto text-sm">Gross <span className="font-semibold tabular">{inr(gross)}</span></span><Button variant="outline" onClick={onClose}>Cancel</Button><Button onClick={async () => { try { const r = (await api.post("/portal/sc-bills", { work_order_id: wo.id, period_to: to, lines: q.map((x, i) => ({ line: i, this_qty: Number(x) || 0 })) })).data; toast.success(`Bill ${r.reference} sent to the project manager`); onDone(); } catch (ex) { toast.error(errMsg(ex)); } }}>Send bill</Button></>}>
      <div className="space-y-3">
        <Field label="Work done up to"><Input type="date" value={to} onChange={(e) => setTo(e.target.value)} className="w-44" /></Field>
        {wo.lines.map((ln, i) => (
          <div key={i} className="grid grid-cols-[1fr_110px] items-center gap-3"><span className="text-sm">{ln.description}<span className="block text-xs text-muted">{inr(ln.rate)} a {ln.unit}, ordered {num(ln.qty)}</span></span>
            <Input inputMode="decimal" placeholder={`Qty (${ln.unit})`} value={q[i]} onChange={(e) => setQ(q.map((x, j) => (j === i ? e.target.value : x)))} aria-label={`Quantity for ${ln.description}`} /></div>
        ))}
      </div>
    </Dialog>
  );
}

// ------------------------------------------------------------------ partner
export function PartnerHome() {
  const { meta } = useAuth();
  const { data, refetch } = useApi("/portal/summary");
  const [v, setV] = useState({ name: "", phone: "", company: "", town: "", service: "", message: "", consent: false });
  const [busy, setBusy] = useState(false);
  usePageTitle("Referral partner portal");
  if (!data) return <Skeleton className="h-96" />;
  return (
    <div className="space-y-5">
      <Head title={data.partner?.name || "Referrals"} sub={`You earn ${data.partner?.commission_pct || 0}% of the contract value on referrals that become projects.`} />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-edge bg-surface p-4"><p className="text-xs text-muted">Referrals</p><p className="mt-1 font-display text-[24px] font-extrabold tabular">{data.referrals.length}</p></div>
        <div className="rounded-xl border border-edge bg-surface p-4"><p className="text-xs text-muted">Won</p><p className="mt-1 font-display text-[24px] font-extrabold tabular">{data.referrals.filter((r) => r.status === "Won").length}</p></div>
        <div className="rounded-xl border border-edge bg-surface p-4"><p className="text-xs text-muted">Commission earned</p><p className="mt-1 font-display text-[24px] font-extrabold tabular">{inr(data.commission_total)}</p></div>
      </div>
      <div className="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
        <Panel title="Your referrals" bodyClass="p-0">
          <Table columns={[{ label: "Customer", render: (r) => <span><span className="block font-medium">{r.company || r.name}</span><span className="text-xs text-muted">{r.code}, {fmtDate(r.created_at)}</span></span> }, { label: "Need", key: "service" },
            { label: "Status", render: (r) => <Badge tone={r.status === "Won" ? "green" : r.status === "Closed" ? "gray" : "blue"}>{r.status}</Badge> }, { label: "Commission", right: true, render: (r) => (r.commission ? inr(r.commission) : "—") }]} rows={data.referrals} empty="Refer your first customer" />
        </Panel>
        <Panel title="Refer a customer">
          <div className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Customer name" required><Input value={v.name} onChange={(e) => setV((s) => ({ ...s, name: e.target.value }))} /></Field>
              <Field label="Their mobile" required><Input inputMode="tel" value={v.phone} onChange={(e) => setV((s) => ({ ...s, phone: e.target.value }))} /></Field>
              <Field label="Company"><Input value={v.company} onChange={(e) => setV((s) => ({ ...s, company: e.target.value }))} /></Field>
              <Field label="Town"><Input value={v.town} onChange={(e) => setV((s) => ({ ...s, town: e.target.value }))} /></Field>
            </div>
            <Field label="What they need"><Select value={v.service} onChange={(e) => setV((s) => ({ ...s, service: e.target.value }))} options={meta?.options?.services || []} placeholder="Choose" /></Field>
            <Field label="Notes"><Textarea value={v.message} onChange={(e) => setV((s) => ({ ...s, message: e.target.value }))} /></Field>
            <Checkbox checked={v.consent} onChange={(x) => setV((s) => ({ ...s, consent: x }))} label="The customer agreed that Sellandiamman Power Infra may contact them" />
            <Button loading={busy} onClick={async () => { setBusy(true); try { const r = (await api.post("/portal/referrals", v)).data; toast.success(`Referral sent: ${r.reference}`); setV({ name: "", phone: "", company: "", town: "", service: "", message: "", consent: false }); refetch(); } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(false); } }}><HandCoins className="h-4 w-4" />Send referral</Button>
          </div>
        </Panel>
      </div>
    </div>
  );
}

export { Check, X, Phone, MapPin, ClipboardCheck, Users, FieldValue, stateOf, ago, fmtDateTime };
