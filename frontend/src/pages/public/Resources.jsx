import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { FileText, Download, BookOpen } from "lucide-react";
import { api, errMsg, openFile } from "@/lib/api";
import { useMeta, cn } from "@/lib/utils";
import { fmtDate } from "@/lib/format";
import { Markdown } from "@/lib/markdown";
import { Button, Dialog, Input, Field, Alert, Skeleton, Checkbox } from "@/components/ui/kit";
import { PageHero, Section } from "@/components/public/Layout";
import { Consent, Honeypot, checkContact, useLeadForm, Done } from "@/components/public/forms";
import { tracking } from "@/lib/tracking";
import { useGet, PageLoading, NotFound, Faqs } from "./Content";

const FAQ_CATS = { general: "General", ht: "HT supply & substations", lt: "LT supply", ht_connection: "HT connections", lt_connection: "LT connections", approvals: "Approvals", solar: "Solar", amc: "Maintenance & AMC", billing: "Bills & tariffs", safety: "Safety", process: "How we work" };
const TAGS = { energy_audit: "Energy audits", ht_lt_panels: "Panels", liaison: "Approvals and liaison", testing: "Testing" };

export function ResourcesPage() {
  const dl = useGet("/public/downloads");
  const faqs = useGet("/public/faqs");
  const posts = useGet("/public/insights");
  useMeta({ title: "Guides & resources", description: "Guides to HT connections, CEIG approvals and maintenance, document checklists, FAQs and articles from our engineers." });
  const grouped = useMemo(() => {
    const m = {};
    (faqs.data || []).forEach((f) => { (m[f.category || "general"] = m[f.category || "general"] || []).push(f); });
    return Object.entries(m);
  }, [faqs.data]);
  return (
    <>
      <PageHero title="Guides and answers" text="Plain-language guides to supply, approvals and maintenance in Tamil Nadu, written by the engineers who do the work." crumbs={[["/", "Home"], [null, "Resources"]]} />
      <Section title="Guides and downloads">
        {dl.loading ? <Skeleton className="h-40" /> : (
          <div className="grid gap-6 md:grid-cols-3">
            {(dl.data || []).map((d) => (
              <Link key={d.id} to={`/guides/${d.slug}`} className="group flex flex-col rounded-xl border border-line p-5 hover:border-fg/25">
                <span className="flex h-10 w-10 items-center justify-center rounded-md bg-paper text-cable">{d.kind === "guide" ? <BookOpen className="h-5 w-5" /> : <FileText className="h-5 w-5" />}</span>
                <h3 className="mt-4 font-display text-[17px] font-bold leading-snug group-hover:underline group-hover:decoration-signal group-hover:underline-offset-4">{d.title}</h3>
                <p className="mt-1.5 flex-1 text-sm leading-relaxed text-muted">{d.summary}</p>
                <span className="mt-4 text-sm font-medium text-cable">{d.file ? (d.gated ? "Download (free, needs your details)" : "Read or download") : "Read the guide"}</span>
              </Link>
            ))}
          </div>
        )}
      </Section>
      {(posts.data || []).length > 0 && (
        <Section tone="paper" title="Latest from our engineers" action={<Button as={Link} to="/insights" variant="outline">All articles</Button>}>
          <PostList posts={posts.data.slice(0, 3)} />
        </Section>
      )}
      <Section title="Frequently asked questions">
        <div className="space-y-10">
          {grouped.map(([cat, list]) => (
            <div key={cat} className="grid gap-4 md:grid-cols-[220px_1fr]">
              <h3 className="font-display text-[17px] font-bold">{FAQ_CATS[cat] || cat}</h3>
              <Faqs items={list} />
            </div>
          ))}
        </div>
      </Section>
    </>
  );
}

function PostList({ posts }) {
  return (
    <div className="grid gap-6 md:grid-cols-3">
      {posts.map((p) => (
        <Link key={p.slug} to={`/insights/${p.slug}`} className="group rounded-xl border border-line bg-white p-6 hover:border-fg/25">
          <p className="text-xs text-muted">{fmtDate(p.publish_at)}{p.author ? `, ${p.author}` : ""}</p>
          <h3 className="mt-2 font-display text-[17px] font-bold leading-snug group-hover:underline group-hover:decoration-signal group-hover:underline-offset-4">{p.title}</h3>
          <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-muted">{p.excerpt}</p>
        </Link>
      ))}
    </div>
  );
}

export function InsightsPage() {
  const [tag, setTag] = useState("");
  const { data, loading } = useGet(`/public/insights${tag ? `?tag=${tag}` : ""}`, [tag]);
  const all = useGet("/public/insights");
  useMeta({ title: "Insights", description: "Articles on HT supply, tariffs, power quality, safety and maintenance from Sellandiamman Power Infra's engineers." });
  const tags = useMemo(() => [...new Set((all.data || []).flatMap((p) => p.tags || []))], [all.data]);
  return (
    <>
      <PageHero title="Insights" text="Short, practical articles from site and design work." crumbs={[["/", "Home"], ["/resources", "Resources"], [null, "Insights"]]} />
      <Section>
        {tags.length > 1 && (
          <div className="mb-6 flex flex-wrap gap-2">
            {["", ...tags].map((t) => (
              <button key={t} type="button" onClick={() => setTag(t)} aria-pressed={tag === t} className={cn("rounded-full border px-3.5 py-1.5 text-sm", tag === t ? "border-ink bg-ink text-white" : "border-line hover:border-fg/30")}>{t ? TAGS[t] || t.replace(/_/g, " ") : "All"}</button>
            ))}
          </div>
        )}
        {loading ? <Skeleton className="h-40" /> : <PostList posts={data || []} />}
      </Section>
    </>
  );
}

