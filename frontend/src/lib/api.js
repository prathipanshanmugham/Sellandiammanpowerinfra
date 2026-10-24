import axios from "axios";
import { useEffect, useState, useSyncExternalStore } from "react";

export const IS_DEMO = import.meta.env.VITE_DEMO === "true";
// Inside an embedded frame (the hosted preview) downloads, printing and pop-up windows are blocked.
export const IN_FRAME = (() => { try { return window.self !== window.top; } catch { return true; } })();
export const api = axios.create({ baseURL: "/api", withCredentials: true, timeout: 45000 });

// Short-lived access cookie: on "Session expired" refresh once and retry.
let refreshing = null;
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const cfg = err.config || {};
    const detail = err.response?.data?.detail;
    if (err.response?.status === 401 && !cfg._retry && !String(cfg.url || "").startsWith("/auth/") && /expired|Invalid session/i.test(String(detail || ""))) {
      cfg._retry = true;
      try {
        refreshing = refreshing || api.post("/auth/refresh").finally(() => { refreshing = null; });
        await refreshing;
        return api(cfg);
      } catch { /* fall through */ }
    }
    return Promise.reject(err);
  },
);

export function errMsg(e) {
  const d = e?.response?.data?.detail;
  if (!e?.response) return "Couldn't reach the server. Check your connection and try again.";
  if (d == null) return e.response.status === 429 ? "Too many requests — wait a minute and try again." : "Something went wrong. Try again.";
  if (typeof d === "string") return d === "mfa_setup_required" ? "Set up 2-step sign-in to continue." : d;
  if (Array.isArray(d)) return d.map((x) => x?.msg || JSON.stringify(x)).join(" ");
  return d.msg || String(d);
}

// ---------- browser storage that never throws ----------
export const store = {
  get(k, fallback) { try { const v = localStorage.getItem(k); return v == null ? fallback : JSON.parse(v); } catch { return fallback; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* unavailable */ } },
  del(k) { try { localStorage.removeItem(k); } catch { /* unavailable */ } },
};

// ---------- branch picker (X-Branch header) ----------
let branchPick = store.get("spi_branch", "");
const branchListeners = new Set();
const applyBranch = () => { if (branchPick) api.defaults.headers.common["X-Branch"] = branchPick; else delete api.defaults.headers.common["X-Branch"]; };
applyBranch();
export const branchApi = {
  get: () => branchPick,
  set(v) { branchPick = v || ""; store.set("spi_branch", branchPick); applyBranch(); branchListeners.forEach((l) => l()); },
};
export function useBranchPick() {
  return useSyncExternalStore((cb) => { branchListeners.add(cb); return () => branchListeners.delete(cb); }, () => branchPick, () => branchPick);
}

// ---------- files (PDFs, exports) ----------
// The live site opens the file in a new tab; the hosted preview swaps this for an in-page viewer.
let fileOpener = (path) => window.open(`/api${path}`, "_blank", "noopener");
export const setFileOpener = (fn) => { fileOpener = fn; };
export const openFile = (path, meta) => fileOpener(path, meta);
export async function openStoredFile(file) {
  if (!file?.id) return;
  if (file.url && !file.url.startsWith("/api/") && !IS_DEMO) { window.open(file.url, "_blank", "noopener"); return; }
  try { const r = await api.get(`/files/${file.id}/link`); openFile(r.data.url.replace(/^\/api/, ""), { name: file.name, type: file.type }); } catch (e) { alert(errMsg(e)); }
}

// ---------- small cache for data many pages need ----------
const cache = new Map();
export function cachedGet(path, maxAgeMs = 5 * 60e3) {
  const hit = cache.get(path);
  if (hit && Date.now() - hit.at < maxAgeMs) return hit.p;
  const p = api.get(path).then((r) => r.data);
  p.catch(() => cache.delete(path));
  cache.set(path, { at: Date.now(), p });
  return p;
}
export const clearCache = (prefix = "") => { [...cache.keys()].forEach((k) => { if (k.startsWith(prefix)) cache.delete(k); }); };
export function useCached(path, fallback) {
  const [v, setV] = useState(fallback);
  useEffect(() => { let on = true; if (path) cachedGet(path).then((d) => on && setV(d)).catch(() => {}); return () => { on = false; }; }, [path]);
  return v;
}

export function useMedia(query) {
  const get = () => (typeof window !== "undefined" && window.matchMedia ? window.matchMedia(query).matches : false);
  const [m, setM] = useState(get);
  useEffect(() => {
    if (!window.matchMedia) return undefined;
    const mq = window.matchMedia(query);
    const on = () => setM(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, [query]);
  return m;
}

export function useDebounced(value, ms = 300) {
  const [v, setV] = useState(value);
  useEffect(() => { const t = setTimeout(() => setV(value), ms); return () => clearTimeout(t); }, [value, ms]);
  return v;
}

export const asset = (p) => (p && p.startsWith("/") ? `${import.meta.env.BASE_URL.replace(/\/$/, "")}${p}` : p);
let mediaResolver = null;
export const setMediaResolver = (fn) => { mediaResolver = fn; };
export function fileUrl(f) {
  if (!f) return null;
  if (f.url && !f.url.startsWith("/api/")) return asset(f.url);
  if (f.url) return (mediaResolver && mediaResolver(f.url)) || f.url;
  return null;
}
