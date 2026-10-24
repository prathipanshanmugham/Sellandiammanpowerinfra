import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Plus, Search, Download, ChevronUp, ChevronDown, X, Filter, Trash2, ChevronLeft, ChevronRight, Inbox } from "lucide-react";
import { api, errMsg, openFile, useMedia } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { num } from "@/lib/format";
import { Button, Input, Select, Badge, Empty, Skeleton, Menu, MenuTrigger, MenuContent, MenuItem, Confirm, Checkbox, Alert } from "@/components/ui/kit";
import { Icon } from "@/components/ui/icons";
import { toast } from "sonner";
import { useApi, useInvalidate, fieldOf, optionsFor, titleOf, can, statusField } from "./lib";
import { FieldValue, RefPicker } from "./fields";
import { EntityFormSheet } from "./EntityForm";
import { PageHead, usePageTitle } from "./ui";

const PAGE = 50;

export default function EntityListPage() {
  const { key } = useParams();
  return <EntityList key={key} entityKey={key} />;
}

export function EntityList({ entityKey, fixed = {}, embedded, title, onOpen }) {
  const { meta } = useAuth();
  const e = meta?.entities?.[entityKey];
  const nav = useNavigate();
  const [sp, setSp] = useSearchParams();
  const local = useState({});
  // embedded lists (child tabs) keep their own filters; full pages keep them in the address bar
  const params = embedded ? local[0] : Object.fromEntries([...sp.entries()].filter(([k]) => k !== "new"));
  const setParam = (k, v) => {
    if (embedded) { local[1]((s) => { const n = { ...s, [k]: v }; if (!v) delete n[k]; if (k !== "page") delete n.page; return n; }); return; }
    const n = new URLSearchParams(sp); if (v) n.set(k, v); else n.delete(k); if (k !== "page") n.delete("page"); setSp(n, { replace: true });
  };
  const [q, setQ] = useState(params.q || "");
  useEffect(() => { const t = setTimeout(() => { if ((params.q || "") !== q) setParam("q", q); }, 300); return () => clearTimeout(t); }, [q]); // eslint-disable-line react-hooks/exhaustive-deps
  const query = { ...params, ...fixed, size: embedded ? 20 : PAGE };
  const { data, isLoading, error, isFetching } = useApi(e && can(e, "r") ? `/e/${entityKey}` : null, query);
  const [creating, setCreating] = useState(!embedded && sp.get("new") === "1");
  const [sel, setSel] = useState([]);
  const [del, setDel] = useState(false);
  const invalidate = useInvalidate();
  const mobile = useMedia("(max-width: 767px)");
  usePageTitle(title || e?.plural, !embedded);

  if (!meta) return <div className="p-6"><Skeleton className="h-64" /></div>;
  if (!e) return <Empty title="You don't have access to this list" text="Ask your administrator if you need it." className="py-24" />;
  const sf = statusField(e);
  const cols = (e.list || []).filter((k) => !Object.keys(fixed).includes(k)).map((k) => fieldOf(e, k)).filter(Boolean);
  const filters = (e.filters || []).filter((k) => k !== sf && !Object.keys(fixed).includes(k)).map((k) => fieldOf(e, k)).filter(Boolean);
  const sort = params.sort || e.sort || "-created_at";
  const toggleSort = (k) => setParam("sort", sort === k ? `-${k}` : sort === `-${k}` ? "" : k);
  const page = Number(params.page || 1);
  const pages = data ? Math.max(1, Math.ceil(data.total / (embedded ? 20 : PAGE))) : 1;
  const open = (d) => (onOpen ? onOpen(d) : nav(`/erp/e/${entityKey}/${d.id}`));
  const activeFilters = filters.filter((f) => params[f.k]).length + (params.status ? 1 : 0);
  const states = e.status?.states || [];
  const prefill = embedded ? fixed : Object.fromEntries([...sp.entries()].filter(([k]) => e.fields.some((f) => f.k === k)));
  if (!can(e, "r")) {
    return (
      <div>
        <Empty title={`You can add ${e.plural.toLowerCase()}, but not see the list`} text="What you add goes to the team that handles it; you'll be notified when it moves." className="py-20"
          action={can(e, "w") && <Button onClick={() => setCreating(true)}><Plus className="h-4 w-4" />New {e.label.toLowerCase()}</Button>} />
        <EntityFormSheet open={creating} onOpenChange={setCreating} entityKey={entityKey} initial={prefill} onSaved={() => { setCreating(false); toast.success("Sent"); }} />
      </div>
    );
  }

  async function bulkDelete(reason) {
    const r = await api.post(`/e/${entityKey}/bulk`, { op: "delete", ids: sel, reason });
    toast.success(`Deleted ${r.data.done}`);
    if (r.data.errors.length) toast.error(r.data.errors[0].error);
    setSel([]);
    invalidate(`/e/${entityKey}`);
  }
  const exportAs = (fmt) => openFile(`/e/${entityKey}/export/${fmt}?${new URLSearchParams(Object.fromEntries(Object.entries({ ...params, ...fixed }).filter(([, v]) => v))).toString()}`, { name: `${entityKey}.${fmt}` });

  return (
    <div className={embedded ? "" : "pb-10"}>
      {!embedded && (
        <PageHead icon={e.icon} title={title || e.plural} sub={e.help}
          actions={<>
            {can(e, "e") && (
              <Menu>
                <MenuTrigger asChild><Button variant="outline" size="sm"><Download className="h-4 w-4" />Export</Button></MenuTrigger>
                <MenuContent><MenuItem onSelect={() => exportAs("xlsx")}>Excel (.xlsx)</MenuItem><MenuItem onSelect={() => exportAs("csv")}>CSV</MenuItem><MenuItem onSelect={() => exportAs("pdf")}>PDF</MenuItem></MenuContent>
              </Menu>
            )}
            {can(e, "w") && !e.readonly && <Button size="sm" onClick={() => setCreating(true)}><Plus className="h-4 w-4" />New {e.label.toLowerCase()}</Button>}
          </>} />
      )}
      {states.length > 0 && (
        <div className="scrollbar-thin -mx-1 mb-3 flex gap-1 overflow-x-auto px-1">
          {[{ value: "", label: "All" }, ...states].map((s) => (
            <button key={s.value} type="button" onClick={() => setParam("status", s.value)} aria-pressed={(params.status || "") === s.value}
              className={cn("shrink-0 rounded-full px-3 py-1 text-[13px]", (params.status || "") === s.value ? "bg-ink text-white" : "bg-surface text-fg/75 ring-1 ring-inset ring-edge hover:bg-canvas")}>{s.label}</button>
          ))}
        </div>
      )}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <label className="relative min-w-[200px] flex-1 sm:max-w-xs">
          <span className="sr-only">Search {e.plural}</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <Input value={q} onChange={(ev) => setQ(ev.target.value)} placeholder={`Search ${e.plural.toLowerCase()}`} className="h-9 pl-9" />
        </label>
        {filters.slice(0, mobile ? 0 : 4).map((f) => <FilterControl key={f.k} f={f} value={params[f.k]} onChange={(v) => setParam(f.k, v)} refs={data?.refs} />)}
        {(mobile ? filters.length : filters.length > 4) && <MoreFilters filters={mobile ? filters : filters.slice(4)} params={params} setParam={setParam} refs={data?.refs} />}
        {activeFilters > 0 && <Button variant="ghost" size="sm" onClick={() => { if (embedded) local[1]({}); else setSp({}, { replace: true }); setQ(""); }}><X className="h-3.5 w-3.5" />Clear</Button>}
        {embedded && can(e, "w") && !e.readonly && <Button size="sm" variant="outline" className="ml-auto" onClick={() => setCreating(true)}><Plus className="h-4 w-4" />Add</Button>}
        {!embedded && data && <span className="ml-auto text-sm text-muted tabular">{num(data.total)} {data.total === 1 ? e.label.toLowerCase() : e.plural.toLowerCase()}</span>}
      </div>
      {sel.length > 0 && (
        <div className="mb-3 flex items-center gap-3 rounded-lg bg-ink px-4 py-2 text-sm text-white">
          <span>{sel.length} selected</span>
          {can(e, "d") && <Button size="sm" variant="danger" onClick={() => setDel(true)}><Trash2 className="h-4 w-4" />Delete</Button>}
          <Button size="sm" variant="light" onClick={() => setSel([])}>Cancel</Button>
        </div>
      )}
      {error ? <Alert tone="red">{errMsg(error)}</Alert> : isLoading ? <Skeleton className="h-72" /> : !data?.items.length ? (
        <div className="rounded-xl border border-edge bg-surface"><Empty icon={Inbox} title={activeFilters || params.q ? "Nothing matches" : `No ${e.plural.toLowerCase()} yet`}
          text={activeFilters || params.q ? "Try fewer filters or a different search." : can(e, "w") ? `Add the first ${e.label.toLowerCase()}.` : undefined}
          action={!activeFilters && can(e, "w") && !e.readonly ? <Button size="sm" onClick={() => setCreating(true)}><Plus className="h-4 w-4" />New {e.label.toLowerCase()}</Button> : null} /></div>
      ) : mobile ? (
        <ul className="divide-y divide-edge overflow-hidden rounded-xl border border-edge bg-surface">
          {data.items.map((d) => (
            <li key={d.id}>
              <button type="button" onClick={() => open(d)} className="block w-full px-4 py-3 text-left active:bg-canvas">
                <div className="flex items-start justify-between gap-3">
                  <span className="min-w-0"><span className="block truncate font-medium">{titleOf(e, d, data.refs)}</span>
                    {d.code && e.title !== "code" && <span className="block text-xs text-muted tabular">{d.code}</span>}</span>
                  {sf && d[sf] && <FieldValue f={fieldOf(e, sf)} v={d[sf]} e={e} compact />}
                </div>
                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted">
                  {cols.filter((c) => c.k !== sf && c.k !== e.title && c.k !== "code").slice(0, 3).map((c) => <span key={c.k}><FieldValue f={c} v={d[c.k]} refs={data.refs} e={e} compact /></span>)}
                </div>
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <div className={cn("overflow-hidden rounded-xl border border-edge bg-surface", isFetching && "opacity-80")}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-edge bg-canvas text-left text-xs text-muted">
                <tr>
                  {can(e, "d") && !embedded && <th className="w-10 px-3 py-2.5"><Checkbox checked={sel.length === data.items.length} onChange={(v) => setSel(v ? data.items.map((d) => d.id) : [])} /></th>}
                  {cols.map((c) => {
                    const s = sort === c.k ? "asc" : sort === `-${c.k}` ? "desc" : null;
                    return (
                      <th key={c.k} scope="col" className={cn("whitespace-nowrap px-3 py-2.5 font-medium", ["money", "number", "percent"].includes(c.t) && "text-right")} aria-sort={s === "asc" ? "ascending" : s === "desc" ? "descending" : undefined}>
                        <button type="button" onClick={() => toggleSort(c.k)} className="inline-flex items-center gap-1 hover:text-fg">{c.l}{s === "asc" ? <ChevronUp className="h-3 w-3" /> : s === "desc" ? <ChevronDown className="h-3 w-3" /> : null}</button>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody className="divide-y divide-edge">
                {data.items.map((d) => (
                  <tr key={d.id} onClick={() => open(d)} className="cursor-pointer hover:bg-canvas/70">
                    {can(e, "d") && !embedded && <td className="px-3 py-2.5" onClick={(ev) => ev.stopPropagation()}><Checkbox checked={sel.includes(d.id)} onChange={(v) => setSel(v ? [...sel, d.id] : sel.filter((x) => x !== d.id))} /></td>}
                    {cols.map((c, i) => (
                      <td key={c.k} className={cn("max-w-[280px] px-3 py-2.5", ["money", "number", "percent"].includes(c.t) && "whitespace-nowrap text-right", i === 0 && "font-medium")}>
                        {i === 0 ? <Link to={`/erp/e/${entityKey}/${d.id}`} onClick={(ev) => { if (onOpen) { ev.preventDefault(); } }} className="truncate hover:underline"><FieldValue f={c} v={d[c.k]} refs={data.refs} e={e} compact /></Link>
                          : <span className="block truncate"><FieldValue f={c} v={d[c.k]} refs={data.refs} e={e} compact /></span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {pages > 1 && (
        <div className="mt-3 flex items-center justify-end gap-2 text-sm">
          <span className="text-muted tabular">Page {page} of {pages}</span>
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setParam("page", String(page - 1))} aria-label="Previous page"><ChevronLeft className="h-4 w-4" /></Button>
          <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => setParam("page", String(page + 1))} aria-label="Next page"><ChevronRight className="h-4 w-4" /></Button>
        </div>
      )}
      <EntityFormSheet open={creating} onOpenChange={(v) => { setCreating(v); if (!v && sp.get("new")) { const n = new URLSearchParams(sp); n.delete("new"); setSp(n, { replace: true }); } }}
        entityKey={entityKey} initial={prefill} onSaved={(d) => { setCreating(false); invalidate(`/e/${entityKey}`); if (!embedded) nav(`/erp/e/${entityKey}/${d.id}`); }} />
      <Confirm open={del} onOpenChange={setDel} title={`Delete ${sel.length} ${e.plural.toLowerCase()}?`} text="They move to the deleted list and are kept in the activity log." tone="danger" confirmLabel="Delete" reason onConfirm={bulkDelete} />
    </div>
  );
}

function FilterControl({ f, value, onChange, refs }) {
  const { meta } = useAuth();
  if (f.t === "select") return <div className="w-[160px]"><Select value={value || ""} onChange={(ev) => onChange(ev.target.value)} options={optionsFor(meta, f)} placeholder={`Any ${f.l.toLowerCase()}`} className="h-9" /></div>;
  if (f.t === "ref") return <div className="w-[190px]"><RefPicker f={f} value={value || null} onChange={(v) => onChange(v || "")} refs={refs} placeholder={`Any ${f.l.toLowerCase()}`} className="h-9" /></div>;
  if (f.t === "bool") return <div className="w-[140px]"><Select value={value || ""} onChange={(ev) => onChange(ev.target.value)} options={[{ value: "true", label: "Yes" }, { value: "false", label: "No" }]} placeholder={f.l} className="h-9" /></div>;
  return <div className="w-[150px]"><Input value={value || ""} onChange={(ev) => onChange(ev.target.value)} placeholder={f.l} className="h-9" /></div>;
}

function MoreFilters({ filters, params, setParam, refs }) {
  const [open, setOpen] = useState(false);
  const n = filters.filter((f) => params[f.k]).length;
  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen((x) => !x)} aria-expanded={open}><Filter className="h-4 w-4" />Filters{n ? <Badge tone="ink">{n}</Badge> : null}</Button>
      {open && <div className="flex w-full flex-wrap gap-2 rounded-lg border border-edge bg-surface p-2">{filters.map((f) => <FilterControl key={f.k} f={f} value={params[f.k]} onChange={(v) => setParam(f.k, v)} refs={refs} />)}</div>}
    </>
  );
}

export { Icon };