export function InsightDetail() {
  const { slug } = useParams();
  const { data, error, loading } = useGet(`/public/insights/${slug}`);
  const p = data?.post;
  useMeta({ title: p?.title, description: p?.excerpt, jsonLd: p && { "@context": "https://schema.org", "@type": "Article", headline: p.title, datePublished: p.publish_at, author: { "@type": "Organization", name: p.author || "Sellandiamman Power Infra" } } });
  if (loading) return <PageLoading />;
  if (error || !p) return <NotFound />;
  return (
    <>
      <PageHero title={p.title} dark={false} crumbs={[["/", "Home"], ["/insights", "Insights"], [null, "Article"]]}>
        <p className="text-sm text-muted">{fmtDate(p.publish_at)}{p.author ? `, ${p.author}` : ""}</p>
      </PageHero>
      <article className="container py-12"><Markdown text={p.body} className="prose-site" /></article>
      {data.more?.length > 0 && <Section tone="paper" title="Read next"><PostList posts={data.more} /></Section>}
    </>
  );
}

export function GuidePage() {
  const { slug } = useParams();
  const { data: g, error, loading } = useGet(`/public/guides/${slug}`);
  const [ask, setAsk] = useState(false);
  useMeta({ title: g?.title, description: g?.summary });
  if (loading) return <PageLoading />;
  if (error || !g) return <NotFound />;
  async function openIt() {
    if (g.gated) { setAsk(true); return; }
    openFile(`/public/download/${g.slug}`, { name: g.file?.name, type: "application/pdf" });
  }
  return (
    <>
      <PageHero title={g.title} text={g.summary} dark={false} crumbs={[["/", "Home"], ["/resources", "Resources"], [null, "Guide"]]}>
        {g.file && <Button onClick={openIt}><Download className="h-4 w-4" />Download {g.file.name ? `(${g.file.name})` : "PDF"}</Button>}
      </PageHero>
      {g.body && <article className="container py-12"><Markdown text={g.body} className="prose-site" /></article>}
      <div className="container pb-14">
        <div className="flex flex-col items-start justify-between gap-4 rounded-xl bg-ink p-6 text-white md:flex-row md:items-center">
          <div><p className="font-display text-[19px] font-bold text-white">Want us to handle this for you?</p><p className="mt-1 text-sm text-white/75">Our liaison team prepares and files the paperwork and follows up until it's done.</p></div>
          <Button as={Link} to="/get-quote?service=liaison">Talk to us</Button>
        </div>
      </div>
      <GatedDialog open={ask} onClose={() => setAsk(false)} guide={g} />
    </>
  );
}

function GatedDialog({ open, onClose, guide }) {
  const [v, setV, set] = useLeadForm({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(false);
  async function go(e) {
    e.preventDefault();
    const bad = checkContact(v);
    if (bad) { setErr(bad); return; }
    setBusy(true);
    try {
      const r = await api.post(`/public/download/${guide.slug}`, { ...v, tracking: tracking(), email: v.email || undefined });
      setDone(true);
      openFile(r.data.url.replace(/^\/api/, ""), { name: guide.file?.name, type: "application/pdf" });
    } catch (ex) { setErr(errMsg(ex)); } finally { setBusy(false); }
  }
  return (
    <Dialog open={open} onOpenChange={(x) => !x && onClose()} title={`Download: ${guide.title}`} description="Free. We'll send occasional updates only if you ask.">
      {done ? <Done title="Your download has started" /> : (
        <form onSubmit={go} className="relative space-y-3" noValidate>
          <Honeypot value={v.website} onChange={(x) => setV((s) => ({ ...s, website: x }))} />
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Your name" required><Input value={v.name} onChange={set("name")} /></Field>
            <Field label="Mobile number" required><Input value={v.phone} onChange={set("phone")} inputMode="tel" /></Field>
          </div>
          <Field label="Email (optional)"><Input type="email" value={v.email} onChange={set("email")} /></Field>
          <Consent checked={v.consent} onChange={set("consent")} id="consent-dl" />
          {err && <Alert tone="red">{err}</Alert>}
          <Button type="submit" loading={busy}>Download</Button>
        </form>
      )}
    </Dialog>
  );
}

export function NewsletterForm({ dark }) {
  const [email, setEmail] = useState("");
  const [ok, setOk] = useState(false);
  const [consent, setConsent] = useState(false);
  const [err, setErr] = useState("");
  if (ok) return <p className={cn("text-sm", dark ? "text-white" : "text-good")}>You're subscribed. We write about once a month.</p>;
  return (
    <form className="space-y-2" onSubmit={async (e) => { e.preventDefault(); setErr(""); try { await api.post("/public/newsletter", { email, consent }); setOk(true); } catch (ex) { setErr(errMsg(ex)); } }}>
      <div className="flex gap-2"><Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" aria-label="Email" /><Button type="submit">Subscribe</Button></div>
      <Checkbox checked={consent} onChange={setConsent} label={<span className={cn("text-xs", dark ? "text-white/75" : "text-muted")}>Send me occasional articles and tariff updates</span>} />
      {err && <p className="text-xs text-bad">{err}</p>}
    </form>
  );
}
