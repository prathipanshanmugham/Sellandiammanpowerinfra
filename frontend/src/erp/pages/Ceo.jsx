import { useState } from "react";
import { Link } from "react-router-dom";
import { FileText, AlertTriangle, ShieldCheck, Wrench, Gavel, Filter } from "lucide-react";
import { api, errMsg, openFile } from "@/lib/api";
import { cn } from "@/lib/utils";
import { inr, num, pct, fmtDate, todayIST, addDays } from "@/lib/format";
import { Button, Badge, Skeleton, Select, Input } from "@/components/ui/kit";
import { toast } from "sonner";
import { useApi } from "../lib";
import { PageHead, Kpi, Panel, Table, Bar, RISK, usePageTitle } from "../ui";

function Dial({ score }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  const tone = score >= 75 ? "#1B7A4B" : score >= 50 ? "#E09B00" : "#B42318";
  return (
    <svg viewBox="0 0 128 128" className="h-36 w-36" role="img" aria-label={`Business health ${score} out of 100`}>
      <circle cx="64" cy="64" r={r} fill="none" stroke="rgb(var(--edge))" strokeWidth="12" />
      <circle cx="64" cy="64" r={r} fill="none" stroke={tone} strokeWidth="12" strokeLinecap="round" strokeDasharray={`${(score / 100) * c} ${c}`} transform="rotate(-90 64 64)" />
      <text x="64" y="66" textAnchor="middle" fontSize="34" fontWeight="800" fontFamily="Archivo, IBM Plex Sans, sans-serif" fill="rgb(var(--fg))">{score}</text>
      <text x="64" y="86" textAnchor="middle" fontSize="11" fill="rgb(var(--muted))">out of 100</text>
    </svg>
  );
}

const PERIODS = [["30", "Last 30 days"], ["90", "Last 90 days"], ["fy", "This financial year"]];
const ALERT_STATUS = [{ value: "new", label: "New" }, { value: "seen", label: "Seen" }, { value: "handling", label: "Being handled" }, { value: "resolved", label: "Resolved" }, { value: "not_a_problem", label: "Not a problem" }];

