import { useQuery, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { inr, num, pct, fmtDate, fmtDateTime } from "@/lib/format";

// ------------------------------------------------------------------ data
export function useApi(path, params, opts = {}) {
  return useQuery({
    queryKey: [path, params || null],
    queryFn: async () => (await api.get(path, { params })).data,
    enabled: !!path && opts.enabled !== false,
    staleTime: opts.staleTime ?? 20e3,
    placeholderData: opts.keep === false ? undefined : keepPreviousData,
    ...opts,
  });
}
export function useInvalidate() {
  const qc = useQueryClient();
  return (prefix) => qc.invalidateQueries({ predicate: (q) => !prefix || String(q.queryKey[0]).startsWith(prefix) });
}

// ------------------------------------------------------------------ registry helpers
export function useEntity(key) {
  const { meta } = useAuth();
  return meta?.entities?.[key] || null;
}
export function optionsFor(meta, f) {
  if (!f?.opts) return [];
  return Array.isArray(f.opts) ? f.opts : meta?.options?.[f.opts] || [];
}
export function optLabel(meta, f, v) {
  const o = optionsFor(meta, f).find((x) => String(x.value) === String(v));
  return o ? o.label : v;
}
export const statusField = (e) => e?.status?.field || null;
export const stateOf = (e, v) => (e?.status?.states || []).find((s) => s.value === v) || null;
export const titleOf = (e, d, refs) => {
  if (!d) return "";
  const tk = e?.title || "name";
  const f = e?.fields?.find((x) => x.k === tk);
  let t = d[tk];
  if (f && f.t === "ref" && t) t = refs?.[f.ref]?.[t] || t;
  if (tk === "code" || !t) t = d.code || d.name || d.title || d.subject || d.id;
  return String(t ?? "");
};
export const fieldOf = (e, k) => e?.fields?.find((f) => f.k === k) || (k === "code" ? { k, t: "text", l: "Number" } : k === "created_at" ? { k, t: "datetime", l: "Created" } : k === "status" ? { k, t: "select", l: "Status" } : null);

export function visibleField(f, doc) {
  if (!f.show) return true;
  return Object.entries(f.show).every(([k, v]) => (Array.isArray(v) ? v.includes(doc?.[k]) : doc?.[k] === v));
}

export function groupFields(fields) {
  const out = [];
  const idx = {};
  for (const f of fields) {
    const g = f.group || "";
    if (!(g in idx)) { idx[g] = out.length; out.push({ group: g, fields: [] }); }
    out[idx[g]].fields.push(f);
  }
  return out;
}

// Plain text for a value (tables, exports, search results)
export function textOf(meta, f, v, refs) {
  if (v === null || v === undefined || v === "") return "";
  if (!f) return String(v);
  switch (f.t) {
    case "money": return inr(v);
    case "number": return `${num(v)}${f.unit ? ` ${f.unit}` : ""}`;
    case "percent": return pct(v);
    case "date": return fmtDate(v);
    case "datetime": return fmtDateTime(v);
    case "bool": return v ? "Yes" : "No";
    case "select": return optLabel(meta, f, v);
    case "multiselect": return (v || []).map((x) => optLabel(meta, f, x)).join(", ");
    case "ref": return refs?.[f.ref]?.[v] || "…";
    case "refs": return (v || []).map((x) => refs?.[f.ref]?.[x] || "…").join(", ");
    case "lines": return `${(v || []).length} lines`;
    case "files": return `${(v || []).length} files`;
    case "file": return v?.name || "File";
    case "geo": return v?.lat ? `${Number(v.lat).toFixed(5)}, ${Number(v.lng).toFixed(5)}` : "";
    case "json": return typeof v === "object" ? (v.title || v.headline?.label || "Details") : String(v);
    default: return String(v);
  }
}

export const can = (e, letter) => !!e && (e.perm || "").includes(letter);
export const isLocked = (e, doc) => !!e?.locked && doc && e.locked.includes(doc[statusField(e)]);

export const MODULE_HOME = {
  crm: "/erp/crm", marketing: "/erp/marketing", finance: "/erp/finance", stores: "/erp/stores", service: "/erp/service", reports: "/erp/reports",
};
