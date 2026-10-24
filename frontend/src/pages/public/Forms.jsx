import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { Phone, MessageCircle, AlertTriangle, Mail, Briefcase, MapPin, Wrench, ShieldCheck } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useMeta, cn } from "@/lib/utils";
import { telLink, waLink, fmtDate } from "@/lib/format";
import { Markdown } from "@/lib/markdown";
import { useT } from "@/lib/i18n";
import { Button, Input, Select, Textarea, Field, Alert, Dialog, Skeleton } from "@/components/ui/kit";
import { useSite } from "@/components/public/site";
import { PageHero, Section } from "@/components/public/Layout";
import { LeadForm, QuoteWizard, SurveyBooking, FileDrop, Consent, Honeypot, Done, checkContact, useLeadForm, submitLead } from "@/components/public/forms";
import { useGet, Branches, PageLoading, NotFound } from "./Content";

function TwoCol({ children, aside }) {
  return <div className="container grid gap-10 py-12 lg:grid-cols-[1fr_360px] lg:gap-14">{children}<aside className="space-y-5">{aside}</aside></div>;
}

function ContactAside() {
  const site = useSite();
  const s = site.settings || {};
  return (
    <div className="rounded-xl bg-paper p-5">
      <h2 className="font-display text-[17px] font-bold">Prefer to talk?</h2>
      <ul className="mt-3 space-y-2.5 text-[16px]">
        {s.phone && <li><a href={telLink(s.phone)} dir="ltr" className="flex items-center gap-2.5 hover:underline"><Phone className="h-4 w-4 text-cable" />{s.phone}</a></li>}
        {s.whatsapp && <li><a href={waLink(s.whatsapp, "Hello, I need help with an electrical project.")} target="_blank" rel="noreferrer" className="flex items-center gap-2.5 hover:underline"><MessageCircle className="h-4 w-4 text-good" />WhatsApp us</a></li>}
        {s.email && <li><a href={`mailto:${s.email}`} className="flex items-center gap-2.5 hover:underline"><Mail className="h-4 w-4 text-cable" />{s.email}</a></li>}
      </ul>
      {s.emergency_phone && <Link to="/emergency" className="mt-4 flex items-center gap-2 border-t border-line pt-3 text-sm font-semibold text-bad"><AlertTriangle className="h-4 w-4" />Breakdown? {s.emergency_phone}</Link>}
    </div>
  );
}

// ------------------------------------------------------------------ contact
export function ContactPage() {
  useMeta({ title: "Contact us", description: "Call, WhatsApp or write to Sellandiamman Power Infra, or visit our offices in Perundurai, Erode and Coimbatore." });
  return (
    <>
      <PageHero title="Talk to an engineer" text="Tell us what you're planning or what's gone wrong. We reply within working hours, usually the same day." crumbs={[["/", "Home"], [null, "Contact"]]} />
      <TwoCol aside={<ContactAside />}>
        <div><LeadForm form="contact_form" fields={["email", "company", "town", "message"]} files /></div>
      </TwoCol>
      <Section tone="paper" title="Our offices"><Branches /></Section>
    </>
  );
}

// ------------------------------------------------------------------ quote and survey
export function GetQuotePage() {
  const [sp] = useSearchParams();
  useMeta({ title: "Get a quote", description: "Four quick steps: what you need, your site, timeline and files, your details. An engineer calls you back." });
  const preset = sp.get("service") ? { service: sp.get("service") } : {};
  return (
    <>
      <PageHero title="Get a quote" text="Four short steps. Attach drawings, a load list or a recent bill if you have them, and we'll come back with questions or a price." crumbs={[["/", "Home"], [null, "Get a quote"]]} />
      <TwoCol aside={<><ContactAside /><WhatNext /></>}>
        <div className="rounded-xl border border-line bg-white p-5 md:p-7"><QuoteWizard preset={preset} /></div>
      </TwoCol>
    </>
  );
}

