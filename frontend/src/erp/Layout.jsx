import { useEffect, useMemo, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import * as RDialog from "@radix-ui/react-dialog";
import { Command } from "cmdk";
import { Menu as MenuIcon, X, Search, Bell, ChevronDown, LogOut, User, ExternalLink, Building2, CheckCheck, Moon, Sun } from "lucide-react";
import { api, branchApi, useBranchPick, useDebounced, store, IS_DEMO } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { ago, initials } from "@/lib/format";
import { Logo } from "@/components/brand/Logo";
import { Icon } from "@/components/ui/icons";
import { Kbd, Skeleton, Menu, MenuTrigger, MenuContent, MenuItem, MenuSeparator, MenuLabel, Popover, PopoverTrigger, PopoverContent, Badge, Button } from "@/components/ui/kit";
import { useApi, useInvalidate } from "./lib";
import { buildNav, specialFor } from "./nav";
import { Empty } from "@/components/ui/kit";
import ErrorBoundary from "@/components/ErrorBoundary";

// Demo-only banner slot (role switcher) supplied by the preview build
let demoBar = null;
export const setDemoBar = (C) => { demoBar = C; };

function useTheme() {
  const [t, setT] = useState(() => store.get("spi_theme", "light"));
  useEffect(() => { document.documentElement.dataset.theme = t; store.set("spi_theme", t); return () => { document.documentElement.dataset.theme = "light"; }; }, [t]);
  return [t, setT];
}

function Sidebar({ sections, onNavigate, counts }) {
  const loc = useLocation();
  const [closed, setClosed] = useState(() => store.get("spi_nav_closed", {}));
  const toggle = (n) => { const c = { ...closed, [n]: !closed[n] }; setClosed(c); store.set("spi_nav_closed", c); };
  return (
    <nav aria-label="Staff menu" className="scrollbar-thin flex-1 overflow-y-auto px-2 pb-6">
      {sections.map((s) => {
        const active = s.items.some((i) => loc.pathname === i.to || (i.to !== "/erp" && loc.pathname.startsWith(`${i.to}/`)));
        const open = active || !closed[s.name];
        return (
          <div key={s.name} className="mt-3">
            <button type="button" onClick={() => toggle(s.name)} aria-expanded={open} className="flex w-full items-center justify-between rounded px-2 py-1 text-[13px] font-semibold text-white/65 hover:text-white/85">
              {s.name}<ChevronDown className={cn("h-3.5 w-3.5 transition-transform", !open && "-rotate-90")} />
            </button>
            {open && (
              <ul className="mt-0.5 space-y-px">
                {s.items.map((i) => (
                  <li key={i.to}>
                    <NavLink to={i.to} end={i.end} onClick={onNavigate}
                      className={({ isActive }) => cn("flex items-center gap-2.5 rounded-md px-2 py-1.5 text-[14.5px] text-white/85 hover:bg-white/[.06] hover:text-white", (isActive || (!i.end && loc.pathname.startsWith(`${i.to}/`))) && "bg-white/[.09] font-medium text-white")}>
                      <Icon name={i.icon} className="h-4 w-4 shrink-0 text-white/65" />
                      <span className="truncate">{i.label}</span>
                      {i.badge && counts?.[i.badge] > 0 && <span className="ml-auto rounded-full bg-signal px-1.5 text-[12px] font-bold text-white tabular">{counts[i.badge]}</span>}
                    </NavLink>
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </nav>
  );
}

function BranchPicker() {
  const { user } = useAuth();
  const pick = useBranchPick();
  const { data: all } = useApi("/branches/all", null, { staleTime: 10 * 60e3 });
  const invalidate = useInvalidate();
  const allowed = useMemo(() => {
    if (!all) return [];
    return user.branch_ids?.length ? all.filter((b) => user.branch_ids.includes(b.id)) : all;
  }, [all, user]);
  if (!all || allowed.length < 2) return null;
  const cur = allowed.find((b) => b.id === pick);
  return (
    <Menu>
      <MenuTrigger asChild>
        <button type="button" className="hidden h-9 items-center gap-1.5 rounded-md border border-edge bg-surface px-2.5 text-sm hover:bg-canvas md:flex">
          <Building2 className="h-4 w-4 text-muted" /><span className="max-w-[140px] truncate">{cur ? cur.name.replace("Head office — ", "") : "All branches"}</span><ChevronDown className="h-3.5 w-3.5 text-muted" />
        </button>
      </MenuTrigger>
      <MenuContent align="end">
        <MenuLabel>Show records for</MenuLabel>
        <MenuItem onSelect={() => { branchApi.set(""); invalidate(); }}>{!pick && <CheckCheck className="h-4 w-4" />}All my branches</MenuItem>
        {allowed.map((b) => <MenuItem key={b.id} onSelect={() => { branchApi.set(b.id); invalidate(); }}>{pick === b.id && <CheckCheck className="h-4 w-4" />}{b.name}</MenuItem>)}
      </MenuContent>
    </Menu>
  );
}

function Notifications() {
  const nav = useNavigate();
  const { data, refetch } = useApi("/notifications", null, { refetchInterval: 60e3 });
  const [open, setOpen] = useState(false);
  const unread = data?.unread || 0;
  async function readAll() { await api.post("/notifications/read", {}); refetch(); }
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button type="button" className="relative flex h-9 w-9 items-center justify-center rounded-md text-fg/80 hover:bg-fg/5 hover:text-fg" aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}>
          <Bell className="h-[18px] w-[18px]" />
          {unread > 0 && <span className="absolute right-1 top-1 min-w-[16px] rounded-full bg-bad px-1 text-center text-[11px] font-bold leading-4 text-white tabular">{unread > 99 ? "99+" : unread}</span>}
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[min(380px,calc(100vw-24px))] p-0">
        <div className="flex items-center justify-between border-b border-edge px-4 py-2.5"><p className="text-sm font-semibold">Notifications</p>{unread > 0 && <button type="button" onClick={readAll} className="text-xs text-cable hover:underline">Mark all read</button>}</div>
        <ul className="max-h-[60vh] divide-y divide-edge overflow-y-auto">
          {!data?.items.length && <li className="px-4 py-8 text-center text-sm text-muted">You're all caught up</li>}
          {data?.items.slice(0, 30).map((n) => (
            <li key={n.id}>
              <button type="button" onClick={async () => { setOpen(false); if (!n.read) api.post("/notifications/read", { ids: [n.id] }).then(() => refetch()); if (n.link) nav(n.link); }}
                className={cn("block w-full px-4 py-2.5 text-left hover:bg-canvas", !n.read && "bg-signal-soft/30")}>
                <p className={cn("text-sm", !n.read && "font-semibold")}>{n.title}</p>
                {n.body && <p className="line-clamp-2 text-xs text-muted">{n.body}</p>}
                <p className="mt-0.5 text-[12px] text-muted">{ago(n.created_at)}</p>
              </button>
            </li>
          ))}
        </ul>
      </PopoverContent>
    </Popover>
  );
}

function Palette({ open, setOpen, sections }) {
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const dq = useDebounced(q, 220);
  const { data: hits } = useApi(dq.length >= 2 ? "/search" : null, { q: dq });
  useEffect(() => { if (!open) setQ(""); }, [open]);
  const items = sections.flatMap((s) => s.items.map((i) => ({ ...i, section: s.name })));
  const ql = q.toLowerCase();
  const pages = (ql ? items.filter((i) => i.label.toLowerCase().includes(ql) || i.section.toLowerCase().includes(ql)) : items.slice(0, 8)).slice(0, 10);
  const go = (to) => { setOpen(false); nav(to); };
  return (
    <RDialog.Root open={open} onOpenChange={setOpen}>
      <RDialog.Portal>
        <RDialog.Overlay className="fixed inset-0 z-50 bg-ink/50" />
        <RDialog.Content className="fixed left-1/2 top-[12vh] z-50 w-[calc(100vw-24px)] max-w-xl -translate-x-1/2 overflow-hidden rounded-xl bg-surface shadow-pop" aria-describedby={undefined}>
          <RDialog.Title className="sr-only">Search</RDialog.Title>
          <Command shouldFilter={false} loop>
            <div className="flex items-center gap-2 border-b border-edge px-4"><Search className="h-4 w-4 text-muted" />
              <Command.Input value={q} onValueChange={setQ} placeholder="Search leads, projects, invoices, items… or jump to a screen" className="h-12 flex-1 bg-transparent text-[16px] outline-none" autoFocus /><Kbd>Esc</Kbd></div>
            <Command.List className="max-h-[60vh] overflow-y-auto p-2">
              <Command.Empty className="px-3 py-6 text-center text-sm text-muted">{q.length < 2 ? "Type to search" : "Nothing found"}</Command.Empty>
              {pages.length > 0 && (
                <Command.Group heading="Go to" className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-muted">
                  {pages.map((i) => (
                    <Command.Item key={i.to} value={`page:${i.to}`} onSelect={() => go(i.to)} className="flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-2 text-sm data-[selected=true]:bg-fg/5">
                      <Icon name={i.icon} className="h-4 w-4 text-muted" />{i.label}<span className="ml-auto text-xs text-muted">{i.section}</span>
                    </Command.Item>
                  ))}
                </Command.Group>
              )}
              {hits?.length > 0 && (
                <Command.Group heading="Records" className="mt-1 [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-muted">
                  {hits.map((h) => (
                    <Command.Item key={`${h.entity}:${h.id}`} value={`rec:${h.entity}:${h.id}`} onSelect={() => go(`/erp/e/${h.entity}/${h.id}`)} className="flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-2 text-sm data-[selected=true]:bg-fg/5">
                      <Icon name={h.icon} className="h-4 w-4 text-muted" /><span className="truncate">{h.title}</span>{h.code && h.code !== h.title && <span className="shrink-0 text-xs text-muted tabular">{h.code}</span>}<span className="ml-auto shrink-0 text-xs text-muted">{h.entity_label}</span>
                    </Command.Item>
                  ))}
                </Command.Group>
              )}
            </Command.List>
          </Command>
        </RDialog.Content>
      </RDialog.Portal>
    </RDialog.Root>
  );
}

export default function ErpLayout() {
  const { user, meta, logout } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [drawer, setDrawer] = useState(false);
  const [palette, setPalette] = useState(false);
  const [theme, setTheme] = useTheme();
  const sections = useMemo(() => buildNav(meta, user), [meta, user]);
  const sp = specialFor(loc.pathname);
  const blocked = !!(sp?.need && !(user?.permissions?.[sp.need[0]] || "").includes(sp.need[1]));
  const { data: inbox } = useApi(user ? "/approvals/inbox" : null, null, { refetchInterval: 120e3 });
  useEffect(() => { setDrawer(false); }, [loc.pathname]);
  useEffect(() => {
    const on = (e) => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPalette((x) => !x); } };
    window.addEventListener("keydown", on);
    return () => window.removeEventListener("keydown", on);
  }, []);
  const DemoBar = IS_DEMO ? demoBar : null;
  const side = (
    <>
      <div className="flex h-14 shrink-0 items-center px-4"><Link to="/erp" aria-label="Dashboard"><Logo theme="dark" compact /></Link></div>
      <Sidebar sections={sections} counts={{ approvals: inbox?.count }} onNavigate={() => setDrawer(false)} />
      <div className="border-t border-white/10 p-3 text-xs text-white/65">
        <Link to="/" className="inline-flex items-center gap-1 hover:text-white">Open the website<ExternalLink className="h-3 w-3" /></Link>
      </div>
    </>
  );
  return (
    <div className={cn("min-h-screen bg-canvas", DemoBar && "pt-10")}>
      {DemoBar && <DemoBar />}
      <aside className={cn("fixed bottom-0 left-0 z-30 hidden w-[248px] flex-col bg-ink lg:flex", DemoBar ? "top-10" : "top-0")}>{side}</aside>
      {drawer && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <div className="absolute inset-0 bg-ink/50" onClick={() => setDrawer(false)} />
          <aside className="absolute inset-y-0 left-0 flex w-[280px] flex-col bg-ink">{side}<button type="button" onClick={() => setDrawer(false)} className="absolute right-2 top-3 rounded-md p-2 text-white/85" aria-label="Close menu"><X className="h-5 w-5" /></button></aside>
        </div>
      )}
      <div className="lg:pl-[248px]">
        <header className={cn("sticky z-20 flex h-14 items-center gap-2 border-b border-edge bg-surface/95 px-3 backdrop-blur sm:px-5", DemoBar ? "top-10" : "top-0")}>
          <button type="button" className="rounded-md p-2 lg:hidden" onClick={() => setDrawer(true)} aria-label="Open menu"><MenuIcon className="h-5 w-5" /></button>
          <button type="button" onClick={() => setPalette(true)} className="flex h-9 min-w-0 flex-1 items-center gap-2 rounded-md border border-edge bg-canvas px-3 text-left text-sm text-muted hover:border-fg/25 sm:max-w-md">
            <Search className="h-4 w-4 shrink-0" /><span className="truncate">Search or jump to…</span><span className="ml-auto hidden sm:block"><Kbd>Ctrl K</Kbd></span>
          </button>
          <div className="ml-auto flex items-center gap-1.5">
            <BranchPicker />
            <Notifications />
            <Menu>
              <MenuTrigger asChild>
                <button type="button" className="flex items-center gap-2 rounded-md p-1 pr-2 hover:bg-fg/5" aria-label="Your account">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-ink text-xs font-bold text-signal-bright">{initials(user?.name)}</span>
                  <span className="hidden text-left leading-tight md:block"><span className="block max-w-[140px] truncate text-sm font-medium">{user?.name}</span><span className="block max-w-[140px] truncate text-[12px] text-muted">{user?.role_label}</span></span>
                </button>
              </MenuTrigger>
              <MenuContent>
                <MenuItem onSelect={() => nav("/erp/me")}><User className="h-4 w-4" />My profile, attendance & security</MenuItem>
                <MenuItem onSelect={() => setTheme(theme === "dark" ? "light" : "dark")}>{theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}{theme === "dark" ? "Light mode" : "Dark mode"}</MenuItem>
                <MenuSeparator />
                <MenuItem onSelect={async () => { await logout(); nav("/erp/login"); }}><LogOut className="h-4 w-4" />Sign out</MenuItem>
              </MenuContent>
            </Menu>
          </div>
        </header>
        <main id="main" className="mx-auto max-w-[1400px] px-3 py-5 sm:px-5 lg:px-7">
          {meta ? <ErrorBoundary resetKey={loc.pathname}>{blocked ? <Empty title="This screen isn't part of your role" text="Ask your administrator if you need it." className="py-24" /> : <Outlet />}</ErrorBoundary> : <div className="space-y-4"><Skeleton className="h-10 w-1/3" /><Skeleton className="h-64" /></div>}
        </main>
      </div>
      <Palette open={palette} setOpen={setPalette} sections={sections} />
    </div>
  );
}

export { Badge, Button };
