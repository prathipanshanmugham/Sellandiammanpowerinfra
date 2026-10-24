import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Eye, EyeOff, KeyRound, ArrowLeft } from "lucide-react";
import { api, errMsg, IS_DEMO } from "@/lib/api";
import { useAuth, homeFor } from "@/lib/auth";
import { useTitle, cn } from "@/lib/utils";
import { Button, Input, Field, Alert } from "@/components/ui/kit";
import { Logo } from "@/components/brand/Logo";
import SLD from "@/components/public/SLD";

// Demo-only: the preview build fills this with sign-in shortcuts for every role.
let demoPicker = null;
export const setDemoPicker = (C) => { demoPicker = C; };

function Shell({ children, staff }) {
  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-[1fr_minmax(0,560px)]">
      <div className="relative hidden overflow-hidden bg-ink lg:block">
        <div className="absolute inset-0 flex items-center justify-center p-16 opacity-90"><SLD className="h-full max-h-[620px] w-auto" /></div>
        <div className="absolute bottom-10 start-10 end-10 text-white">
          <p className="font-display text-[26px] font-extrabold leading-tight text-white">{staff ? "Every project, store and bill in one place." : "Your project, drawings, bills and service in one place."}</p>
          <p className="mt-2 text-white/75">{staff ? "Sign in with your company email." : "Approvals, progress photos, invoices and breakdown requests."}</p>
        </div>
      </div>
      <div className="flex flex-col px-5 py-8 sm:px-10">
        <Link to="/" className="self-start" aria-label="Back to the website"><Logo theme="light" /></Link>
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-10">{children}</div>
        <p className="text-center text-xs text-muted">© {new Date().getFullYear()} Sellandiamman Power Infra</p>
      </div>
    </div>
  );
}

export function LoginPage({ staff = false }) {
  const { login, user } = useAuth();
  const nav = useNavigate();
  const [sp] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [mfa, setMfa] = useState(false);
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useTitle(staff ? "Staff sign in" : "Client & partner sign in");
  useEffect(() => { if (user) nav(sp.get("next") || homeFor(user), { replace: true }); }, [user]); // eslint-disable-line react-hooks/exhaustive-deps
  async function go(e) {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const r = await login(email.trim(), password, mfa ? code : undefined, !staff);
      if (r.mfa) { setMfa(true); setBusy(false); return; }
      nav(sp.get("next") || homeFor(r.user), { replace: true });
    } catch (ex) { setErr(errMsg(ex)); } finally { setBusy(false); }
  }
  const Picker = IS_DEMO ? demoPicker : null;
  return (
    <Shell staff={staff}>
      <h1 className="text-[28px] font-extrabold">{staff ? "Staff sign in" : "Sign in"}</h1>
      <p className="mt-1 text-sm text-muted">{staff ? "For Sellandiamman Power Infra employees." : "For clients, consultants, vendors, subcontractors and referral partners."}</p>
      {Picker && <div className="mt-6"><Picker staff={staff} /></div>}
      <form onSubmit={go} className="mt-6 space-y-4" noValidate>
        {!mfa ? (
          <>
            <Field label="Email" htmlFor="email"><Input id="email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus={!Picker} /></Field>
            <Field label="Password" htmlFor="pw">
              <div className="relative">
                <Input id="pw" type={show ? "text" : "password"} autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required className="pe-10" />
                <button type="button" onClick={() => setShow((x) => !x)} className="absolute end-2 top-1/2 -translate-y-1/2 rounded p-1.5 text-muted hover:text-fg" aria-label={show ? "Hide password" : "Show password"}>{show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button>
              </div>
            </Field>
          </>
        ) : (
          <Field label="6-digit code from your authenticator app" hint="Or one of your recovery codes" htmlFor="code">
            <Input id="code" inputMode="numeric" autoComplete="one-time-code" value={code} onChange={(e) => setCode(e.target.value)} autoFocus className="text-center text-lg tracking-[0.3em] tabular" />
          </Field>
        )}
        {err && <Alert tone="red">{err}</Alert>}
        <Button type="submit" size="lg" className="w-full" loading={busy}>{mfa ? "Verify and sign in" : "Sign in"}</Button>
        {mfa && <Button type="button" variant="ghost" className="w-full" onClick={() => { setMfa(false); setCode(""); }}><ArrowLeft className="rtl:-scale-x-100 h-4 w-4" />Use a different account</Button>}
      </form>
      <div className="mt-6 flex flex-wrap justify-between gap-2 text-sm">
        <Link to={`/forgot-password${staff ? "?staff=1" : ""}`} className="text-cable hover:underline">Forgot password?</Link>
        {staff ? <Link to="/login" className="text-muted hover:text-fg">Client sign in</Link> : <Link to="/erp/login" className="text-muted hover:text-fg">Staff sign in</Link>}
      </div>
      {!staff && <p className="mt-6 rounded-lg bg-paper p-3 text-sm text-muted">No login yet? Your project manager or our office sends you a link to set a password once your project or contract starts.</p>}
    </Shell>
  );
}