function WhatNext() {
  const steps = ["An engineer calls you to understand the site", "We visit for a survey if the job needs one", "You get a scope, drawings and a fixed price", "Approvals, work and handover, all visible in your portal"];
  return (
    <div className="rounded-xl border border-line p-5">
      <h2 className="font-display text-[17px] font-bold">What happens next</h2>
      <ol className="mt-3 space-y-2.5">{steps.map((s, n) => <li key={s} className="flex gap-3 text-sm"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-ink text-xs font-bold text-signal-bright tabular">{n + 1}</span>{s}</li>)}</ol>
    </div>
  );
}

export function BookSurveyPage() {
  useMeta({ title: "Book a site survey", description: "Pick a date and time for an engineer to visit your site, measure, check the existing supply and discuss options." });
  return (
    <>
      <PageHero title="Book a site survey" text="An engineer visits, checks your existing supply and loads, takes measurements and photos, and talks through the options. No charge for sites in our service area." crumbs={[["/", "Home"], [null, "Book a site survey"]]} />
      <TwoCol aside={<ContactAside />}>
        <div className="rounded-xl border border-line bg-white p-5 md:p-7"><SurveyBooking /></div>
      </TwoCol>
    </>
  );
}

// ------------------------------------------------------------------ bill review
export function BillReviewPage() {
  const [v, setV, set] = useLeadForm({ tariff: "", service_no: "", units: "", amount: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(null);
  useMeta({ title: "Free electricity bill review", description: "Send us your HT or LT bill. We check demand charges, power factor penalties, ToD and tariff category, and tell you what you can save." });
  async function go(e) {
    e.preventDefault();
    const bad = checkContact(v);
    if (bad) { setErr(bad); return; }
    if (!v.attachments.length) { setErr("Attach at least one recent bill (photo or PDF)"); return; }
    setBusy(true); setErr("");
    try {
      setDone(await submitLead({ ...v, message: `Bill review. Service no: ${v.service_no || "-"}, tariff: ${v.tariff || "-"}, units/month: ${v.units || "-"}, bill/month: ${v.amount || "-"}. ${v.message || ""}` },
        { form: "bill_review", service: "energy_audit", supply: v.tariff?.startsWith("HT") ? "HT" : v.tariff?.startsWith("LT") ? "LT" : undefined, extra: { service_no: v.service_no, tariff: v.tariff, units: v.units, amount: v.amount } }));
    } catch (ex) { setErr(errMsg(ex)); } finally { setBusy(false); }
  }
  const CHECKS = ["Contract demand set too high, or exceeded and penalised", "Power factor penalties, and the capacitor bank that would stop them", "Peak-hour (ToD) usage that can move to cheaper hours", "Whether your tariff category is right for your use", "Whether LT to HT conversion would pay back"];
  return (
    <>
      <PageHero title="Free electricity bill review" text="Most HT and large LT bills we see carry charges that can be cut: demand set too high, power factor penalties, peak-hour use. Send a few recent bills and we'll tell you where the money goes." crumbs={[["/", "Home"], [null, "Bill review"]]} />
      <TwoCol aside={<div className="rounded-xl bg-paper p-5"><h2 className="font-display text-[17px] font-bold">What we check</h2><ul className="mt-3 space-y-2.5">{CHECKS.map((c) => <li key={c} className="flex gap-2.5 text-sm"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-good" />{c}</li>)}</ul>
        <p className="mt-4 border-t border-line pt-3 text-sm text-muted"><span className="block">Want a quick number first? Try these calculators:</span><span className="mt-1 flex flex-wrap gap-x-4"><Link to="/tools/bill-estimator" className="text-cable underline">Electricity bill estimator</Link><Link to="/tools/contract-demand" className="text-cable underline">Contract demand optimiser</Link></span></p></div>}>
        {done ? <Done title="We've got your bills" reference={done.reference} /> : (
          <form onSubmit={go} className="relative space-y-4 rounded-xl border border-line bg-white p-5 md:p-7" noValidate>
            <Honeypot value={v.website} onChange={(x) => setV((s) => ({ ...s, website: x }))} />
            <FileDrop files={v.attachments} onChange={(a) => setV((s) => ({ ...s, attachments: a }))} label="Your last 3–12 bills (photos or PDFs)" />
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Tariff / category"><Select value={v.tariff} onChange={set("tariff")} placeholder="Not sure" options={[{ value: "HT_I", label: "HT I (industry)" }, { value: "HT_III", label: "HT III (commercial)" }, { value: "HT_other", label: "HT, other" }, { value: "LT_IIIB", label: "LT industrial (IIIB)" }, { value: "LT_V", label: "LT commercial (V)" }, { value: "LT_other", label: "LT, other" }]} /></Field>
              <Field label="Service / consumer number"><Input value={v.service_no} onChange={set("service_no")} /></Field>
              <Field label="Units a month (approx.)"><Input inputMode="numeric" value={v.units} onChange={set("units")} /></Field>
              <Field label="Bill a month (approx. ₹)"><Input inputMode="numeric" value={v.amount} onChange={set("amount")} /></Field>
              <Field label="Your name" required><Input value={v.name} onChange={set("name")} autoComplete="name" /></Field>
              <Field label="Mobile number" required><Input value={v.phone} onChange={set("phone")} inputMode="tel" placeholder="98765 43210" /></Field>
              <Field label="Company"><Input value={v.company} onChange={set("company")} /></Field>
              <Field label="Town"><Input value={v.town} onChange={set("town")} /></Field>
            </div>
            <Consent checked={v.consent} onChange={set("consent")} id="consent-bill" />
            {err && <Alert tone="red">{err}</Alert>}
            <Button type="submit" size="lg" loading={busy}>Send for review</Button>
          </form>
        )}
      </TwoCol>
    </>
  );
}

// ------------------------------------------------------------------ tenders
export function TendersPage() {
  const [v, setV, set] = useLeadForm({ tender_name: "", buyer: "", due_on: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(null);
  useMeta({ title: "Invite us to bid", description: "Send your tender, RFQ or BOQ. We price electrical packages for EPC contractors, builders, consultants and government buyers." });
  async function go(e) {
    e.preventDefault();
    const bad = checkContact(v);
    if (bad) { setErr(bad); return; }
    setBusy(true); setErr("");
    try {
      setDone(await submitLead({ ...v, message: `Tender / RFQ: ${v.tender_name || "-"}. Buyer: ${v.buyer || "-"}. Due: ${v.due_on || "-"}. ${v.message || ""}` }, { form: "tender_invite", extra: { tender_name: v.tender_name, buyer: v.buyer, due_on: v.due_on } }));
    } catch (ex) { setErr(errMsg(ex)); } finally { setBusy(false); }
  }
  return (
    <>
      <PageHero title="Invite us to bid" text="EPC contractors, builders, consultants and public buyers: send the tender documents or BOQ and we'll price the electrical package, with technical compliance and deviations listed." crumbs={[["/", "Home"], [null, "Tenders"]]} />
      <TwoCol aside={<ContactAside />}>
        {done ? <Done title="Thanks — our tender team has it" reference={done.reference} /> : (
          <form onSubmit={go} className="relative space-y-4 rounded-xl border border-line bg-white p-5 md:p-7" noValidate>
            <Honeypot value={v.website} onChange={(x) => setV((s) => ({ ...s, website: x }))} />
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Tender / RFQ name or number" className="sm:col-span-2"><Input value={v.tender_name} onChange={set("tender_name")} /></Field>
              <Field label="Buyer / main contractor"><Input value={v.buyer} onChange={set("buyer")} /></Field>
              <Field label="Bid due date"><Input type="date" value={v.due_on} onChange={set("due_on")} /></Field>
            </div>
            <FileDrop files={v.attachments} onChange={(a) => setV((s) => ({ ...s, attachments: a }))} label="Tender documents, BOQ, drawings" max={10} />
            <Field label="Notes"><Textarea value={v.message} onChange={set("message")} rows={3} placeholder="Scope, site visit date, pre-bid meeting…" /></Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Your name" required><Input value={v.name} onChange={set("name")} /></Field>
              <Field label="Mobile number" required><Input value={v.phone} onChange={set("phone")} inputMode="tel" /></Field>
              <Field label="Email (optional)"><Input type="email" value={v.email} onChange={set("email")} /></Field>
              <Field label="Company"><Input value={v.company} onChange={set("company")} /></Field>
            </div>
            <Consent checked={v.consent} onChange={set("consent")} id="consent-tender" />
            {err && <Alert tone="red">{err}</Alert>}
            <Button type="submit" size="lg" loading={busy}>Send the tender</Button>
          </form>
        )}
      </TwoCol>
    </>
  );
}

// ------------------------------------------------------------------ emergency
const EQUIP = [["transformer", "Transformer"], ["ht_panel", "HT panel / VCB / RMU"], ["lt_panel", "LT panel / ACB"], ["cable", "Cable fault"], ["dg", "DG set"], ["apfc", "APFC / capacitor"], ["other", "Something else / not sure"]];
export function EmergencyPage() {
  const t = useT();
  const site = useSite();
  const s = site.settings || {};
  const [v, setV, set] = useLeadForm({ equipment: "", consent: true });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(null);
  useMeta({ title: "24×7 breakdown service", description: "Transformer, HT panel, cable or DG failure? Call our breakdown line or log the fault here and the duty engineer will call you." });
  async function go(e) {
    e.preventDefault();
    if (!v.name.trim() || !/\d{10}/.test(v.phone.replace(/\D/g, ""))) { setErr("Enter your name and mobile number"); return; }
    setBusy(true); setErr("");
    try { setDone((await api.post("/public/emergency", { ...v, email: v.email || undefined })).data); } catch (ex) { setErr(errMsg(ex)); } finally { setBusy(false); }
  }
  return (
    <>
      <section className="bg-bad text-white">
        <div className="container py-10 md:py-14">
          <h1 className="text-[30px] font-semibold leading-tight text-white md:text-[42px]" style={{ letterSpacing: "-0.02em" }}>Power down? Call the breakdown line.</h1>
          <p className="mt-3 max-w-2xl text-lg text-white/85">Keep people away from the equipment. Don't reset a tripped HT breaker until the cause is found.</p>
          {s.emergency_phone && <a href={telLink(s.emergency_phone)} dir="ltr" className="mt-6 inline-flex h-14 items-center gap-3 rounded-lg bg-white px-6 font-display text-[22px] font-semibold text-bad tabular"><Phone className="h-6 w-6" />{s.emergency_phone}</a>}
        </div>
      </section>
      <TwoCol aside={<div className="rounded-xl bg-paper p-5 text-sm leading-relaxed"><h2 className="font-display text-[17px] font-bold">While you wait</h2>
        <ul className="mt-3 list-disc space-y-1.5 ps-5"><li>Note what tripped and any alarms or smells.</li><li>Take photos from a safe distance.</li><li>If there is fire, call 101 first.</li><li>AMC clients: your contract response time applies.</li></ul></div>}>
        {done ? <Done title="Breakdown logged"><p className="mt-1 text-sm">{t("Reference {ref}. The duty engineer will call you shortly.", { ref: <span key="r" className="font-semibold">{done.reference}</span> })}</p></Done> : (
          <form onSubmit={go} className="relative space-y-4 rounded-xl border border-line bg-white p-5 md:p-7" noValidate>
            <h2 className="font-display text-[19px] font-bold">Or log it here and we'll call you</h2>
            <Honeypot value={v.website} onChange={(x) => setV((s2) => ({ ...s2, website: x }))} />
            <Field label="What has failed?">
              <div className="grid gap-2 sm:grid-cols-2">
                {EQUIP.map(([k, l]) => (
                  <label key={k} className={cn("cursor-pointer rounded-md border px-3 py-2 text-sm", v.equipment === k ? "border-ink bg-ink text-white" : "border-line hover:border-fg/30")}>
                    <input type="radio" className="sr-only" name="equip" value={k} checked={v.equipment === k} onChange={set("equipment")} />{l}
                  </label>
                ))}
              </div>
            </Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Your name" required><Input value={v.name} onChange={set("name")} /></Field>
              <Field label="Mobile number" required><Input value={v.phone} onChange={set("phone")} inputMode="tel" /></Field>
              <Field label="Company / site"><Input value={v.company} onChange={set("company")} /></Field>
              <Field label="Town"><Input value={v.town} onChange={set("town")} /></Field>
            </div>
            <Field label="What happened?"><Textarea value={v.message} onChange={set("message")} rows={3} /></Field>
            <FileDrop files={v.attachments} onChange={(a) => setV((s2) => ({ ...s2, attachments: a }))} label="Photos (optional)" max={5} accept=".jpg,.jpeg,.png,.webp" />
            {err && <Alert tone="red">{err}</Alert>}
            <Button type="submit" size="lg" variant="danger" loading={busy}>Log the breakdown</Button>
          </form>
        )}
      </TwoCol>
    </>
  );
}

// ------------------------------------------------------------------ careers
const DEPTS = { f1: "Sales & estimation", f3: "Projects", f4: "Purchase & stores", f5: "Liaison", f6: "Service", f7: "Quality & safety", f8: "Accounts & HR", mgmt: "Management" };
export function CareersPage() {
  const t = useT();
  const { data, loading } = useGet("/public/jobs");
  const [apply, setApply] = useState(null);
  useMeta({ title: "Careers", description: "Site engineers, supervisors, electricians, jointers, estimators and service technicians: join our team." });
  return (
    <>
      <PageHero title="Work on power projects that matter" text="Substations, factories, hospitals, solar plants. We train people properly, work safely and pay on time." crumbs={[["/", "Home"], [null, "Careers"]]} />
      <Section title="Open positions">
        {loading ? <Skeleton className="h-40" /> : !data?.length ? <p className="text-muted">No openings right now. Send your CV to the email on the contact page and we'll keep it on file.</p> : (
          <div className="divide-y divide-line border-y border-line">
            {data.map((j) => (
              <div key={j.id} className="grid gap-4 py-6 md:grid-cols-[1fr_auto] md:items-start">
                <div>
                  <h3 className="font-display text-[19px] font-bold">{j.title}</h3>
                  <p className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
                    <span className="inline-flex items-center gap-1"><Briefcase className="h-3.5 w-3.5" />{DEPTS[j.department] || j.department}</span>
                    {j.jtype && <span>{j.jtype}</span>}
                    {j.location && <span className="inline-flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{j.location}</span>}
                    {j.closes_on && <span>{t("Apply by {date}", { date: fmtDate(j.closes_on) })}</span>}
                  </p>
                  <p className="mt-3 max-w-2xl text-[16px] leading-relaxed">{j.description}</p>
                  {j.requirements && <Markdown text={j.requirements} className="prose-site mt-2 text-sm" />}
                </div>
                <Button onClick={() => setApply(j)}>Apply</Button>
              </div>
            ))}
          </div>
        )}
      </Section>
      <ApplyDialog job={apply} onClose={() => setApply(null)} />
    </>
  );
}

function ApplyDialog({ job, onClose }) {
  const [v, setV, set] = useLeadForm({ experience_years: "", current_role: "", cv: [] });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(false);
  async function go(e) {
    e.preventDefault();
    const bad = checkContact(v);
    if (bad) { setErr(bad); return; }
    setBusy(true); setErr("");
    try {
      await api.post(`/public/careers/${job.id}/apply`, { name: v.name, phone: v.phone, email: v.email || undefined, experience_years: v.experience_years ? Number(v.experience_years) : null,
        current_role: v.current_role, cv: v.attachments[0] || null, message: v.message, consent: v.consent, website: v.website });
      setDone(true);
    } catch (ex) { setErr(errMsg(ex)); } finally { setBusy(false); }
  }
  return (
    <Dialog open={!!job} onOpenChange={(x) => { if (!x) { onClose(); setDone(false); } }} title={job ? `Apply: ${job.title}` : ""}>
      {done ? <Done title="Application sent">We'll call you if your profile fits.</Done> : job && (
        <form onSubmit={go} className="relative space-y-3" noValidate>
          <Honeypot value={v.website} onChange={(x) => setV((s) => ({ ...s, website: x }))} />
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Your name" required><Input value={v.name} onChange={set("name")} /></Field>
            <Field label="Mobile number" required><Input value={v.phone} onChange={set("phone")} inputMode="tel" /></Field>
            <Field label="Email (optional)"><Input type="email" value={v.email} onChange={set("email")} /></Field>
            <Field label="Years of experience"><Input inputMode="decimal" value={v.experience_years} onChange={set("experience_years")} /></Field>
            <Field label="Current role" className="sm:col-span-2"><Input value={v.current_role} onChange={set("current_role")} /></Field>
          </div>
          <FileDrop files={v.attachments} onChange={(a) => setV((s) => ({ ...s, attachments: a.slice(0, 1) }))} label="Your CV" max={1} accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" />
          <Consent checked={v.consent} onChange={set("consent")} id="consent-apply" />
          {err && <Alert tone="red">{err}</Alert>}
          <Button type="submit" loading={busy}>Send application</Button>
        </form>
      )}
    </Dialog>
  );
}

// ------------------------------------------------------------------ vendor registration
export function VendorRegistrationPage() {
  const [v, setV] = useState({ company: "", vtype: "supplier", trade: "", gstin: "", contact_person: "", phone: "", email: "", town: "", licence_no: "", documents: [], consent: false, website: "" });
  const set = (k) => (e) => setV((s) => ({ ...s, [k]: e?.target ? (e.target.type === "checkbox" ? e.target.checked : e.target.value) : e }));
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(false);
  useMeta({ title: "Vendor & subcontractor registration", description: "Suppliers, subcontractors, labour contractors and transporters: register to work with Sellandiamman Power Infra." });
  async function go(e) {
    e.preventDefault();
    if (!v.company.trim() || !v.phone.trim()) { setErr("Enter the company name and a phone number"); return; }
    if (!v.consent) { setErr("Tick the consent box"); return; }
    setBusy(true); setErr("");
    try { await api.post("/public/vendor-registration", { ...v, email: v.email || undefined }); setDone(true); } catch (ex) { setErr(errMsg(ex)); } finally { setBusy(false); }
  }
  return (
    <>
      <PageHero title="Supply to us, or work with us on site" text="We buy cables, transformers, panels, switchgear and consumables, and work with licensed subcontractors and labour contractors across Tamil Nadu. Register once; our purchase team reviews every application." crumbs={[["/", "Home"], [null, "Vendor registration"]]} />
      <TwoCol aside={<div className="rounded-xl bg-paper p-5 text-sm leading-relaxed"><h2 className="font-display text-[17px] font-bold">Have these ready</h2><ul className="mt-3 list-disc space-y-1.5 ps-5"><li>GST certificate and PAN</li><li>Electrical contractor licence (for subcontractors)</li><li>Price list or rate card</li><li>Two recent client references</li></ul><p className="mt-3 text-muted">Approved vendors get a portal login for RFQs, purchase orders and bills.</p></div>}>
        {done ? <Done title="Registration received">Our purchase team will review it and get in touch.</Done> : (
          <form onSubmit={go} className="relative space-y-4 rounded-xl border border-line bg-white p-5 md:p-7" noValidate>
            <Honeypot value={v.website} onChange={(x) => setV((s) => ({ ...s, website: x }))} />
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Company name" required className="sm:col-span-2"><Input value={v.company} onChange={set("company")} /></Field>
              <Field label="You are a"><Select value={v.vtype} onChange={set("vtype")} options={[{ value: "supplier", label: "Supplier" }, { value: "subcontractor", label: "Subcontractor" }, { value: "labour_contractor", label: "Labour contractor" }, { value: "transporter", label: "Transporter / crane hire" }]} /></Field>
              <Field label="What you supply / do"><Input value={v.trade} onChange={set("trade")} placeholder="e.g. HT cables, cable laying" /></Field>
              <Field label="GSTIN"><Input value={v.gstin} onChange={set("gstin")} maxLength={15} className="uppercase" /></Field>
              <Field label="Licence number (if any)"><Input value={v.licence_no} onChange={set("licence_no")} /></Field>
              <Field label="Contact person"><Input value={v.contact_person} onChange={set("contact_person")} /></Field>
              <Field label="Phone" required><Input value={v.phone} onChange={set("phone")} inputMode="tel" /></Field>
              <Field label="Email"><Input type="email" value={v.email} onChange={set("email")} /></Field>
              <Field label="Town"><Input value={v.town} onChange={set("town")} /></Field>
            </div>
            <FileDrop files={v.documents} onChange={(a) => setV((s) => ({ ...s, documents: a }))} label="GST certificate, licence, price list" max={10} />
            <Consent checked={v.consent} onChange={set("consent")} id="consent-vendor" />
            {err && <Alert tone="red">{err}</Alert>}
            <Button type="submit" size="lg" loading={busy}>Register</Button>
          </form>
        )}
      </TwoCol>
    </>
  );
}

// ------------------------------------------------------------------ equipment QR page
export function AssetPage() {
  const t = useT();
  const { token } = useParams();
  const { data: a, error, loading } = useGet(`/public/asset/${token}`);
  const [v, setV, set] = useLeadForm({ issue: "", priority: "normal" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(null);
  useMeta({ title: a ? `${a.kind} ${a.code}` : "Equipment", noindex: true });
  if (loading) return <PageLoading />;
  if (error || !a) return <NotFound />;
  async function go(e) {
    e.preventDefault();
    if (!v.name.trim() || !v.phone.trim() || !v.issue.trim()) { setErr("Enter your name, phone and what's wrong"); return; }
    setBusy(true); setErr("");
    try { setDone((await api.post(`/public/asset/${token}/request`, { name: v.name, phone: v.phone, issue: v.issue, priority: v.priority, photos: v.attachments, website: v.website })).data); } catch (ex) { setErr(errMsg(ex)); } finally { setBusy(false); }
  }
  const rows = [["Equipment", a.kind], ["Tag", a.code], ["Make", a.make], ["Rating", a.rating], ["Site", a.site], ["Client", a.client],
    ["Warranty until", a.warranty_until && fmtDate(a.warranty_until)], ["AMC until", a.amc_until ? fmtDate(a.amc_until) : "No active AMC"], ["Last service", a.last_service_on ? fmtDate(a.last_service_on) : "—"]].filter(([, x]) => x);
  return (
    <div className="container max-w-2xl py-10">
      <p className="flex items-center gap-2 text-sm text-muted"><Wrench className="h-4 w-4" />Maintained by Sellandiamman Power Infra</p>
      <h1 className="mt-2 text-[28px] font-semibold">{a.kind} {a.code}</h1>
      <dl className="mt-5 divide-y divide-line rounded-xl border border-line text-[16px]">
        {rows.map(([k, x]) => <div key={k} className="flex justify-between gap-4 px-4 py-2.5"><dt className="text-muted">{k}</dt><dd className="text-end font-medium">{x}</dd></div>)}
      </dl>
      <div className="mt-8">
        {done ? <Done title="Request logged"><p className="mt-1 text-sm">{t("Reference {ref}. Our service team will call you.", { ref: <span key="r" className="font-semibold">{done.reference}</span> })}</p></Done> : (
          <form onSubmit={go} className="relative space-y-3 rounded-xl border border-line bg-white p-5" noValidate>
            <h2 className="font-display text-[19px] font-bold">Report a problem with this equipment</h2>
            <Honeypot value={v.website} onChange={(x) => setV((s) => ({ ...s, website: x }))} />
            <Field label="What's wrong?" required><Textarea value={v.issue} onChange={set("issue")} rows={3} /></Field>
            <Field label="How urgent?"><Select value={v.priority} onChange={set("priority")} options={[{ value: "urgent", label: "Urgent: supply is down" }, { value: "high", label: "High: running, but at risk" }, { value: "normal", label: "Normal" }, { value: "low", label: "Low: next visit is fine" }]} /></Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Your name" required><Input value={v.name} onChange={set("name")} /></Field>
              <Field label="Mobile number" required><Input value={v.phone} onChange={set("phone")} inputMode="tel" /></Field>
            </div>
            <FileDrop files={v.attachments} onChange={(x) => setV((s) => ({ ...s, attachments: x }))} label="Photos (optional)" max={5} accept=".jpg,.jpeg,.png,.webp" />
            {err && <Alert tone="red">{err}</Alert>}
            <Button type="submit" loading={busy}>Send request</Button>
          </form>
        )}
      </div>
    </div>
  );
}
