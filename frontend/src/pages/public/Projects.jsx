import { useMemo } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { Quote, MapPin, CalendarDays } from "lucide-react";
import { fileUrl } from "@/lib/api";
import { useMeta, cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";
import { Button, Select, Skeleton } from "@/components/ui/kit";
import { useSite, optLabel } from "@/components/public/site";
import { PageHero, Section } from "@/components/public/Layout";
import { ProjectCard, Cover, Chip } from "@/components/public/bits";
import { LeadForm } from "@/components/public/forms";
import { useGet, PageLoading, NotFound } from "./Content";

const FILTERS = [["service", "Service", "services"], ["sector", "Sector", "sectors"], ["supply", "Supply", null], ["town", "Town", null], ["year", "Year", null]];

export function ProjectsPage() {
  const site = useSite();
  const t = useT();
  const [sp, setSp] = useSearchParams();
  const qs = sp.toString();
  const { data, loading } = useGet(`/public/projects${qs ? `?${qs}` : ""}`, [qs]);
  useMeta({ title: "Projects", description: "HT substations, LT to HT conversions, panels, cabling, solar and EV charging projects delivered across Tamil Nadu." });
  const facets = data?.facets || {};
  const set = (k, v) => { const n = new URLSearchParams(sp); if (v) n.set(k, v); else n.delete(k); setSp(n, { replace: true }); };
  const state = sp.get("state") || "";
  const active = FILTERS.some(([k]) => sp.get(k)) || state;
  return (
    <>
      <PageHero title="Projects" text="A selection of finished and ongoing work. Client names appear only with permission." crumbs={[["/", "Home"], [null, "Projects"]]} />
      <div className="sticky top-16 z-20 border-b border-line bg-white/95 backdrop-blur">
        <div className="container flex flex-wrap items-end gap-3 py-3">
          <div className="flex rounded-md border border-line p-0.5" role="group" aria-label="Status">
            {[["", "All"], ["completed", "Completed"], ["ongoing", "Ongoing"]].map(([v, l]) => (
              <button key={v} type="button" onClick={() => set("state", v)} aria-pressed={state === v}
                className={cn("rounded px-3 py-1.5 text-sm", state === v ? "bg-ink text-white" : "text-muted hover:text-fg")}>{l}</button>
            ))}
          </div>
          {FILTERS.map(([k, l, opt]) => (facets[k] || []).length > 1 && (
            <label key={k} className="w-[150px]">
              <span className="sr-only">{l}</span>
              <Select value={sp.get(k) || ""} onChange={(e) => set(k, e.target.value)} placeholder={`Any ${l.toLowerCase()}`}
                options={(facets[k] || []).map((v) => ({ value: v, label: opt ? optLabel(site, opt, v) : v }))} className="h-9" />
            </label>
          ))}
          {active && <Button variant="ghost" size="sm" onClick={() => setSp({}, { replace: true })}>Clear filters</Button>}
          {data && <p className="ms-auto self-center text-sm text-muted tabular">{data.items.length === 1 ? t("1 project") : t("{n} projects", { n: data.items.length })}</p>}
        </div>
      </div>
      <Section>
        {loading ? <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">{[1, 2, 3].map((n) => <Skeleton key={n} className="aspect-[4/3]" />)}</div> : !data?.items.length ? (
          <div className="py-10"><p className="font-semibold">No projects match these filters.</p><p className="mt-1 text-muted">Try fewer filters, or ask us — not every project is published.</p></div>
        ) : (
          <div className="grid gap-x-8 gap-y-12 sm:grid-cols-2 lg:grid-cols-3">{data.items.map((p) => <ProjectCard key={p.slug} p={p} />)}</div>
        )}
      </Section>
    </>
  );
}

