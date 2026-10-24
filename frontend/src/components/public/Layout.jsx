import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { Menu as MenuIcon, X, Phone, MessageCircle, ChevronDown, AlertTriangle, ArrowUpRight, LogIn } from "lucide-react";
import { useSite } from "./site";
import { Logo } from "@/components/brand/Logo";
import { useT, useLang, setLang } from "@/lib/i18n";
import { telLink, waLink } from "@/lib/format";
import { captureTouch } from "@/lib/tracking";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/kit";
import { Icon } from "@/components/ui/icons";
import ErrorBoundary from "@/components/ErrorBoundary";

export { Icon };

function LangToggle({ dark }) {
  const l = useLang();
  return (
    <button type="button" onClick={() => setLang(l === "ta" ? "en" : "ta")} className={cn("rounded px-2 py-1 text-xs font-medium", dark ? "text-white/70 hover:text-white" : "text-muted hover:text-fg")}
      aria-label={l === "ta" ? "Switch to English" : "தமிழில் பார்க்க"}>{l === "ta" ? "English" : "தமிழ்"}</button>
  );
}

function ServicesMenu({ onClose }) {
  const site = useSite();
  const t = useT();
  return (
    <div className="grid gap-x-8 gap-y-1 p-5 md:grid-cols-2 lg:w-[720px]">
      {site.services.map((s) => (
        <Link key={s.slug} to={`/services/${s.slug}`} onClick={onClose} className="group flex items-start gap-3 rounded-md p-2 hover:bg-white/5">
          <Icon name={s.icon} className="mt-0.5 h-4 w-4 shrink-0 text-signal" />
          <span><span className="block text-sm font-medium text-white">{s.title}</span><span className="line-clamp-1 text-xs text-white/55">{s.summary}</span></span>
        </Link>
      ))}
      <Link to="/services" onClick={onClose} className="mt-2 rounded-md p-2 text-sm font-semibold text-signal hover:bg-white/5 md:col-span-2">{t("All services")}</Link>
    </div>
  );
}

const NAV = [["/projects", "Projects"], ["/industries", "Industries"], ["/tools", "Tools"], ["/about", "About"], ["/contact", "Contact"]];

