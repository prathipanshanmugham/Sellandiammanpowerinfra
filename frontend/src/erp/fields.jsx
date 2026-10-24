import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Check, ChevronsUpDown, Paperclip, Plus, Trash2, Upload, X, MapPin, Search, Loader2, Copy } from "lucide-react";
import { api, errMsg, openStoredFile, useDebounced } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { inr, num, pct, fmtDate, fmtDateTime, telLink } from "@/lib/format";
import { Badge, Input, Select, Textarea, Switch, Popover, PopoverTrigger, PopoverContent, Button } from "@/components/ui/kit";
import { Markdown } from "@/lib/markdown";
import { optionsFor, optLabel, titleOf } from "./lib";

// ------------------------------------------------------------------ values (read-only)
export function FieldValue({ f, v, refs, e, compact }) {
  const { meta } = useAuth();
  if (v === null || v === undefined || v === "" || (Array.isArray(v) && !v.length)) return <span className="text-muted">—</span>;
  switch (f.t) {
    case "money": return <span className="tabular">{inr(v)}</span>;
    case "number": return <span className="tabular">{num(v)}{f.unit ? <span className="text-muted"> {f.unit}</span> : null}</span>;
    case "percent": return <span className="tabular">{pct(v)}</span>;
    case "date": return <span className="tabular">{fmtDate(v)}</span>;
    case "datetime": return <span className="tabular">{fmtDateTime(v)}</span>;
    case "bool": return v ? <Badge tone="green">Yes</Badge> : <span className="text-muted">No</span>;
    case "phone": return <a href={telLink(v)} className="tabular hover:underline" onClick={(ev) => ev.stopPropagation()}>{v}</a>;
    case "email": return <a href={`mailto:${v}`} className="hover:underline" onClick={(ev) => ev.stopPropagation()}>{v}</a>;
    case "select": {
      const st = e?.status?.field === f.k ? (e.status.states || []).find((s) => s.value === v) : null;
      return st ? <Badge tone={st.tone} dot>{st.label}</Badge> : <span>{optLabel(meta, f, v)}</span>;
    }
    case "multiselect": return <span className="flex flex-wrap gap-1">{v.map((x) => <Badge key={x}>{optLabel(meta, f, x)}</Badge>)}</span>;
    case "ref": {
      const t = refs?.[f.ref]?.[v];
      if (compact || f.ref === "users" || f.ref === "branches" || !meta?.entities?.[f.ref]) return <span>{t || "…"}</span>;
      return <Link to={`/erp/e/${f.ref}/${v}`} className="text-cable hover:underline" onClick={(ev) => ev.stopPropagation()}>{t || "Open"}</Link>;
    }
    case "refs": return <span>{v.map((x) => refs?.[f.ref]?.[x] || "…").join(", ")}</span>;
    case "file": return <FileChip file={v} />;
    case "files": return compact ? <span className="text-muted">{v.length} file{v.length === 1 ? "" : "s"}</span> : <span className="flex flex-wrap gap-1.5">{v.map((x) => <FileChip key={x.id} file={x} />)}</span>;
    case "geo": return v?.lat ? <a href={`https://www.google.com/maps/search/?api=1&query=${v.lat},${v.lng}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-cable hover:underline"><MapPin className="h-3.5 w-3.5" />{Number(v.lat).toFixed(5)}, {Number(v.lng).toFixed(5)}</a> : <span className="text-muted">—</span>;
    case "markdown": return compact ? <span className="line-clamp-1">{String(v).slice(0, 80)}</span> : <Markdown text={v} className="prose-site text-sm" />;
    case "textarea": return compact ? <span className="line-clamp-1">{String(v)}</span> : <span className="whitespace-pre-line">{v}</span>;
    case "json": return <JsonValue v={v} />;
    case "lines": return compact ? <span className="text-muted">{v.length} lines</span> : <LinesView f={f} rows={v} refs={refs} />;
    default: return <span>{String(v)}</span>;
  }
}

function JsonValue({ v }) {
  if (v && typeof v === "object" && v.title && v.headline) {
    return (
      <div className="rounded-md bg-canvas p-3 text-sm">
        <p className="font-medium">{v.title}</p>
        <p className="mt-1 text-muted">{v.headline.label}: <span className="font-semibold text-fg">{typeof v.headline.value === "number" ? num(v.headline.value) : v.headline.value} {v.headline.unit}</span></p>
        {v.verdict && <p className="mt-1">{v.verdict}</p>}
      </div>
    );
  }
  return <pre className="max-h-48 overflow-auto rounded-md bg-canvas p-2 text-xs">{JSON.stringify(v, null, 2)}</pre>;
}

export function FileChip({ file, onRemove }) {
  if (!file) return null;
  return (
    <span className="inline-flex max-w-full items-center gap-1.5 rounded-md border border-edge bg-surface px-2 py-1 text-xs">
      <Paperclip className="h-3.5 w-3.5 shrink-0 text-muted" />
      <button type="button" onClick={(ev) => { ev.stopPropagation(); openStoredFile(file); }} className="truncate hover:underline">{file.name || "File"}</button>
      {onRemove && <button type="button" onClick={onRemove} className="text-muted hover:text-bad" aria-label={`Remove ${file.name}`}><X className="h-3.5 w-3.5" /></button>}
    </span>
  );
}

export function LinesView({ f, rows, refs }) {
  const cols = f.fields.filter((x) => x.t !== "textarea" || x.k === "description");
  const totals = cols.map((c) => (["money"].includes(c.t) || (c.t === "number" && /amount|qty|total/i.test(c.k)) ? rows.reduce((a, r) => a + (Number(r[c.k]) || 0), 0) : null));
  return (
    <div className="overflow-x-auto rounded-lg border border-edge">
      <table className="w-full text-sm">
        <thead className="bg-canvas text-left text-xs text-muted">
          <tr><th className="w-8 px-2 py-2 font-medium">#</th>{cols.map((c) => <th key={c.k} className={cn("whitespace-nowrap px-2 py-2 font-medium", ["money", "number", "percent"].includes(c.t) && "text-right")}>{c.l}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-edge">
          {rows.map((r, i) => (
            <tr key={i} className="align-top">
              <td className="px-2 py-2 text-muted tabular">{i + 1}</td>
              {cols.map((c) => <td key={c.k} className={cn("px-2 py-2", ["money", "number", "percent"].includes(c.t) && "text-right", c.k === "description" && "min-w-[220px]")}><FieldValue f={c} v={r[c.k]} refs={refs} compact /></td>)}
            </tr>
          ))}
        </tbody>
        {rows.length > 1 && totals.some((x) => x !== null) && (
          <tfoot className="border-t border-edge bg-canvas font-semibold">
            <tr><td />{cols.map((c, i) => <td key={c.k} className="px-2 py-2 text-right tabular">{totals[i] === null ? "" : c.t === "money" ? inr(totals[i]) : /qty/i.test(c.k) ? "" : num(totals[i])}</td>)}</tr>
          </tfoot>
        )}
      </table>
    </div>
  );
}

// ------------------------------------------------------------------ inputs
export function FieldInput({ f, value, onChange, refs, onRefTitle, doc, id }) {
  const { meta } = useAuth();
  const ro = f.ro || f.calc;
  if (ro) return <div className="flex min-h-10 items-center rounded-md bg-canvas px-3 text-sm"><FieldValue f={f} v={value} refs={refs} compact /></div>;
  switch (f.t) {
    case "textarea": return <Textarea id={id} value={value ?? ""} onChange={(e) => onChange(e.target.value)} rows={3} />;
    case "markdown": return <Textarea id={id} value={value ?? ""} onChange={(e) => onChange(e.target.value)} rows={8} className="font-mono text-[13px]" />;
    case "number": case "money": case "percent":
      return (
        <div className="relative">
          {f.t === "money" && <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted">₹</span>}
          <Input id={id} inputMode="decimal" value={value ?? ""} onChange={(e) => { const s = e.target.value.replace(/[^\d.\-]/g, ""); onChange(s === "" ? null : s); }}
            className={cn("tabular", f.t === "money" && "pl-7", (f.unit || f.t === "percent") && "pr-14")} />
          {(f.unit || f.t === "percent") && <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted">{f.t === "percent" ? "%" : f.unit}</span>}
        </div>
      );
    case "date": return <Input id={id} type="date" value={value ?? ""} onChange={(e) => onChange(e.target.value || null)} />;
    case "datetime": return <Input id={id} type="datetime-local" value={value ? String(value).slice(0, 16) : ""} onChange={(e) => onChange(e.target.value || null)} />;
    case "bool": return <div className="flex h-10 items-center"><Switch checked={!!value} onChange={onChange} label={value ? "Yes" : "No"} /></div>;
    case "select": return <Select id={id} value={value ?? ""} onChange={(e) => onChange(e.target.value || null)} options={optionsFor(meta, f)} placeholder="Choose" />;
    case "multiselect": return <MultiSelect f={f} value={value || []} onChange={onChange} />;
    case "ref": return <RefPicker f={f} value={value} onChange={onChange} refs={refs} onRefTitle={onRefTitle} doc={doc} />;
    case "refs": return <RefsPicker f={f} value={value || []} onChange={onChange} refs={refs} onRefTitle={onRefTitle} />;
    case "phone": return <Input id={id} type="tel" inputMode="tel" value={value ?? ""} onChange={(e) => onChange(e.target.value)} />;
    case "email": return <Input id={id} type="email" value={value ?? ""} onChange={(e) => onChange(e.target.value)} />;
    case "file": return <FilesInput value={value ? [value] : []} onChange={(x) => onChange(x[0] || null)} max={1} />;
    case "files": return <FilesInput value={value || []} onChange={onChange} />;
    case "geo": return <GeoInput value={value} onChange={onChange} />;
    case "json": return <div className="rounded-md bg-canvas px-3 py-2 text-sm text-muted">Filled in automatically</div>;
    default: return <Input id={id} value={value ?? ""} onChange={(e) => onChange(e.target.value)} />;
  }
}

function MultiSelect({ f, value, onChange }) {
  const { meta } = useAuth();
  const opts = optionsFor(meta, f);
  return (
    <div className="flex flex-wrap gap-1.5 rounded-md border border-edge bg-surface p-1.5">
      {opts.map((o) => {
        const on = value.includes(o.value);
        return <button key={o.value} type="button" onClick={() => onChange(on ? value.filter((x) => x !== o.value) : [...value, o.value])} aria-pressed={on}
          className={cn("rounded px-2 py-1 text-xs", on ? "bg-ink text-white" : "bg-canvas text-fg/75 hover:bg-fg/10")}>{o.label}</button>;
      })}
    </div>
  );
}

// Reference picker: searches the referenced list (users come from the staff directory).
export function useRefSearch(ref, q, enabled, extra) {
  const { meta } = useAuth();
  const [state, set] = useState({ items: [], loading: false, error: "" });
  const dq = useDebounced(q, 200);
  const ex = JSON.stringify(extra || {});
  useEffect(() => {
    if (!enabled) return undefined;
    let on = true;
    set((s) => ({ ...s, loading: true, error: "" }));
    const p = ref === "users" ? api.get("/users/lookup", { params: { q: dq } }).then((r) => r.data.map((u) => ({ id: u.id, title: u.name, sub: u.designation || u.role })))
      : ref === "branches" ? api.get("/branches/all").then((r) => r.data.filter((b) => !dq || b.name.toLowerCase().includes(dq.toLowerCase())).map((b) => ({ id: b.id, title: b.name, sub: b.code })))
        : api.get(`/e/${ref}`, { params: { q: dq, size: 25, ...JSON.parse(ex) } }).then((r) => {
          const e = meta?.entities?.[ref];
          return r.data.items.map((d) => ({ id: d.id, title: titleOf(e, d, r.data.refs), sub: d.code && e?.title !== "code" ? d.code : (d.town || d.unit || "") }));
        });
    p.then((items) => on && set({ items, loading: false, error: "" })).catch((e) => on && set({ items: [], loading: false, error: errMsg(e) }));
    return () => { on = false; };
  }, [ref, dq, enabled, ex, meta]);
  return state;
}

export function RefPicker({ f, value, onChange, refs, onRefTitle, placeholder = "Choose", className, filter }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const { items, loading, error } = useRefSearch(f.ref, q, open, filter);
  const title = value ? refs?.[f.ref]?.[value] || "Selected" : "";
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button type="button" className={cn("flex h-10 w-full items-center justify-between gap-2 rounded-md border border-edge bg-surface px-3 text-left text-sm focus:border-signal-deep focus:outline-none focus:ring-2 focus:ring-signal/40", className)}>
          <span className={cn("truncate", !value && "text-muted/80")}>{title || placeholder}</span>
          <span className="flex items-center gap-1">
            {value && <span role="button" tabIndex={-1} onClick={(ev) => { ev.stopPropagation(); onChange(null); }} className="rounded p-0.5 text-muted hover:text-bad" aria-label="Clear"><X className="h-3.5 w-3.5" /></span>}
            <ChevronsUpDown className="h-4 w-4 shrink-0 text-muted" />
          </span>
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-[min(360px,calc(100vw-24px))] p-0" align="start">
        <div className="flex items-center gap-2 border-b border-edge px-3"><Search className="h-4 w-4 text-muted" /><input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search" className="h-10 flex-1 bg-transparent text-sm outline-none" /></div>
        <div className="max-h-72 overflow-y-auto p-1">
          {loading && <p className="flex items-center gap-2 px-3 py-2 text-sm text-muted"><Loader2 className="h-4 w-4 animate-spin" />Searching…</p>}
          {error && <p className="px-3 py-2 text-sm text-bad">{error}</p>}
          {!loading && !error && !items.length && <p className="px-3 py-2 text-sm text-muted">Nothing found</p>}
          {items.map((it) => (
            <button key={it.id} type="button" onClick={() => { onRefTitle?.(f.ref, it.id, it.title); onChange(it.id); setOpen(false); setQ(""); }}
              className={cn("flex w-full items-center justify-between gap-2 rounded-md px-3 py-2 text-left text-sm hover:bg-fg/5", it.id === value && "bg-fg/5")}>
              <span className="min-w-0"><span className="block truncate">{it.title}</span>{it.sub && <span className="block truncate text-xs text-muted">{it.sub}</span>}</span>
              {it.id === value && <Check className="h-4 w-4 shrink-0" />}
            </button>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
}

function RefsPicker({ f, value, onChange, refs, onRefTitle }) {
  return (
    <div className="space-y-2">
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {value.map((id) => <span key={id} className="inline-flex items-center gap-1 rounded-md bg-canvas px-2 py-1 text-xs">{refs?.[f.ref]?.[id] || "…"}<button type="button" onClick={() => onChange(value.filter((x) => x !== id))} aria-label="Remove" className="text-muted hover:text-bad"><X className="h-3 w-3" /></button></span>)}
        </div>
      )}
      <RefPicker f={f} value={null} onChange={(id) => id && !value.includes(id) && onChange([...value, id])} refs={refs} onRefTitle={onRefTitle} placeholder="Add" />
    </div>
  );
}

export function FilesInput({ value, onChange, max = 10, portal }) {
  const ref = useRef(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  async function pick(list) {
    setBusy(true); setErr("");
    const out = [...value];
    for (const file of Array.from(list).slice(0, max - value.length)) {
      const fd = new FormData();
      fd.append("file", file);
      try { out.push((await api.post(portal ? "/portal/files" : "/files", fd)).data); } catch (e) { setErr(errMsg(e)); }
    }
    setBusy(false);
    onChange(out);
  }
  return (
    <div>
      {value.length > 0 && <div className="mb-2 flex flex-wrap gap-1.5">{value.map((x) => <FileChip key={x.id} file={x} onRemove={() => onChange(value.filter((y) => y.id !== x.id))} />)}</div>}
      {value.length < max && (
        <button type="button" onClick={() => ref.current?.click()} onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); pick(e.dataTransfer.files); }}
          className="flex w-full items-center gap-2 rounded-md border border-dashed border-edge px-3 py-2.5 text-sm text-muted hover:border-fg/30">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}{busy ? "Uploading…" : "Add files (drag here or click)"}
        </button>
      )}
      <input ref={ref} type="file" multiple={max > 1} className="hidden" onChange={(e) => pick(e.target.files)} />
      {err && <p className="mt-1 text-xs text-bad">{err}</p>}
    </div>
  );
}

function GeoInput({ value, onChange }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button type="button" variant="outline" size="sm" loading={busy} onClick={() => {
        if (!navigator.geolocation) { setErr("Location isn't available on this device"); return; }
        setBusy(true); setErr("");
        navigator.geolocation.getCurrentPosition((p) => { onChange({ lat: p.coords.latitude, lng: p.coords.longitude, accuracy: Math.round(p.coords.accuracy) }); setBusy(false); },
          (e) => { setErr(e.message || "Couldn't get the location"); setBusy(false); }, { enableHighAccuracy: true, timeout: 15000 });
      }}><MapPin className="h-4 w-4" />Use my location</Button>
      {value?.lat && <span className="text-sm tabular">{Number(value.lat).toFixed(5)}, {Number(value.lng).toFixed(5)}</span>}
      {err && <span className="text-xs text-bad">{err}</span>}
    </div>
  );
}

// ------------------------------------------------------------------ line items editor
export function LinesEditor({ f, rows, onChange, refs, onRefTitle, doc }) {
  const { meta } = useAuth();
  const blank = () => Object.fromEntries(f.fields.map((x) => [x.k, x.default ?? null]));
  const set = (i, k, v) => onChange(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  const editable = f.fields.filter((x) => !x.hide || true);
  const wide = (x) => ["description", "name", "item", "activity", "point"].includes(x.k) || x.t === "textarea";
  return (
    <div className="space-y-2">
      {rows.map((r, i) => (
        <div key={i} className="rounded-lg border border-edge bg-surface p-3">
          <div className="mb-2 flex items-center justify-between text-xs text-muted"><span className="tabular">Line {i + 1}</span>
            <span className="flex gap-1">
              <button type="button" className="rounded p-1 hover:bg-fg/5 hover:text-fg" aria-label="Copy line" onClick={() => onChange([...rows.slice(0, i + 1), { ...r }, ...rows.slice(i + 1)])}><Copy className="h-3.5 w-3.5" /></button>
              <button type="button" className="rounded p-1 hover:bg-bad/10 hover:text-bad" aria-label="Remove line" onClick={() => onChange(rows.filter((_, j) => j !== i))}><Trash2 className="h-3.5 w-3.5" /></button>
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-6">
            {editable.map((x) => (
              <label key={x.k} className={cn("block min-w-0", wide(x) ? "col-span-2 md:col-span-6" : x.t === "ref" ? "col-span-2 md:col-span-3" : "col-span-1")}>
                <span className="mb-0.5 block text-[11px] text-muted">{x.l}{x.unit ? ` (${x.unit})` : ""}</span>
                {x.t === "textarea" ? <Textarea rows={2} value={r[x.k] ?? ""} onChange={(e) => set(i, x.k, e.target.value)} />
                  : x.t === "select" ? <Select value={r[x.k] ?? ""} onChange={(e) => set(i, x.k, e.target.value || null)} options={optionsFor(meta, x)} placeholder="—" className="h-9" />
                    : x.t === "ref" ? <RefPicker f={x} value={r[x.k]} onChange={(v) => set(i, x.k, v)} refs={refs} onRefTitle={onRefTitle} className="h-9" />
                      : x.t === "bool" ? <div className="flex h-9 items-center"><Switch checked={!!r[x.k]} onChange={(v) => set(i, x.k, v)} /></div>
                        : x.t === "date" ? <Input type="date" value={r[x.k] ?? ""} onChange={(e) => set(i, x.k, e.target.value || null)} className="h-9" />
                          : x.calc || x.ro ? <div className="flex h-9 items-center rounded-md bg-canvas px-2 text-sm tabular"><FieldValue f={x} v={r[x.k]} refs={refs} compact /></div>
                            : x.t === "file" ? <FilesInput value={r[x.k] ? [r[x.k]] : []} onChange={(v) => set(i, x.k, v[0] || null)} max={1} />
                              : <Input value={r[x.k] ?? ""} inputMode={["number", "money", "percent"].includes(x.t) ? "decimal" : undefined} className="h-9 tabular"
                                onChange={(e) => set(i, x.k, ["number", "money", "percent"].includes(x.t) ? (e.target.value.replace(/[^\d.\-]/g, "") || null) : e.target.value)} />}
              </label>
            ))}
          </div>
        </div>
      ))}
      <Button type="button" variant="outline" size="sm" onClick={() => onChange([...rows, blank()])}><Plus className="h-4 w-4" />Add a line</Button>
    </div>
  );
}

// numbers typed as text become numbers before saving
export function cleanForSave(e, doc) {
  const out = { ...doc };
  const numT = ["number", "money", "percent"];
  for (const f of e.fields) {
    if (f.ro || f.calc) { delete out[f.k]; continue; }
    const v = out[f.k];
    if (numT.includes(f.t) && typeof v === "string") out[f.k] = v === "" ? null : Number(v);
    if (f.t === "lines" && Array.isArray(v)) {
      out[f.k] = v.map((r) => {
        const row = { ...r };
        for (const sf of f.fields) if (numT.includes(sf.t) && typeof row[sf.k] === "string") row[sf.k] = row[sf.k] === "" ? null : Number(row[sf.k]);
        return row;
      });
    }
  }
  for (const k of Object.keys(out)) if (k.startsWith("_")) delete out[k];
  return out;
}

export function useRefCache(initial) {
  const [refs, setRefs] = useState(initial || {});
  useEffect(() => { if (initial) setRefs((r) => mergeRefs(r, initial)); }, [initial]);
  const add = (ent, id, title) => setRefs((r) => ({ ...r, [ent]: { ...(r[ent] || {}), [id]: title } }));
  return [refs, add];
}
export const mergeRefs = (a, b) => { const o = { ...a }; for (const [k, v] of Object.entries(b || {})) o[k] = { ...(o[k] || {}), ...v }; return o; };
export { useMemo };
