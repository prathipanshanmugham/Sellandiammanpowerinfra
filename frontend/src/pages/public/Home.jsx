import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Phone, Quote } from "lucide-react";
import { api } from "@/lib/api";
import { useMeta, cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";
import { telLink, fmtDate } from "@/lib/format";
import { Button } from "@/components/ui/kit";
import { useSite } from "@/components/public/site";
import { Section, Icon } from "@/components/public/Layout";
import { ProjectCard } from "@/components/public/bits";
import { CallbackButton } from "@/components/public/forms";
import SLD from "@/components/public/SLD";

function Hero() {
  const site = useSite();
  const t = useT();
  const h = site.settings?.hero || {};
  const phone = site.settings?.phone;
  return (
    <section className="relative overflow-hidden bg-ink text-white">
      <div className="container grid items-center gap-10 py-14 md:py-20 lg:grid-cols-[1.05fr_1fr] lg:gap-14">
        <div>
          {h.eyebrow && <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/15 px-3 py-1 text-[14px] text-white/85"><span className="h-1.5 w-1.5 rounded-full bg-signal" />{h.eyebrow}</p>}
          <h1 className="hero-title font-display text-[40px] font-extrabold leading-[1.02] text-white sm:text-[52px] lg:text-[60px]" style={{ letterSpacing: "-0.035em" }}>
            {h.title || "Power infrastructure, engineered and energised."}
          </h1>
          <p className="mt-6 max-w-xl text-[17px] leading-relaxed text-white/80">{h.text}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button as={Link} to="/get-quote" size="lg">{t("Get a quote")}</Button>
            <Button as={Link} to="/book-survey" size="lg" variant="light">{t("Book a site survey")}</Button>
          </div>
          {phone && <p className="mt-6 text-sm text-white/70">Prefer to talk? <a href={telLink(phone)} dir="ltr" className="font-medium text-white underline decoration-signal underline-offset-4">{phone}</a></p>}
        </div>
        <div className="relative mx-auto w-full max-w-[520px]">
          <SLD className="h-auto w-full" />
        </div>
      </div>
    </section>
  );
}

function Trust() {
  const site = useSite();
  const items = site.settings?.trust || [];
  if (!items.length) return null;
  return (
    <div className="border-b border-line bg-white">
      <div className="container grid grid-cols-2 divide-line md:grid-cols-4 md:divide-x md:rtl:divide-x-reverse">
        {items.map((x) => (
          <div key={x.label} className="py-6 md:px-6 md:first:ps-0">
            <p dir="ltr" className="font-display text-[26px] font-extrabold leading-none tracking-tight rtl:text-right">{x.value}</p>
            <p className="mt-2 text-sm text-muted">{x.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function Services() {
  const site = useSite();
  const t = useT();
  return (
    <Section title="What we build and look after" text="One accountable team from the first site survey to approvals, energisation and maintenance."
      action={<Button as={Link} to="/services" variant="outline">{t("All services")}</Button>}>
      <ul className="grid border-t border-line md:grid-cols-2 md:gap-x-10">
        {site.services.map((s, n) => (
          <li key={s.slug} className={cn("border-b border-line", n >= 8 && "hidden md:block")}>
            <Link to={`/services/${s.slug}`} className="group flex items-start gap-4 py-4">
              <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-ink text-signal-bright"><Icon name={s.icon} className="h-[18px] w-[18px]" /></span>
              <span className="min-w-0 flex-1">
                <span className="block font-display text-[17px] font-bold leading-snug">{s.title}</span>
                <span className="mt-0.5 block text-sm leading-relaxed text-muted">{s.summary}</span>
              </span>
              <ArrowRight className="rtl:-scale-x-100 mt-2 h-4 w-4 shrink-0 text-steel transition-transform group-hover:translate-x-0.5 group-hover:text-fg" aria-hidden />
            </Link>
          </li>
        ))}
      </ul>
    </Section>
  );
}

function Sectors({ industries }) {
  if (!industries.length) return null;
  return (
    <Section tone="paper" title="Built for how your site runs" text="A hospital can't go dark for a shutdown; a spinning mill can't trip at peak. We plan the work around your operation.">
      <div className="grid gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
        {industries.slice(0, 8).map((x) => (
          <Link key={x.slug} to={`/industries/${x.slug}`} className="group bg-white p-5 hover:bg-paper">
            <h3 className="font-display text-[17px] font-bold">{x.name}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">{x.summary}</p>
            <span className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-cable">How we help<ArrowRight className="rtl:-scale-x-100 h-3.5 w-3.5" /></span>
          </Link>
        ))}
        {Math.min(industries.length, 8) % 4 !== 0 && (
          <Link to="/contact" className="group flex flex-col bg-ink p-5 text-white hover:bg-ink-800">
            <h3 className="font-display text-[17px] font-bold text-white">Something else?</h3>
            <p className="mt-2 text-sm leading-relaxed text-white/75">Quarries, temples, data rooms, cold chains: tell us how your site runs and we'll plan around it.</p>
            <span className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-signal-bright">Talk to an engineer<ArrowRight className="rtl:-scale-x-100 h-3.5 w-3.5" /></span>
          </Link>
        )}
      </div>
    </Section>
  );
}

function Projects({ projects }) {
  const t = useT();
  if (!projects.length) return null;
  const [a, b, ...rest] = projects;
  return (
    <Section title="Recent work" text="Substations, conversions and upgrades delivered across Tamil Nadu." action={<Button as={Link} to="/projects" variant="outline">{t("See all projects")}</Button>}>
      <div className="grid gap-8 md:grid-cols-2">
        {[a, b].filter(Boolean).map((p) => <ProjectCard key={p.slug} p={p} big />)}
      </div>
      {rest.length > 0 && <div className="mt-10 hidden gap-8 sm:grid sm:grid-cols-2 lg:grid-cols-4">{rest.slice(0, 4).map((p) => <ProjectCard key={p.slug} p={p} />)}</div>}
    </Section>
  );
}

function Clients({ data }) {
  if (!data || (!data.clients.length && !data.testimonials.length)) return null;
  const tm = data.testimonials[0];
  return (
    <Section tone="paper" title="Trusted by plants, hospitals and builders" action={<Button as={Link} to="/clients" variant="outline">All clients</Button>}>
      <div className="grid gap-10 lg:grid-cols-[1.4fr_1fr]">
        <ul className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-3">
          {data.clients.slice(0, 9).map((c) => (
            <li key={c.id} className="flex min-h-[84px] items-center bg-white px-4 py-3">
              <span className="font-display text-[15px] font-bold leading-tight text-fg/80">{c.name}</span>
            </li>
          ))}
        </ul>
        {tm && (
          <figure className="rounded-lg bg-ink p-7 text-white">
            <Quote className="h-7 w-7 text-signal-bright" aria-hidden />
            <blockquote className="mt-4 text-[18px] leading-relaxed">{tm.quote}</blockquote>
            <figcaption className="mt-5 text-sm text-white/75">{tm.person}, {tm.company}{tm.sample ? " (sample)" : ""}</figcaption>
          </figure>
        )}
      </div>
    </Section>
  );
}

function Tools() {
  const site = useSite();
  const pick = ["connected-load", "lt-vs-ht", "contract-demand", "cable-size", "pf-correction", "solar-rooftop"];
  const tools = pick.map((s) => site.tools.find((t) => t.slug === s)).filter(Boolean);
  return (
    <Section tone="ink" title="Work it out before you call" text={`${site.tools.length || 24} free calculators for LT and HT customers — each shows its working and the standard it follows.`}
      action={<Button as={Link} to="/tools" variant="primary">All calculators</Button>}>
      <div className="grid gap-px overflow-hidden rounded-lg bg-white/10 sm:grid-cols-2 lg:grid-cols-3">
        {tools.map((t) => (
          <Link key={t.slug} to={`/tools/${t.slug}`} className="group flex gap-4 bg-ink p-5 hover:bg-ink-800">
            <Icon name={t.icon} className="mt-0.5 h-5 w-5 shrink-0 text-signal-bright" />
            <span>
              <span className="block font-display text-[16px] font-bold text-white">{t.title}</span>
              <span className="mt-1 block text-sm leading-relaxed text-white/75">{t.summary}</span>
            </span>
          </Link>
        ))}
      </div>
    </Section>
  );
}

function Process() {
  const site = useSite();
  const steps = site.settings?.process || [];
  if (!steps.length) return null;
  return (
    <Section title="How a project runs" text="The same seven stages on every job, visible to you in the client portal.">
      <ol className="relative grid gap-6 md:grid-cols-7 md:gap-3">
        <span className="absolute start-[15px] top-2 h-[calc(100%-16px)] w-[2px] bg-line md:start-0 md:top-[15px] md:h-[2px] md:w-full" aria-hidden />
        {steps.map((s, n) => (
          <li key={s.step} className="relative flex gap-4 md:block">
            <span className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 border-ink bg-white font-display text-sm font-bold tabular">{n + 1}</span>
            <div className="md:mt-4">
              <p className="font-display text-[16px] font-bold">{s.step}</p>
              <p className="mt-1 text-sm leading-relaxed text-muted">{s.text}</p>
            </div>
          </li>
        ))}
      </ol>
    </Section>
  );
}

function Insights({ posts }) {
  if (!posts.length) return null;
  return (
    <Section tone="paper" title="From our engineers" action={<Button as={Link} to="/insights" variant="outline">All insights</Button>}>
      <div className="grid gap-6 md:grid-cols-3">
        {posts.slice(0, 3).map((p) => (
          <Link key={p.slug} to={`/insights/${p.slug}`} className="group rounded-lg border border-line bg-white p-6 hover:border-fg/25">
            <p className="text-xs text-muted">{fmtDate(p.publish_at)}</p>
            <h3 className="mt-2 font-display text-[17px] font-bold leading-snug group-hover:underline group-hover:decoration-signal group-hover:underline-offset-4">{p.title}</h3>
            <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-muted">{p.excerpt}</p>
          </Link>
        ))}
      </div>
    </Section>
  );
}

function CTA() {
  const t = useT();
  const site = useSite();
  return (
    <section className="bg-signal">
      <div className="container flex flex-col items-start justify-between gap-6 py-12 md:flex-row md:items-center">
        <div>
          <h2 className="text-[26px] font-extrabold leading-tight text-white md:text-[32px]" style={{ letterSpacing: "-0.02em" }}>Planning a substation, upgrade or AMC?</h2>
          <p className="mt-2 max-w-xl text-white/90">Tell us what you need. An engineer calls you back, usually the same working day.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button as={Link} to="/get-quote" variant="dark" size="lg">{t("Get a quote")}</Button>
          {site.settings?.phone ? <Button as="a" href={telLink(site.settings.phone)} dir="ltr" variant="outline" size="lg" className="border-white/40 bg-transparent text-white hover:bg-white/10"><Phone className="h-4 w-4" />{site.settings.phone}</Button> : <CallbackButton />}
        </div>
      </div>
    </section>
  );
}

export default function Home() {
  const [projects, setProjects] = useState([]);
  const [industries, setIndustries] = useState([]);
  const [clients, setClients] = useState(null);
  const [posts, setPosts] = useState([]);
  useMeta({ description: "HT substations, transformers, panels, cabling, earthing, solar and EV charging — designed, approved, built and maintained by Sellandiamman Power Infra across Tamil Nadu." });
  useEffect(() => {
    api.get("/public/projects", { params: { limit: 6 } }).then((r) => setProjects(r.data.items)).catch(() => {});
    api.get("/public/industries").then((r) => setIndustries(r.data)).catch(() => {});
    api.get("/public/clients").then((r) => setClients(r.data)).catch(() => {});
    api.get("/public/insights").then((r) => setPosts(r.data)).catch(() => {});
  }, []);
  return (
    <>
      <Hero />
      <Trust />
      <Services />
      <Sectors industries={industries} />
      <Projects projects={projects} />
      <Clients data={clients} />
      <Tools />
      <Process />
      <Insights posts={posts} />
      <CTA />
    </>
  );
}