function Header() {
  const site = useSite();
  const t = useT();
  const [open, setOpen] = useState(false);
  const [svc, setSvc] = useState(false);
  const loc = useLocation();
  useEffect(() => { setOpen(false); setSvc(false); }, [loc.pathname]);
  const s = site.settings || {};
  const ann = s.announcement;
  return (
    <>
      {ann?.active && ann?.text && (
        <div className="bg-signal px-4 py-2 text-center text-[13px] font-medium text-ink">
          {ann.link ? <Link to={ann.link} className="underline-offset-2 hover:underline">{ann.text}</Link> : ann.text}
        </div>
      )}
      <header className="sticky top-0 z-40 border-b border-white/10 bg-ink/95 backdrop-blur supports-[backdrop-filter]:bg-ink/85">
        <div className="container flex h-16 items-center justify-between gap-4">
          <Link to="/" className="shrink-0" aria-label="Sellandiamman Power Infra home"><Logo theme="dark" /></Link>
          <nav className="hidden items-center gap-1 lg:flex" aria-label="Main">
            <div className="relative" onMouseLeave={() => setSvc(false)}>
              <button type="button" onClick={() => setSvc((x) => !x)} onMouseEnter={() => setSvc(true)} aria-expanded={svc}
                className={cn("flex items-center gap-1 rounded-md px-3 py-2 text-sm text-white/80 hover:text-white", loc.pathname.startsWith("/services") && "text-white")}>
                {t("Services")}<ChevronDown className="h-3.5 w-3.5" />
              </button>
              {svc && <div className="absolute left-0 top-full rounded-xl border border-white/10 bg-ink-800 shadow-pop"><ServicesMenu onClose={() => setSvc(false)} /></div>}
            </div>
            {NAV.map(([to, l]) => (
              <NavLink key={to} to={to} className={({ isActive }) => cn("rounded-md px-3 py-2 text-sm text-white/80 hover:text-white", isActive && "text-white")}>{t(l)}</NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-1.5">
            <LangToggle dark />
            {s.phone && <a href={telLink(s.phone)} className="hidden items-center gap-1.5 whitespace-nowrap rounded-md px-2 py-2 text-sm text-white/85 hover:text-white min-[1380px]:flex"><Phone className="h-4 w-4 text-signal" />{s.phone}</a>}
            <Link to="/login" className="hidden items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 text-sm text-white/80 hover:text-white md:flex"><LogIn className="h-4 w-4" />{t("Client login")}</Link>
            <Button as={Link} to="/get-quote" size="sm" className="hidden sm:inline-flex">{t("Get a quote")}</Button>
            <button type="button" className="rounded-md p-2 text-white lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu"><MenuIcon className="h-6 w-6" /></button>
          </div>
        </div>
      </header>
      {open && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-ink text-white lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <div className="container flex h-16 items-center justify-between">
            <Logo theme="dark" />
            <button type="button" onClick={() => setOpen(false)} className="rounded-md p-2" aria-label="Close menu"><X className="h-6 w-6" /></button>
          </div>
          <nav className="container space-y-1 pb-10 pt-2" aria-label="Mobile">
            <p className="pb-1 pt-3 text-xs text-white/50">{t("Services")}</p>
            {site.services.map((sv) => <Link key={sv.slug} to={`/services/${sv.slug}`} className="block rounded-md px-2 py-2 text-[15px] hover:bg-white/5">{sv.title}</Link>)}
            <div className="my-3 h-px bg-white/10" />
            {[...NAV, ["/products", "Products"], ["/clients", "Clients"], ["/gallery", "Gallery"], ["/resources", "Resources"], ["/amc", "AMC & maintenance"], ["/emergency", "24×7 breakdown"], ["/careers", "Careers"]].map(([to, l]) => (
              <Link key={to} to={to} className="block rounded-md px-2 py-2 text-lg font-semibold hover:bg-white/5">{t(l)}</Link>
            ))}
            <div className="flex flex-col gap-2 pt-4">
              <Button as={Link} to="/get-quote" size="lg">{t("Get a quote")}</Button>
              <Button as={Link} to="/login" size="lg" variant="light">{t("Client login")}</Button>
            </div>
          </nav>
        </div>
      )}
    </>
  );
}

function Footer() {
  const site = useSite();
  const t = useT();
  const s = site.settings || {};
  const year = new Date().getFullYear();
  return (
    <footer className="bg-ink-900 pb-24 text-white/75 sm:pb-0">
      <div className="container grid gap-10 py-14 md:grid-cols-12">
        <div className="md:col-span-4">
          <Logo theme="dark" />
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-white/60">LT and HT electrical contracting and consulting across Tamil Nadu — part of the Sellandiamman Group.</p>
          <div className="mt-5 space-y-1.5 text-sm">
            {s.phone && <a href={telLink(s.phone)} className="flex items-center gap-2 hover:text-white"><Phone className="h-4 w-4 text-signal" />{s.phone}</a>}
            {s.whatsapp && <a href={waLink(s.whatsapp)} target="_blank" rel="noreferrer" className="flex items-center gap-2 hover:text-white"><MessageCircle className="h-4 w-4 text-signal" />WhatsApp</a>}
            {s.email && <a href={`mailto:${s.email}`} className="block hover:text-white">{s.email}</a>}
            {s.emergency_phone && <Link to="/emergency" className="mt-2 flex items-center gap-2 font-semibold text-signal"><AlertTriangle className="h-4 w-4" />24×7 breakdown: {s.emergency_phone}</Link>}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-8 md:col-span-8 md:grid-cols-4">
          <div>
            <p className="mb-3 text-sm font-semibold text-white">{t("Services")}</p>
            <ul className="space-y-2 text-sm">{site.services.slice(0, 8).map((x) => <li key={x.slug}><Link to={`/services/${x.slug}`} className="hover:text-white">{x.title.replace(/ \(.*\)/, "")}</Link></li>)}</ul>
          </div>
          <div>
            <p className="mb-3 text-sm font-semibold text-white">Company</p>
            <ul className="space-y-2 text-sm">
              {[["/about", "About"], ["/projects", "Projects"], ["/clients", "Clients"], ["/gallery", "Gallery"], ["/safety-quality", "Safety & quality"], ["/careers", "Careers"], ["/insights", "Insights"]].map(([to, l]) => <li key={to}><Link to={to} className="hover:text-white">{t(l)}</Link></li>)}
            </ul>
          </div>
          <div>
            <p className="mb-3 text-sm font-semibold text-white">Work with us</p>
            <ul className="space-y-2 text-sm">
              {[["/get-quote", "Get a quote"], ["/book-survey", "Book a site survey"], ["/bill-review", "Free bill review"], ["/tenders", "Invite us to bid"], ["/amc", "AMC & maintenance"], ["/tools", "Tools"], ["/vendor-registration", "Vendor registration"]].map(([to, l]) => <li key={to}><Link to={to} className="hover:text-white">{t(l)}</Link></li>)}
            </ul>
          </div>
          <div>
            <p className="mb-3 text-sm font-semibold text-white">Branches</p>
            <ul className="space-y-3 text-sm">
              {site.branches.map((b) => (
                <li key={b.id}><span className="block text-white">{b.name}</span>{b.phone && <a href={telLink(b.phone)} className="text-white/60 hover:text-white">{b.phone}</a>}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
      {(s.group_companies || []).length > 0 && (
        <div className="border-t border-white/10">
          <div className="container flex flex-wrap items-center gap-x-6 gap-y-2 py-5 text-sm">
            <span className="text-white/50">Sellandiamman Group</span>
            {s.group_companies.map((g) => g.url ? <a key={g.name} href={g.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-white">{g.name}<ArrowUpRight className="h-3 w-3" /></a> : <span key={g.name}>{g.name}</span>)}
          </div>
        </div>
      )}
      <div className="border-t border-white/10">
        <div className="container flex flex-col gap-3 py-5 text-xs text-white/50 sm:flex-row sm:items-center sm:justify-between">
          <p className="flex flex-wrap gap-x-4 gap-y-1"><span>© {year} Sellandiamman Power Infra</span>{s.gstin && <span>GSTIN {s.gstin}</span>}{s.elb_licence && <span>Licence {s.elb_licence}</span>}</p>
          <div className="flex flex-wrap gap-4">
            <Link to="/privacy" className="hover:text-white">{t("Privacy")}</Link>
            <Link to="/terms" className="hover:text-white">{t("Terms")}</Link>
            <Link to="/cookies" className="hover:text-white">Cookies</Link>
            <Link to="/erp/login" className="hover:text-white">{t("Staff login")}</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}

// Phone: a bottom bar with call, WhatsApp and quote. Desktop: a WhatsApp button in the corner.
function QuickActions() {
  const site = useSite();
  const t = useT();
  const s = site.settings || {};
  const loc = useLocation();
  const msg = `Hello, I'm looking at ${window.location.host}${loc.pathname} and need help with an electrical project.`;
  return (
    <>
      <div className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-3 border-t border-white/10 bg-ink text-white sm:hidden" style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
        {s.phone ? <a href={telLink(s.phone)} className="flex flex-col items-center gap-0.5 py-2 text-[11px]"><Phone className="h-5 w-5 text-signal" />{t("Call us")}</a> : <span />}
        {s.whatsapp ? <a href={waLink(s.whatsapp, msg)} target="_blank" rel="noreferrer" className="flex flex-col items-center gap-0.5 py-2 text-[11px]"><MessageCircle className="h-5 w-5 text-signal" />WhatsApp</a> : <span />}
        <Link to="/get-quote" className="flex flex-col items-center justify-center bg-signal py-2 text-[12px] font-semibold text-ink">{t("Get a quote")}</Link>
      </div>
      {s.whatsapp && (
        <a href={waLink(s.whatsapp, msg)} target="_blank" rel="noreferrer" aria-label={t("WhatsApp us")}
          className="fixed bottom-6 right-6 z-30 hidden h-12 items-center gap-2 rounded-full bg-[#1F7A4D] px-4 text-sm font-semibold text-white shadow-pop hover:bg-[#19663f] sm:flex">
          <MessageCircle className="h-5 w-5" />WhatsApp
        </a>
      )}
    </>
  );
}

export default function PublicLayout() {
  const loc = useLocation();
  useEffect(() => { captureTouch(); }, [loc.pathname]);
  useEffect(() => { window.scrollTo(0, 0); }, [loc.pathname]);
  return (
    <div className="flex min-h-screen flex-col bg-white">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded focus:bg-signal focus:px-3 focus:py-2 focus:text-ink">Skip to content</a>
      <Header />
      <main id="main" className="flex-1">
        <ErrorBoundary resetKey={loc.pathname}><Outlet /></ErrorBoundary>
      </main>
      <Footer />
      <QuickActions />
    </div>
  );
}

// ------------------------------------------------------------------ shared page pieces
export function PageHero({ title, text, children, crumbs, dark = true, className }) {
  return (
    <section className={cn(dark ? "bg-ink text-white" : "bg-paper", className)}>
      <div className="container py-12 md:py-16">
        {crumbs && (
          <nav aria-label="Breadcrumb" className={cn("mb-4 text-sm", dark ? "text-white/55" : "text-muted")}>
            {crumbs.map(([to, l], n) => <span key={l}>{n > 0 && <span className="mx-2">/</span>}{to ? <Link to={to} className="hover:underline">{l}</Link> : <span className={dark ? "text-white/85" : "text-fg"}>{l}</span>}</span>)}
          </nav>
        )}
        <h1 className={cn("max-w-3xl text-[32px] font-extrabold leading-[1.1] md:text-[44px]", dark && "text-white")} style={{ letterSpacing: "-0.025em" }}>{title}</h1>
        {text && <p className={cn("mt-4 max-w-2xl text-lg leading-relaxed", dark ? "text-white/70" : "text-muted")}>{text}</p>}
        {children && <div className="mt-6">{children}</div>}
      </div>
    </section>
  );
}

export function Section({ title, text, children, className, id, action, tone = "white" }) {
  return (
    <section id={id} className={cn(tone === "paper" ? "bg-paper" : tone === "ink" ? "bg-ink text-white" : "bg-white", className)}>
      <div className="container py-14 md:py-20">
        {(title || action) && (
          <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
            <div className="max-w-2xl">
              {title && <h2 className={cn("text-[26px] font-extrabold leading-tight md:text-[34px]", tone === "ink" && "text-white")} style={{ letterSpacing: "-0.02em" }}>{title}</h2>}
              {text && <p className={cn("mt-3 text-[17px] leading-relaxed", tone === "ink" ? "text-white/65" : "text-muted")}>{text}</p>}
            </div>
            {action}
          </div>
        )}
        {children}
      </div>
    </section>
  );
}
