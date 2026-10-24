// Extra panels and tabs on particular record pages (project hub, lead timeline, RFQ comparison, UPI QR…)
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { MessageCircle, ArrowRightLeft, FileText, Receipt, AlertTriangle, CheckCircle2, Trophy, Send, PhoneCall, Users, ClipboardList, Calendar, Mail, Clock } from "lucide-react";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from "recharts";
import { api, errMsg, openFile, IN_FRAME } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { inr, num, pct, fmtDate, fmtDateTime, ago, todayIST } from "@/lib/format";
import { Button, Badge, Dialog, Field, Input, Select, Alert, Skeleton, Progress } from "@/components/ui/kit";
import { toast } from "sonner";
import { useApi, useInvalidate, optionsFor } from "./lib";
import { RefPicker } from "./fields";
import { Kpi, Panel, Table, Bar } from "./ui";

// ------------------------------------------------------------------ leads
const KIND_ICON = { call: PhoneCall, whatsapp: MessageCircle, meeting: Users, email: Mail, survey: Calendar, proposal: FileText, created: ClipboardList };
function LeadExtra({ doc, refresh }) {
  const { meta, can } = useAuth();
  const nav = useNavigate();
  const { data: tl } = useApi(`/crm/leads/${doc.id}/timeline`);
  const [conv, setConv] = useState(false);
  const [stage, setStage] = useState("");
  const [busy, setBusy] = useState(false);
  const stages = meta.options.lead_stages || [];
  const [ask, setAsk] = useState(null);
  async function move(s, extra = {}) {
    if ((s === "lost" && !extra.lost_reason) || (s === "on_hold" && !extra.hold_until)) { setAsk({ stage: s }); return; }
    setBusy(true);
    try { await api.post(`/crm/leads/${doc.id}/move`, { stage: s, ...extra }); toast.success("Stage changed"); setAsk(null); refresh(); } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(false); setStage(""); }
  }
  async function wa() {
    try {
      const r = await api.get(`/crm/leads/${doc.id}/whatsapp`);
      if (!IN_FRAME) { window.open(r.data.url, "_blank", "noopener"); return; }
      toast("WhatsApp message ready", { description: <a href={r.data.url} target="_blank" rel="noopener noreferrer" className="font-semibold text-cable underline">Open WhatsApp</a>, duration: 10000 });
    } catch (ex) { toast.error(errMsg(ex)); }
  }
  const overdue = doc.response_due_at && !doc.first_response_at && doc.response_due_at < new Date().toISOString();
  return (
    <div className="grid items-start gap-4 lg:grid-cols-[1fr_340px]">
      <Panel title="Timeline" bodyClass="p-0">
        {!tl ? <Skeleton className="m-4 h-24" /> : (
          <ol className="divide-y divide-edge">
            {tl.map((t, i) => {
              const I = KIND_ICON[t.kind] || Clock;
              return (
                <li key={i} className="flex gap-3 px-4 py-3">
                  <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-canvas text-muted"><I className="h-3.5 w-3.5" /></span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm">{t.entity ? <Link to={`/erp/e/${t.entity}/${t.id}`} className="hover:underline">{t.title}</Link> : t.title}</p>
                    {t.text && <p className="text-sm text-muted">{t.text}</p>}
                    <p className="text-xs text-muted">{fmtDateTime(t.at)}{t.by ? `, ${t.by}` : ""}</p>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </Panel>
      <div className="space-y-3">
        {overdue && <Alert tone="red" icon={AlertTriangle} title="First response is overdue">Respond by was {fmtDateTime(doc.response_due_at)}. Log a call to clear it.</Alert>}
        <Panel title="Next step">
          <div className="space-y-2">
            {can("crm", "w") && (
              <Select value={stage} onChange={(e) => { setStage(e.target.value); if (e.target.value) move(e.target.value); }} disabled={busy}
                options={stages.filter((s) => s.value !== doc.stage)} placeholder="Move to stage…" />
            )}
            <div className="grid grid-cols-2 gap-2">
              <Button variant="outline" size="sm" onClick={wa}><MessageCircle className="h-4 w-4" />WhatsApp</Button>
              <Button variant="outline" size="sm" as={Link} to={`/erp/e/activities?new=1&lead_id=${doc.id}`}><PhoneCall className="h-4 w-4" />Log a call</Button>
              <Button variant="outline" size="sm" as={Link} to={`/erp/e/surveys?new=1&lead_id=${doc.id}`}><Calendar className="h-4 w-4" />Book survey</Button>
              <Button variant="outline" size="sm" as={Link} to={`/erp/e/boqs?new=1&lead_id=${doc.id}`}><ClipboardList className="h-4 w-4" />Start BOQ</Button>
            </div>
            {!doc.project_id && can("crm", "w") && ["quoted", "negotiation", "won"].includes(doc.stage) && <Button className="w-full" onClick={() => setConv(true)}><Trophy className="h-4 w-4" />Won: create client & project</Button>}
            {doc.project_id && <Button as={Link} to={`/erp/e/projects/${doc.project_id}`} variant="dark" className="w-full">Open the project</Button>}
          </div>
        </Panel>
        {doc.score != null && (
          <Panel title="Lead score">
            <div className="flex items-center gap-3"><span className="font-display text-[28px] font-extrabold tabular">{doc.score}</span><Bar value={doc.score} max={100} tone={doc.score >= 70 ? "good" : doc.score >= 40 ? "signal" : "bad"} /></div>
            <p className="mt-1 text-xs text-muted">From load, LT/HT, timeline, source and engagement.</p>
          </Panel>
        )}
      </div>
      <Dialog open={!!ask} onOpenChange={(x) => { if (!x) { setAsk(null); setStage(""); } }} title={ask?.stage === "lost" ? "Mark as lost" : "Put on hold"}
        footer={<><Button variant="outline" onClick={() => { setAsk(null); setStage(""); }}>Cancel</Button><Button loading={busy} onClick={() => move(ask.stage, ask)}>Save</Button></>}>
        {ask?.stage === "lost" ? (
          <div className="space-y-3">
            <Field label="Why was it lost?" required><Select value={ask.lost_reason || ""} onChange={(e) => setAsk((a) => ({ ...a, lost_reason: e.target.value }))} options={meta.options.lost_reasons || []} placeholder="Choose" /></Field>
            <Field label="Note"><Input value={ask.lost_note || ""} onChange={(e) => setAsk((a) => ({ ...a, lost_note: e.target.value }))} /></Field>
          </div>
        ) : ask && <Field label="Get back in touch on" required><Input type="date" value={ask.hold_until || ""} onChange={(e) => setAsk((a) => ({ ...a, hold_until: e.target.value }))} /></Field>}
      </Dialog>
      <ConvertDialog open={conv} onClose={() => setConv(false)} lead={doc} onDone={(r) => { setConv(false); refresh(); if (r.project_id) nav(`/erp/e/projects/${r.project_id}`); }} />
    </div>
  );
}

function ConvertDialog({ open, onClose, lead, onDone }) {
  const [v, setV] = useState({ account_id: lead.account_id || null, project_name: "", manager_id: null, start_date: todayIST(), create_project: true });
  const [refs, setRefs] = useState({ accounts: lead._refs?.accounts || {}, users: {} });
  const [busy, setBusy] = useState(false);
  const addRef = (e, id, t) => setRefs((r) => ({ ...r, [e]: { ...(r[e] || {}), [id]: t } }));
  return (
    <Dialog open={open} onOpenChange={(x) => !x && onClose()} title="Convert to client and project" description="Carries the contact, surveys, BOQs and accepted proposal over."
      footer={<><Button variant="outline" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={async () => { setBusy(true); try { const r = await api.post(`/crm/leads/${lead.id}/convert`, v); toast.success("Converted"); onDone(r.data); } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(false); } }}>Convert</Button></>}>
      <div className="space-y-3">
        <Field label="Existing client" hint="Leave empty to create a new client from the lead"><RefPicker f={{ ref: "accounts" }} value={v.account_id} onChange={(x) => setV((s) => ({ ...s, account_id: x }))} refs={refs} onRefTitle={addRef} placeholder="New client" /></Field>
        <Field label="Project name"><Input value={v.project_name} onChange={(e) => setV((s) => ({ ...s, project_name: e.target.value }))} placeholder={`${lead.company || lead.name} — …`} /></Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Project manager"><RefPicker f={{ ref: "users" }} value={v.manager_id} onChange={(x) => setV((s) => ({ ...s, manager_id: x }))} refs={refs} onRefTitle={addRef} /></Field>
          <Field label="Start"><Input type="date" value={v.start_date} onChange={(e) => setV((s) => ({ ...s, start_date: e.target.value }))} /></Field>
        </div>
      </div>
    </Dialog>
  );
}

// ------------------------------------------------------------------ projects
const COUNT_LABEL = { rfis: ["Open RFIs", "rfis"], snags: ["Open snags", "snags"], ncrs: ["Open NCRs", "ncrs"], hindrances: ["Open hindrances", "hindrances"], drawings: ["Drawings with client", "drawings"],
  permits: ["Active permits", "permits"], purchase_requests: ["Material requests", "purchase_requests"], variations: ["Variations pending", "variations"] };
function ProjectExtra({ doc, refresh }) {
  const { data, isLoading } = useApi(`/projects/${doc.id}/hub`);
  const { can } = useAuth();
  const [busy, setBusy] = useState(false);
  if (isLoading || !data) return <Skeleton className="h-48" />;
  const n = data.numbers || {};
  async function raFromMb() {
    setBusy(true);
    try { const r = await api.post(`/projects/${doc.id}/ra-from-mb`, {}); toast.success(`RA bill ${r.data.code || ""} drafted from the measurement book`); refresh(); } catch (ex) { toast.error(errMsg(ex)); } finally { setBusy(false); }
  }
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {can("projects", "w") && <Button size="sm" variant="dark" loading={busy} onClick={raFromMb}><Receipt className="h-4 w-4" />Draft RA bill from measurements</Button>}
        <Button size="sm" variant="outline" onClick={() => openFile(`/projects/${doc.id}/handover-pack.pdf`, { name: `handover-${doc.code}.pdf`, type: "application/pdf", kind: "handover-pack" })}><FileText className="h-4 w-4" />Handover pack</Button>
        <Button size="sm" variant="outline" as={Link} to={`/erp/e/dprs?new=1&project_id=${doc.id}`}>Add daily report</Button>
      </div>
      {data.risks?.length > 0 && (
        <div className="space-y-2">{data.risks.map((r, i) => <Alert key={i} tone={r.tone === "red" ? "red" : "amber"} icon={AlertTriangle}>{r.text}</Alert>)}</div>
      )}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi label="Contract value" value={n.contract_value} fmt="inr" />
        <Kpi label="Work done" value={n.percent_complete} fmt="pct" sub={`earned ${inr(n.earned_value, { compact: true })}`} />
        <Kpi label="Billed / received" value={n.billed} fmt="inr" sub={`received ${inr(n.received, { compact: true })}`} />
        <Kpi label={n.over_under_billed < 0 ? "Under-billed" : "Over-billed"} value={Math.abs(n.over_under_billed || 0)} fmt="inr" tone={n.over_under_billed < -0.1 * (n.contract_value || 1) ? "bad" : undefined} />
        {n.forecast_margin_pct !== undefined && <Kpi label="Forecast margin" value={n.forecast_margin_pct} fmt="pct" tone={n.forecast_margin_pct < 8 ? "bad" : n.forecast_margin_pct < 15 ? "warn" : "good"} sub={inr(n.forecast_margin, { compact: true })} />}
        {n.actual_cost !== undefined && <Kpi label="Cost so far" value={n.actual_cost} fmt="inr" sub={`committed ${inr(n.committed, { compact: true })}`} />}
        {n.cost_to_complete !== undefined && <Kpi label="Cost to complete" value={n.cost_to_complete} fmt="inr" sub={`budget ${inr(n.budget, { compact: true })}`} />}
        <Kpi label="Retention held" value={n.retention_held} fmt="inr" />
      </div>
      <div className="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
        <Panel title="Progress against plan" sub="S-curve, % of work">
          {data.s_curve?.length ? (
            <div className="h-56">
              <ResponsiveContainer>
                <LineChart data={data.s_curve} margin={{ top: 4, right: 8, left: -18, bottom: 0 }}>
                  <CartesianGrid stroke="rgb(var(--edge))" vertical={false} />
                  <XAxis dataKey="month" tick={{ fontSize: 11, fill: "rgb(var(--muted))" }} tickLine={false} axisLine={false} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "rgb(var(--muted))" }} tickLine={false} axisLine={false} />
                  <Tooltip formatter={(v) => `${v}%`} contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="planned" name="Planned" stroke="#A9ADB3" strokeWidth={2} dot={false} strokeDasharray="4 3" isAnimationActive={false} />
                  <Line type="monotone" dataKey="actual" name="Actual" stroke="#0A1626" strokeWidth={2.5} dot={{ r: 2.5 }} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : <p className="text-sm text-muted">Add milestones with dates and weights to see the plan.</p>}
        </Panel>
        <Panel title="Open items">
          <ul className="grid grid-cols-2 gap-2">
            {Object.entries(data.counts || {}).map(([k, c]) => (
              <li key={k}><Link to={`/erp/e/${COUNT_LABEL[k]?.[1] || k}?project_id=${doc.id}`} className={cn("flex items-center justify-between rounded-md border border-edge px-3 py-2 text-sm hover:bg-canvas", c > 0 && k !== "permits" && "border-signal/60 bg-signal-soft/40")}>
                <span className="text-fg/80">{COUNT_LABEL[k]?.[0] || k}</span><span className="font-semibold tabular">{c}</span></Link></li>
            ))}
          </ul>
        </Panel>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Coming up" bodyClass="p-0">
          <Table dense columns={[{ label: "Milestone", render: (m) => <Link to={`/erp/e/milestones/${m.id}`} className="hover:underline">{m.name}</Link> }, { label: "Finish", render: (m) => <span className={cn(m.planned_end < todayIST() && "font-semibold text-bad")}>{fmtDate(m.planned_end)}</span> },
            { label: "Done", right: true, render: (m) => pct(m.percent, 0) }]} rows={data.upcoming} empty="No open milestones" />
        </Panel>
        <Panel title="Latest daily reports" bodyClass="p-0">
          <Table dense columns={[{ label: "Date", render: (d) => <Link to={`/erp/e/dprs/${d.id}`} className="hover:underline">{fmtDate(d.date)}</Link> }, { label: "Work done", render: (d) => <span className="line-clamp-1">{Array.isArray(d.work_done) ? d.work_done.map((w) => w.description).filter(Boolean).join("; ") || "—" : d.work_done || d.summary || "—"}</span> },
            { label: "Crew", right: true, render: (d) => (Array.isArray(d.manpower) ? d.manpower.reduce((a, m) => a + (Number(m.own) || 0) + (Number(m.subcon) || 0), 0) : d.manpower ?? "—") }]} rows={data.dprs} empty="No reports yet" />
        </Panel>
      </div>
      {data.liaison?.length > 0 && (
        <Panel title="Approvals with TNPDCL / CEIG" bodyClass="p-0">
          <Table dense columns={[{ label: "Application", render: (l) => <Link to={`/erp/e/liaisons/${l.id}`} className="hover:underline">{l.title || l.code}</Link> }, { label: "Authority", render: (l) => (l.authority || "").toUpperCase() }, { label: "Stage", render: (l) => <Badge tone="blue">{(l.stage || l.status || "").replace(/_/g, " ")}</Badge> }]} rows={data.liaison} />
        </Panel>
      )}
    </div>
  );
}

function GanttTab({ doc }) {
  const { data } = useApi(`/projects/${doc.id}/gantt`);
  if (!data) return <Skeleton className="h-48" />;
  if (!data.length) return <p className="py-8 text-center text-sm text-muted">No milestones yet. <Link to={`/erp/e/milestones?new=1&project_id=${doc.id}`} className="text-cable underline">Add the first one</Link></p>;
  const start = Math.min(...data.map((m) => +new Date(m.planned_start || doc.start_date)));
  const end = Math.max(...data.map((m) => +new Date(m.planned_end || doc.end_date)));
  const span = Math.max(1, end - start);
  const today = +new Date(todayIST());
  return (
    <div className="overflow-x-auto rounded-xl border border-edge bg-surface p-4">
      <div className="relative min-w-[640px] space-y-2">
        {today >= start && today <= end && <div className="absolute bottom-0 top-0 z-10 w-px bg-bad" style={{ left: `calc(200px + (100% - 200px) * ${(today - start) / span})` }} title="Today" />}
        {data.map((m) => {
          const s = +new Date(m.planned_start); const e = +new Date(m.planned_end);
          const late = m.status !== "done" && m.planned_end < todayIST();
          return (
            <div key={m.id} className="grid grid-cols-[200px_1fr] items-center gap-0 text-sm">
              <Link to={`/erp/e/milestones/${m.id}`} className="truncate pr-3 hover:underline">{m.wbs ? `${m.wbs}. ` : ""}{m.name}</Link>
              <div className="relative h-6 rounded bg-canvas">
                <div className={cn("absolute top-0 h-6 overflow-hidden rounded", late ? "bg-bad/20" : "bg-ink/15")} style={{ left: `${((s - start) / span) * 100}%`, width: `${Math.max(1.5, ((e - s) / span) * 100)}%` }}>
                  <div className={cn("h-full", late ? "bg-bad" : m.status === "done" ? "bg-good" : "bg-ink")} style={{ width: `${m.percent || 0}%` }} />
                </div>
              </div>
            </div>
          );
        })}
        <div className="grid grid-cols-[200px_1fr] pt-1 text-xs text-muted"><span /><span className="flex justify-between"><span>{fmtDate(new Date(start).toISOString().slice(0, 10))}</span><span>{fmtDate(new Date(end).toISOString().slice(0, 10))}</span></span></div>
      </div>
    </div>
  );
}

function MaterialsTab({ doc }) {
  const { data } = useApi(`/projects/${doc.id}/materials`);
  if (!data) return <Skeleton className="h-48" />;
  return (
    <Panel title="Material reconciliation" sub="Issued to site, returned, used (from daily reports) and against the BOQ" bodyClass="p-0">
      <Table columns={[{ label: "Item", key: "name" }, { label: "BOQ", right: true, render: (r) => num(r.boq) }, { label: "Issued", right: true, render: (r) => num(r.issued) }, { label: "Returned", right: true, render: (r) => num(r.returned) },
        { label: "Used", right: true, render: (r) => num(r.used) }, { label: "At site", right: true, render: (r) => num(r.balance_at_site) }, { label: "Unit", key: "unit" },
        { label: "Wastage", right: true, render: (r) => <span className={cn(r.wastage_pct > 5 && "font-semibold text-bad")}>{r.wastage_pct == null ? "—" : pct(r.wastage_pct)}</span> }]} rows={data} empty="No material issued yet" />
    </Panel>
  );
}

// ------------------------------------------------------------------ procurement
function RfqExtra({ doc, refresh }) {
  const { data } = useApi(`/rfqs/${doc.id}/comparison`);
  const nav = useNavigate();
  const { can } = useAuth();
  if (!data) return <Skeleton className="h-32" />;
  if (!data.totals.length) return <Alert tone="blue" icon={Send}>Waiting for quotes. Vendors on this RFQ see it in their portal and can quote there, or add a quote yourself under Vendor quotes.</Alert>;
  async function award(q) {
    try { const po = (await api.post(`/rfqs/${doc.id}/award`, { quote_id: q.quote_id })).data; toast.success(`Purchase order ${po.code} drafted`); nav(`/erp/e/purchase_orders/${po.id}`); } catch (ex) { toast.error(errMsg(ex)); }
  }
  return (
    <Panel title="Quote comparison" sub="Lowest rate per line is highlighted" bodyClass="p-0">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-edge text-left text-xs text-muted">
            <tr><th className="px-3 py-2 font-medium">Item</th><th className="px-3 py-2 text-right font-medium">Qty</th>{data.totals.map((t) => <th key={t.vendor_id} className="px-3 py-2 text-right font-medium">{t.vendor}<Badge tone={t.rank === "L1" ? "green" : "gray"} className="ml-1.5">{t.rank}</Badge></th>)}</tr>
          </thead>
          <tbody className="divide-y divide-edge">
            {data.rows.map((r) => (
              <tr key={r.line}><td className="px-3 py-2">{r.description}</td><td className="px-3 py-2 text-right tabular">{num(r.qty)} {r.unit}</td>
                {data.totals.map((t) => { const c = r.quotes.find((x) => x.vendor_id === t.vendor_id) || {}; return <td key={t.vendor_id} className={cn("px-3 py-2 text-right tabular", c.lowest && "bg-good/10 font-semibold text-good")}>{c.rate ? inr(c.rate) : "—"}{c.make ? <span className="block text-xs font-normal text-muted">{c.make}</span> : null}</td>; })}
              </tr>
            ))}
          </tbody>
          <tfoot className="border-t border-edge">
            <tr className="font-semibold"><td className="px-3 py-2" colSpan={2}>Total</td>{data.totals.map((t) => <td key={t.vendor_id} className="px-3 py-2 text-right tabular">{inr(t.total)}</td>)}</tr>
            <tr className="text-xs text-muted"><td className="px-3 py-1" colSpan={2}>Payment / valid until</td>{data.totals.map((t) => <td key={t.vendor_id} className="px-3 py-1 text-right">{t.payment_terms || "—"}, {fmtDate(t.valid_until)}</td>)}</tr>
            {doc.status !== "closed" && can("procurement", "w") && <tr><td colSpan={2} />{data.totals.map((t) => <td key={t.vendor_id} className="px-3 py-2 text-right"><Button size="sm" variant={t.rank === "L1" ? "primary" : "outline"} onClick={() => award(t)}>Award</Button></td>)}</tr>}
          </tfoot>
        </table>
      </div>
    </Panel>
  );
}

function PrExtra({ doc }) {
  const nav = useNavigate();
  if (doc.status !== "approved") return null;
  return (
    <Alert tone="green" icon={CheckCircle2} title="Approved">
      <span className="flex flex-wrap items-center gap-3">Ready to ask vendors for prices.
        <Button size="sm" onClick={async () => { try { const r = (await api.post(`/purchase_requests/${doc.id}/to-rfq`, {})).data; toast.success(`RFQ ${r.code} created`); nav(`/erp/e/rfqs/${r.id}`); } catch (ex) { toast.error(errMsg(ex)); } }}><Send className="h-4 w-4" />Create RFQ</Button></span>
    </Alert>
  );
}

// ------------------------------------------------------------------ finance
function InvoiceExtra({ doc }) {
  const [qr, setQr] = useState(null);
  if (!["issued", "part_paid"].includes(doc.status)) return null;
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-edge bg-surface p-4">
      <div className="min-w-0 flex-1"><p className="text-sm text-muted">Balance due</p><p className="font-display text-[24px] font-extrabold tabular">{inr(doc.balance)}</p>{doc.due_date && <p className={cn("text-xs", doc.due_date < todayIST() ? "font-semibold text-bad" : "text-muted")}>Due {fmtDate(doc.due_date)}</p>}</div>
      <Button size="sm" variant="outline" onClick={async () => { try { setQr((await api.get(`/finance/upi/${doc.id}`)).data); } catch (ex) { toast.error(errMsg(ex)); } }}>Show UPI QR</Button>
      <Button size="sm" as={Link} to={`/erp/e/receipts?new=1&account_id=${doc.account_id}`} variant="dark">Record a receipt</Button>
      <Dialog open={!!qr} onOpenChange={(x) => !x && setQr(null)} title={`Pay ${inr(qr?.amount)}`} description="Scan with any UPI app">
        {qr && <div className="space-y-3 text-center"><div className="mx-auto w-56 [&_svg]:h-auto [&_svg]:w-full" dangerouslySetInnerHTML={{ __html: qr.qr_svg }} /><p className="break-all text-xs text-muted">{qr.upi_uri}</p>{qr.bank_details && <p className="text-sm">{qr.bank_details}</p>}</div>}
      </Dialog>
    </div>
  );
}

function PartnerExtra({ doc }) {
  const { data } = useApi(`/crm/partners/${doc.id}/statement`);
  if (!data) return null;
  return (
    <Panel title="Referral statement" bodyClass="p-0">
      <Table dense columns={[{ label: "Lead", render: (r) => <Link to={`/erp/e/leads/${r.id}`} className="hover:underline">{r.name || r.code}</Link> }, { label: "Stage", render: (r) => (r.stage || "").replace(/_/g, " ") }, { label: "Value", right: true, render: (r) => inr(r.value) }, { label: "Commission", right: true, render: (r) => inr(r.commission) }]}
        rows={data.rows || data.referrals || []} empty="No referrals yet" foot={["Total", "", "", inr(data.commission_total || data.total)]} />
    </Panel>
  );
}

export const DETAIL_EXTRAS = { leads: LeadExtra, projects: ProjectExtra, rfqs: RfqExtra, purchase_requests: PrExtra, invoices: InvoiceExtra, partners: PartnerExtra };
export const DETAIL_TABS = {
  projects: [{ key: "gantt", label: "Gantt", C: GanttTab }, { key: "materials", label: "Materials", C: MaterialsTab, can: (meta) => !!meta.entities.material_moves }],
};
export { optionsFor };
