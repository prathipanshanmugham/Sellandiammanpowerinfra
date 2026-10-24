// Indian digit grouping (12,34,567), IST dates, labels.
const n0 = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
const n2 = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const nAny = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 3 });

export const num = (v, d) => (v === null || v === undefined || v === "" ? "—" : d === 0 ? n0.format(Number(v)) : d === 2 ? n2.format(Number(v)) : nAny.format(Number(v)));
export function inr(v, opts = {}) {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  if (opts.compact) {
    const a = Math.abs(n);
    if (a >= 1e7) return `₹${(n / 1e7).toFixed(2).replace(/\.?0+$/, "")} Cr`;
    if (a >= 1e5) return `₹${(n / 1e5).toFixed(2).replace(/\.?0+$/, "")} L`;
  }
  return `₹${opts.paise ? n2.format(n) : n0.format(Math.round(n))}`;
}
export const pct = (v, d = 1) => (v === null || v === undefined || v === "" ? "—" : `${Number(v).toFixed(d).replace(/\.0+$/, "")}%`);

function parse(s) {
  if (!s) return null;
  const str = String(s);
  const d = new Date(str.length === 10 ? `${str}T00:00:00+05:30` : str.length === 16 ? `${str}:00+05:30` : str);
  return Number.isNaN(d.getTime()) ? null : d;
}
export function fmtDate(s, opts) {
  const d = parse(s);
  if (!d) return s ? String(s) : "—";
  return d.toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short", year: opts?.noYear ? undefined : "numeric" });
}
export function fmtDateTime(s) {
  const d = parse(s);
  if (!d) return s ? String(s) : "—";
  return d.toLocaleString("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}
export function ago(s) {
  const d = parse(s);
  if (!d) return "";
  const sec = (Date.now() - d.getTime()) / 1000;
  const fut = sec < 0;
  const a = Math.abs(sec);
  const t = a < 60 ? "just now" : a < 3600 ? `${Math.round(a / 60)} min` : a < 86400 ? `${Math.round(a / 3600)} h` : `${Math.round(a / 86400)} d`;
  if (t === "just now") return t;
  return fut ? `in ${t}` : `${t} ago`;
}
export const todayIST = () => new Date(Date.now() + 5.5 * 3600e3).toISOString().slice(0, 10);
export const nowIST = () => new Date(Date.now() + 5.5 * 3600e3).toISOString().slice(0, 16);
export const addDays = (iso, n) => { const d = new Date(`${iso}T00:00:00Z`); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
export const daysBetween = (a, b) => Math.round((new Date(`${String(a).slice(0, 10)}T00:00:00Z`) - new Date(`${String(b).slice(0, 10)}T00:00:00Z`)) / 864e5);
export const label = (s) => (s ? String(s).replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase()) : "—");
export const initials = (name) => String(name || "?").split(/\s+/).filter(Boolean).slice(0, 2).map((x) => x[0]).join("").toUpperCase();
export const uid = () => (crypto?.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);
export const telLink = (p) => `tel:${String(p || "").replace(/[^\d+]/g, "")}`;
export const waLink = (p, text = "") => { const d = String(p || "").replace(/\D/g, ""); return d ? `https://wa.me/${d}${text ? `?text=${encodeURIComponent(text)}` : ""}` : null; };
export function fmtValue(v, fmt) {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v !== "number") return String(v);
  if (fmt === "inr") return inr(v);
  if (fmt === "int") return num(v, 0);
  if (fmt === "1dp") return new Intl.NumberFormat("en-IN", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v);
  if (fmt === "2dp") return n2.format(v);
  if (fmt === "3dp") return new Intl.NumberFormat("en-IN", { minimumFractionDigits: 3, maximumFractionDigits: 3 }).format(v);
  if (fmt === "4dp") return new Intl.NumberFormat("en-IN", { minimumFractionDigits: 4, maximumFractionDigits: 4 }).format(v);
  return nAny.format(v);
}