export function ForgotPage() {
  const [sp] = useSearchParams();
  const [email, setEmail] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useTitle("Reset password");
  return (
    <Shell staff={sp.get("staff") === "1"}>
      <h1 className="text-[28px] font-extrabold">Reset your password</h1>
      <p className="mt-1 text-sm text-muted">We'll email a link to set a new password. It works for 24 hours.</p>
      {msg ? <Alert tone="green" className="mt-6">{msg}</Alert> : (
        <form className="mt-6 space-y-4" onSubmit={async (e) => { e.preventDefault(); setBusy(true); setErr(""); try { setMsg((await api.post("/auth/forgot", { email })).data.message); } catch (ex) { setErr(errMsg(ex)); } finally { setBusy(false); } }}>
          <Field label="Email"><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus /></Field>
          {err && <Alert tone="red">{err}</Alert>}
          <Button type="submit" size="lg" className="w-full" loading={busy}>Send the link</Button>
        </form>
      )}
      <Link to={sp.get("staff") === "1" ? "/erp/login" : "/login"} className="mt-6 inline-flex items-center gap-1 text-sm text-cable hover:underline"><ArrowLeft className="rtl:-scale-x-100 h-3.5 w-3.5" />Back to sign in</Link>
    </Shell>
  );
}

export function SetPasswordPage() {
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(null);
  useTitle("Set your password");
  const strong = pw.length >= 10 && /[A-Z]/.test(pw) && /\d/.test(pw);
  async function go(e) {
    e.preventDefault();
    if (pw !== pw2) { setErr("The two passwords don't match"); return; }
    setBusy(true); setErr("");
    try { setDone(await api.post("/auth/set-password", { token: sp.get("token"), password: pw }).then((r) => r.data)); } catch (ex) { setErr(errMsg(ex)); } finally { setBusy(false); }
  }
  return (
    <Shell>
      <h1 className="text-[28px] font-extrabold">Set your password</h1>
      {done ? (
        <div className="mt-6 space-y-4"><Alert tone="green">Password saved. Sign in with your email and the new password.</Alert><Button size="lg" className="w-full" onClick={() => nav(done.portal ? "/login" : "/erp/login")}>Go to sign in</Button></div>
      ) : (
        <form className="mt-6 space-y-4" onSubmit={go}>
          <Field label="New password" hint="At least 10 characters, with a capital letter and a number">
            <Input type="password" autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)} required autoFocus />
          </Field>
          <div className={cn("h-1.5 rounded-full bg-fg/10")}><div className={cn("h-full rounded-full transition-all", strong ? "w-full bg-good" : pw.length >= 6 ? "w-2/3 bg-amber" : pw ? "w-1/3 bg-bad" : "w-0")} /></div>
          <Field label="Type it again"><Input type="password" autoComplete="new-password" value={pw2} onChange={(e) => setPw2(e.target.value)} required /></Field>
          {err && <Alert tone="red">{err}</Alert>}
          <Button type="submit" size="lg" className="w-full" loading={busy} disabled={!strong}><KeyRound className="h-4 w-4" />Save password</Button>
        </form>
      )}
    </Shell>
  );
}
