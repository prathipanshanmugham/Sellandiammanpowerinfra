import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Pencil, FileText, MoreHorizontal, Trash2, History, Clock, CheckCircle2, XCircle, ShieldAlert, ArrowLeft } from "lucide-react";
import { api, errMsg, openFile } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { fmtDateTime, ago } from "@/lib/format";
import { Button, Badge, Tabs, TabPanel, Skeleton, Empty, Alert, Dialog, Field, Textarea, Confirm, Menu, MenuTrigger, MenuContent, MenuItem, MenuSeparator } from "@/components/ui/kit";
import { toast } from "sonner";
import { useApi, useInvalidate, groupFields, visibleField, stateOf, statusField, titleOf, can, isLocked, fieldOf } from "./lib";
import { FieldValue, FieldInput, useRefCache, cleanForSave } from "./fields";
import { EntityFormSheet } from "./EntityForm";
import { EntityList } from "./EntityList";
import { PageHead, usePageTitle } from "./ui";
import { DETAIL_EXTRAS, DETAIL_TABS } from "./extras";

const WIDE = ["textarea", "markdown", "lines", "files", "json"];

export default function EntityDetailPage() {
  const { key, id } = useParams();
  return <EntityDetail key={`${key}/${id}`} entityKey={key} id={id} />;
}

