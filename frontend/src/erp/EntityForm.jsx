import { useEffect, useMemo, useState } from "react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { todayIST } from "@/lib/format";
import { computeRecord } from "@/lib/expr";
import { Button, Field, Sheet, Alert } from "@/components/ui/kit";
import { toast } from "sonner";
import { groupFields, visibleField } from "./lib";
import { FieldInput, LinesEditor, cleanForSave, useRefCache } from "./fields";

const FULL = ["textarea", "markdown", "lines", "files", "refs", "multiselect", "json"];
const NUMT = ["number", "money", "percent"];

function numberize(e, doc) {
  const out = { ...doc };
  for (const f of e.fields) {
    const v = out[f.k];
    if (NUMT.includes(f.t) && typeof v === "string") out[f.k] = v === "" ? null : Number(v);
    if (f.t === "lines" && Array.isArray(v)) out[f.k] = v.map((r) => { const row = { ...r }; for (const sf of f.fields) if (NUMT.includes(sf.t) && typeof row[sf.k] === "string") row[sf.k] = row[sf.k] === "" ? 0 : Number(row[sf.k]); return row; });
  }
  return out;
}

function defaults(e, initial) {
  const d = {};
  for (const f of e.fields) {
    if (f.default !== undefined) d[f.k] = f.t === "number" || f.t === "money" || f.t === "percent" ? Number(f.default) : f.default;
    else if (f.t === "lines") d[f.k] = [];
    else if (f.t === "date" && f.req && /^(date|.*_on|from_date|start)$/.test(f.k)) d[f.k] = todayIST();
  }
  if (e.status?.default && e.status.field) d[e.status.field] = e.status.default;
  return { ...d, ...initial };
}

export function EntityFormSheet({ open, onOpenChange, entityKey, record, initial, onSaved, title }) {
  const { meta } = useAuth();
  const e = meta?.entities?.[entityKey];
  const [doc, setDoc] = useState({});
  const [refs, addRef] = useRefCache(record?._refs);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => { if (open && e) { setDoc(record ? { ...record } : defaults(e, initial)); setErr(""); } }, [open, record?.id]); // eslint-disable-line react-hooks/exhaustive-deps
  const computed = useMemo(() => (e ? computeRecord(e, numberize(e, doc)) : doc), [e, doc]);
  if (!e) return null;
  const sf = e.status?.field;
  const fields = e.fields.filter((f) => visibleField(f, computed) && !(f.k === sf && (e.actions || e.approval)) && !(record && f.ro && computed[f.k] == null));
  const groups = groupFields(fields);
  const set = (k) => (v) => setDoc((s) => ({ ...s, [k]: v }));
  async function save(ev) {
    ev.preventDefault();
    const missing = fields.filter((f) => f.req && !f.ro && !f.calc && (computed[f.k] === null || computed[f.k] === undefined || computed[f.k] === "" || (Array.isArray(computed[f.k]) && !computed[f.k].length)));
    if (missing.length) { setErr(`Fill in: ${missing.map((f) => f.l).join(", ")}`); return; }
    setBusy(true); setErr("");
    try {
      const body = cleanForSave(e, numberize(e, doc));
      const r = record ? await api.patch(`/e/${entityKey}/${record.id}`, body) : await api.post(`/e/${entityKey}`, body);
      toast.success(record ? "Saved" : `${e.label} added${r.data.code ? `: ${r.data.code}` : ""}`);
      onSaved?.(r.data);
    } catch (ex) { setErr(errMsg(ex)); } finally { setBusy(false); }
  }
  return (
    <Sheet open={open} onOpenChange={onOpenChange} title={title || (record ? `Edit ${e.label.toLowerCase()}` : `New ${e.label.toLowerCase()}`)} description={record?.code}
      footer={<><Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" form={`form-${entityKey}`} loading={busy}>{record ? "Save changes" : `Add ${e.label.toLowerCase()}`}</Button></>}>
      <form id={`form-${entityKey}`} onSubmit={save} className="space-y-6" noValidate>
        {groups.map((g) => (
          <fieldset key={g.group || "main"} className="space-y-3">
            {g.group && <legend className="mb-1 w-full border-b border-edge pb-1.5 text-[14px] font-semibold text-fg/80">{g.group}</legend>}
            <div className="grid gap-3 sm:grid-cols-2">
              {g.fields.map((f) => (
                <Field key={f.k} label={`${f.l}${f.unit && !["number", "money", "percent"].includes(f.t) ? ` (${f.unit})` : ""}`} required={f.req && !f.ro} hint={f.help} htmlFor={`f-${f.k}`}
                  className={cn(FULL.includes(f.t) && "sm:col-span-2")}>
                  {f.t === "lines" && !f.ro
                    ? <LinesEditor f={f} rows={doc[f.k] || []} onChange={set(f.k)} refs={refs} onRefTitle={addRef} doc={computed} />
                    : <FieldInput f={f} id={`f-${f.k}`} value={f.calc || f.ro ? computed[f.k] : doc[f.k]} onChange={set(f.k)} refs={refs} onRefTitle={addRef} doc={computed} />}
                </Field>
              ))}
            </div>
          </fieldset>
        ))}
        {err && <Alert tone="red">{err}</Alert>}
      </form>
    </Sheet>
  );
}
