import { store } from "./api";

// First and last touch, UTM tags, click ids and QR codes — sent with every website form so each lead carries its source.
const KEYS = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid", "qr"];

export function captureTouch() {
  try {
    const p = new URLSearchParams(window.location.search);
    const found = {};
    KEYS.forEach((k) => { if (p.get(k)) found[k] = p.get(k).slice(0, 200); });
    const ref = document.referrer && !document.referrer.includes(window.location.host) ? document.referrer : "";
    const touch = found.utm_source || found.gclid ? `${found.utm_source || "google"}/${found.utm_medium || (found.gclid ? "cpc" : "")}` : found.qr ? "qr" : ref ? new URL(ref).hostname : "";
    const first = store.get("spi_first_touch", null);
    if (!first) store.set("spi_first_touch", { touch: touch || "direct", landing: window.location.pathname, ref, at: Date.now() });
    if (Object.keys(found).length || touch) store.set("spi_last_touch", { ...found, touch: touch || "direct", landing: window.location.pathname, ref, at: Date.now() });
  } catch { /* ignore */ }
}

export function tracking() {
  const first = store.get("spi_first_touch", {}) || {};
  const last = store.get("spi_last_touch", {}) || {};
  const out = { first_touch: first.touch, last_touch: last.touch || first.touch, landing_page: last.landing || first.landing, referrer: last.ref || first.ref };
  KEYS.forEach((k) => { if (last[k]) out[k] = last[k]; });
  return out;
}
