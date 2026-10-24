import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Plus, Flame, AlertTriangle, Clock, Users, LayoutGrid, List } from "lucide-react";
import { ResponsiveContainer, BarChart, Bar as RBar, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from "recharts";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { inr, num, pct, ago, fmtDate } from "@/lib/format";
import { Button, Badge, Skeleton, Dialog, Field, Select, Input } from "@/components/ui/kit";
import { toast } from "sonner";
import { useApi, useInvalidate, optLabel } from "../lib";
import { PageHead, Kpi, Panel, Table, usePageTitle } from "../ui";
import { RefPicker } from "../fields";

export function Pipeline() {
  const { meta, can } = useAuth();
  const nav = useNavigate();
  const [owner, setOwner] = useState(null);
  const [service, setService] = useState("");
  const { data, isLoading, refetch } = useApi("/crm/pipeline", { owner: owner || undefined, service: service || undefined });
  const [drag, setDrag] = useState(null);
  const [over, setOver] = useState(null);
  const [ask, setAsk] = useState(null);
  const [ownerRefs, setOwnerRefs] = useState({});
  const invalidate = useInvalidate();
  usePageTitle("Pipeline");
  const fService = meta?.entities?.leads?.fields.find((f) => f.k === "service");
  async function move(lead, stage, extra = {}) {
    if ((stage === "lost" && !extra.lost_reason) || (stage === "on_hold" && !extra.hold_until)) { setAsk({ lead, stage }); return; }
    try { await api.post(`/crm/leads/${lead.id}/move`, { stage, ...extra }); toast.success(`Moved to ${meta.options.lead_stages.find((s) => s.value === stage)?.label}`); setAsk(null); refetch(); invalidate("/e/leads"); } catch (ex) { toast.error(errMsg(ex)); }
  }
  const now = new Date().toISOString();
  return (
    <div className="pb-10">
      <PageHead icon="route" title="Sales pipeline" sub={data ? `Weighted value ${inr(data.weighted_value, { compact: true })}. Drag a card to change its stage.` : "Every open lead by stage"}
        actions={<>
          <div className="w-[180px]"><RefPicker f={{ ref: "users" }} value={owner} onChange={setOwner} refs={{ users: ownerRefs }} onRefTitle={(e, id, t) => setOwnerRefs((r) => ({ ...r, [id]: t }))} placeholder="Everyone" className="h-9" /></div>
          <div className="w-[170px]"><Select value={service} onChange={(e) => setService(e.target.value)} options={meta?.options?.services || []} placeholder="All services" className="h-9" /></div>
          <Button size="sm" variant="outline" as={Link} to="/erp/e/leads"><List className="h-4 w-4" />List</Button>
          {can("crm", "w") && <Button size="sm" as={Link} to="/erp/e/leads?new=1"><Plus className="h-4 w-4" />New lead</Button>}
        </>} />
      {isLoading || !data ? <Skeleton className="h-96" /> : (
        <div className="scrollbar-thin -mx-3 flex gap-3 overflow-x-auto px-3 pb-4 sm:-mx-5 sm:px-5">
          {data.columns.map((c) => {
            const st = meta.entities.leads.status.states.find((s) => s.value === c.stage);
            return (
              <section key={c.stage} aria-label={c.label} onDragOver={(e) => { e.preventDefault(); setOver(c.stage); }} onDragLeave={() => setOver(null)}
                onDrop={(e) => { e.preventDefault(); setOver(null); if (drag && drag.stage !== c.stage) move(drag, c.stage); setDrag(null); }}
                className={cn("flex w-[272px] shrink-0 flex-col rounded-xl bg-fg/[.04] transition-colors", over === c.stage && "bg-signal-soft ring-2 ring-signal")}>
                <header className="flex items-center justify-between px-3 py-2.5">
                  <span className="flex items-center gap-2 text-sm font-semibold"><Badge tone={st?.tone} dot>{c.label}</Badge><span className="text-muted tabular">{c.count}</span></span>
                  <span className="text-xs text-muted tabular">{inr(c.value, { compact: true })}</span>
                </header>
                <ul className="flex-1 space-y-2 px-2 pb-2">
                  {c.items.map((l) => {
                    const late = l.response_due_at && !l.first_response_at && l.response_due_at < now;
                    const follow = l.next_follow_up && l.next_follow_up.slice(0, 10) <= now.slice(0, 10);
                    return (
                      <li key={l.id} draggable={can("crm", "w")} onDragStart={() => setDrag(l)} onDragEnd={() => setDrag(null)}>
                        <button type="button" onClick={() => nav(`/erp/e/leads/${l.id}`)} className={cn("block w-full rounded-lg border border-edge bg-surface p-3 text-left shadow-card hover:border-fg/25", drag?.id === l.id && "opacity-50")}>
                          <div className="flex items-start justify-between gap-2">
                            <span className="min-w-0"><span className="block truncate text-sm font-semibold">{l.company || l.name}</span><span className="block truncate text-xs text-muted">{l.company ? l.name : ""}{l.town ? `${l.company ? ", " : ""}${l.town}` : ""}</span></span>
                            {l.score >= 85 && <Flame className="h-4 w-4 shrink-0 text-bad" aria-label="Hot lead" />}
                          </div>
                          <p className="mt-1.5 truncate text-xs">{optLabel(meta, fService, l.service)}{l.load_kva ? `, ${num(l.load_kva)} kVA` : ""}{["LT", "HT"].includes(l.supply) ? ` ${l.supply}` : ""}</p>
                          <div className="mt-2 flex items-center justify-between gap-2 text-[12px]">
                            <span className="truncate text-muted">{data.refs?.users?.[l.owner_id] || "Unassigned"}</span>
                            {late ? <span className="flex items-center gap-1 font-semibold text-bad"><AlertTriangle className="h-3 w-3" />Reply overdue</span>
                              : follow ? <span className="flex items-center gap-1 font-semibold text-warn"><Clock className="h-3 w-3" />Follow up</span>
                                : l.value ? <span className="font-semibold tabular">{inr(l.value, { compact: true })}</span> : <span className="text-muted">{ago(l.created_at)}</span>}
                          </div>
                        </button>
                      </li>
                    );
                  })}
                  {!c.items.length && <li className="rounded-lg border border-dashed border-edge px-3 py-6 text-center text-xs text-muted">Drop a lead here</li>}
                </ul>
              </section>
            );
          })}
        </div>
      )}
      <Dialog open={!!ask} onOpenChange={(x) => !x && setAsk(null)} title={ask?.stage === "lost" ? "Why was it lost?" : "Put on hold until"}
        footer={<><Button variant="outline" onClick={() => setAsk(null)}>Cancel</Button><Button onClick={() => move(ask.lead, ask.stage, ask)}>Save</Button></>}>
        {ask?.stage === "lost" ? (
          <div className="space-y-3"><Field label="Reason" required><Select value={ask.lost_reason || ""} onChange={(e) => setAsk((a) => ({ ...a, lost_reason: e.target.value }))} options={meta.options.lost_reasons || []} placeholder="Choose" /></Field>
            <Field label="Note"><Input value={ask.lost_note || ""} onChange={(e) => setAsk((a) => ({ ...a, lost_note: e.target.value }))} /></Field></div>
        ) : ask && <Field label="Get back in touch on" required><Input type="date" value={ask.hold_until || ""} onChange={(e) => setAsk((a) => ({ ...a, hold_until: e.target.value }))} /></Field>}
      </Dialog>
    </div>
  );
}

export function Marketing() {
  const [days, setDays] = useState("90");
  const to = new Date(Date.now() + 5.5 * 3600e3).toISOString().slice(0, 10);
  const frm = new Date(Date.now() + 5.5 * 3600e3 - (Number(days) - 1) * 864e5).toISOString().slice(0, 10);
  const { data, isLoading } = useApi("/crm/marketing", days === "90" ? null : { frm, to });
  const tools = useMemo(() => (data?.tools || []).slice().sort((a, b) => b.runs - a.runs), [data]);
  usePageTitle("Marketing results");
  if (isLoading || !data) return <Skeleton className="h-96" />;
  const src = data.by_source.slice().sort((a, b) => b.leads - a.leads);
  return (
    <div className="space-y-5 pb-10">
      <PageHead icon="megaphone" title="Marketing results" sub={`${fmtDate(data.from)} to ${fmtDate(data.to)}. Where leads come from, what they cost and how many turn into work.`}
        actions={<div className="w-[160px]"><Select value={days} onChange={(e) => setDays(e.target.value)} options={[{ value: "30", label: "Last 30 days" }, { value: "90", label: "Last 90 days" }, { value: "365", label: "Last 12 months" }]} className="h-9" /></div>} />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <Kpi label="Leads" value={data.total} fmt="int" />
        <Kpi label="Won" value={data.won} fmt="int" sub={data.total ? `${pct((data.won / data.total) * 100)} conversion` : undefined} />
        <Kpi label="Ad spend" value={data.spend} fmt="inr" sub={data.total ? `${inr(data.spend / data.total)} a lead` : undefined} />
        <Kpi label="Median first reply" value={data.median_first_response_min} fmt="min" tone={data.median_first_response_min > 30 ? "warn" : "good"} />
        <Kpi label="Replied within target" value={data.responded_in_time_pct} fmt="pct" />
      </div>
      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Panel title="Leads and wins by month">
          <div className="h-60">
            <ResponsiveContainer>
              <BarChart data={data.by_month} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid stroke="rgb(var(--edge))" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: "rgb(var(--muted))" }} tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "rgb(var(--muted))" }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} cursor={{ fill: "rgb(var(--fg) / .04)" }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <RBar dataKey="leads" name="Leads" fill="#94A3B8" radius={[3, 3, 0, 0]} />
                <RBar dataKey="won" name="Won" fill="#FFC400" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Calculators that bring leads" bodyClass="p-0">
          <Table dense columns={[{ label: "Calculator", render: (t) => <Link to={`/tools/${t.slug}`} target="_blank" className="hover:underline">{t.slug.replace(/-/g, " ")}</Link> }, { label: "Runs", right: true, key: "runs" }, { label: "Leads", right: true, key: "leads" },
            { label: "Rate", right: true, render: (t) => (t.runs ? pct((t.leads / t.runs) * 100, 0) : "—") }]} rows={tools} empty="No calculator use yet" />
        </Panel>
      </div>
      <Panel title="By source" sub="Revenue is the value of won leads; ROI = revenue ÷ spend" bodyClass="p-0">
        <Table columns={[
          { label: "Source", render: (s) => <Link to={`/erp/e/leads?source=${s.source}`} className="font-medium hover:underline">{s.label}</Link> },
          { label: "Leads", right: true, key: "leads" }, { label: "Won", right: true, key: "won" },
          { label: "Conversion", right: true, render: (s) => pct(s.conversion_pct) },
          { label: "Replied on time", right: true, render: (s) => (s.responded ? `${s.responded_in_time}/${s.responded}` : "—") },
          { label: "Spend", right: true, render: (s) => (s.spend ? inr(s.spend) : "—") },
          { label: "Cost a lead", right: true, render: (s) => (s.cost_per_lead ? inr(s.cost_per_lead) : "—") },
          { label: "Revenue", right: true, render: (s) => inr(s.revenue, { compact: true }) },
          { label: "ROI", right: true, render: (s) => (s.roi ? `${num(s.roi)}×` : "—") },
        ]} rows={src} />
      </Panel>
    </div>
  );
}

export { Users, LayoutGrid };
