import { createContext, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

const SiteCtx = createContext(null);
const EMPTY = { settings: {}, branches: [], services: [], options: {}, tools: [], tool_groups: [] };

export function SiteProvider({ children }) {
  const [site, setSite] = useState(null);
  useEffect(() => {
    let on = true;
    const preview = new URLSearchParams(window.location.search).get("preview") === "1";
    api.get("/public/site").then(async (r) => {
      let data = r.data;
      if (preview) {
        try { const d = await api.get("/cms/preview"); data = { ...data, settings: { ...data.settings, ...d.data }, previewing: true }; } catch { /* staff only */ }
      }
      if (on) setSite(data);
    }).catch(() => on && setSite(EMPTY));
    return () => { on = false; };
  }, []);
  return <SiteCtx.Provider value={site || { ...EMPTY, loading: true }}>{children}</SiteCtx.Provider>;
}

export const useSite = () => useContext(SiteCtx);
export const optLabel = (site, key, value) => (site.options?.[key] || []).find((o) => o.value === value)?.label || value;
