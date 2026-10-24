import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Check, ChevronDown, MapPin, Phone, Clock, Mail, ArrowUpRight, ShieldCheck, ClipboardCheck, Quote, X } from "lucide-react";
import { api, fileUrl } from "@/lib/api";
import { useMeta, cn } from "@/lib/utils";
import { useT, translateIn } from "@/lib/i18n";
import { telLink, fmtDate } from "@/lib/format";
import { Markdown } from "@/lib/markdown";
import { Button, Dialog, Skeleton } from "@/components/ui/kit";
import { useSite, optLabel } from "@/components/public/site";
import { PageHero, Section, Icon } from "@/components/public/Layout";
import { ProjectCard, Cover, Chip, illustrationFor } from "@/components/public/bits";
import { LeadForm, CallbackButton } from "@/components/public/forms";

// ------------------------------------------------------------------ small helpers
function useGet(path, deps = []) {
  const [state, set] = useState({ data: null, error: null, loading: true });
  useEffect(() => {
    let on = true;
    set((s) => ({ ...s, loading: true }));
    api.get(path).then((r) => on && set({ data: r.data, error: null, loading: false }))
      .catch((e) => on && set({ data: null, error: e.response?.status || 500, loading: false }));
    return () => { on = false; };
  }, [path, ...deps]); // eslint-disable-line react-hooks/exhaustive-deps
  return state;
}
export { useGet };

export function PageLoading() {
  return (
    <div className="container space-y-4 py-16">
      <Skeleton className="h-10 w-2/3" /><Skeleton className="h-5 w-1/2" /><Skeleton className="mt-8 h-64 w-full" />
    </div>
  );
}

function Faqs({ items }) {
  if (!items?.length) return null;
  return (
    <div className="divide-y divide-line border-y border-line">
      {items.map((f, n) => (
        <details key={n} className="group py-4">
          <summary className="flex cursor-pointer list-none items-start justify-between gap-4 font-display text-[17px] font-bold">
            {f.q || f.question}
            <ChevronDown className="mt-1 h-4 w-4 shrink-0 transition-transform group-open:rotate-180" aria-hidden />
          </summary>
          <p className="mt-2 max-w-3xl text-[16px] leading-relaxed text-muted">{f.a || f.answer}</p>
        </details>
      ))}
    </div>
  );
}
export { Faqs };

function EnquiryAside({ title = "Talk to an engineer", text, form, extra, files }) {
  const site = useSite();
  return (
    <aside className="rounded-xl border border-line bg-paper p-5 lg:sticky lg:top-24">
      <h2 className="text-[19px] font-extrabold">{title}</h2>
      <p className="mb-4 mt-1 text-sm text-muted">{text || "Tell us about your site. We reply within working hours, usually the same day."}</p>
      <LeadForm form={form} extra={extra} compact files={files} fields={["company", "town", "message"]} />
      {site.settings?.phone && <p className="mt-4 border-t border-line pt-3 text-sm text-muted">Or call <a className="font-semibold text-fg" href={telLink(site.settings.phone)} dir="ltr">{site.settings.phone}</a></p>}
    </aside>
  );
}

// ------------------------------------------------------------------ services
export function ServicesPage() {
  const site = useSite();
  const t = useT();
  useMeta({ title: "Services", description: "HT substations, transformers, LT and HT panels, cabling, earthing, solar EPC, EV charging, testing, approvals and AMC across Tamil Nadu." });
  return (
    <>
      <PageHero title="Everything between the grid and your machines" text="Fourteen services, one team. Pick what you need, or tell us the problem and we'll work out the scope with you."
        crumbs={[["/", "Home"], [null, t("Services")]]}>
        <div className="flex flex-wrap gap-3"><Button as={Link} to="/get-quote">{t("Get a quote")}</Button><Button as={Link} to="/book-survey" variant="light">{t("Book a site survey")}</Button></div>
      </PageHero>
      <Section>
        <div className="grid gap-x-10 gap-y-2 md:grid-cols-2">
          {site.services.map((s) => (
            <Link key={s.slug} to={`/services/${s.slug}`} className="group grid grid-cols-[96px_1fr] gap-4 border-b border-line py-5 sm:grid-cols-[132px_1fr]">
              <Cover service={s.service_key} className="aspect-[4/3] rounded-md" label={false} />
              <div>
                <h2 className="flex items-center gap-2 font-display text-[17px] font-bold leading-snug group-hover:underline group-hover:decoration-signal group-hover:decoration-2 group-hover:underline-offset-4">
                  <Icon name={s.icon} className="h-4 w-4 shrink-0 text-signal-deep" />{s.title}
                </h2>
                <p className="mt-1.5 text-sm leading-relaxed text-muted">{s.summary}</p>
              </div>
            </Link>
          ))}
        </div>
      </Section>
    </>
  );
}

