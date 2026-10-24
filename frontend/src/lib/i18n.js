import { useSyncExternalStore } from "react";
import { store } from "./api";

// Website languages. The menus, buttons, forms, headings and the main page text are translated; long articles, case studies,
// calculator inputs and legal text stay in English. Text added later in the website editor shows as written until its
// translation is added to src/lib/locales/<code>.json (keyed by the English text). The staff ERP and the portals stay in English.
export const LANGS = [
  { code: "en", name: "English", native: "English", group: "global", locale: "en-IN" },
  { code: "ar", name: "Arabic", native: "العربية", group: "global", locale: "ar", dir: "rtl" },
  { code: "zh", name: "Chinese (Simplified)", native: "简体中文", group: "global", locale: "zh-CN" },
  { code: "fr", name: "French", native: "Français", group: "global", locale: "fr-FR" },
  { code: "de", name: "German", native: "Deutsch", group: "global", locale: "de-DE" },
  { code: "ja", name: "Japanese", native: "日本語", group: "global", locale: "ja-JP" },
  { code: "pt", name: "Portuguese", native: "Português", group: "global", locale: "pt-BR" },
  { code: "ru", name: "Russian", native: "Русский", group: "global", locale: "ru-RU" },
  { code: "es", name: "Spanish", native: "Español", group: "global", locale: "es-ES" },
  { code: "hi", name: "Hindi", native: "हिन्दी", group: "india", locale: "hi-IN" },
  { code: "bn", name: "Bengali", native: "বাংলা", group: "india", locale: "bn-IN" },
  { code: "mr", name: "Marathi", native: "मराठी", group: "india", locale: "mr-IN" },
  { code: "te", name: "Telugu", native: "తెలుగు", group: "india", locale: "te-IN" },
  { code: "ta", name: "Tamil", native: "தமிழ்", group: "india", locale: "ta-IN" },
  { code: "gu", name: "Gujarati", native: "ગુજરાતી", group: "india", locale: "gu-IN" },
  { code: "ur", name: "Urdu", native: "اردو", group: "india", locale: "ur-IN", dir: "rtl" },
  { code: "kn", name: "Kannada", native: "ಕನ್ನಡ", group: "india", locale: "kn-IN" },
  { code: "or", name: "Odia", native: "ଓଡ଼ିଆ", group: "india", locale: "or-IN" },
  { code: "ml", name: "Malayalam", native: "മലയാളം", group: "india", locale: "ml-IN" },
  { code: "pa", name: "Punjabi", native: "ਪੰਜਾਬੀ", group: "india", locale: "pa-IN" },
];
const BY = Object.fromEntries(LANGS.map((l) => [l.code, l]));
// scripts whose marks sit above and below the line (or that are not Latin at all) get taller headings, see index.css
const SIMPLE = new Set(["en", "fr", "de", "pt", "es", "ru"]);
const loaders = import.meta.glob("./locales/*.json");

let lang = "en";
let dict = {};
const listeners = new Set();
const emit = () => listeners.forEach((f) => f());

async function load(code) {
  if (code === "en") return {};
  const ld = loaders[`./locales/${code}.json`];
  if (!ld) return null;
  try { return (await ld()).default; } catch { return null; }
}

function detect() {
  const saved = store.get("spi_lang", null);
  if (saved && BY[saved]) return saved;
  try {
    const first = (navigator.languages?.[0] || navigator.language || "en").toLowerCase().split("-")[0];
    return BY[first] ? first : "en";
  } catch { return "en"; }
}

// Called once before the first render, so a returning visitor never sees the English flash.
export async function initLang() {
  const code = detect();
  const d = await load(code);
  if (d) { lang = code; dict = d; }
}

export async function setLang(code) {
  if (!BY[code] || code === lang) return;
  const d = await load(code);
  if (!d) return;
  lang = code;
  dict = d;
  store.set("spi_lang", code);
  if (active) { applyDocument(); retranslateAll(); }
  emit();
}

export const getLang = () => lang;
export function useLang() { return useSyncExternalStore((cb) => { listeners.add(cb); return () => listeners.delete(cb); }, () => lang, () => lang); }
export function useLocale() { return BY[useLang()]?.locale || "en-IN"; }

