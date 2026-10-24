import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { FileSpreadsheet, FileText, Download, Search } from "lucide-react";
import { openFile } from "@/lib/api";
import { cn } from "@/lib/utils";
import { todayIST, addDays, fmtDate } from "@/lib/format";
import { Button, Input, Skeleton, Empty } from "@/components/ui/kit";
import { useApi } from "../lib";
import { PageHead, Panel, usePageTitle } from "../ui";

export function ReportsHome() {
  const { data, isLoading } = useApi("/reports");
  const [q, setQ] = useState("");
  usePageTitle("Reports");
  const groups = useMemo(() => {
    const m = {};
    (data || []).filter((r) => !q || r.title.toLowerCase().includes(q.toLowerCase())).forEach((r) => { (m[r.group] = m[r.group] || []).push(r); });
    return Object.entries(m);
  }, [data, q]);
  return (
    <div className="pb-10">
      <PageHead icon="file-spreadsheet" title="Reports" sub="Pick a report, set the dates, and view it here or download it as Excel, CSV or PDF on the letterhead."
        actions={<label className="relative"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" /><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Find a report" className="h-9 w-56 pl-9" /></label>} />
      {isLoading ? <Skeleton className="h-64" /> : !groups.length ? <Empty title="No reports match" /> : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {groups.map(([g, list]) => (
            <Panel key={g} title={g} bodyClass="p-0">
              <ul className="divide-y divide-edge">{list.map((r) => <li key={r.key}><Link to={`/erp/reports/${r.key}`} className="flex items-center gap-2.5 px-4 py-2.5 text-sm hover:bg-canvas"><FileSpreadsheet className="h-4 w-4 text-muted" />{r.title}</Link></li>)}</ul>
            </Panel>
          ))}
        </div>
      )}
    </div>
  );
}

export function ReportView() {
  const { key } = useParams();
  const t = todayIST();
  const [frm, setFrm] = useState(addDays(t, -89));
  const [to, setTo] = useState(t);
  const [q, setQ] = useState("");
  const params = frm === addDays(t, -89) && to === t ? null : { frm, to };
  const { data, isLoading, error } = useApi(`/reports/${key}`, params);
  usePageTitle(data?.title || "Report");
  const rows = useMemo(() => (data?.rows || []).filter((r) => !q || r.join(" ").toLowerCase().includes(q.toLowerCase())), [data, q]);
  const numeric = useMemo(() => (data?.columns || []).map((_, i) => (data.rows || []).length > 0 && data.rows.every((r) => r[i] === null || r[i] === "" || typeof r[i] === "number")), [data]);
  const dl = (fmt) => openFile(`/reports/${key}?fmt=${fmt}&frm=${frm}&to=${to}`, { name: `${key}.${fmt}`, type: fmt === "pdf" ? "application/pdf" : undefined, kind: "report" });
  return (
    <div className="pb-10">
      <PageHead back={["/erp/reports", "← Reports"]} title={data?.title || "Report"} sub={data ? `${rows.length} rows` : undefined}
        actions={<>
          <Button size="sm" variant="outline" onClick={() => dl("xlsx")}><Download className="h-4 w-4" />Excel</Button>
          <Button size="sm" variant="outline" onClick={() => dl("csv")}>CSV</Button>
          <Button size="sm" variant="outline" onClick={() => dl("pdf")}><FileText className="h-4 w-4" />PDF</Button>
        </>} />
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-2 text-sm text-muted">From<Input type="date" value={frm} onChange={(e) => setFrm(e.target.value)} className="h-9 w-40" /></label>
        <label className="flex items-center gap-2 text-sm text-muted">to<Input type="date" value={to} onChange={(e) => setTo(e.target.value)} className="h-9 w-40" /></label>
        <label className="relative ml-auto"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" /><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter rows" className="h-9 w-56 pl-9" /></label>
      </div>
      {isLoading ? <Skeleton className="h-72" /> : error ? <Empty title="This report isn't available to you" /> : !rows.length ? <Empty title="No rows for these dates" /> : (
        <div className="overflow-hidden rounded-xl border border-edge bg-surface">
          <div className="max-h-[70vh] overflow-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 border-b border-edge bg-canvas text-left text-xs text-muted"><tr>{data.columns.map((c, i) => <th key={c} className={cn("whitespace-nowrap px-3 py-2 font-medium", numeric[i] && "text-right")}>{c}</th>)}</tr></thead>
              <tbody className="divide-y divide-edge">
                {rows.map((r, i) => <tr key={i}>{r.map((x, j) => <td key={j} className={cn("px-3 py-2", numeric[j] ? "whitespace-nowrap text-right tabular" : "max-w-[320px] truncate")}>{typeof x === "number" ? new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(x) : /^\d{4}-\d{2}-\d{2}$/.test(String(x)) ? fmtDate(x) : x ?? "—"}</td>)}</tr>)}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