export function ServiceDetail() {
  const { slug } = useParams();
  const { data, error, loading } = useGet(`/public/services/${slug}`);
  const site = useSite();
  const s = data?.service;
  useMeta({ title: s?.title, description: s?.summary, jsonLd: s && { "@context": "https://schema.org", "@type": "Service", name: s.title, description: s.summary, provider: { "@type": "Organization", name: "Sellandiamman Power Infra" }, areaServed: "Tamil Nadu" } });
  if (loading) return <PageLoading />;
  if (error || !s) return <NotFound />;
  const tools = site.tools.filter((t) => (TOOLS_FOR[s.service_key] || []).includes(t.slug));
  return (
    <>
      <PageHero title={s.title} text={s.summary} crumbs={[["/", "Home"], ["/services", "Services"], [null, s.title.replace(/ \(.*\)/, "")]]}>
        <div className="flex flex-wrap gap-3">
          <Button as={Link} to={`/get-quote?service=${s.service_key}`}>Get a quote for this</Button>
          <CallbackButton variant="light" />
        </div>
      </PageHero>
      <div className="container grid gap-12 py-14 lg:grid-cols-[1fr_380px]">
        <div className="min-w-0">
          <Markdown text={s.body} className="prose-site" />
          {s.scope?.length > 0 && (
            <div className="mt-10">
              <h2 className="text-[22px] font-extrabold">What's included</h2>
              <ul className="mt-4 grid gap-x-8 gap-y-2.5 sm:grid-cols-2">
                {s.scope.map((x, n) => <li key={n} className="flex gap-2.5 text-[16px]"><Check className="mt-0.5 h-4 w-4 shrink-0 text-good" />{x.item || x}</li>)}
              </ul>
            </div>
          )}
          {s.standards?.length > 0 && (
            <div className="mt-10">
              <h2 className="text-[22px] font-extrabold">Standards we work to</h2>
              <dl className="mt-4 divide-y divide-line border-y border-line">
                {s.standards.map((x, n) => (
                  <div key={n} className="grid grid-cols-[140px_1fr] gap-4 py-2.5 text-[16px]"><dt className="font-semibold tabular">{x.code}</dt><dd className="text-muted">{x.title}</dd></div>
                ))}
              </dl>
            </div>
          )}
          {tools.length > 0 && (
            <div className="mt-10 rounded-xl bg-ink p-6 text-white">
              <h2 className="text-[19px] font-extrabold text-white">Check the numbers first</h2>
              <ul className="mt-3 space-y-2">
                {tools.map((t) => <li key={t.slug}><Link to={`/tools/${t.slug}`} className="inline-flex items-center gap-2 text-[16px] text-white hover:text-signal-bright"><Icon name={t.icon} className="h-4 w-4 text-signal-bright" />{t.title}</Link></li>)}
              </ul>
            </div>
          )}
          {s.faqs?.length > 0 && <div className="mt-10"><h2 className="mb-4 text-[22px] font-extrabold">Questions we get asked</h2><Faqs items={s.faqs} /></div>}
        </div>
        <div><EnquiryAside form="service_enquiry" extra={{ service: s.service_key }} files /></div>
      </div>
      {data.projects?.length > 0 && (
        <Section tone="paper" title="Recent work like this" action={<Button as={Link} to={`/projects?service=${s.service_key}`} variant="outline">More projects</Button>}>
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">{data.projects.slice(0, 3).map((p) => <ProjectCard key={p.slug} p={p} />)}</div>
        </Section>
      )}
    </>
  );
}