// t("Apply by {date}", { date }) -> translated text with the values filled in. A React element as a value returns an array for JSX.
export function translate(s, vars) {
  const str = (lang !== "en" && dict[s]) || s;
  if (!vars) return str;
  const parts = str.split(/\{(\w+)\}/);
  if (parts.length === 1) return str;
  const out = parts.map((p, i) => (i % 2 ? (vars[p] ?? `{${p}}`) : p));
  return out.some((p) => p && typeof p === "object") ? out : out.join("");
}
// For a word that means different things in different places (the "Standard" AMC plan vs a product's "Standard"),
// a locale can carry "<context>|<English>"; otherwise this falls back to the plain translation.
export function translateIn(ctx, s) {
  return (lang !== "en" && dict[`${ctx}|${s}`]) || translate(s);
}
export function useT() {
  useLang();
  return translate;
}

// ------------------------------------------------------------------ page translation
// Most of the website's text is rendered as plain English. While the public site is on screen, this watches the page and swaps
// any text, placeholder, label or tooltip that has a translation, and swaps it back when the visitor picks English again.
const ATTRS = ["placeholder", "aria-label", "title", "alt"];
const origText = new WeakMap();
const wroteText = new WeakMap();
const origAttr = new WeakMap();
const wroteAttr = new WeakMap();
let active = false;
let observer = null;

function skip(el) {
  return !el || el.closest?.("script,style,textarea,code,pre,[data-no-translate],[translate='no']");
}
function lookup(en) {
  const k = en.trim();
  if (!k || lang === "en") return en;
  const v = dict[k];
  return v ? en.replace(k, () => v) : en;
}
function doText(node, fresh) {
  if (skip(node.parentElement)) return;
  const cur = node.nodeValue;
  if (!fresh && wroteText.get(node) === cur) return;
  if (fresh || !origText.has(node) || wroteText.get(node) !== cur) origText.set(node, cur);
  const out = lookup(origText.get(node));
  if (out !== cur) node.nodeValue = out;
  wroteText.set(node, out);
}
function doAttr(el, name) {
  if (skip(el)) return;
  const cur = el.getAttribute(name);
  if (cur == null) return;
  const w = wroteAttr.get(el) || {};
  if (w[name] === cur) return;
  const o = origAttr.get(el) || {};
  o[name] = cur;
  origAttr.set(el, o);
  const out = lookup(cur);
  if (out !== cur) el.setAttribute(name, out);
  wroteAttr.set(el, { ...w, [name]: out });
}
function walk(root) {
  if (root.nodeType === 3) { doText(root); return; }
  if (root.nodeType !== 1 || skip(root)) return;
  const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = tw.nextNode())) doText(n);
  const els = [root, ...root.querySelectorAll("[placeholder],[aria-label],[title],[alt]")];
  for (const el of els) for (const a of ATTRS) if (el.hasAttribute?.(a)) doAttr(el, a);
}
function retranslateAll() {
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = tw.nextNode())) {
    if (origText.has(n) && wroteText.get(n) === n.nodeValue) {
      const out = lookup(origText.get(n));
      if (out !== n.nodeValue) n.nodeValue = out;
      wroteText.set(n, out);
    } else doText(n);
  }
  document.querySelectorAll("[placeholder],[aria-label],[title],[alt]").forEach((el) => {
    const o = origAttr.get(el) || {};
    const w = wroteAttr.get(el) || {};
    for (const a of ATTRS) {
      if (!el.hasAttribute(a)) continue;
      if (o[a] != null && w[a] === el.getAttribute(a)) {
        const out = lookup(o[a]);
        el.setAttribute(a, out);
        wroteAttr.set(el, { ...(wroteAttr.get(el) || {}), [a]: out });
      } else doAttr(el, a);
    }
  });
}
function applyDocument() {
  const el = document.documentElement;
  el.lang = active ? lang : "en";
  el.dir = active && BY[lang]?.dir === "rtl" ? "rtl" : "ltr";
  if (active && !SIMPLE.has(lang)) el.dataset.script = "complex";
  else delete el.dataset.script;
}

export function startPageTranslation() {
  active = true;
  applyDocument();
  walk(document.body);
  observer = new MutationObserver((list) => {
    for (const m of list) {
      if (m.type === "characterData") doText(m.target);
      else if (m.type === "attributes") doAttr(m.target, m.attributeName);
      else m.addedNodes.forEach((n) => walk(n));
    }
  });
  observer.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS });
}
export function stopPageTranslation() {
  observer?.disconnect();
  observer = null;
  active = false;
  applyDocument();
}
