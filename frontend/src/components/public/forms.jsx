import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, Paperclip, X, CalendarDays, Upload, Phone } from "lucide-react";
import { api, errMsg, store } from "@/lib/api";
import { tracking } from "@/lib/tracking";
import { useT, useLocale } from "@/lib/i18n";
import { fmtDate, telLink } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Button, Input, Select, Textarea, Field, Checkbox, Alert, Dialog } from "@/components/ui/kit";
import { useSite } from "./site";

export const CONSENT = "I agree that Sellandiamman Power Infra may contact me by phone, WhatsApp or email about this enquiry, as explained in the privacy notice.";

export function Consent({ checked, onChange, id = "consent" }) {
  return (
    <Checkbox id={id} checked={checked} onChange={onChange}
      label={<span className="text-[14px] text-muted"><span>I agree that Sellandiamman Power Infra may contact me by phone, WhatsApp or email about this enquiry.</span> <Link to="/privacy" className="text-cable underline">Read the privacy notice</Link></span>} />
  );
}

// Hidden field that people never fill; bots do.
export const Honeypot = ({ value, onChange }) => (
  <div aria-hidden className="absolute start-[-9999px] top-auto h-px w-px overflow-hidden">
    <label>Website <input tabIndex={-1} autoComplete="off" value={value} onChange={(e) => onChange(e.target.value)} /></label>
  </div>
);

