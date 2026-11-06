// Installable app ("Add to Home screen" / "Install app").
// Three apps share this site: the website, the staff ERP (/erp) and the customer / vendor portals (signed in at /login).
// The page head links the manifest of the app the current page belongs to, so installing from the ERP gives an
// "SPI ERP" icon that opens the ERP, and installing from the website gives the website.
import { useEffect, useSyncExternalStore } from "react";
import { IS_DEMO } from "@/lib/api";

export const APPS = {
  site: { manifest: "/site.webmanifest?v=3", title: "Power Infra", name: "Sellandiamman Power Infra" },
  erp: { manifest: "/erp.webmanifest?v=3", title: "SPI ERP", name: "SPI ERP" },
  portal: { manifest: "/portal.webmanifest?v=3", title: "SPI Portal", name: "SPI Portal" },
};
const PORTAL_PATHS = ["/login", "/client", "/consultant", "/vendor", "/subcontractor", "/partner"];

export function appFor(path) {
  if (path === "/erp" || path.startsWith("/erp/")) return "erp";
  if (PORTAL_PATHS.some((p) => path === p || path.startsWith(`${p}/`))) return "portal";
  return "site";
}

// keep the page head pointing at the right app as the user moves around
export function useAppManifest(pathname) {
  useEffect(() => {
    const app = APPS[appFor(pathname)];
    const link = document.getElementById("app-manifest");
    if (link && link.getAttribute("href") !== app.manifest) link.setAttribute("href", app.manifest);
    const title = document.getElementById("app-title");
    if (title && title.getAttribute("content") !== app.title) title.setAttribute("content", app.title);
  }, [pathname]);
}

// ---- install state ---------------------------------------------------------------------------------------------
let deferred = null; // the browser's install offer (Chrome, Edge, Samsung Internet), kept for our "Install" buttons
let justInstalled = false;
const subs = new Set();
let snap = null;

const mq = (q) => typeof window !== "undefined" && window.matchMedia?.(q).matches;
export const isInstalled = () => justInstalled || mq("(display-mode: standalone)") || mq("(display-mode: fullscreen)") || window.navigator?.standalone === true;

export function platform() {
  const ua = navigator.userAgent || "";
  const ios = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  if (ios) return /CriOS|FxiOS|EdgiOS/.test(ua) ? "ios-other" : "ios";
  if (/SamsungBrowser/.test(ua)) return "samsung";
  if (/Firefox/.test(ua) && /Android/.test(ua)) return "firefox";
  if (/Android/.test(ua)) return "android";
  return "desktop";
}

function compute() {
  const touch = mq("(pointer: coarse)");
  const installed = isInstalled();
  const p = platform();
  // the hosted preview runs on another address and can't be installed
  return { installed, canPrompt: !!deferred, platform: p, show: !IS_DEMO && !installed && (!!deferred || touch || p === "ios" || p === "ios-other") };
}
function emit() {
  snap = compute();
  subs.forEach((f) => f());
}

export function initPwa() {
  if (typeof window === "undefined" || IS_DEMO) return;
  // Not calling preventDefault keeps the browser's own install bar; the event is kept for our buttons too.
  window.addEventListener("beforeinstallprompt", (e) => { deferred = e; emit(); });
  window.addEventListener("appinstalled", () => { deferred = null; justInstalled = true; emit(); });
  window.matchMedia?.("(display-mode: standalone)").addEventListener?.("change", emit);
  if (import.meta.env.PROD && "serviceWorker" in navigator) {
    window.addEventListener("load", () => { navigator.serviceWorker.register("/sw.js").catch(() => {}); });
  }
}

export function useInstall() {
  return useSyncExternalStore(
    (f) => { subs.add(f); return () => subs.delete(f); },
    () => snap || (snap = compute()),
    () => ({ installed: false, canPrompt: false, platform: "desktop", show: false }),
  );
}

// Show the browser's install dialog when it offers one. Returns "accepted", "dismissed" or "manual" (show the steps).
export async function promptInstall() {
  if (!deferred) return "manual";
  const e = deferred;
  deferred = null;
  emit();
  try {
    await e.prompt();
    const choice = await e.userChoice;
    if (choice?.outcome === "accepted") { justInstalled = true; emit(); return "accepted"; }
    return "dismissed";
  } catch {
    return "manual";
  }
}
