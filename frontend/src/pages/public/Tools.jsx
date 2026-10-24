import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Search, Plus, Trash2, FileDown, UserCheck, ChevronDown, Info, CheckCircle2, AlertTriangle, XCircle, RotateCcw } from "lucide-react";
import { api, errMsg, openFile, cachedGet, IN_FRAME } from "@/lib/api";
import { useMeta, cn } from "@/lib/utils";
import { num, inr } from "@/lib/format";
import { useT } from "@/lib/i18n";
import { Button, Input, Select, Switch, Field, Alert, Dialog, Tip } from "@/components/ui/kit";
import { useSite } from "@/components/public/site";
import { PageHero, Section, Icon } from "@/components/public/Layout";
import { Consent, Honeypot, Done, checkContact, useLeadForm } from "@/components/public/forms";
import { tracking } from "@/lib/tracking";
import { makeEngine } from "@/calc/engine";
import TOOLS from "@/shared/tools.json";
import DEFAULTS from "@/shared/constants.json";
import { NotFound } from "./Content";

const ENGINE = makeEngine(TOOLS, DEFAULTS);

// Rates the office has changed in settings (tariffs, prices) arrive from the server; the bundled ones are the fallback.
function useConstants() {
  const [c, setC] = useState(null);
  useEffect(() => { cachedGet("/public/calc/constants", 30 * 60e3).then((d) => setC(d.constants)).catch(() => setC(null)); }, []);
  return c;
}

