import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Check, X, ArrowUpRight, Clock, CalendarClock, Stamp, Plus } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { inr, fmtDate, fmtDateTime, ago, todayIST, daysBetween } from "@/lib/format";
import { Button, Badge, Skeleton, Empty, Tabs, TabPanel, Confirm, Alert } from "@/components/ui/kit";
import { Icon } from "@/components/ui/icons";
import { toast } from "sonner";
import { useApi, useInvalidate, stateOf } from "../lib";
import { PageHead, Kpi, Panel, usePageTitle } from "../ui";

const greet = () => { const h = new Date().getHours(); return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening"; };
const QUICK = [["leads", "Lead", "crm"], ["activities", "Call or visit", "crm"], ["dprs", "Daily report", "site"], ["purchase_requests", "Material request", "procurement"], ["tickets", "Service request", "service"], ["expenses", "Expense", "finance"]];

export function Dashboard() {
  const { user, meta } = useAuth();
  const { data, isLoading } = useApi("/dashboard");
  usePageTitle("Dashboard");
  const nav = useNavigate();
  const quick = QUICK.filter(([k]) => meta?.entities?.[k]?.perm?.includes("w"));
  return (
    <div className="space-y-5 pb-10">
      <PageHead title={`${greet()}, ${user?.name?.split(" ")[0] || ""}`} sub={`${user?.role_label}, ${new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", timeZone: "Asia/Kolkata" })}`}
        actions={quick.length > 0 && <div className="flex flex-wrap gap-2">{quick.slice(0, 4).map(([k, l]) => <Button key={k} size="sm" variant="outline" as={Link} to={`/erp/e/${k}?new=1`}><Plus className="h-3.5 w-3.5" />{l}</Button>)}</div>} />
      {isLoading ? <Skeleton className="h-28" /> : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
          {data.kpis.map((k) => <Kpi key={k.key} label={k.label} value={k.value} fmt={k.fmt} link={k.link} change={k.change_pct} good={k.good} />)}
        </div>
      )}
      <div className="grid items-start gap-4 xl:grid-cols-3">
        <div className="grid items-start gap-4 md:grid-cols-2 xl:col-span-2">
          {(data?.lists || []).map((l) => <ListPanel key={l.title} l={l} />)}
        </div>
        <div className="space-y-4">
          <Panel title="Waiting for approval" actions={<Link to="/erp/approvals" className="text-xs text-cable hover:underline">Open approvals</Link>} bodyClass="p-0">
            {!data ? <Skeleton className="m-4 h-20" /> : !data.approvals.length ? <p className="px-4 py-6 text-center text-sm text-muted">Nothing waiting</p> : (
              <ul className="divide-y divide-edge">
                {data.approvals.slice(0, 6).map((a) => (
                  <li key={a.id}><Link to="/erp/approvals" className="flex items-center justify-between gap-3 px-4 py-2.5 hover:bg-canvas">
                    <span className="min-w-0"><span className="block truncate text-sm">{a.title}</span><span className="text-xs text-muted">{ago(a.at)}</span></span>
                    {a.amount > 0 && <span className="shrink-0 text-sm font-semibold tabular">{inr(a.amount, { compact: true })}</span>}
                  </Link></li>
                ))}
              </ul>
            )}
          </Panel>
          <Expiring />
        </div>
      </div>
    </div>
  );
}

