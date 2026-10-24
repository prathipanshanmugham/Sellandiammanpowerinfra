import { Fragment, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Download, FileText, AlertTriangle, Truck, Search, Wrench, CalendarCheck, Clock } from "lucide-react";
import { ResponsiveContainer, BarChart, Bar as RBar, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from "recharts";
import { openFile } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { inr, num, pct, fmtDate, fmtDateTime, ago, todayIST } from "@/lib/format";
import { Button, Badge, Skeleton, Select, Input, Tabs, TabPanel, Checkbox, Alert } from "@/components/ui/kit";
import { useApi } from "../lib";
import { PageHead, Kpi, Panel, Table, Bar, usePageTitle } from "../ui";

// ------------------------------------------------------------------ stores
export function Stores() {
  const [store, setStore] = useState("");
  const [low, setLow] = useState(false);
  const [q, setQ] = useState("");
  const { data, isLoading } = useApi("/stores/stock", { store_id: store || undefined, low: low || undefined });
  const { data: transit } = useApi("/stores/in-transit");
  const { data: stores } = useApi("/e/stores", { size: 50 });
  usePageTitle("Stock on hand");
  const rows = useMemo(() => (data?.rows || []).filter((r) => !q || `${r.item} ${r.code}`.toLowerCase().includes(q.toLowerCase())), [data, q]);
  const lowCount = (data?.rows || []).filter((r) => r.below_reorder).length;
  return (
    <div className="space-y-5 pb-10">
      <PageHead icon="boxes" title="Stock on hand" sub="Quantity and value by store, at weighted average cost. Moves come from posted GRNs, issues, returns and transfers."
        actions={<><Button size="sm" variant="outline" as={Link} to="/erp/e/grns?new=1">Receive goods (GRN)</Button><Button size="sm" as={Link} to="/erp/e/material_moves?new=1">Issue / transfer</Button></>} />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi label="Stock value" value={data?.total_value} fmt="inr" />
        <Kpi label="Lines" value={data?.rows.length} fmt="int" />
        <Kpi label="Below reorder level" value={lowCount} fmt="int" tone={lowCount ? "warn" : undefined} />
        <Kpi label="Transfers in transit" value={transit?.length} fmt="int" link="/erp/e/material_moves?status=in_transit" />
      </div>
      <Panel title="Stock" actions={<div className="flex flex-wrap items-center gap-2">
        <label className="relative"><Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" /><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Find an item" className="h-8 w-44 pl-8 text-sm" /></label>
        <div className="w-[160px]"><Select value={store} onChange={(e) => setStore(e.target.value)} options={(stores?.items || []).map((s) => ({ value: s.id, label: s.name }))} placeholder="All stores" className="h-8 text-sm" /></div>
        <Checkbox checked={low} onChange={setLow} label="Below reorder only" />
      </div>} bodyClass="p-0">
        {isLoading ? <Skeleton className="m-4 h-40" /> : (
          <Table columns={[
            { label: "Item", render: (r) => <Link to={`/erp/e/items/${r.item_id}`} className="font-medium hover:underline">{r.item}</Link>, className: "min-w-[220px]" },
            { label: "Code", key: "code", className: "tabular text-muted" }, { label: "Store", key: "store" },
            { label: "Qty", right: true, render: (r) => <span className={cn(r.below_reorder && "font-semibold text-warn")}>{num(r.qty)} {r.unit}</span> },
            { label: "Reorder at", right: true, render: (r) => (r.reorder_level == null ? "—" : num(r.reorder_level)) },
            { label: "Avg rate", right: true, render: (r) => inr(r.avg_rate) }, { label: "Value", right: true, render: (r) => inr(r.value) },
          ]} rows={rows.map((r) => ({ ...r, id: `${r.item_id}:${r.store_id}` }))} foot={["Total", "", "", "", "", "", inr(rows.reduce((a, r) => a + r.value, 0))]} />
        )}
      </Panel>
      {transit?.length > 0 && (
        <Panel title="In transit between stores" bodyClass="p-0">
          <Table columns={[{ label: "Transfer", render: (m) => <Link to={`/erp/e/material_moves/${m.id}`} className="hover:underline">{m.code}</Link> }, { label: "Date", render: (m) => fmtDate(m.date) },
            { label: "Lines", right: true, render: (m) => m.lines?.length }, { label: "Vehicle", key: "vehicle_no" }]} rows={transit} />
        </Panel>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ service desk
export function ServiceDesk() {
  const { user, can } = useAuth();
  const { data: mine } = useApi("/service/my-jobs");
  const { data: open } = useApi("/e/tickets", { status: "new,assigned,in_progress,waiting_customer,reopened", size: 50, sort: "restore_by" });
  const { data: renewals } = useApi("/service/renewals");
  usePageTitle("Service desk");
  const now = new Date().toISOString();
  const breached = (open?.items || []).filter((t) => t.sla_breached || (t.restore_by && t.restore_by < now)).length;
  return (
    <div className="space-y-5 pb-10">
      <PageHead icon="life-buoy" title="Service desk" sub="Breakdown calls, planned maintenance visits and AMC renewals."
        actions={can("service", "w") && <Button size="sm" as={Link} to="/erp/e/tickets?new=1">Log a service request</Button>} />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi label="Open requests" value={open?.total} fmt="int" link="/erp/e/tickets" />
        <Kpi label="Past target" value={breached} fmt="int" tone={breached ? "bad" : undefined} />
        <Kpi label="My jobs" value={(mine?.tickets.length || 0) + (mine?.visits.length || 0)} fmt="int" />
        <Kpi label="AMC renewals, 60 days" value={renewals?.length} fmt="int" link="/erp/e/amc_contracts" />
      </div>
      {(mine?.tickets.length > 0 || mine?.visits.length > 0) && (
        <Panel title={`Jobs for ${user.name.split(" ")[0]}`} bodyClass="p-0">
          <ul className="divide-y divide-edge">
            {mine.tickets.map((t) => (
              <li key={t.id}><Link to={`/erp/e/tickets/${t.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-canvas">
                <Wrench className={cn("h-4 w-4 shrink-0", t.priority === "urgent" ? "text-bad" : "text-muted")} />
                <span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium">{t.title}</span><span className="text-xs text-muted">{t.code}, {mine.accounts?.[t.account_id]?.name || t.contact_name}</span></span>
                <span className={cn("shrink-0 text-right text-xs tabular", t.restore_by < now ? "font-semibold text-bad" : "text-muted")}>Fix by<br />{fmtDateTime(t.restore_by)}</span>
              </Link></li>
            ))}
            {mine.visits.map((v) => (
              <li key={v.id}><Link to={`/erp/e/pm_jobs/${v.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-canvas">
                <CalendarCheck className="h-4 w-4 shrink-0 text-cable" />
                <span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium">Maintenance visit, {mine.accounts?.[v.account_id]?.name || "client"}</span><span className="text-xs text-muted">{v.code || ""} {v.asset_ids?.length ? `${v.asset_ids.length} assets` : ""}</span></span>
                <span className={cn("shrink-0 text-xs tabular", v.scheduled_on < todayIST() ? "font-semibold text-bad" : "text-muted")}>{fmtDate(v.scheduled_on)}</span>
              </Link></li>
            ))}
          </ul>
        </Panel>
      )}
      <Panel title="Open requests, most urgent first" bodyClass="p-0">
        <Table columns={[
          { label: "Request", render: (t) => <Link to={`/erp/e/tickets/${t.id}`} className="font-medium hover:underline">{t.title}</Link>, className: "min-w-[220px]" },
          { label: "Client", render: (t) => open.refs?.accounts?.[t.account_id] || t.contact_name || "—" },
          { label: "Priority", render: (t) => <Badge tone={t.priority === "urgent" ? "red" : t.priority === "high" ? "amber" : "gray"}>{t.priority}</Badge> },
          { label: "Assigned", render: (t) => open.refs?.users?.[t.assigned_to] || <span className="text-warn">Unassigned</span> },
          { label: "Fix by", right: true, render: (t) => <span className={cn((t.sla_breached || t.restore_by < now) && "font-semibold text-bad")}>{fmtDateTime(t.restore_by)}</span> },
        ]} rows={open?.items || []} empty="No open requests" />
      </Panel>
      <Panel title="AMC contracts ending in 60 days" bodyClass="p-0">
        <Table columns={[{ label: "Contract", render: (a) => <Link to={`/erp/e/amc_contracts/${a.id}`} className="hover:underline">{a.title || a.code}</Link> }, { label: "Ends", render: (a) => fmtDate(a.end) },
          { label: "Visits a year", right: true, key: "visits_per_year" }, { label: "Price", right: true, render: (a) => inr(a.price) }]} rows={renewals || []} empty="No renewals coming up" />
      </Panel>
    </div>
  );
}

// ------------------------------------------------------------------ finance
const AGE = ["not_due", "0–30", "31–60", "61–90", "90+"];
export function Finance() {
  const { can } = useAuth();
  const [tab, setTab] = useState("ar");
  const [month, setMonth] = useState(todayIST().slice(0, 7));
  const bal = useApi("/finance/balances");
  const ar = useApi("/finance/receivables");
  const ap = useApi("/finance/payables", null, { enabled: tab === "ap" });
  const gst = useApi("/finance/gst", { month }, { enabled: tab === "gst" });
  const tds = useApi("/finance/tds", null, { enabled: tab === "tds" });
  const pnl = useApi("/finance/pnl");
  const cf = useApi("/finance/cashflow");
  usePageTitle("Finance");
  const arTot = ar.data?.rows.reduce((a, r) => a + r.total, 0) || 0;
  return (
    <div className="space-y-5 pb-10">
      <PageHead icon="landmark" title="Finance" sub="Cash, receivables, payables, GST and profit. Figures are without GST unless marked."
        actions={<>
          <Button size="sm" variant="outline" onClick={() => openFile("/finance/credit-report?fmt=pdf", { name: "credit-report.pdf", type: "application/pdf", kind: "credit-report" })}><FileText className="h-4 w-4" />Daily credit report</Button>
          {can("finance", "e") && <Button size="sm" variant="outline" onClick={() => openFile("/finance/tally.xml", { name: "tally-sales.xml", type: "application/xml" })}><Download className="h-4 w-4" />Tally export</Button>}
        </>} />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi label="Cash & bank" value={bal.data?.total} fmt="inr" />
        <Kpi label="Receivables" value={arTot} fmt="inr" sub={ar.data ? `${inr(ar.data.overdue, { compact: true })} overdue` : undefined} tone={ar.data?.overdue > 0 ? "warn" : undefined} />
        <Kpi label={`Income ${pnl.data ? `since ${fmtDate(pnl.data.from, { noYear: true })}` : ""}`} value={pnl.data?.income} fmt="inr" />
        <Kpi label="Gross margin" value={pnl.data?.gross_margin_pct} fmt="pct" tone={pnl.data?.gross_margin_pct < 0 ? "bad" : undefined} sub={pnl.data ? inr(pnl.data.gross_margin, { compact: true }) : undefined} />
      </div>
      <div className="grid gap-4 lg:grid-cols-[1fr_1.3fr]">
        <Panel title="Bank and cash accounts" bodyClass="p-0">
          <Table dense columns={[{ label: "Account", render: (a) => <Link to={`/erp/e/bank_accounts/${a.id}`} className="hover:underline">{a.name}</Link> }, { label: "In", right: true, render: (a) => inr(a.in, { compact: true }) },
            { label: "Out", right: true, render: (a) => inr(a.out, { compact: true }) }, { label: "Balance", right: true, render: (a) => <span className="font-semibold">{inr(a.balance)}</span> }]} rows={bal.data?.accounts || []} />
        </Panel>
        <Panel title="Cash in and out by month">
          <div className="h-52">
            <ResponsiveContainer>
              <BarChart data={cf.data || []} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="rgb(var(--edge))" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: "rgb(var(--muted))" }} tickLine={false} axisLine={false} />
                <YAxis tickFormatter={(v) => inr(v, { compact: true })} tick={{ fontSize: 11, fill: "rgb(var(--muted))" }} tickLine={false} axisLine={false} width={64} />
                <Tooltip formatter={(v) => inr(v)} contentStyle={{ fontSize: 12, borderRadius: 8 }} cursor={{ fill: "rgb(var(--fg) / .04)" }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <RBar dataKey="in" name="Money in" fill="#1B7A4B" radius={[3, 3, 0, 0]} />
                <RBar dataKey="out" name="Money out" fill="#B42318" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>
      <Tabs value={tab} onValueChange={setTab} tabs={[{ value: "ar", label: "Receivables" }, { value: "ap", label: "Payables" }, { value: "gst", label: "GST" }, { value: "tds", label: "TDS" }, { value: "pnl", label: "Profit & loss" }]}>
        <TabPanel value="ar"><Ageing rows={ar.data?.rows} nameKey="client" link={(r) => `/erp/e/accounts/${r.account_id}`} expand /></TabPanel>
        <TabPanel value="ap"><Ageing rows={ap.data?.rows} nameKey="vendor" link={(r) => `/erp/e/vendors/${r.vendor_id}`} /></TabPanel>
        <TabPanel value="gst">
          <div className="mb-3 flex items-center gap-2"><span className="text-sm text-muted">Month</span><Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="h-9 w-40" /></div>
          {gst.data && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
                <Kpi label="Outward taxable" value={gst.data.gstr3b.outward_taxable} fmt="inr" />
                <Kpi label="Output tax" value={gst.data.gstr3b.output_tax} fmt="inr" />
                <Kpi label="ITC on purchases" value={gst.data.gstr3b.itc_purchases} fmt="inr" />
                <Kpi label="ITC on expenses" value={gst.data.gstr3b.itc_expenses} fmt="inr" />
                <Kpi label={gst.data.gstr3b.net_payable < 0 ? "Credit carried forward" : "Net GST payable"} value={Math.abs(gst.data.gstr3b.net_payable)} fmt="inr" />
              </div>
              <Panel title="GSTR-1 B2B invoices" bodyClass="p-0">
                <Table dense columns={[{ label: "Invoice", key: "invoice" }, { label: "Date", render: (r) => fmtDate(r.date) }, { label: "Client", key: "client" }, { label: "GSTIN", key: "gstin", className: "tabular" },
                  { label: "Taxable", right: true, render: (r) => inr(r.taxable) }, { label: "CGST", right: true, render: (r) => inr(r.cgst) }, { label: "SGST", right: true, render: (r) => inr(r.sgst) }, { label: "IGST", right: true, render: (r) => inr(r.igst) }, { label: "Total", right: true, render: (r) => inr(r.total) }]} rows={gst.data.gstr1_b2b} empty="No B2B invoices this month" />
              </Panel>
              {gst.data.note && <p className="text-xs text-muted">{gst.data.note}</p>}
            </div>
          )}
        </TabPanel>
        <TabPanel value="tds">
          {tds.data && (
            <div className="grid gap-4 lg:grid-cols-2">
              <Panel title={`Deducted by us: ${inr(tds.data.total_deducted)}`} sub="On subcontractor and vendor payments" bodyClass="p-0"><Table dense columns={[{ label: "Date", render: (r) => fmtDate(r.date) }, { label: "Vendor", key: "vendor" }, { label: "PAN", key: "pan" }, { label: "Section", key: "section" }, { label: "Paid", right: true, render: (r) => inr(r.paid) }, { label: "TDS", right: true, render: (r) => inr(r.tds) }]} rows={tds.data.deducted_by_us} empty="None this period" /></Panel>
              <Panel title={`Deducted by clients: ${inr(tds.data.total_by_clients)}`} sub="Claim in your return; collect Form 16A" bodyClass="p-0"><Table dense columns={[{ label: "Date", render: (r) => fmtDate(r.date) }, { label: "Receipt", key: "receipt" }, { label: "TDS", right: true, render: (r) => inr(r.tds) }]} rows={tds.data.deducted_by_clients} empty="None this period" /></Panel>
            </div>
          )}
        </TabPanel>
        <TabPanel value="pnl">
          {pnl.data && (
            <Panel title={`Profit and loss, ${fmtDate(pnl.data.from)} to ${fmtDate(pnl.data.to)}`} sub={pnl.data.note}>
              <dl className="max-w-md divide-y divide-edge text-sm">
                <div className="flex justify-between py-2 font-semibold"><dt>Income</dt><dd className="tabular">{inr(pnl.data.income)}</dd></div>
                {Object.entries(pnl.data.costs).map(([k, v]) => <div key={k} className="flex justify-between py-2"><dt className="text-muted">{k.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase())}</dt><dd className="tabular">{inr(v)}</dd></div>)}
                <div className="flex justify-between py-2"><dt>Total cost</dt><dd className="tabular">{inr(pnl.data.total_cost)}</dd></div>
                <div className={cn("flex justify-between py-2 font-semibold", pnl.data.gross_margin < 0 && "text-bad")}><dt>Gross margin ({pct(pnl.data.gross_margin_pct)})</dt><dd className="tabular">{inr(pnl.data.gross_margin)}</dd></div>
              </dl>
            </Panel>
          )}
        </TabPanel>
      </Tabs>
    </div>
  );
}

function Ageing({ rows, nameKey, link, expand }) {
  const [open, setOpen] = useState(null);
  if (!rows) return <Skeleton className="h-40" />;
  const tot = AGE.map((k) => rows.reduce((a, r) => a + (r[k] || 0), 0));
  return (
    <div className="overflow-hidden rounded-xl border border-edge bg-surface">
      <div className="overflow-x-auto">
        <table className="w-full text-[14px]">
          <thead className="border-b border-edge text-left text-xs text-muted"><tr><th className="px-3 py-2 font-medium">{nameKey === "client" ? "Client" : "Vendor"}</th>{["Not due", "1–30 days", "31–60", "61–90", "Over 90"].map((h) => <th key={h} className="px-3 py-2 text-right font-medium">{h}</th>)}<th className="px-3 py-2 text-right font-medium">Total</th></tr></thead>
          <tbody className="divide-y divide-edge">
            {rows.map((r, i) => (
              <Fragment key={i}>
                <tr className={cn(expand && "cursor-pointer hover:bg-canvas/60")} onClick={() => expand && setOpen(open === i ? null : i)}>
                  <td className="px-3 py-2.5"><Link to={link(r)} onClick={(e) => e.stopPropagation()} className="font-medium hover:underline">{r[nameKey]}</Link></td>
                  {AGE.map((k, j) => <td key={k} className={cn("px-3 py-2.5 text-right tabular", j >= 3 && r[k] > 0 && "font-semibold text-bad", j === 2 && r[k] > 0 && "text-warn")}>{r[k] ? inr(r[k]) : "—"}</td>)}
                  <td className="px-3 py-2.5 text-right font-semibold tabular">{inr(r.total)}</td>
                </tr>
                {expand && open === i && r.invoices?.map((inv) => (
                  <tr key={inv.id} className="bg-canvas/50 text-xs"><td className="px-6 py-1.5" colSpan={2}><Link to={`/erp/e/invoices/${inv.id}`} className="hover:underline">{inv.code}</Link>, {fmtDate(inv.date)}</td>
                    <td className="px-3 py-1.5 text-right" colSpan={3}>Due {fmtDate(inv.due_date)}{inv.overdue_days > 0 ? <span className="font-semibold text-bad">, {inv.overdue_days} days late</span> : ""}</td><td className="px-3 py-1.5 text-right tabular" colSpan={2}>{inr(inv.balance)}</td></tr>
                ))}
              </Fragment>
            ))}
          </tbody>
          <tfoot className="border-t border-edge font-semibold"><tr><td className="px-3 py-2">Total</td>{tot.map((v, j) => <td key={j} className="px-3 py-2 text-right tabular">{inr(v)}</td>)}<td className="px-3 py-2 text-right tabular">{inr(tot.reduce((a, b) => a + b, 0))}</td></tr></tfoot>
        </table>
      </div>
    </div>
  );
}

export { AlertTriangle, Truck, Clock, Bar, Alert, ago };
