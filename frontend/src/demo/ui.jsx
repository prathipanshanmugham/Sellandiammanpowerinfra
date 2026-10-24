import { useState, useSyncExternalStore } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Download, ExternalLink, RotateCcw, FileText, LogIn } from "lucide-react";
import { useAuth, homeFor } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Button, Dialog, Menu, MenuTrigger, MenuContent, MenuItem, MenuLabel, MenuSeparator } from "@/components/ui/kit";
import { S, me } from "./store";
import { IN_FRAME } from "@/lib/api";
import { signInAs } from "./adapter";

const STAFF = [["director", "Director / CEO"], ["branch_manager", "Branch manager"], ["sales", "Sales"], ["estimator", "Estimation engineer"], ["tender_exec", "Tender executive"],
  ["project_manager", "Project manager"], ["site_engineer", "Site engineer"], ["liaison", "Liaison officer"], ["qaqc", "QA/QC & testing"], ["safety", "Safety officer"],
  ["purchase", "Purchase"], ["store", "Store keeper"], ["accounts", "Accounts"], ["hr", "HR"], ["service_manager", "Service manager"], ["technician", "Service technician"],
  ["marketing", "Marketing"], ["auditor", "Auditor (read-only)"], ["employee", "Employee"], ["super_admin", "Super admin"]];
const PORTAL = [["client", "Client"], ["consultant", "Consultant / architect"], ["vendor", "Vendor"], ["subcontractor", "Subcontractor"], ["partner", "Referral partner"]];
const label = (r) => [...STAFF, ...PORTAL].find(([k]) => k === r)?.[1] || r;

function useSwitch() {
  const { setUser, reloadMeta } = useAuth();
  const qc = useQueryClient();
  const nav = useNavigate();
  return async (role) => {
    signInAs(role);
    qc.clear();
    const u = me();
    setUser({ ...u });
    await reloadMeta();
    nav(homeFor(u));
  };
}

export function DemoBar() {
  const { user } = useAuth();
  const go = useSwitch();
  const nav = useNavigate();
  return (
    <div className="fixed inset-x-0 top-0 z-40 flex h-10 items-center gap-3 bg-signal px-3 text-[13px] text-ink sm:px-5">
      <span className="hidden font-semibold sm:inline">Preview with sample data</span>
      <span className="hidden text-ink/70 md:inline">Changes stay until you reload.</span>
      <span className="ml-auto text-ink/75">Signed in as</span>
      <Menu>
        <MenuTrigger asChild>
          <button type="button" className="flex items-center gap-1 rounded-md bg-ink px-2.5 py-1 font-semibold text-white">{label(user?.role)}<ChevronDown className="h-3.5 w-3.5" /></button>
        </MenuTrigger>
        <MenuContent className="max-h-[70vh] overflow-y-auto">
          <MenuLabel>Staff</MenuLabel>
          {STAFF.map(([k, l]) => <MenuItem key={k} onSelect={() => go(k)} className={cn(user?.role === k && "font-semibold")}>{l}</MenuItem>)}
          <MenuSeparator />
          <MenuLabel>Portals</MenuLabel>
          {PORTAL.map(([k, l]) => <MenuItem key={k} onSelect={() => go(k)} className={cn(user?.role === k && "font-semibold")}>{l}</MenuItem>)}
        </MenuContent>
      </Menu>
      <button type="button" onClick={() => nav("/")} className="hidden items-center gap-1 rounded-md px-2 py-1 font-medium hover:bg-ink/10 sm:flex"><ExternalLink className="h-3.5 w-3.5" />Website</button>
      <button type="button" onClick={() => window.location.reload()} className="flex items-center gap-1 rounded-md px-2 py-1 font-medium hover:bg-ink/10" title="Reload the sample data"><RotateCcw className="h-3.5 w-3.5" /><span className="hidden sm:inline">Reset</span></button>
    </div>
  );
}

// Shortcuts on the sign-in pages
export function DemoPicker({ staff }) {
  const go = useSwitch();
  const list = staff ? STAFF.filter(([k]) => ["director", "sales", "project_manager", "site_engineer", "accounts", "store", "technician", "hr"].includes(k)) : PORTAL;
  return (
    <div className="rounded-xl border border-signal/60 bg-signal-soft/60 p-4">
      <p className="text-sm font-semibold">Preview: sign in with one tap</p>
      <p className="mt-0.5 text-xs text-ink/70">{staff ? "Every role sees its own menu and permissions. Switch roles any time from the yellow bar." : "Each portal shows only that customer's or partner's records."}</p>
      <div className="mt-3 grid grid-cols-2 gap-2">
        {list.map(([k, l]) => (
          <button key={k} type="button" onClick={() => go(k)} className="flex items-center gap-1.5 rounded-md border border-ink/15 bg-white px-2.5 py-2 text-left text-[13px] font-medium hover:border-ink/40"><LogIn className="h-3.5 w-3.5 shrink-0 text-ink/60" />{l}</button>
        ))}
      </div>
      <p className="mt-3 text-xs text-ink/60">Or type a demo login, e.g. {staff ? "director" : "client"}@demo.sellandiammanpowerinfra.test, password Demo@12345.</p>
    </div>
  );
}

// ------------------------------------------------------------------ file viewer (PDFs, exports)
let current = null;
const subs = new Set();
const setCurrent = (v) => { current = v; subs.forEach((f) => f()); };
export const showFile = (f) => setCurrent(f);

export function FileViewer() {
  const f = useSyncExternalStore((cb) => { subs.add(cb); return () => subs.delete(cb); }, () => current);
  if (!f) return null;
  return (
    <Dialog open onOpenChange={(x) => !x && setCurrent(null)} wide title={f.title} description={f.note}
      footer={<>{f.url && !IN_FRAME && <Button as="a" href={f.url} download={f.name} variant="outline"><Download className="h-4 w-4" />Download</Button>}<Button onClick={() => setCurrent(null)}>Close</Button></>}>
      {f.kind === "pdf" && f.pages?.length ? (
        <div className="max-h-[68vh] space-y-3 overflow-y-auto rounded-md bg-canvas p-3">
          {f.pages.map((src, i) => <img key={src} src={src} alt={`Page ${i + 1}`} className="mx-auto w-full max-w-[720px] rounded bg-white shadow-card" loading="lazy" />)}
        </div>
      ) : f.kind === "pdf" ? (
        <object data={f.url} type="application/pdf" className="h-[68vh] w-full rounded-md border border-edge bg-canvas">
          <div className="flex h-40 flex-col items-center justify-center gap-2 text-sm text-muted"><FileText className="h-6 w-6" />This browser can't show the PDF here.</div>
        </object>
      ) : f.kind === "text" ? (
        <pre className="max-h-[60vh] overflow-auto rounded-md bg-canvas p-3 text-xs">{f.text}</pre>
      ) : <p className="text-sm text-muted">{f.text}</p>}
    </Dialog>
  );
}
export { S };