export function FileDrop({ files, onChange, label = "Drawings, load list, bills or photos", max = 6, accept = ".pdf,.jpg,.jpeg,.png,.webp,.xlsx,.docx" }) {
  const t = useT();
  const ref = useRef(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  async function pick(list) {
    setErr("");
    setBusy(true);
    const out = [...files];
    for (const f of Array.from(list).slice(0, max - files.length)) {
      if (f.size > 15 * 1024 * 1024) { setErr(t("{name} is larger than 15 MB", { name: f.name })); continue; }
      const fd = new FormData();
      fd.append("file", f);
      try { const r = await api.post("/public/upload", fd); out.push(r.data); } catch (e) { setErr(errMsg(e)); }
    }
    setBusy(false);
    onChange(out);
  }
  return (
    <div>
      <button type="button" onClick={() => ref.current?.click()} onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); pick(e.dataTransfer.files); }}
        className="flex w-full items-center gap-3 rounded-md border border-dashed border-edge bg-canvas px-4 py-3 text-start text-sm text-muted hover:border-fg/30">
        <Upload className="h-4 w-4 shrink-0" aria-hidden />
        <span>{busy ? "Uploading…" : <>{label} <span className="text-fg/75">{t("PDF, photo or Excel, up to 15 MB each")}</span></>}</span>
      </button>
      <input ref={ref} type="file" className="hidden" multiple accept={accept} onChange={(e) => pick(e.target.files)} />
      {err && <p className="mt-1 text-xs text-bad">{err}</p>}
      {files.length > 0 && (
        <ul className="mt-2 space-y-1">
          {files.map((f) => (
            <li key={f.id} className="flex items-center gap-2 text-sm"><Paperclip className="h-3.5 w-3.5 text-muted" /><span className="truncate">{f.name}</span>
              <button type="button" onClick={() => onChange(files.filter((x) => x.id !== f.id))} className="ms-auto text-muted hover:text-bad" aria-label={`Remove ${f.name}`}><X className="h-4 w-4" /></button></li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function useLeadForm(initial = {}) {
  const [v, setV] = useState({ name: "", phone: "", email: "", company: "", town: "", message: "", consent: false, website: "", attachments: [], ...initial });
  const set = (k) => (e) => setV((s) => ({ ...s, [k]: e?.target ? (e.target.type === "checkbox" ? e.target.checked : e.target.value) : e }));
  return [v, setV, set];
}

export function Done({ title = "Thank you", reference, children, compact }) {
  const site = useSite();
  const t = useT();
  return (
    <div className={cn("rounded-lg border border-good/30 bg-good/5 p-5", compact && "p-4")} role="status">
      <div className="flex items-start gap-3">
        <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-good" />
        <div>
          <p className="font-semibold">{title}</p>
          {reference && <p className="mt-1 text-sm">{t("Your reference is {ref}.", { ref: <span key="r" className="font-semibold tabular">{reference}</span> })} {t("An engineer will call you within {time}.", { time: t(site.settings?.first_response_text || "30 working minutes") })}</p>}
          {children}
        </div>
      </div>
    </div>
  );
}

const PHONE_RE = /^(?:\+?91|0)?[6-9]\d{9}$/;
export function checkContact(v) {
  if (!v.name.trim()) return "Enter your name";
  if (!PHONE_RE.test(v.phone.replace(/[\s\-()]/g, ""))) return "Enter a 10-digit mobile number";
  if (v.email && !/^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$/.test(v.email)) return "Check the email address";
  if (!v.consent) return "Tick the consent box so we can contact you";
  return null;
}

export async function submitLead(v, extra = {}, url = "/public/leads") {
  const body = { ...v, ...extra, tracking: tracking() };
  if (!body.email) delete body.email;
  const r = await api.post(url, body);
  return r.data;
}

// ------------------------------------------------------------------ generic enquiry form
export function LeadForm({ form = "contact_form", defaults = {}, fields = ["company", "town", "message"], submitLabel = "Send enquiry", files = false, extra, compact, onDone, messageLabel = "What do you need?" }) {
  const t = useT();
  const [v, setV, set] = useLeadForm(defaults);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(null);
  if (done) return <Done reference={done.reference} compact={compact} />;
  async function go(e) {
    e.preventDefault();
    const bad = checkContact(v);
    if (bad) { setErr(bad); return; }
    setBusy(true); setErr("");
    try { const r = await submitLead(v, { form, ...(extra || {}) }); setDone(r); onDone?.(r); } catch (ex) { setErr(errMsg(ex)); } finally { setBusy(false); }
  }
  return (
    <form onSubmit={go} className="relative space-y-3" noValidate>
      <Honeypot value={v.website} onChange={(x) => setV((s) => ({ ...s, website: x }))} />
      <div className={cn("grid gap-3", !compact && "sm:grid-cols-2")}>
        <Field label={t("Your name")} required><Input value={v.name} onChange={set("name")} autoComplete="name" /></Field>
        <Field label={t("Mobile number")} required><Input value={v.phone} onChange={set("phone")} inputMode="tel" autoComplete="tel" placeholder="98765 43210" /></Field>
        {fields.includes("email") && <Field label={t("Email (optional)")}><Input type="email" value={v.email} onChange={set("email")} autoComplete="email" /></Field>}
        {fields.includes("company") && <Field label={t("Company")}><Input value={v.company} onChange={set("company")} autoComplete="organization" /></Field>}
        {fields.includes("town") && <Field label={t("Town")}><Input value={v.town} onChange={set("town")} /></Field>}
      </div>
      {fields.includes("message") && <Field label={messageLabel}><Textarea value={v.message} onChange={set("message")} rows={compact ? 3 : 4} /></Field>}
      {files && <FileDrop files={v.attachments} onChange={(a) => setV((s) => ({ ...s, attachments: a }))} label={typeof files === "string" ? files : undefined} />}
      <Consent checked={v.consent} onChange={set("consent")} id={`consent-${form}`} />
      {err && <Alert tone="red">{err}</Alert>}
      <Button type="submit" loading={busy} size={compact ? "md" : "lg"} className="w-full sm:w-auto">{submitLabel}</Button>
    </form>
  );
}

// ------------------------------------------------------------------ quote wizard
const WIZ_KEY = "spi_quote_draft";
export function QuoteWizard({ preset = {} }) {
  const site = useSite();
  const t = useT();
  const opts = site.options || {};
  const saved = useMemo(() => store.get(WIZ_KEY, null), []);
  const [step, setStep] = useState(saved?.step || 0);
  const [v, setV, set] = useLeadForm({ service: "", site_type: "", supply: "", load_kva: "", timeline: "", ...(saved?.v || {}), ...preset, consent: false, website: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(null);
  useEffect(() => { if (!done) store.set(WIZ_KEY, { step, v: { ...v, consent: false } }); }, [step, v, done]);
  if (done) {
    return (
      <Done title="Your request is in" reference={done.reference}>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button as={Link} to="/book-survey" variant="dark" size="sm">{t("Book a site survey")}</Button>
          <Button as={Link} to="/tools" variant="outline" size="sm">Try the calculators</Button>
        </div>
      </Done>
    );
  }
  const STEPS = ["What you need", "Your site", "Timeline & files", "Your details"];
  const services = (opts.services || []).filter((o) => o.value !== "other").concat((opts.services || []).filter((o) => o.value === "other"));
  function next() {
    setErr("");
    if (step === 0 && !v.service) { setErr("Pick the closest service"); return; }
    if (step === 1 && !v.town.trim()) { setErr("Enter the town where the site is"); return; }
    setStep(step + 1);
  }
  async function submit(e) {
    e.preventDefault();
    const bad = checkContact(v);
    if (bad) { setErr(bad); return; }
    setBusy(true); setErr("");
    try {
      const r = await submitLead({ ...v, load_kva: v.load_kva ? Number(v.load_kva) : null }, { form: "quote_wizard" });
      store.del(WIZ_KEY);
      setDone(r);
    } catch (ex) { setErr(errMsg(ex)); } finally { setBusy(false); }
  }
  return (
    <form onSubmit={step === 3 ? submit : (e) => { e.preventDefault(); next(); }} className="relative" noValidate>
      <Honeypot value={v.website} onChange={(x) => setV((s) => ({ ...s, website: x }))} />
      <ol className="mb-6 grid grid-cols-4 gap-2" aria-label="Steps">
        {STEPS.map((s, n) => (
          <li key={s} className="min-w-0">
            <div className={cn("h-1 rounded-full", n <= step ? "bg-signal" : "bg-fg/10")} />
            <p className={cn("mt-2 truncate text-xs", n === step ? "font-semibold text-fg" : "text-muted")}><span className="tabular">{n + 1}</span> <span className="hidden sm:inline">{s}</span></p>
          </li>
        ))}
      </ol>
      {step === 0 && (
        <fieldset>
          <legend className="mb-3 font-display text-lg font-bold">What do you need?</legend>
          <div className="grid gap-2 sm:grid-cols-2">
            {services.map((o) => (
              <label key={o.value} className={cn("flex cursor-pointer items-center gap-3 rounded-md border px-3 py-2.5 text-sm transition-colors", v.service === o.value ? "border-ink bg-ink text-white" : "border-edge bg-surface hover:border-fg/30")}>
                <input type="radio" name="service" value={o.value} checked={v.service === o.value} onChange={set("service")} className="sr-only" />
                <span className={cn("h-3 w-3 shrink-0 rounded-full border-2", v.service === o.value ? "border-signal bg-signal" : "border-steel")} />
                {o.label}
              </label>
            ))}
          </div>
        </fieldset>
      )}
      {step === 1 && (
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Type of site"><Select value={v.site_type} onChange={set("site_type")} options={opts.sectors || []} placeholder="Choose" /></Field>
          <Field label="Supply" hint="Not sure? Leave it — we'll check."><Select value={v.supply} onChange={set("supply")} options={opts.supply || []} placeholder="Choose" /></Field>
          <Field label="Load or transformer size (kVA)" hint="Approximate is fine"><Input inputMode="decimal" value={v.load_kva} onChange={set("load_kva")} placeholder="e.g. 500" /></Field>
          <Field label="Town / location of the site" required><Input value={v.town} onChange={set("town")} placeholder="e.g. Perundurai" /></Field>
          <Field label="Company / site name" className="sm:col-span-2"><Input value={v.company} onChange={set("company")} /></Field>
        </div>
      )}
      {step === 2 && (
        <div className="space-y-3">
          <Field label="When do you need it?"><Select value={v.timeline} onChange={set("timeline")} options={opts.timeline || []} placeholder="Choose" /></Field>
          <Field label="Anything we should know?"><Textarea value={v.message} onChange={set("message")} rows={4} placeholder="Existing supply, the problem you're solving, deadlines…" /></Field>
          <FileDrop files={v.attachments} onChange={(a) => setV((s) => ({ ...s, attachments: a }))} />
        </div>
      )}
      {step === 3 && (
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={t("Your name")} required><Input value={v.name} onChange={set("name")} autoComplete="name" /></Field>
            <Field label={t("Mobile number")} required><Input value={v.phone} onChange={set("phone")} inputMode="tel" autoComplete="tel" placeholder="98765 43210" /></Field>
            <Field label={t("Email (optional)")} className="sm:col-span-2"><Input type="email" value={v.email} onChange={set("email")} autoComplete="email" /></Field>
          </div>
          <Consent checked={v.consent} onChange={set("consent")} id="consent-wizard" />
        </div>
      )}
      {err && <Alert tone="red" className="mt-4">{err}</Alert>}
      <div className="mt-6 flex items-center justify-between gap-3">
        {step > 0 ? <Button type="button" variant="ghost" onClick={() => setStep(step - 1)}>{t("Back")}</Button> : <span />}
        <Button type="submit" size="lg" loading={busy}>{step === 3 ? "Send my request" : t("Next")}</Button>
      </div>
    </form>
  );
}

// ------------------------------------------------------------------ site survey booking
export function SurveyBooking({ defaultType = "site_survey" }) {
  const locale = useLocale();
  const [slots, setSlots] = useState(null);
  const [pick, setPick] = useState(null);
  const [day, setDay] = useState(null);
  const [v, setV, set] = useLeadForm({ survey_type: defaultType, address: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(null);
  useEffect(() => { api.get("/public/survey-slots").then((r) => { setSlots(r.data); setDay(r.data.find((x) => x.slots.length)?.date || null); }).catch(() => setSlots([])); }, []);
  if (done) {
    return (
      <Done title="Your survey is booked" reference={done.reference}>
        <p className="mt-1 text-sm">{fmtDate(done.when)} at {done.when.slice(11)}{done.engineer ? ` with ${done.engineer}` : ""}. We'll call to confirm before we come.</p>
        <a href={done.ics} className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-cable underline"><CalendarDays className="h-4 w-4" />Add to calendar</a>
      </Done>
    );
  }
  const today = slots?.find((x) => x.date === day);
  async function go(e) {
    e.preventDefault();
    if (!pick) { setErr("Pick a date and time"); return; }
    const bad = checkContact(v);
    if (bad) { setErr(bad); return; }
    setBusy(true); setErr("");
    try { setDone(await submitLead({ ...v, slot: pick }, { form: "survey_booking" }, "/public/survey-booking")); } catch (ex) { setErr(errMsg(ex)); } finally { setBusy(false); }
  }
  return (
    <form onSubmit={go} className="relative space-y-5" noValidate>
      <Honeypot value={v.website} onChange={(x) => setV((s) => ({ ...s, website: x }))} />
      <Field label="Visit for">
        <div className="grid gap-2 sm:grid-cols-3">
          {[["site_survey", "Site survey"], ["energy_audit", "Energy audit"], ["bill_review", "Bill review meeting"]].map(([k, l]) => (
            <label key={k} className={cn("cursor-pointer rounded-md border px-3 py-2 text-sm", v.survey_type === k ? "border-ink bg-ink text-white" : "border-edge hover:border-fg/30")}>
              <input type="radio" className="sr-only" name="stype" value={k} checked={v.survey_type === k} onChange={set("survey_type")} />{l}
            </label>
          ))}
        </div>
      </Field>
      <div>
        <p className="field-label">Pick a day</p>
        {!slots ? <p className="text-sm text-muted">Loading free slots…</p> : (
          <div className="scrollbar-thin -mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
            {slots.map((x) => (
              <button type="button" key={x.date} disabled={!x.slots.length} onClick={() => { setDay(x.date); setPick(null); }}
                className={cn("flex w-[68px] shrink-0 flex-col items-center rounded-md border py-2 text-xs disabled:opacity-35", day === x.date ? "border-ink bg-ink text-white" : "border-edge hover:border-fg/30")}>
                <span>{new Date(`${x.date}T00:00:00+05:30`).toLocaleDateString(locale, { weekday: "short" })}</span>
                <span className="font-display text-lg font-bold">{x.date.slice(8)}</span>
                <span>{new Date(`${x.date}T00:00:00+05:30`).toLocaleDateString(locale, { month: "short" })}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      {today && (
        <div>
          <p className="field-label">Time</p>
          <div className="flex flex-wrap gap-2">
            {today.slots.map((s) => {
              const key = `${today.date}T${s}`;
              return <button type="button" key={s} onClick={() => setPick(key)} className={cn("rounded-md border px-4 py-2 text-sm tabular", pick === key ? "border-signal bg-signal font-semibold text-white" : "border-edge hover:border-fg/30")}>{s}</button>;
            })}
          </div>
        </div>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Your name" required><Input value={v.name} onChange={set("name")} autoComplete="name" /></Field>
        <Field label="Mobile number" required><Input value={v.phone} onChange={set("phone")} inputMode="tel" placeholder="98765 43210" /></Field>
        <Field label="Company"><Input value={v.company} onChange={set("company")} /></Field>
        <Field label="Town" required><Input value={v.town} onChange={set("town")} /></Field>
        <Field label="Site address" className="sm:col-span-2"><Textarea rows={2} value={v.address} onChange={set("address")} /></Field>
      </div>
      <Consent checked={v.consent} onChange={set("consent")} id="consent-booking" />
      {err && <Alert tone="red">{err}</Alert>}
      <Button type="submit" size="lg" loading={busy}>Book the visit</Button>
    </form>
  );
}

// ------------------------------------------------------------------ call-back dialog
export function CallbackButton({ children, className, variant = "outline", size = "md" }) {
  const [open, setOpen] = useState(false);
  const t = useT();
  return (
    <>
      <Button type="button" variant={variant} size={size} className={className} onClick={() => setOpen(true)}><Phone className="h-4 w-4" />{children || t("Request a call back")}</Button>
      <Dialog open={open} onOpenChange={setOpen} title="We'll call you back" description="Leave your number; an engineer calls within working hours.">
        <LeadForm form="callback" fields={["town", "message"]} messageLabel="Best time to call / what it's about" compact submitLabel="Call me back" />
      </Dialog>
    </>
  );
}

export function PhoneLink({ className }) {
  const site = useSite();
  const p = site.settings?.phone;
  if (!p) return null;
  return <a href={telLink(p)} dir="ltr" className={className}>{p}</a>;
}