export function EntityDetail({ entityKey, id }) {
  const { meta, user } = useAuth();
  const e = meta?.entities?.[entityKey];
  const nav = useNavigate();
  const { data: doc, isLoading, error, refetch } = useApi(e ? `/e/${entityKey}/${id}` : null, null, { keep: false });
  const [edit, setEdit] = useState(false);
  const [tab, setTab] = useState("details");
  const [act, setAct] = useState(null);
  const [del, setDel] = useState(false);
  const invalidate = useInvalidate();
  const title = doc && e ? titleOf(e, doc, doc._refs) : "";
  usePageTitle(title || e?.label);
  if (!meta || isLoading) return <div className="space-y-4"><Skeleton className="h-10 w-1/2" /><Skeleton className="h-72" /></div>;
  if (!e) return <Empty title="You don't have access to this" className="py-24" />;
  if (error) return <div className="py-16"><Alert tone="red" title="Couldn't open this record">{errMsg(error)}</Alert><Button as={Link} to={`/erp/e/${entityKey}`} variant="outline" className="mt-4"><ArrowLeft className="h-4 w-4" />Back to {e.plural.toLowerCase()}</Button></div>;
  const sf = statusField(e);
  const st = sf ? stateOf(e, doc[sf]) : null;
  const locked = isLocked(e, doc);
  const appr = doc._approval;
  const Extra = DETAIL_EXTRAS[entityKey];
  const extraTabs = (DETAIL_TABS[entityKey] || []).filter((t) => !t.can || t.can(meta, user));
  const children = (e.children || []).filter((c) => meta.entities[c.entity]);
  const refresh = () => { refetch(); invalidate(`/e/${entityKey}`); };

  async function run(a, body = {}) {
    try {
      await api.post(`/e/${entityKey}/${id}/action/${a.key}`, body);
      toast.success(a.key === "submit" ? "Sent for approval" : `${a.label}: done`);
      setAct(null);
      refresh();
    } catch (ex) { toast.error(errMsg(ex)); throw ex; }
  }
  const onAction = (a) => (a.confirm || a.reason || a.need?.length ? setAct(a) : run(a));

  const tabs = [{ value: "details", label: "Details" }, ...extraTabs.map((t) => ({ value: t.key, label: t.label })),
    ...children.map((c) => ({ value: `c:${c.entity}`, label: c.label })), { value: "history", label: "History" }];
  return (
    <div className="pb-12">
      <PageHead back={[`/erp/e/${entityKey}`, `← ${e.plural}`]} icon={e.icon} title={title}
        actions={<>
          {(doc._actions || []).map((a) => <Button key={a.key} size="sm" variant={a.key === "submit" || a.tone === "primary" ? "primary" : /cancel|reject|lost|void|suspend/i.test(a.key) ? "outline" : "dark"} onClick={() => onAction(a)}>{a.label}</Button>)}
          {can(e, "w") && !locked && !e.readonly && <Button size="sm" variant="outline" onClick={() => setEdit(true)}><Pencil className="h-4 w-4" />Edit</Button>}
          <Button size="sm" variant="outline" onClick={() => openFile(`/e/${entityKey}/${id}/pdf`, { name: `${doc.code || entityKey}.pdf`, type: "application/pdf", kind: entityKey })}><FileText className="h-4 w-4" />PDF</Button>
          {can(e, "d") && (
            <Menu>
              <MenuTrigger asChild><Button size="sm" variant="ghost" aria-label="More"><MoreHorizontal className="h-4 w-4" /></Button></MenuTrigger>
              <MenuContent><MenuItem onSelect={() => setTab("history")}><History className="h-4 w-4" />History</MenuItem><MenuSeparator /><MenuItem danger onSelect={() => setDel(true)}><Trash2 className="h-4 w-4" />Delete</MenuItem></MenuContent>
            </Menu>
          )}
        </>}>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted">
          {st && <Badge tone={st.tone} dot>{st.label}</Badge>}
          {doc.code && e.title !== "code" && <span className="tabular">{doc.code}</span>}
          {doc.branch_id && doc._refs?.branches?.[doc.branch_id] && <span>{doc._refs.branches[doc.branch_id]}</span>}
          {doc.updated_at && <span>Updated {ago(doc.updated_at)}</span>}
          {locked && <Badge tone="gray">Locked</Badge>}
        </div>
      </PageHead>

      {appr && appr.status === "pending" && (
        <Alert tone="amber" icon={Clock} className="mb-4" title="Waiting for approval">
          Sent {ago(appr.created_at)} to {appr.approver_roles?.map((r) => meta.roles.find((x) => x.value === r)?.label || r).join(" or ")}{appr.amount ? ` for ₹${Number(appr.amount).toLocaleString("en-IN")}` : ""}. <Link to="/erp/approvals" className="font-semibold underline">Open approvals</Link>
        </Alert>
      )}
      {appr && appr.status === "rejected" && <Alert tone="red" icon={XCircle} className="mb-4" title="Rejected">{appr.reason || doc.decision_note}</Alert>}
      {doc.status_reason && <Alert tone="gray" icon={ShieldAlert} className="mb-4">Reason: {doc.status_reason}</Alert>}

      <Tabs value={tab} onValueChange={setTab} tabs={tabs}>
        <TabPanel value="details">
          {Extra && <div className="mb-5"><Extra doc={doc} e={e} refresh={refresh} /></div>}
          <Details e={e} doc={doc} />
        </TabPanel>
        {extraTabs.map((t) => <TabPanel key={t.key} value={t.key}>{tab === t.key && <t.C doc={doc} e={e} refresh={refresh} />}</TabPanel>)}
        {children.map((c) => <TabPanel key={c.entity} value={`c:${c.entity}`}>{tab === `c:${c.entity}` && <EntityList entityKey={c.entity} fixed={{ [c.field]: id }} embedded />}</TabPanel>)}
        <TabPanel value="history">{tab === "history" && <HistoryList entityKey={entityKey} id={id} />}</TabPanel>
      </Tabs>

      <EntityFormSheet open={edit} onOpenChange={setEdit} entityKey={entityKey} record={doc} onSaved={() => { setEdit(false); refresh(); }} />
      <ActionDialog a={act} e={e} doc={doc} onClose={() => setAct(null)} onRun={run} />
      <Confirm open={del} onOpenChange={setDel} title={`Delete this ${e.label.toLowerCase()}?`} text="It moves to the deleted list; the activity log keeps a record." tone="danger" confirmLabel="Delete" reason
        onConfirm={async (reason) => { try { await api.delete(`/e/${entityKey}/${id}`, { params: { reason } }); toast.success("Deleted"); invalidate(`/e/${entityKey}`); nav(`/erp/e/${entityKey}`); } catch (ex) { toast.error(errMsg(ex)); } }} />
    </div>
  );
}