function ListPanel({ l }) {
  const { meta } = useAuth();
  const e = meta?.entities?.[l.entity];
  return (
    <Panel title={l.title} actions={<Link to={l.link} className="text-xs text-cable hover:underline">See all</Link>} bodyClass="p-0">
      {!l.items.length ? <p className="px-4 py-6 text-center text-sm text-muted">{l.empty}</p> : (
        <ul className="divide-y divide-edge">
          {l.items.slice(0, 7).map((it) => {
            const st = stateOf(e, it.status);
            const overdue = it.date && String(it.date).slice(0, 10) < todayIST() && !["done", "closed", "resolved", "paid"].includes(it.status);
            return (
              <li key={it.id}>
                <Link to={`/erp/e/${l.entity}/${it.id}`} className="flex items-center gap-3 px-4 py-2.5 hover:bg-canvas">
                  <span className="min-w-0 flex-1"><span className="block truncate text-sm">{it.title}</span>
                    <span className="block truncate text-xs text-muted">{[it.code !== it.title ? it.code : null, it.sub].filter(Boolean).join(", ")}</span></span>
                  <span className="shrink-0 text-right">
                    {st && <Badge tone={st.tone}>{st.label}</Badge>}
                    {it.date && <span className={cn("block text-[12px] tabular", overdue ? "font-semibold text-bad" : "text-muted")}>{String(it.date).length > 10 ? fmtDateTime(it.date) : fmtDate(it.date)}</span>}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </Panel>
  );
}

function Expiring() {
  const { data } = useApi("/calendar/expiries", { days: 30 });
  if (!data?.length) return null;
  return (
    <Panel title="Expiring in 30 days" actions={<Link to="/erp/calendar" className="text-xs text-cable hover:underline">Calendar</Link>} bodyClass="p-0">
      <ul className="divide-y divide-edge">
        {data.slice(0, 7).map((x, i) => (
          <li key={i}><Link to={x.link} className="flex items-center justify-between gap-3 px-4 py-2 hover:bg-canvas">
            <span className="truncate text-sm">{x.what}</span>
            <span className={cn("shrink-0 text-xs font-semibold tabular", x.days_left < 0 ? "text-bad" : x.days_left <= 7 ? "text-warn" : "text-muted")}>{x.days_left < 0 ? `${-x.days_left} d overdue` : x.days_left === 0 ? "today" : `${x.days_left} d`}</span>
          </Link></li>
        ))}
      </ul>
    </Panel>
  );
}

// ------------------------------------------------------------------ approvals inbox
export function Approvals() {
  const { data, isLoading, refetch } = useApi("/approvals/inbox");
  const [tab, setTab] = useState("decide");
  const [rej, setRej] = useState(null);
  const invalidate = useInvalidate();
  usePageTitle("Approvals");
  async function decide(a, decision, reason) {
    try {
      await api.post(`/approvals/${a.id}/decide`, { decision, reason });
      toast.success(decision === "approve" ? "Approved" : "Rejected");
      refetch(); invalidate("/dashboard"); invalidate(`/e/${a.doc_entity}`);
    } catch (ex) { toast.error(errMsg(ex)); }
  }
  return (
    <div className="pb-10">
      <PageHead icon="stamp" title="Approvals" sub="Purchase orders, payments, discounts, leave, payroll and more, routed by amount and branch. Nobody approves their own request." />
      <Tabs value={tab} onValueChange={setTab} tabs={[{ value: "decide", label: "For me to decide", count: data?.to_decide.length }, { value: "mine", label: "My requests", count: data?.my_requests.length }]}>
        <TabPanel value="decide">
          {isLoading ? <Skeleton className="h-40" /> : !data.to_decide.length ? <Empty icon={Stamp} title="Nothing waiting for you" text="New requests appear here and in your notifications." /> : (
            <ul className="space-y-2">
              {data.to_decide.map((a) => (
                <li key={a.id} className="flex flex-wrap items-center gap-3 rounded-xl border border-edge bg-surface p-4 shadow-card">
                  <div className="min-w-0 flex-1">
                    <p className="text-xs text-muted">{a.entity_label}</p>
                    <Link to={`/erp/e/${a.doc_entity}/${a.doc_id}`} className="font-medium hover:underline">{a.title}</Link>
                    <p className="mt-0.5 text-xs text-muted">Asked by {a.requested_by_name || "someone"} {ago(a.created_at)}</p>
                  </div>
                  {a.amount > 0 && <p className="font-display text-[20px] font-semibold tabular">{inr(a.amount)}</p>}
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => setRej(a)}><X className="h-4 w-4" />Reject</Button>
                    <Button size="sm" onClick={() => decide(a, "approve", "")}><Check className="h-4 w-4" />Approve</Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </TabPanel>
        <TabPanel value="mine">
          {!data?.my_requests.length ? <Empty title="You haven't asked for any approvals" /> : (
            <ul className="divide-y divide-edge rounded-xl border border-edge bg-surface">
              {data.my_requests.map((a) => (
                <li key={a.id} className="flex items-center justify-between gap-3 px-4 py-3">
                  <span className="min-w-0"><Link to={`/erp/e/${a.doc_entity}/${a.doc_id}`} className="block truncate text-sm font-medium hover:underline">{a.title}</Link><span className="text-xs text-muted">{ago(a.created_at)}{a.why_not ? `, ${a.why_not}` : ""}</span></span>
                  <Badge tone={a.status === "approved" ? "green" : a.status === "rejected" ? "red" : "amber"}>{a.status === "pending" ? "Waiting" : a.status}</Badge>
                </li>
              ))}
            </ul>
          )}
        </TabPanel>
      </Tabs>
      <Confirm open={!!rej} onOpenChange={(v) => !v && setRej(null)} title={`Reject: ${rej?.title || ""}`} text="The requester sees your reason." tone="danger" confirmLabel="Reject" reason reasonLabel="Why are you rejecting it?"
        onConfirm={(reason) => decide(rej, "reject", reason)} />
    </div>
  );
}

// ------------------------------------------------------------------ expiry calendar
const KIND = { instruments: "Calibration", bank_guarantees: "Bank guarantee", compliance_items: "Licence / compliance", amc_contracts: "AMC", vehicles: "Vehicle papers", tools: "Tool test", authorised_persons: "Authorisation", employees: "Employee document", documents: "Document", prequal_docs: "Pre-qualification", workers: "Worker document" };
export function CalendarPage() {
  const { data, isLoading } = useApi("/calendar/expiries", { days: 120 });
  usePageTitle("Expiry calendar");
  const months = {};
  (data || []).forEach((x) => { const m = x.days_left < 0 ? "Overdue" : new Date(`${x.date}T00:00:00+05:30`).toLocaleDateString("en-IN", { month: "long", year: "numeric" }); (months[m] = months[m] || []).push(x); });
  return (
    <div className="pb-10">
      <PageHead icon="calendar-clock" title="Expiry calendar" sub="Calibration, bank guarantees, licences, insurance, AMC contracts, permits and staff authorisations for the next four months. Reminders go out 30, 15 and 7 days before." />
      {isLoading ? <Skeleton className="h-64" /> : !data?.length ? <Empty icon={CalendarClock} title="Nothing expiring in the next 120 days" /> : (
        <div className="space-y-5">
          {Object.entries(months).map(([m, list]) => (
            <Panel key={m} title={m} className={m === "Overdue" ? "border-bad/40" : ""} bodyClass="p-0">
              <ul className="divide-y divide-edge">
                {list.map((x, i) => (
                  <li key={i}><Link to={x.link} className="grid grid-cols-[1fr_auto] items-center gap-3 px-4 py-2.5 hover:bg-canvas sm:grid-cols-[140px_1fr_auto]">
                    <span className="hidden text-xs text-muted sm:block">{KIND[x.kind] || x.kind}</span>
                    <span className="truncate text-sm">{x.what}</span>
                    <span className="text-right text-sm tabular"><span className={cn("font-semibold", x.days_left < 0 ? "text-bad" : x.days_left <= 15 ? "text-warn" : "")}>{fmtDate(x.date)}</span><span className="block text-xs text-muted">{x.days_left < 0 ? `${-x.days_left} days ago` : `in ${x.days_left} days`}</span></span>
                  </Link></li>
                ))}
              </ul>
            </Panel>
          ))}
        </div>
      )}
    </div>
  );
}

export { Icon, ArrowUpRight, Clock, Alert, daysBetween };