const TOOLS_FOR = {
  ht_substation: ["lt-vs-ht", "transformer-sizing", "ht-connection-roadmap", "fault-level"], transformers: ["transformer-sizing", "transformer-losses"],
  ht_lt_panels: ["breaker-selector", "pf-correction", "fault-level"], lt_electrification: ["connected-load", "cable-size", "voltage-drop"],
  cabling: ["cable-size", "voltage-drop"], earthing_lps: ["earthing", "lightning-risk"], dg_ups: ["dg-sizing", "ups-battery"],
  street_lighting: ["lighting-lux"], solar_epc: ["solar-rooftop"], ev_charging: ["ev-charger-load"], liaison: ["ht-connection-roadmap", "document-checklists"],
  testing: ["earthing", "transformer-losses"], amc: ["pf-correction", "harmonics"], energy_audit: ["energy-savings", "pf-correction", "bill-estimator", "harmonics"],
};

// ------------------------------------------------------------------ industries
export function IndustriesPage() {
  const { data, loading } = useGet("/public/industries");
  useMeta({ title: "Industries", description: "Electrical work planned around how factories, hospitals, commercial buildings, campuses, residential towers and infrastructure run." });
  return (
    <>
      <PageHero title="Built around how your site runs" text="Every sector has its own constraints: shutdown windows, standby power, approvals, inspections. We plan for them from the first survey." crumbs={[["/", "Home"], [null, "Industries"]]} />
      <Section>
        {loading ? <Skeleton className="h-64" /> : (
          <div className="grid gap-px overflow-hidden rounded-xl border border-line bg-line md:grid-cols-2">
            {(data || []).map((x) => (
              <Link key={x.slug} to={`/industries/${x.slug}`} className="group bg-white p-6 hover:bg-paper">
                <h2 className="font-display text-[19px] font-extrabold">{x.name}</h2>
                <p className="mt-2 text-[16px] leading-relaxed text-muted">{x.summary}</p>
                {x.needs?.length > 0 && <ul className="mt-4 space-y-1.5">{x.needs.slice(0, 4).map((n, i) => <li key={i} className="flex gap-2 text-sm"><Check className="mt-0.5 h-4 w-4 shrink-0 text-good" />{n.item || n}</li>)}</ul>}
              </Link>
            ))}
          </div>
        )}
      </Section>
    </>
  );
}