const empty = (v) => v === null || v === undefined || v === "" || (Array.isArray(v) && !v.length);
export function Details({ e, doc }) {
  const [all, setAll] = useState(false);
  const sf = statusField(e);
  const fields = e.fields.filter((f) => visibleField(f, doc) && f.k !== sf);
  const hidden = fields.filter((f) => empty(doc[f.k])).length;
  const groups = groupFields(all ? fields : fields.filter((f) => !empty(doc[f.k])));
  return (
    <div className="space-y-5">
      {groups.map((g) => {
        const narrow = g.fields.filter((f) => !WIDE.includes(f.t));
        const wide = g.fields.filter((f) => WIDE.includes(f.t) && doc[f.k] !== null && doc[f.k] !== undefined && doc[f.k] !== "" && !(Array.isArray(doc[f.k]) && !doc[f.k].length));
        if (!narrow.some((f) => doc[f.k] !== null && doc[f.k] !== undefined && doc[f.k] !== "") && !wide.length) return null;
        return (
          <section key={g.group || "main"} className="rounded-xl border border-edge bg-surface p-4 shadow-card">
            {g.group && <h2 className="mb-3 font-sans text-[14px] font-semibold tracking-normal text-muted">{g.group}</h2>}
            {narrow.length > 0 && (
              <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
                {narrow.map((f) => <div key={f.k} className="min-w-0"><dt className="text-xs text-muted">{f.l}</dt><dd className="mt-0.5 break-words text-[15px]"><FieldValue f={f} v={doc[f.k]} refs={doc._refs} e={e} /></dd></div>)}
              </dl>
            )}
            {wide.map((f) => <div key={f.k} className="mt-4"><p className="mb-1.5 text-xs text-muted">{f.l}</p><FieldValue f={f} v={doc[f.k]} refs={doc._refs} e={e} /></div>)}
          </section>
        );
      })}
      {hidden > 0 && <button type="button" onClick={() => setAll((x) => !x)} className="text-sm text-cable hover:underline">{all ? "Hide empty fields" : `Show ${hidden} empty field${hidden === 1 ? "" : "s"}`}</button>}
      <p className="text-xs text-muted">Created {fmtDateTime(doc.created_at)}{doc.created_by && doc._refs?.users?.[doc.created_by] ? ` by ${doc._refs.users[doc.created_by]}` : ""}</p>
    </div>
  );
}

function ActionDialog({ a, e, doc, onClose, onRun }) {
  const [body, setBody] = useState({});
  const [busy, setBusy] = useState(false);
  const [refs, addRef] = useRefCache(doc?._refs);
  const need = useMemo(() => (a?.need || []).map((k) => fieldOf(e, k)).filter(Boolean), [a, e]);
  if (!a) return null;
  return (
    <Dialog open onOpenChange={(x) => { if (!x) { onClose(); setBody({}); } }} title={a.label} description={a.confirm || undefined}
      footer={<><Button variant="outline" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={async () => { setBusy(true); try { await onRun(a, cleanForSave({ fields: need }, body)); setBody({}); } catch { /* shown */ } finally { setBusy(false); } }}>{a.label}</Button></>}>
      <div className="space-y-3">
        {need.map((f) => <Field key={f.k} label={f.l} required><FieldInput f={{ ...f, ro: false, calc: null }} value={body[f.k] ?? doc[f.k]} onChange={(v) => setBody((s) => ({ ...s, [f.k]: v }))} refs={refs} onRefTitle={addRef} /></Field>)}
        {a.reason && <Field label="Reason" required><Textarea value={body.reason || ""} onChange={(ev) => setBody((s) => ({ ...s, reason: ev.target.value }))} autoFocus /></Field>}
        {!need.length && !a.reason && <p className="text-sm text-muted">{a.confirm}</p>}
      </div>
    </Dialog>
  );
}

const short = (x) => (x === null || x === undefined || x === "" ? "blank" : typeof x === "object" ? "…" : /^[0-9a-f-]{36}$/.test(String(x)) ? "another record" : String(x).slice(0, 40));
const ACTION_LABEL = { create: "Created", update: "Changed", delete: "Deleted", submitted: "Sent for approval", approve: "Approved", reject: "Rejected", auto_approved: "Approved automatically" };
function HistoryList({ entityKey, id }) {
  const { data, isLoading } = useApi(`/e/${entityKey}/${id}/history`);
  if (isLoading) return <Skeleton className="h-40" />;
  if (!data?.length) return <Empty title="No history yet" />;
  return (
    <ol className="relative space-y-4 border-l border-edge pl-5">
      {data.map((h) => (
        <li key={h.id} className="relative">
          <span className={cn("absolute -left-[26px] top-1 h-3 w-3 rounded-full border-2 border-surface", h.action === "reject" || h.action === "delete" ? "bg-bad" : h.action === "approve" ? "bg-good" : "bg-steel")} />
          <p className="text-sm"><span className="font-medium">{ACTION_LABEL[h.action] || h.action.replace(/_/g, " ")}</span> by {h.user_name || "System"}</p>
          <p className="text-xs text-muted tabular">{fmtDateTime(h.at)}</p>
          {h.details?.changes && <ul className="mt-1 space-y-0.5 text-xs text-muted">{Object.entries(h.details.changes).slice(0, 8).map(([k, v]) => <li key={k}><span className="font-medium text-fg/85">{k.replace(/_id$/, "").replace(/_/g, " ")}</span>{Array.isArray(v) ? <>: {short(v[0])} to {short(v[1])}</> : " changed"}</li>)}</ul>}
          {h.details?.reason && <p className="mt-1 text-xs">“{h.details.reason}”</p>}
        </li>
      ))}
    </ol>
  );
}

export { CheckCircle2 };