// ------------------------------------------------------------------ hub
export function ToolsHub() {
  const [q, setQ] = useState("");
  useMeta({ title: "Electrical calculators for LT and HT", description: "24 free calculators: connected load, LT vs HT cost, contract demand, transformer, cable size, voltage drop, fault level, PF correction, solar, earthing and more." });
  const groups = TOOLS.groups.map((g) => ({ ...g, tools: TOOLS.tools.filter((t) => t.group === g.key && (!q || `${t.title} ${t.summary}`.toLowerCase().includes(q.toLowerCase()))) })).filter((g) => g.tools.length);
  return (
    <>
      <PageHero title="Calculators for LT and HT customers" text="Work out your load, supply, equipment sizes and savings before you talk to anyone. Each result shows the working and the standard it follows, and you can download it as a PDF.">
        <label className="relative block max-w-md">
          <span className="sr-only">Search calculators</span>
          <Search className="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/65" aria-hidden />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search, e.g. cable, solar, earthing"
            className="h-11 w-full rounded-lg border border-white/20 bg-white/5 ps-9 pe-3 text-white placeholder:text-white/65 focus:border-signal focus:outline-none" />
        </label>
      </PageHero>
      <div className="container py-12">
        {groups.length === 0 && <p className="text-muted">No calculator matches "{q}".</p>}
        <div className="space-y-12">
          {groups.map((g) => (
            <section key={g.key} aria-labelledby={`g-${g.key}`} className="grid gap-4 lg:grid-cols-[260px_1fr] lg:gap-10">
              <div>
                <h2 id={`g-${g.key}`} className="text-[21px] font-extrabold">{g.label}</h2>
                <p className="mt-1 text-sm text-muted">{g.blurb}</p>
              </div>
              <ul className="grid gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-2">
                {g.tools.map((t) => (
                  <li key={t.slug} className="bg-white">
                    <Link to={`/tools/${t.slug}`} className="group flex h-full gap-3.5 p-4 hover:bg-paper">
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-ink text-signal-bright"><Icon name={t.icon} className="h-[18px] w-[18px]" /></span>
                      <span><span className="block font-display text-[16px] font-bold leading-snug group-hover:underline group-hover:decoration-signal group-hover:underline-offset-4">{t.title}</span>
                        <span className="mt-1 block text-[14.5px] leading-relaxed text-muted">{t.summary}</span></span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </div>
    </>
  );
}

// The same calculators inside the staff app
export function StaffToolsHub() {
  return (
    <div className="pb-10">
      <h1 className="mb-1 font-display text-[26px] font-extrabold">Calculators</h1>
      <p className="mb-5 text-sm text-muted">The 24 calculators on the website, with the rates set in Settings. Results print on plain paper; the website version emails a PDF to the customer.</p>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {TOOLS.groups.map((g) => (
          <section key={g.key} className="rounded-xl border border-edge bg-surface shadow-card">
            <h2 className="border-b border-edge px-4 py-3 font-sans text-[16px] font-semibold tracking-normal">{g.label}</h2>
            <ul className="divide-y divide-edge">{TOOLS.tools.filter((t) => t.group === g.key).map((t) => <li key={t.slug}><Link to={`/erp/tools/${t.slug}`} className="flex items-center gap-2.5 px-4 py-2.5 text-sm hover:bg-canvas"><Icon name={t.icon} className="h-4 w-4 text-muted" />{t.title}</Link></li>)}</ul>
          </section>
        ))}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ one calculator
const initial = (spec) => Object.fromEntries(spec.inputs.map((f) => [f.k, f.t === "lines" ? (f.def || []).map((r) => ({ ...r })) : f.t === "series" ? [...(f.def || [])] : f.def ?? (f.t === "bool" ? false : "")]));
function visible(f, v) {
  if (f.show && !Object.entries(f.show).every(([k, x]) => String(v[k]) === String(x))) return false;
  if (f.show_in && !Object.entries(f.show_in).every(([k, xs]) => xs.map(String).includes(String(v[k])))) return false;
  if (f.show_if_gt && !Object.entries(f.show_if_gt).every(([k, x]) => Number(v[k]) > Number(x))) return false;
  return true;
}

export function ToolPage({ staff = false }) {
  const { slug } = useParams();
  const base = staff ? "/erp/tools" : "/tools";
  const spec = ENGINE.SPEC[slug];
  const C = useConstants();
  const [v, setV] = useState(() => (spec ? initial(spec) : {}));
  const [lead, setLead] = useState(null);
  useEffect(() => { if (spec) setV(initial(spec)); }, [slug]); // eslint-disable-line react-hooks/exhaustive-deps
  useMeta({ title: spec?.title, description: spec?.summary,
    jsonLd: spec && { "@context": "https://schema.org", "@type": "WebApplication", name: spec.title, applicationCategory: "Engineering calculator", description: spec.summary, offers: { "@type": "Offer", price: 0, priceCurrency: "INR" } } });
  const { res, err } = useMemo(() => {
    if (!spec) return {};
    try { return { res: ENGINE.run(slug, v, C || undefined) }; } catch (e) { return { err: e.message || String(e) }; }
  }, [slug, v, C, spec]);
  if (!spec) return <NotFound />;
  const group = TOOLS.groups.find((g) => g.key === spec.group);
  const related = TOOLS.tools.filter((t) => t.group === spec.group && t.slug !== slug).slice(0, 4);
  return (
    <>
      <section className="border-b border-line bg-paper">
        <div className="container py-8 md:py-10">
          <nav aria-label="Breadcrumb" className="mb-3 text-sm text-muted"><Link to={base} className="hover:underline">Calculators</Link><span className="mx-2">/</span>{group?.label}</nav>
          <h1 className="flex items-center gap-3 text-[28px] font-extrabold leading-tight md:text-[36px]" style={{ letterSpacing: "-0.02em" }}>
            <span className="hidden h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-ink text-signal-bright sm:flex"><Icon name={spec.icon} className="h-5 w-5" /></span>{spec.title}
          </h1>
          <p className="mt-2 max-w-2xl text-[17px] text-muted">{spec.summary}</p>
        </div>
      </section>
      <div className="container grid gap-8 py-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] lg:gap-10">
        <form className="space-y-4 self-start rounded-xl border border-line bg-white p-5 lg:sticky lg:top-24" onSubmit={(e) => e.preventDefault()} aria-label="Inputs">
          <div className="flex items-center justify-between"><h2 className="font-display text-[17px] font-bold">Your inputs</h2>
            <Button type="button" variant="ghost" size="sm" onClick={() => setV(initial(spec))}><RotateCcw className="h-3.5 w-3.5" />Reset</Button></div>
          {/* Calculator fields are English technical text with numbers and units, so they stay left-to-right in Arabic and Urdu too. */}
          <div dir="ltr" className="space-y-4">
            {spec.inputs.filter((f) => visible(f, v)).map((f) => <InputField key={f.k} f={f} value={v[f.k]} C={C} onChange={(x) => setV((s) => ({ ...s, [f.k]: x }))} />)}
          </div>
          {res?.headline && (
            <button type="button" onClick={() => document.getElementById("calc-result")?.scrollIntoView({ behavior: "smooth", block: "start" })}
              className="flex w-full items-center justify-between rounded-lg bg-ink px-4 py-3 text-start text-white lg:hidden">
              <span className="text-sm text-white/80">{res.headline.label}</span>
              <span className="font-display text-lg font-extrabold tabular">{fmtItem(res.headline)}<span className="ms-2 text-sm font-medium text-signal-bright">See result</span></span>
            </button>
          )}
        </form>
        <div className="min-w-0 scroll-mt-24" id="calc-result">
          {err ? <Alert tone="amber" icon={Info} title="Check the inputs">{err}</Alert> : res ? <Result res={res} onLead={staff ? null : setLead} /> : null}
          {related.length > 0 && (
            <div className="mt-10">
              <h2 className="font-display text-[17px] font-bold">Related calculators</h2>
              <ul className="mt-3 grid gap-2 sm:grid-cols-2">
                {related.map((t) => <li key={t.slug}><Link to={`${base}/${t.slug}`} className="flex items-center gap-2 rounded-md border border-line px-3 py-2.5 text-sm hover:border-fg/30"><Icon name={t.icon} className="h-4 w-4 text-signal-deep" />{t.title}</Link></li>)}
              </ul>
            </div>
          )}
        </div>
      </div>
      {!staff && <LeadDialog want={lead} slug={slug} inputs={v} title={spec.title} onClose={() => setLead(null)} />}
    </>
  );
}

function InputField({ f, value, onChange, C }) {
  const id = `in-${f.k}`;
  const label = <span className="inline-flex items-center gap-1">{f.l}{f.help && <Tip text={f.help}><button type="button" className="text-muted" aria-label={`About ${f.l}`}><Info className="h-3.5 w-3.5" /></button></Tip>}</span>;
  if (f.t === "number") {
    return (
      <Field label={label} htmlFor={id}>
        <div className="relative">
          <Input id={id} inputMode="decimal" value={value ?? ""} onChange={(e) => onChange(e.target.value.replace(/[^\d.\-]/g, ""))} className={f.unit ? "pe-14" : ""} />
          {f.unit && <span className="pointer-events-none absolute end-3 top-1/2 -translate-y-1/2 text-sm text-muted">{f.unit}</span>}
        </div>
      </Field>
    );
  }
  if (f.t === "select") {
    const opts = f.opts || (C ? ENGINE.optionsFrom(f.opts_from, ENGINE.constants(C)) : ENGINE.optionsFrom(f.opts_from, ENGINE.constants()));
    return <Field label={label} htmlFor={id}><Select id={id} value={value ?? ""} onChange={(e) => onChange(e.target.value)} options={opts} /></Field>;
  }
  if (f.t === "bool") return <div className="pt-1"><Switch checked={!!value} onChange={onChange} label={f.l} /></div>;
  if (f.t === "series") {
    const vals = value || [];
    const months = ["Month 1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"];
    return (
      <fieldset>
        <legend className="field-label">{f.l}{f.unit ? ` (${f.unit})` : ""}</legend>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
          {vals.map((x, n) => (
            <label key={n} className="block"><span className="sr-only">{months[n] || n + 1}</span>
              <Input inputMode="decimal" value={x ?? ""} onChange={(e) => { const c = [...vals]; c[n] = e.target.value.replace(/[^\d.]/g, ""); onChange(c); }} className="h-9 text-center tabular" /></label>
          ))}
        </div>
        <div className="mt-2 flex gap-2">
          {vals.length < 24 && <Button type="button" variant="ghost" size="sm" onClick={() => onChange([...vals, ""])}><Plus className="h-3.5 w-3.5" />Add month</Button>}
          {vals.length > 1 && <Button type="button" variant="ghost" size="sm" onClick={() => onChange(vals.slice(0, -1))}>Remove last</Button>}
        </div>
      </fieldset>
    );
  }
  if (f.t === "lines") {
    const rows = value || [];
    const blank = Object.fromEntries(f.fields.map((x) => [x.k, x.t === "number" ? "" : x.t === "select" ? x.opts[0].value : ""]));
    const set = (n, k, x) => onChange(rows.map((r, i) => (i === n ? { ...r, [k]: x } : r)));
    return (
      <fieldset>
        <legend className="field-label">{f.l}</legend>
        <div className="space-y-2">
          {rows.map((r, n) => (
            <div key={n} className="grid gap-2 rounded-lg border border-line p-2.5 sm:[grid-template-columns:var(--cols)]" style={{ "--cols": f.fields.map((x) => (x.t === "text" ? "minmax(0,1.9fr)" : x.t === "select" ? "minmax(0,1.6fr)" : "minmax(0,1fr)")).join(" ") + " 36px" }}>
              {f.fields.map((x) => (
                <label key={x.k} className={cn("block min-w-0", x.t === "text" && f.fields.length > 3 && "sm:col-span-1")}>
                  <span className="mb-0.5 block text-[12px] text-muted">{x.l}</span>
                  {x.t === "select" ? <Select value={r[x.k] ?? ""} onChange={(e) => set(n, x.k, e.target.value)} options={x.opts} className="h-9" />
                    : <Input value={r[x.k] ?? ""} inputMode={x.t === "number" ? "decimal" : undefined} onChange={(e) => set(n, x.k, x.t === "number" ? e.target.value.replace(/[^\d.]/g, "") : e.target.value)} className="h-9" />}
                </label>
              ))}
              <button type="button" onClick={() => onChange(rows.filter((_, i) => i !== n))} className="self-end rounded-md p-2 text-muted hover:bg-bad/10 hover:text-bad" aria-label={`Remove row ${n + 1}`}><Trash2 className="h-4 w-4" /></button>
            </div>
          ))}
        </div>
        <Button type="button" variant="outline" size="sm" className="mt-2" onClick={() => onChange([...rows, { ...blank }])}><Plus className="h-3.5 w-3.5" />Add a row</Button>
      </fieldset>
    );
  }
  return <Field label={label}><Input value={value ?? ""} onChange={(e) => onChange(e.target.value)} /></Field>;
}

export function fmtItem(it) {
  const v = it.value;
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "string") return v;
  if (it.fmt === "inr" || it.unit === "₹") return inr(v);
  const d = it.fmt === "int" ? 0 : it.fmt === "1dp" ? 1 : it.fmt === "2dp" ? 2 : it.fmt === "3dp" ? 3 : undefined;
  const s = d === undefined ? num(v) : new Intl.NumberFormat("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: d }).format(v);
  return it.unit ? `${s} ${it.unit}` : s;
}
const cellText = (x) => (typeof x === "number" ? new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(x) : x ?? "");
const STATUS = { ok: ["border-good/30 bg-good/[.06]", CheckCircle2, "text-good"], warn: ["border-amber/60 bg-amber-soft/70", AlertTriangle, "text-amber-ink"], bad: ["border-bad/30 bg-bad/[.06]", XCircle, "text-bad"] };

function Result({ res, onLead }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [S, StIcon, stTone] = STATUS[res.status] || STATUS.ok;
  const h = res.headline || {};
  return (
    <div aria-live="polite">
      <div className="overflow-hidden rounded-xl bg-ink text-white">
        <div className="p-6">
          <p dir="auto" className="text-sm text-white/75">{h.label}</p>
          <p dir="ltr" className="mt-1 text-start font-display text-[42px] font-extrabold leading-none tabular md:text-[52px]" style={{ letterSpacing: "-0.03em" }}>
            {h.fmt === "inr" || h.unit === "₹" ? inr(h.value) : typeof h.value === "number" ? num(h.value) : h.value}
            {h.unit && h.unit !== "₹" && <span className="ms-2 text-[22px] font-bold text-signal-bright">{h.unit}</span>}
          </p>
          {h.sub && <p dir="auto" className="mt-2 text-[16px] text-white/85">{h.sub}</p>}
        </div>
        <div className={cn("flex gap-3 border-t border-white/10 bg-white text-fg px-5 py-4", "border-s-4", res.status === "bad" ? "border-s-bad" : res.status === "warn" ? "border-s-amber" : "border-s-good")}>
          <StIcon className={cn("mt-0.5 h-5 w-5 shrink-0", stTone)} aria-hidden />
          <p dir="auto" className="text-[16px] leading-relaxed">{res.verdict}</p>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2 print:hidden">
        {onLead ? <>
          <Button onClick={() => onLead("report")}><FileDown className="h-4 w-4" />Download PDF report</Button>
          <Button variant="outline" onClick={() => onLead("review")}><UserCheck className="h-4 w-4" />Ask an engineer to check this</Button>
        </> : !IN_FRAME && <Button variant="outline" onClick={() => window.print()}><FileDown className="h-4 w-4" />Print or save as PDF</Button>}
      </div>
      {res.items?.length > 0 && (
        <dl dir="ltr" className="mt-6 divide-y divide-line rounded-xl border border-line bg-white">
          {res.items.map((it, n) => (
            <div key={n} className="flex items-baseline justify-between gap-4 px-4 py-2.5">
              <dt className="text-sm text-muted">{it.label}</dt>
              <dd className={cn("text-end font-semibold tabular", it.tone === "good" && "text-good", it.tone === "bad" && "text-bad", it.tone === "warn" && "text-warn", it.tone === "accent" && "rounded bg-signal-soft px-1.5 text-signal-ink")}>{fmtItem(it)}</dd>
            </div>
          ))}
        </dl>
      )}
      {res.checklist?.length > 0 && (
        <ol dir="auto" className="mt-6 space-y-2 rounded-xl border border-line bg-white p-5">
          {res.checklist.map((c, n) => <li key={n} className="flex gap-3 text-[16px]"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-paper text-xs font-bold tabular">{n + 1}</span>{c}</li>)}
        </ol>
      )}
      {res.table && !res.checklist?.length && (
        <div dir="ltr" className="mt-6 overflow-hidden rounded-xl border border-line bg-white">
          {res.table.title && <p className="border-b border-line px-4 py-2.5 text-sm font-semibold">{res.table.title}</p>}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="bg-paper text-start">{res.table.columns.map((c, i) => <th key={i} scope="col" className={cn("whitespace-nowrap px-3 py-2 font-medium text-muted", i > 0 && "text-end")}>{c}</th>)}</tr></thead>
              <tbody className="divide-y divide-line">
                {res.table.rows.map((r, i) => <tr key={i}>{r.map((x, j) => <td key={j} className={cn("whitespace-nowrap px-3 py-2 tabular", j > 0 && "text-end", /total/i.test(String(r[0])) && "font-semibold")}>{cellText(x)}</td>)}</tr>)}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {res.steps?.length > 0 && (
        <div className="mt-6 rounded-xl border border-line bg-white">
          <button type="button" onClick={() => setOpen((x) => !x)} aria-expanded={open} className="flex w-full items-center justify-between px-4 py-3 text-start text-sm font-semibold">
            {t("Show the working ({n} steps)", { n: res.steps.length })}<ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
          </button>
          {open && (
            <ol dir="ltr" className="divide-y divide-line border-t border-line">
              {res.steps.map((s, n) => (
                <li key={n} className="grid gap-1 px-4 py-2.5 text-sm sm:grid-cols-[1fr_auto] sm:gap-4">
                  <div><p className="font-medium">{s.label}</p><p className="font-mono text-[13.5px] text-muted">{s.formula}</p></div>
                  {s.value !== "" && s.value !== null && s.value !== undefined && <p className="font-semibold tabular sm:text-end">{typeof s.value === "number" ? new Intl.NumberFormat("en-IN", { maximumFractionDigits: 3 }).format(s.value) : s.value}{s.unit ? ` ${s.unit}` : ""}</p>}
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
      {res.notes?.length > 0 && <ul className="mt-6 space-y-1.5 text-sm text-muted">{res.notes.map((n, i) => <li key={i} dir="auto" className="flex gap-2"><Info className="mt-0.5 h-4 w-4 shrink-0" />{n}</li>)}</ul>}
      <p className="mt-6 border-t border-line pt-4 text-xs leading-relaxed text-muted">
        {t("Basis: {basis}.", { basis: <bdi key="b">{res.basis}</bdi> })} {res.rates_as_of && t("Rates as of {date}.", { date: <bdi key="d">{res.rates_as_of}</bdi> })} {t("This is an estimate for planning; the final design must be done and signed by a licensed electrical engineer.")}
      </p>
    </div>
  );
}

function LeadDialog({ want, slug, inputs, title, onClose }) {
  const [v, setV, set] = useLeadForm({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(null);
  useEffect(() => { if (want) { setDone(null); setErr(""); } }, [want]);
  async function go(e) {
    e.preventDefault();
    const bad = checkContact(v);
    if (bad) { setErr(bad); return; }
    setBusy(true); setErr("");
    try {
      const r = await api.post(`/public/calc/${slug}/lead`, { ...v, inputs, want, tracking: tracking(), email: v.email || undefined });
      setDone(r.data);
      if (want === "report") openFile(r.data.pdf.replace(/^\/api/, ""), { name: `${slug}.pdf`, type: "application/pdf" });
    } catch (ex) { setErr(errMsg(ex)); } finally { setBusy(false); }
  }
  return (
    <Dialog open={!!want} onOpenChange={(x) => !x && onClose()} title={want === "review" ? "Ask an engineer to check this" : "Download the PDF report"}
      description={want === "review" ? "We'll call you to go through the result and your site." : "Your report includes the inputs, result and working, on our letterhead."}>
      {done ? (
        <Done title={want === "review" ? "An engineer will call you" : "Your report is ready"} reference={done.reference}>
          <Button variant="outline" size="sm" className="mt-3" onClick={() => openFile(done.pdf.replace(/^\/api/, ""), { name: `${slug}.pdf`, type: "application/pdf" })}><FileDown className="h-4 w-4" />Open the PDF</Button>
        </Done>
      ) : (
        <form onSubmit={go} className="relative space-y-3" noValidate>
          <Honeypot value={v.website} onChange={(x) => setV((s) => ({ ...s, website: x }))} />
          <p className="rounded-md bg-paper px-3 py-2 text-sm">{title}</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Your name" required><Input value={v.name} onChange={set("name")} autoComplete="name" /></Field>
            <Field label="Mobile number" required><Input value={v.phone} onChange={set("phone")} inputMode="tel" placeholder="98765 43210" /></Field>
            <Field label="Email (optional)"><Input type="email" value={v.email} onChange={set("email")} /></Field>
            <Field label="Company"><Input value={v.company} onChange={set("company")} /></Field>
          </div>
          <Consent checked={v.consent} onChange={set("consent")} id="consent-calc" />
          {err && <Alert tone="red">{err}</Alert>}
          <Button type="submit" loading={busy} className="w-full sm:w-auto">{want === "review" ? "Ask for a call" : "Get the PDF"}</Button>
        </form>
      )}
    </Dialog>
  );
}
