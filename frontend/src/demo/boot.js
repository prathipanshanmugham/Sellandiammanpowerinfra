// Hosted preview: load the recorded sample data, answer /api in the browser, and add the role switcher and file viewer.
import { createElement } from "react";
import { createRoot } from "react-dom/client";
import { api, setFileOpener } from "@/lib/api";
import { setDemoPicker } from "@/pages/Auth";
import { setDemoBar } from "@/erp/Layout";
import { setPortalDemoBar } from "@/portal/Portal";
import { load, S, coll, listRecords, ent, roleMeta } from "./store";
import { demoAdapter, restoreRole } from "./adapter";
import { DemoBar, DemoPicker, FileViewer, showFile } from "./ui";

const BASE = import.meta.env.BASE_URL;
const PDF_FOR = { invoices: "invoice", proposals: "proposal", test_reports: "test_report", permits: "permit", purchase_orders: "purchase_order", ra_bills: "ra_bill", boqs: "boq",
  work_orders: "work_order", payroll_runs: "payslip" };

function csv(rows) {
  return rows.map((r) => r.map((c) => { const s = c === null || c === undefined ? "" : String(c); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; }).join(",")).join("\n");
}
function blobUrl(text, type) { return URL.createObjectURL(new Blob([text], { type })); }
let PAGES = {};
function pdf(name, title, note) { showFile({ kind: "pdf", url: `${BASE}pdf/${name}.pdf`, name: `${name}.pdf`, title, note, pages: (PAGES[name] || []).map((p) => `${BASE}pdf/${p}`) }); }

function openFile(path) {
  const [p, qs] = path.split("?");
  const q = Object.fromEntries(new URLSearchParams(qs || ""));
  let m;
  const NOTE = "In the preview every document of this kind opens the same sample PDF, made by the real server from the sample data.";
  if ((m = p.match(/^\/e\/([a-z_]+)\/export\/(csv|xlsx|pdf)$/))) {
    if (m[2] === "pdf") return pdf("export", `${ent(m[1])?.plural || "List"} as PDF`, "A sample list export on the letterhead. Excel and CSV exports give the actual rows.");
    const e = roleMeta().entities[m[1]];
    const data = listRecords(m[1], { ...q, size: 500 });
    const cols = e.list.map((k) => e.fields.find((f) => f.k === k) || { k, l: k });
    const rows = [cols.map((c) => c.l), ...data.items.map((d) => cols.map((c) => (c.t === "ref" ? data.refs?.[c.ref]?.[d[c.k]] || "" : Array.isArray(d[c.k]) ? d[c.k].length : d[c.k])))];
    const text = csv(rows);
    return showFile({ kind: "text", text: text.split("\n").slice(0, 40).join("\n"), url: blobUrl(text, "text/csv"), name: `${m[1]}.csv`, title: `${e.plural}: ${data.total} rows`, note: "The live system downloads Excel; the preview gives you the same rows as CSV." });
  }
  if ((m = p.match(/^\/e\/([a-z_]+)\/[^/]+\/pdf$/))) return pdf(PDF_FOR[m[1]] || "generic", `${ent(m[1])?.label || "Record"} PDF`, NOTE);
  if (p === "/ceo/report.pdf") return pdf("ceo-report", "CEO report", "Health score, pillars, alerts and the key numbers for the period.");
  if (p === "/finance/credit-report") return pdf("credit-report", "Daily credit report", "Overdue invoices with the last follow-up, for the morning collections call.");
  if (/\/handover-pack\.pdf$/.test(p)) return pdf("handover-pack", "Handover pack", "Test certificates, drawings, warranties and contacts, bound into one PDF for the client.");
  if ((m = p.match(/^\/reports\/([a-z_]+)$/))) {
    if (q.fmt === "pdf") return pdf("report", "Report PDF", "A sample report on the letterhead (project status).");
    const r = S.shared[`/reports/${m[1]}`];
    if (r) { const text = csv([r.columns, ...r.rows]); return showFile({ kind: "text", text: text.split("\n").slice(0, 40).join("\n"), url: blobUrl(text, "text/csv"), name: `${m[1]}.csv`, title: r.title, note: "Excel and CSV download the same rows." }); }
  }
  if (p.startsWith("/public/calc-report/")) return pdf("calc-report", "Calculator report", "The PDF a visitor gets after entering their name and phone: inputs, result and working on the letterhead.");
  if (p === "/finance/tally.xml") {
    const inv = coll("invoices").filter((i) => ["issued", "part_paid", "paid"].includes(i.status)).slice(0, 3);
    const text = `<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDATA>\n${inv.map((i) => `  <VOUCHER VCHTYPE="Sales"><DATE>${String(i.date).replace(/-/g, "")}</DATE><VOUCHERNUMBER>${i.code}</VOUCHERNUMBER><AMOUNT>${i.total}</AMOUNT></VOUCHER>`).join("\n")}\n</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>`;
    return showFile({ kind: "text", text, url: blobUrl(text, "application/xml"), name: "tally-sales.xml", title: "Tally export", note: "Sales vouchers for Tally Prime (Gateway, Import, Vouchers). Shortened here." });
  }
  if ((m = p.match(/^\/files\/get\/(.+)$/))) {
    const f = coll("files").find((x) => x.id === m[1]);
    if (f?.url) return showFile({ kind: f.type === "application/pdf" ? "pdf" : "other", url: f.url, name: f.name, title: f.name, text: "Your uploaded file, kept in this browser tab." });
    return showFile({ kind: "other", title: "Sample attachment", text: "Attachments in the sample data are placeholders. Files you upload in the preview open from here." });
  }
  if (p.startsWith("/public/download/")) return showFile({ kind: "other", title: "Guide download", text: "In the live site this downloads the PDF brochure or guide. The sample data has the guide text only; it's on the page you were reading." });
  return showFile({ kind: "other", title: "File", text: "This file opens from the live server." });
}

export default async function boot() {
  const get = (n) => fetch(`${BASE}data/${n}.json`).then((r) => { if (!r.ok) throw new Error(`Couldn't load ${n}`); return r.json(); });
  const [db, meta, shared, pub] = await Promise.all([get("db"), get("meta"), get("shared"), get("public")]);
  PAGES = await get("pdf_pages").catch(() => ({}));
  load({ db, meta, shared, pub });
  const s = pub["/public/site"].settings;
  s.announcement = { text: "This is a preview with sample data. Try the staff ERP and the client portal too.", link: "/erp/login", active: true };
  restoreRole();
  api.defaults.adapter = demoAdapter;
  setFileOpener(openFile);
  setDemoPicker(DemoPicker);
  setDemoBar(DemoBar);
  setPortalDemoBar(DemoBar);
  const host = document.createElement("div");
  document.body.appendChild(host);
  createRoot(host).render(createElement(FileViewer));
  window.__spiPreview = S;
}