export function IndustryDetail() {
  const { slug } = useParams();
  const { data, error, loading } = useGet(`/public/industries/${slug}`);
  const s = data?.industry;
  useMeta({ title: s?.name, description: s?.summary });
  if (loading) return <PageLoading />;
  if (error || !s) return <NotFound />;
  return (
    <>
      <PageHero title={s.name} text={s.summary} crumbs={[["/", "Home"], ["/industries", "Industries"], [null, s.name]]} />
      <div className="container grid gap-12 py-14 lg:grid-cols-[1fr_380px]">
        <div>
          {s.body && <Markdown text={s.body} className="prose-site mb-10" />}
          {s.needs?.length > 0 && (
            <>
              <h2 className="text-[22px] font-extrabold">What matters on these sites</h2>
              <ul className="mt-4 space-y-3">{s.needs.map((n, i) => <li key={i} className="flex gap-3 text-[17px]"><span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-signal" />{n.item || n}</li>)}</ul>
            </>
          )}
          {data.projects?.length > 0 && (
            <div className="mt-12">
              <h2 className="text-[22px] font-extrabold">Projects in this sector</h2>
              <div className="mt-6 grid gap-8 sm:grid-cols-2">{data.projects.slice(0, 4).map((p) => <ProjectCard key={p.slug} p={p} />)}</div>
            </div>
          )}
        </div>
        <div><EnquiryAside form="sector_enquiry" extra={{ site_type: s.sector }} /></div>
      </div>
    </>
  );
}

// ------------------------------------------------------------------ products
export function ProductsPage() {
  const site = useSite();
  const { data, loading } = useGet("/public/products");
  const [ask, setAsk] = useState(null);
  const [cat, setCat] = useState("");
  useMeta({ title: "Products", description: "HT and LT panels, transformers, cables, switchgear, APFC, earthing, lighting, EV chargers and DG sets we supply and install." });
  const cats = useMemo(() => (site.options?.product_cats || []).filter((c) => (data || []).some((p) => p.category === c.value)), [site, data]);
  const rows = (data || []).filter((p) => !cat || p.category === cat);
  return (
    <>
      <PageHero title="Equipment we supply and install" text="From approved makes, tested before dispatch, installed by our own teams and supported after handover. Ask for a price with your quantities and we'll send a quote." crumbs={[["/", "Home"], [null, "Products"]]} />
      <Section>
        <div className="mb-6 flex flex-wrap gap-2" role="group" aria-label="Filter by category">
          {[{ value: "", label: "All" }, ...cats].map((c) => (
            <button key={c.value} type="button" onClick={() => setCat(c.value)} aria-pressed={cat === c.value}
              className={cn("rounded-full border px-3.5 py-1.5 text-sm", cat === c.value ? "border-ink bg-ink text-white" : "border-line hover:border-fg/30")}>{c.label}</button>
          ))}
        </div>
        {loading ? <Skeleton className="h-64" /> : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {rows.map((p) => (
              <article key={p.slug} className="flex flex-col rounded-xl border border-line bg-white">
                <Cover file={p.image} service={CAT_ILL[p.category]} className="aspect-[16/9] rounded-t-xl" />
                <div className="flex flex-1 flex-col p-5">
                  <p className="text-xs text-muted">{optLabel(site, "product_cats", p.category)}</p>
                  <h2 className="mt-1 font-display text-[17px] font-bold leading-snug">{p.name}</h2>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted">{p.summary}</p>
                  {p.specs?.length > 0 && (
                    <dl className="mt-4 divide-y divide-line border-y border-line text-sm">
                      {p.specs.map((x, i) => <div key={i} className="flex justify-between gap-4 py-1.5"><dt className="text-muted">{x.label}</dt><dd className="text-end font-medium">{x.value}</dd></div>)}
                    </dl>
                  )}
                  <div className="mt-auto pt-4"><Button variant="outline" size="sm" onClick={() => setAsk(p)}>Ask for a price</Button></div>
                </div>
              </article>
            ))}
          </div>
        )}
      </Section>
      <Dialog open={!!ask} onOpenChange={(v) => !v && setAsk(null)} title={ask ? `Price for ${ask.name}` : ""} description="Quantities and ratings help us quote quickly.">
        {ask && <LeadForm form="product_enquiry" extra={{ product: ask.name }} compact fields={["company", "town", "message"]} messageLabel="Rating, quantity, delivery location" submitLabel="Ask for a price" />}
      </Dialog>
    </>
  );
}
const CAT_ILL = { panels: "ht_lt_panels", transformers: "transformers", cables: "cabling", switchgear: "ht_lt_panels", lighting: "street_lighting", earthing: "earthing_lps", ev_chargers: "ev_charging", solar: "solar_epc", apfc: "ht_lt_panels", dg_ups: "dg_ups" };

// ------------------------------------------------------------------ clients
export function ClientsPage() {
  const { data, loading } = useGet("/public/clients");
  const site = useSite();
  useMeta({ title: "Clients", description: "Factories, hospitals, colleges, builders and public bodies we work for across Tamil Nadu." });
  const bySector = useMemo(() => {
    const m = {};
    (data?.clients || []).forEach((c) => { (m[c.sector || "other"] = m[c.sector || "other"] || []).push(c); });
    return Object.entries(m);
  }, [data]);
  return (
    <>
      <PageHero title="Who we work for" text="Names appear here only with the client's permission." crumbs={[["/", "Home"], [null, "Clients"]]} />
      <Section>
        {loading ? <Skeleton className="h-64" /> : (
          <div className="space-y-10">
            {bySector.map(([sector, list]) => (
              <div key={sector} className="grid gap-4 md:grid-cols-[220px_1fr]">
                <h2 className="font-display text-[17px] font-bold">{optLabel(site, "sectors", sector)}</h2>
                <ul className="grid grid-cols-1 gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
                  {list.map((c) => (
                    <li key={c.id} className="bg-white px-4 py-3.5">
                      {fileUrl(c.logo) ? <img src={fileUrl(c.logo)} alt={c.name} className="h-8 w-auto" /> : <span className="font-display text-[16px] font-bold">{c.name}</span>}
                      {c.town && <span className="mt-0.5 block text-xs text-muted">{c.town}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </Section>
      {data?.testimonials?.length > 0 && (
        <Section tone="paper" title="In their words">
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {data.testimonials.map((t) => (
              <figure key={t.id} className="flex flex-col rounded-xl bg-white p-6 ring-1 ring-line">
                <Quote className="h-6 w-6 text-signal-deep" aria-hidden />
                <blockquote className="mt-3 flex-1 text-[17px] leading-relaxed">{t.quote}</blockquote>
                <figcaption className="mt-4 text-sm"><span className="font-semibold">{t.person}</span>{t.designation ? `, ${t.designation}` : ""}<span className="block text-muted">{t.company}{t.sample ? " (sample)" : ""}</span></figcaption>
              </figure>
            ))}
          </div>
        </Section>
      )}
    </>
  );
}

// ------------------------------------------------------------------ gallery
export function GalleryPage() {
  const site = useSite();
  const [cat, setCat] = useState("");
  const { data, loading } = useGet(`/public/gallery${cat ? `?category=${cat}` : ""}`, [cat]);
  const [open, setOpen] = useState(null);
  useMeta({ title: "Gallery", description: "Substations, panels, cabling, solar and testing work from our sites." });
  return (
    <>
      <PageHero title="From our sites" text="Work in progress and finished installations." crumbs={[["/", "Home"], [null, "Gallery"]]} />
      <Section>
        <div className="mb-6 flex flex-wrap gap-2" role="group" aria-label="Filter photos">
          {[{ value: "", label: "All" }, ...(site.options?.gallery_cats || [])].map((c) => (
            <button key={c.value} type="button" onClick={() => setCat(c.value)} aria-pressed={cat === c.value}
              className={cn("rounded-full border px-3.5 py-1.5 text-sm", cat === c.value ? "border-ink bg-ink text-white" : "border-line hover:border-fg/30")}>{c.label}</button>
          ))}
        </div>
        {loading ? <Skeleton className="h-64" /> : !data?.length ? <p className="text-muted">No photos in this category yet.</p> : (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
            {data.map((g) => (
              <button key={g.id} type="button" onClick={() => setOpen(g)} className="group relative overflow-hidden rounded-lg text-start">
                <img src={fileUrl(g.image) || illustrationFor()} alt={g.title} loading="lazy" className="aspect-square w-full bg-ink object-cover transition-transform duration-300 group-hover:scale-[1.03]" />
                <span className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink/85 to-transparent p-3 pt-8 text-sm font-medium text-white">{g.title}</span>
                {g.sample && <span className="absolute start-2 top-2 rounded bg-ink/80 px-1.5 py-0.5 text-[11px] text-white/85">Illustration</span>}
              </button>
            ))}
          </div>
        )}
      </Section>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/95 p-4" role="dialog" aria-modal="true" aria-label={open.title} onClick={() => setOpen(null)}>
          <button type="button" className="absolute end-4 top-4 rounded-md p-2 text-white" aria-label="Close" onClick={() => setOpen(null)}><X className="h-6 w-6" /></button>
          <figure className="max-h-full max-w-5xl" onClick={(e) => e.stopPropagation()}>
            <img src={fileUrl(open.image) || illustrationFor()} alt={open.title} className="max-h-[80vh] w-auto rounded-lg" />
            <figcaption className="mt-3 text-center text-white">{open.title}{open.taken_on ? <span className="text-white/75">, {fmtDate(open.taken_on)}</span> : null}</figcaption>
          </figure>
        </div>
      )}
    </>
  );
}

// ------------------------------------------------------------------ about
export function AboutPage() {
  const site = useSite();
  const s = site.settings || {};
  useMeta({ title: "About us", description: s.about?.story?.slice(0, 160) });
  return (
    <>
      <PageHero title="One team from survey to switch-on" text={s.about?.mission} crumbs={[["/", "Home"], [null, "About"]]} />
      <Section>
        <div className="grid gap-12 lg:grid-cols-[1.2fr_1fr]">
          <div>
            <h2 className="text-[26px] font-extrabold">Our story</h2>
            <p className="mt-4 max-w-[64ch] text-[17px] leading-8 text-fg/85">{s.about?.story}</p>
            {s.about?.vision && <p className="mt-4 max-w-[64ch] text-[17px] leading-8 text-fg/85">{s.about.vision}</p>}
          </div>
          {(s.values || []).length > 0 && (
            <div className="rounded-xl bg-paper p-6">
              <h2 className="text-[19px] font-extrabold">How we work</h2>
              <dl className="mt-4 space-y-4">
                {s.values.map((v) => <div key={v.title}><dt className="font-display font-bold">{v.title}</dt><dd className="mt-0.5 text-sm leading-relaxed text-muted">{v.text}</dd></div>)}
              </dl>
            </div>
          )}
        </div>
      </Section>
      {(s.leadership || []).length > 0 && (
        <Section tone="paper" title="Leadership">
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {s.leadership.map((p) => (
              <div key={p.name} className="rounded-xl bg-white p-5 ring-1 ring-line">
                <p className="font-display text-[17px] font-bold">{p.name}</p><p className="text-sm text-muted">{p.role}</p>
                {p.bio && <p className="mt-2 text-sm leading-relaxed">{p.bio}</p>}
              </div>
            ))}
          </div>
        </Section>
      )}
      {(s.group_companies || []).length > 0 && (
        <Section tone="ink" title="Part of the Sellandiamman Group" text="Shared supply chain, local presence and a long relationship with the region.">
          <div className="grid gap-px overflow-hidden rounded-xl bg-white/10 md:grid-cols-3">
            {s.group_companies.map((g) => (
              <div key={g.name} className="bg-ink p-6">
                <p className="font-display text-[17px] font-bold text-white">{g.name}</p>
                <p className="mt-1 text-sm text-white/75">{g.text}</p>
                {g.url && <a href={g.url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-signal-bright hover:underline">Visit website<ArrowUpRight className="rtl:-scale-x-100 h-3.5 w-3.5" /></a>}
              </div>
            ))}
          </div>
        </Section>
      )}
      <Section title="Where to find us">
        <Branches />
      </Section>
    </>
  );
}

export function Branches() {
  const site = useSite();
  return (
    <div className="grid gap-6 md:grid-cols-3">
      {site.branches.map((b) => (
        <div key={b.id} className="rounded-xl border border-line p-5">
          <p className="font-display text-[17px] font-bold">{b.name}</p>
          {b.is_head_office && <p className="text-xs font-medium text-signal-ink">Head office</p>}
          <ul className="mt-3 space-y-2 text-sm">
            {b.address && <li className="flex gap-2"><MapPin className="mt-0.5 h-4 w-4 shrink-0 text-muted" />{b.address}</li>}
            {b.phone && <li className="flex gap-2"><Phone className="mt-0.5 h-4 w-4 shrink-0 text-muted" /><a href={telLink(b.phone)} dir="ltr" className="hover:underline">{b.phone}</a></li>}
            {b.email && <li className="flex gap-2"><Mail className="mt-0.5 h-4 w-4 shrink-0 text-muted" /><a href={`mailto:${b.email}`} className="hover:underline">{b.email}</a></li>}
            {b.hours && <li className="flex gap-2"><Clock className="mt-0.5 h-4 w-4 shrink-0 text-muted" />{b.hours}</li>}
          </ul>
          {(b.map_url || (b.lat && b.lng)) && (
            <a href={b.map_url || `https://www.google.com/maps/search/?api=1&query=${b.lat},${b.lng}`} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-cable hover:underline">Directions<ArrowUpRight className="rtl:-scale-x-100 h-3.5 w-3.5" /></a>
          )}
        </div>
      ))}
    </div>
  );
}

// ------------------------------------------------------------------ safety & quality
export function SafetyQualityPage() {
  const site = useSite();
  const s = site.settings?.safety || {};
  useMeta({ title: "Safety & quality", description: "Permit to work, lock-out / tag-out, authorised persons for HT, toolbox talks, inspection and test plans and calibrated instruments." });
  const SAFE = ["Risk assessment and method statement for every job", "Permit to work, with a different person approving", "Lock-out / tag-out and tested-dead before touch",
    "Earthing on both sides of the work", "An authorised person for every HT activity", "Toolbox talk at the start of every shift", "Near-misses reported and investigated"];
  const QUAL = ["Inspection and test plan agreed before work starts", "Material inspection on receipt, with test certificates", "Hold points for client and consultant witness",
    "Instruments calibrated, with certificates on file", "Non-conformances closed with root cause", "Test reports and as-built drawings at handover"];
  return (
    <>
      <PageHero title="Safe work is planned work" text={s.policy} crumbs={[["/", "Home"], [null, "Safety & quality"]]} />
      <Section>
        <div className="grid gap-10 md:grid-cols-2">
          <div>
            <h2 className="flex items-center gap-2 text-[22px] font-extrabold"><ShieldCheck className="h-6 w-6 text-good" />On every site</h2>
            <ul className="mt-5 space-y-3">{SAFE.map((x) => <li key={x} className="flex gap-3 text-[16.5px]"><Check className="mt-0.5 h-4 w-4 shrink-0 text-good" />{x}</li>)}</ul>
          </div>
          <div>
            <h2 className="flex items-center gap-2 text-[22px] font-extrabold"><ClipboardCheck className="h-6 w-6 text-cable" />Quality you can check</h2>
            <p className="mt-3 text-[16.5px] leading-relaxed text-muted">{s.quality}</p>
            <ul className="mt-5 space-y-3">{QUAL.map((x) => <li key={x} className="flex gap-3 text-[16.5px]"><Check className="mt-0.5 h-4 w-4 shrink-0 text-good" />{x}</li>)}</ul>
          </div>
        </div>
      </Section>
      {(site.settings?.certifications || site.settings?.licences || []).length > 0 && (
        <Section tone="paper" title="Licences and certifications">
          <ul className="grid gap-3 sm:grid-cols-2">{(site.settings.certifications || site.settings.licences).map((c, i) => <li key={i} className="rounded-lg bg-white p-4 ring-1 ring-line">{c.name || c}{c.number ? <span className="block text-sm text-muted">{c.number}</span> : null}</li>)}</ul>
        </Section>
      )}
    </>
  );
}

// ------------------------------------------------------------------ AMC
export function AmcPage() {
  const site = useSite();
  const plans = site.settings?.amc_plans || [];
  useT(); // re-render plan names when the language changes
  useMeta({ title: "AMC & maintenance", description: "Annual maintenance contracts for substations, transformers and panels: planned visits, oil tests, thermography and fast breakdown response." });
  return (
    <>
      <PageHero title="Keep it running after handover" text="Planned maintenance catches loose joints, weak oil and failing relays before they trip your plant. Every visit ends with a report in your client portal." crumbs={[["/", "Home"], [null, "AMC & maintenance"]]}>
        <Button as={Link} to="/emergency" variant="light">Breakdown now? Get help</Button>
      </PageHero>
      <Section title="Pick a level of cover" text="We also maintain installations we didn't build, after a first condition survey.">
        <div className="grid gap-6 md:grid-cols-3">
          {plans.map((p, n) => (
            <div key={p.name} className={cn("flex flex-col rounded-xl p-6", n === 1 ? "bg-ink text-white" : "border border-line bg-white")}>
              <h2 data-no-translate className={cn("text-[22px] font-extrabold", n === 1 && "text-white")}>{translateIn("plan", p.name)}</h2>
              <p className={cn("mt-1 text-sm", n === 1 ? "text-white/75" : "text-muted")}>{p.for}</p>
              <dl className={cn("mt-5 space-y-2 border-y py-4 text-sm", n === 1 ? "border-white/15" : "border-line")}>
                <div className="flex justify-between gap-3"><dt className={n === 1 ? "text-white/75" : "text-muted"}>Visits</dt><dd className="text-end font-semibold">{p.visits}</dd></div>
                <div className="flex justify-between gap-3"><dt className={n === 1 ? "text-white/75" : "text-muted"}>Breakdown response</dt><dd className="text-end font-semibold">{p.response}</dd></div>
              </dl>
              <ul className="mt-5 flex-1 space-y-2.5">{(p.items || []).map((x) => <li key={x} className="flex gap-2.5 text-sm"><Check className={cn("mt-0.5 h-4 w-4 shrink-0", n === 1 ? "text-signal-bright" : "text-good")} />{x}</li>)}</ul>
            </div>
          ))}
        </div>
      </Section>
      <Section tone="paper">
        <div className="grid gap-10 lg:grid-cols-[1fr_440px]">
          <div>
            <h2 className="text-[26px] font-extrabold">Get an AMC quote</h2>
            <p className="mt-3 max-w-xl text-[17px] leading-relaxed text-muted">List the equipment you want covered (transformers, HT panels, LT panels, DG, APFC) and the town. We'll visit, check the condition and send a fixed yearly price.</p>
          </div>
          <div className="rounded-xl bg-white p-5 ring-1 ring-line"><LeadForm form="amc_enquiry" extra={{ service: "amc" }} fields={["company", "town", "message"]} messageLabel="Equipment to cover" submitLabel="Ask for an AMC quote" compact /></div>
        </div>
      </Section>
    </>
  );
}

// ------------------------------------------------------------------ town pages
export function TownPage() {
  const { slug } = useParams();
  const { data, error, loading } = useGet(`/public/towns/${slug}`);
  const site = useSite();
  const t = data?.town;
  useMeta({ title: t && `Electrical contractors in ${t.town}`, description: t?.intro });
  if (loading) return <PageLoading />;
  if (error || !t) return <NotFound />;
  const br = site.branches.find((b) => (b.city || "").toLowerCase() === t.town.toLowerCase());
  return (
    <>
      <PageHero title={`Electrical contractors in ${t.town}`} text={t.intro} crumbs={[["/", "Home"], [null, t.town]]}>
        <div className="flex flex-wrap gap-3"><Button as={Link} to="/get-quote">Get a quote</Button><Button as={Link} to="/book-survey" variant="light">Book a site survey</Button></div>
      </PageHero>
      {t.body && <Section><Markdown text={t.body} className="prose-site" /></Section>}
      <Section tone={t.body ? "paper" : "white"} title={`Our work in and around ${t.town}`}>
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">{data.projects.map((p) => <ProjectCard key={p.slug} p={p} />)}</div>
      </Section>
      {br && <Section title="Visit us"><div className="max-w-md"><Branches /></div></Section>}
    </>
  );
}

// ------------------------------------------------------------------ legal & 404
const LEGAL = {
  privacy: {
    title: "Privacy notice",
    body: `## What we collect\n\nWhen you send an enquiry, book a survey, use a calculator report or apply for a job, we keep your name, phone number, email (if given), company, town, what you asked about and any files you attach. We also record which page you came from and campaign tags in the link (for example utm_source), so we know which advertising works.\n\n## Why we use it\n\nTo reply to your enquiry, prepare quotations, run your project or service contract, and send the updates you asked for. We don't sell your details.\n\n## Who sees it\n\nOur staff who handle your enquiry or project, and service providers who run our email, WhatsApp and hosting, under confidentiality.\n\n## How long we keep it\n\nEnquiries that don't become projects are kept for up to three years. Project records are kept as long as the law requires for contracts and tax.\n\n## Your choices\n\nYou can ask to see, correct or delete your details, or stop messages, by writing to us at the email on the contact page. This follows the Digital Personal Data Protection Act, 2023.`,
  },
  terms: {
    title: "Terms of use",
    body: `## The website\n\nThe information and calculators on this website are for general guidance. Calculator results are estimates; final designs must be done and signed by a licensed electrical engineer.\n\n## Quotations\n\nPrices are given only in a written quotation, which states its own validity, scope and terms.\n\n## Client portal\n\nKeep your login private. You're responsible for approvals given from your account.\n\n## Contact\n\nQuestions about these terms: write to us at the email on the contact page.`,
  },
  cookies: {
    title: "Cookies",
    body: `## What we use\n\nThis site uses a few small files in your browser: one to keep you signed in to the portal, one to remember your language, and one to remember which link or campaign brought you here so your enquiry reaches the right team.\n\n## Analytics\n\nIf analytics is switched on, it counts visits to pages without identifying you.\n\n## Your choice\n\nYou can clear these files in your browser settings at any time; the site still works, but you'll need to sign in again.`,
  },
};

export function LegalPage({ kind }) {
  const d = LEGAL[kind];
  useMeta({ title: d.title });
  return (
    <>
      <PageHero title={d.title} dark={false} crumbs={[["/", "Home"], [null, d.title]]} />
      <Section><Markdown text={d.body} className="prose-site" /></Section>
    </>
  );
}

export function NotFound() {
  useMeta({ title: "Page not found", noindex: true });
  return (
    <section className="container flex min-h-[55vh] flex-col items-start justify-center py-16">
      <p className="font-display text-[64px] font-extrabold leading-none text-steel">404</p>
      <h1 className="mt-4 text-[30px] font-extrabold">This page isn't connected</h1>
      <p className="mt-2 max-w-md text-muted">The link may be old, or the page has moved. Try the services list, or tell us what you were looking for.</p>
      <div className="mt-6 flex flex-wrap gap-3"><Button as={Link} to="/">Go to the home page</Button><Button as={Link} to="/contact" variant="outline">Contact us</Button></div>
    </section>
  );
}
