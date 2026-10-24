import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { useEffect } from "react";

export const cn = (...a) => twMerge(clsx(a));

const SITE = "Sellandiamman Power Infra";
function setMeta(attr, key, value) {
  let m = document.head.querySelector(`meta[${attr}="${key}"]`);
  if (!m) { m = document.createElement("meta"); m.setAttribute(attr, key); document.head.appendChild(m); }
  m.setAttribute("content", value || "");
}

// Title, description, canonical, social preview and structured data for a page (the server sets them in the first HTML too).
export function useMeta({ title, description, jsonLd, noindex, image } = {}) {
  const ld = jsonLd ? JSON.stringify(jsonLd) : "";
  useEffect(() => {
    const full = title ? `${title} | ${SITE}` : `${SITE} — LT & HT electrical contractors in Tamil Nadu`;
    document.title = full;
    document.querySelectorAll("#ssr-jsonld").forEach((n) => n.remove());
    if (description) { setMeta("name", "description", description); setMeta("property", "og:description", description); }
    setMeta("property", "og:title", full);
    setMeta("property", "og:url", window.location.href.split("?")[0]);
    if (image) setMeta("property", "og:image", image);
    setMeta("name", "robots", noindex ? "noindex" : "index,follow");
    let s = document.getElementById("page-jsonld");
    if (ld) {
      if (!s) { s = document.createElement("script"); s.type = "application/ld+json"; s.id = "page-jsonld"; document.head.appendChild(s); }
      s.textContent = ld;
    } else if (s) s.remove();
  }, [title, description, ld, noindex, image]);
}

export function useTitle(title) { useMeta({ title, noindex: true }); }