export default function Ceo() {
  const [period, setPeriod] = useState("30");
  const t = todayIST();
  const fy = `${Number(t.slice(0, 4)) - (Number(t.slice(5, 7)) < 4 ? 1 : 0)}-04-01`;
  const params = { frm: period === "fy" ? fy : addDays(t, -(Number(period) - 1)), to: t };
  const { data, isLoading, refetch } = useApi("/ceo", period === "30" ? null : params);
  usePageTitle("CEO view");
  if (isLoading || !data) return <div className="space-y-4"><Skeleton className="h-10 w-64" /><Skeleton className="h-48" /><Skeleton className="h-64" /></div>;
  const kp = Object.fromEntries(data.kpis.map((k) => [k.key, k]));
  async function setAlert(a, status) {
    try { await api.patch(`/ceo/alerts/${a.id}`, { status }); toast.success("Updated"); refetch(); } catch (ex) { toast.error(errMsg(ex)); }
  }
  const open = data.alerts.filter((a) => !["resolved", "not_a_problem"].includes(a.status));
  return (
    <div className="space-y-5 pb-10">
      <PageHead icon="activity" title="CEO view" sub={`${fmtDate(data.from)} to ${fmtDate(data.to)}, compared with the ${fmtDate(data.prev_from)} to ${fmtDate(data.prev_to)} period`}
        actions={<>
          <div className="w-[190px]"><Select value={period} onChange={(e) => setPeriod(e.target.value)} options={PERIODS.map(([v, l]) => ({ value: v, label: l }))} className="h-9" /></div>
          <Button size="sm" variant="outline" onClick={() => openFile(`/ceo/report.pdf${period === "30" ? "" : `?frm=${params.frm}&to=${params.to}`}`, { name: "ceo-report.pdf", type: "application/pdf", kind: "ceo-report" })}><FileText className="h-4 w-4" />PDF report</Button>
        </>} />

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)]">
        <Panel title="Business health">
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
            <Dial score={data.score} />
            <ul className="w-full flex-1 space-y-2.5">
              {data.pillars.map((p) => (
                <li key={p.key}>
                  <div className="flex items-baseline justify-between gap-2 text-sm"><span className="font-medium">{p.label}</span><span className="shrink-0 tabular"><span className="font-semibold">{p.score}</span><span className="text-xs text-muted">/100</span></span></div>
                  <Bar value={p.score} max={100} tone={p.score >= 75 ? "good" : p.score >= 50 ? "amber" : "bad"} className="mt-1" />
                  <p className="mt-0.5 text-xs text-muted">{p.note}. Weight {p.weight}%</p>
                </li>
              ))}
            </ul>
          </div>
        </Panel>
        <Panel title={`Needs your attention (${open.length})`} sub="Raised automatically from projects, cash, sales, safety and service" bodyClass="p-0">
          {!open.length ? <p className="px-4 py-10 text-center text-sm text-muted">Nothing needs you right now.</p> : (
            <ul className="max-h-[420px] divide-y divide-edge overflow-y-auto">
              {open.map((a) => (
                <li key={a.id} className="flex flex-wrap items-start gap-3 px-4 py-3">
                  <AlertTriangle className={cn("mt-0.5 h-4 w-4 shrink-0", a.money > 1e6 ? "text-bad" : "text-warn")} />
                  <div className="min-w-0 flex-1">
                    {a.link ? <Link to={a.link.replace("/erp/projects/", "/erp/e/projects/")} className="text-sm font-medium hover:underline">{a.title}</Link> : <p className="text-sm font-medium">{a.title}</p>}
                    <p className="text-xs text-muted">{a.evidence}{a.owner ? `. Owner: ${a.owner}` : ""}{a.due ? `. Act by ${fmtDate(a.due)}` : ""}</p>
                  </div>
                  {a.money ? <span className="text-sm font-semibold tabular">{inr(a.money, { compact: true })}</span> : null}
                  <div className="w-[150px]"><Select value={a.status || "new"} onChange={(e) => setAlert(a, e.target.value)} options={ALERT_STATUS} className="h-8 text-xs" aria-label="Alert status" /></div>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {data.kpis.map((k) => <Kpi key={k.key} label={k.label.replace(/ %$/, "")} value={k.value} fmt={k.label.endsWith("%") ? "pct" : k.fmt === "1dp" ? undefined : k.fmt} change={k.change_pct} good={k.good}
          tone={k.key === "gm" && k.value < 0 ? "bad" : undefined} sub={k.prev !== undefined ? `was ${k.fmt === "inr" ? inr(k.prev, { compact: true }) : k.label.endsWith("%") ? pct(k.prev) : num(k.prev)}` : undefined} />)}
      </div>

      <Panel title="Live projects" sub="Risk combines schedule, billing and forecast margin" bodyClass="p-0">
        <Table columns={[
          { label: "Project", render: (p) => <Link to={`/erp/e/projects/${p.id}`} className="font-medium hover:underline">{p.name}</Link>, className: "min-w-[220px]" },
          { label: "Manager", key: "manager" },
          { label: "Value", right: true, render: (p) => inr(p.contract_value, { compact: true }) },
          { label: "Done", right: true, render: (p) => pct(p.percent_complete, 0) },
          { label: "Billed", right: true, render: (p) => pct(p.billed_pct, 0) },
          { label: "Schedule", right: true, render: (p) => <span className={cn(p.schedule_variance < -5 && "font-semibold text-bad")}>{p.schedule_variance > 0 ? "+" : ""}{pct(p.schedule_variance)}</span> },
          { label: "Margin", right: true, render: (p) => <span className={cn(p.forecast_margin_pct < 8 && "font-semibold text-bad")}>{p.forecast_margin_pct == null ? "—" : pct(p.forecast_margin_pct)}</span> },
          { label: "Risk", render: (p) => <Badge tone={RISK[p.risk]?.[0]} dot>{RISK[p.risk]?.[1]}</Badge> },
        ]} rows={data.projects} />
      </Panel>

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="Sales funnel" sub="Leads in the period by furthest stage">
          <ul className="space-y-2">
            {data.funnel.map((f) => { const max = Math.max(...data.funnel.map((x) => x.count), 1); return (
              <li key={f.stage} className="grid grid-cols-[100px_1fr_32px] items-center gap-2 text-sm"><span className="text-muted">{f.stage}</span><Bar value={f.count} max={max} tone="cable" /><span className="text-right font-semibold tabular">{f.count}</span></li>
            ); })}
          </ul>
        </Panel>
        <Panel title="Tenders" sub={`Win rate ${data.win_rate}% (last 12 months)`}>
          <ul className="space-y-1.5 text-sm">{data.tenders.map((x) => <li key={x.key} className="flex justify-between gap-2"><Link to={`/erp/e/tenders?status=${x.key}`} className="hover:underline">{x.status} <span className="text-muted">({x.count})</span></Link><span className="tabular">{inr(x.value, { compact: true })}</span></li>)}</ul>
        </Panel>
        <div className="grid gap-4">
          <Panel title="Safety">
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div><dt className="text-xs text-muted">Man-hours</dt><dd className="font-semibold tabular">{num(data.safety.man_hours, 0)}</dd></div>
              <div><dt className="text-xs text-muted">LTIFR</dt><dd className="font-semibold tabular">{num(data.safety.ltifr)}</dd></div>
              <div><dt className="text-xs text-muted">Recordable incidents</dt><dd className={cn("font-semibold tabular", data.safety.recordable > 0 && "text-bad")}>{data.safety.recordable}</dd></div>
              <div><dt className="text-xs text-muted">Near-misses reported</dt><dd className="font-semibold tabular">{data.safety.near_misses}</dd></div>
            </dl>
          </Panel>
          <Panel title="Service">
            <dl className="grid grid-cols-3 gap-3 text-sm">
              <div><dt className="text-xs text-muted">Open</dt><dd className="font-semibold tabular">{data.service.open}</dd></div>
              <div><dt className="text-xs text-muted">Past target</dt><dd className={cn("font-semibold tabular", data.service.breached > 0 && "text-bad")}>{data.service.breached}</dd></div>
              <div><dt className="text-xs text-muted">AMC renewals, 60 d</dt><dd className="font-semibold tabular">{data.service.renewals_60d}</dd></div>
            </dl>
          </Panel>
        </div>
      </div>
    </div>
  );
}