export function ProjectDetail() {
  const { slug } = useParams();
  const site = useSite();
  const { data, error, loading } = useGet(`/public/projects/${slug}`);
  const p = data?.project;
  useMeta({ title: p?.title, description: p?.public_summary, image: p?.cover ? fileUrl(p.cover) : undefined });
  const photos = useMemo(() => [...(p?.photos || []), ...((data?.gallery || []).map((g) => g.image))].filter(Boolean), [p, data]);
  if (loading) return <PageLoading />;
  if (error || !p) return <NotFound />;
  const facts = [
    ["Service", optLabel(site, "services", p.service)], ["Sector", optLabel(site, "sectors", p.sector)], ["Supply", p.supply],
    ["Voltage", p.voltage?.replace("kV", " kV").replace("415V", "415 V")], ["Capacity", p.capacity_kva ? `${p.capacity_kva} kVA` : p.capacity_kw ? `${p.capacity_kw} kW` : null],
    ["Location", p.town], ["Year", p.year], ["Client", p.client],
  ].filter(([, v]) => v);
  return (
    <>
      <section className="bg-ink text-white">
        <div className="container grid gap-10 py-12 md:py-16 lg:grid-cols-[1fr_1.1fr] lg:items-center">
          <div>
            <nav aria-label="Breadcrumb" className="mb-4 text-sm text-white/70"><Link to="/" className="hover:underline">Home</Link><span className="mx-2">/</span><Link to="/projects" className="hover:underline">Projects</Link></nav>
            <div className="flex flex-wrap gap-1.5">{p.ongoing && <Chip dark>Ongoing</Chip>}{p.sample && <Chip dark>Sample project</Chip>}</div>
            <h1 className="mt-3 text-[30px] font-semibold leading-[1.1] text-white md:text-[42px]" style={{ letterSpacing: "-0.025em" }}>{p.title}</h1>
            <p className="mt-4 max-w-xl text-lg leading-relaxed text-white/80">{p.public_summary}</p>
            <p className="mt-5 flex flex-wrap gap-x-5 gap-y-1 text-sm text-white/75">
              {p.town && <span className="inline-flex items-center gap-1.5"><MapPin className="h-4 w-4" />{p.town}</span>}
              {p.year && <span className="inline-flex items-center gap-1.5"><CalendarDays className="h-4 w-4" />{p.year}</span>}
            </p>
          </div>
          <Cover file={p.cover} service={p.service} alt={p.title} className="aspect-[16/10] rounded-xl" />
        </div>
      </section>
      {(p.highlights || []).length > 0 && (
        <div className="border-b border-line bg-white">
          <dl className="container grid grid-cols-2 gap-6 py-7 md:grid-cols-4">
            {p.highlights.map((h) => <div key={h.label}><dt className="text-sm text-muted">{h.label}</dt><dd className="mt-1 font-display text-[24px] font-semibold leading-none tracking-tight">{h.value}</dd></div>)}
          </dl>
        </div>
      )}
      <div className="container grid gap-12 py-14 lg:grid-cols-[1fr_340px]">
        <div className="max-w-[68ch] space-y-9">
          {[["The challenge", p.challenge], ["What we did", p.solution], ["The result", p.results]].filter(([, v]) => v).map(([h, v]) => (
            <div key={h}><h2 className="text-[22px] font-semibold">{h}</h2><p className="mt-3 whitespace-pre-line text-[16.5px] leading-8 text-fg/85">{v}</p></div>
          ))}
          {data.testimonial && (
            <figure className="rounded-xl bg-paper p-6">
              <Quote className="h-6 w-6 text-signal-ink" aria-hidden />
              <blockquote className="mt-3 text-[18px] leading-relaxed">{data.testimonial.quote}</blockquote>
              <figcaption className="mt-4 text-sm text-muted">{data.testimonial.person}, {data.testimonial.company}{data.testimonial.sample ? " (sample)" : ""}</figcaption>
            </figure>
          )}
          {photos.length > 0 && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">{photos.map((f, i) => <img key={i} src={fileUrl(f)} alt="" loading="lazy" className="aspect-square w-full rounded-lg bg-ink object-cover" />)}</div>
          )}
        </div>
        <aside className="space-y-6">
          <dl className="divide-y divide-line rounded-xl border border-line text-sm">
            {facts.map(([k, v]) => <div key={k} className="flex justify-between gap-4 px-4 py-2.5"><dt className="text-muted">{k}</dt><dd className="text-end font-medium">{v}</dd></div>)}
          </dl>
          <div className="rounded-xl bg-ink p-5 text-white lg:sticky lg:top-24">
            <h2 className="text-[18px] font-semibold text-white">Need something similar?</h2>
            <p className="mb-4 mt-1 text-sm text-white/75">We'll look at your site and send a scope and price.</p>
            <div className="rounded-lg bg-white p-4 text-fg">
              <LeadForm form="similar_project" extra={{ service: p.service, message: `Similar to: ${p.title}` }} compact fields={["company", "town"]} submitLabel="Ask for a quote" />
            </div>
          </div>
        </aside>
      </div>
      {data.related?.length > 0 && (
        <Section tone="paper" title="More projects">
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">{data.related.map((r) => <ProjectCard key={r.slug} p={r} />)}</div>
        </Section>
      )}
      <div className="container py-10"><Button as={Link} to="/projects" variant="outline">Back to all projects</Button></div>
    </>
  );
}
