import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { api, clearCache } from "./api";
import { Spinner } from "@/components/ui/kit";

const Ctx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined);
  const [meta, setMeta] = useState(null);
  const loadMeta = useCallback(async () => {
    try { const r = await api.get("/meta"); setMeta(r.data); } catch { setMeta(null); }
  }, []);
  const refresh = useCallback(async () => {
    try {
      const r = await api.get("/auth/me");
      setUser(r.data.user);
      return r.data.user;
    } catch { setUser(null); return null; }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => { if (user) loadMeta(); else setMeta(null); }, [user?.id, user?.role, loadMeta]); // eslint-disable-line react-hooks/exhaustive-deps
  const login = useCallback(async (email, password, code, portal) => {
    const r = await api.post("/auth/login", { email, password, code, portal });
    if (r.data.mfa_required) return { mfa: true };
    setUser(r.data.user);
    return { user: r.data.user };
  }, []);
  const logout = useCallback(async () => {
    try { await api.post("/auth/logout"); } catch { /* ignore */ }
    clearCache();
    setUser(null);
  }, []);
  const can = useCallback((module, action = "r") => !!user && (user.permissions?.[module] || "").includes(action), [user]);
  const value = useMemo(() => ({ user, meta, login, logout, refresh, can, setUser, reloadMeta: loadMeta }), [user, meta, login, logout, refresh, can, loadMeta]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);

export const PORTAL_HOME = { client: "/client", consultant: "/consultant", vendor: "/vendor", subcontractor: "/subcontractor", partner: "/partner" };
export const homeFor = (u) => (!u ? "/" : u.portal ? PORTAL_HOME[u.role] || "/client" : "/erp");

function Wait() {
  return <div className="flex min-h-[60vh] items-center justify-center"><Spinner label="Loading" /></div>;
}

export function RequireStaff({ children }) {
  const { user } = useAuth();
  const loc = useLocation();
  if (user === undefined) return <Wait />;
  if (!user) return <Navigate to={`/erp/login?next=${encodeURIComponent(loc.pathname + loc.search)}`} replace />;
  if (user.portal) return <Navigate to={homeFor(user)} replace />;
  if (user.mfa_setup_required && !loc.pathname.startsWith("/erp/me")) return <Navigate to="/erp/me?setup=mfa" replace />;
  return children;
}

export function RequirePortal({ roles, children }) {
  const { user } = useAuth();
  const loc = useLocation();
  if (user === undefined) return <Wait />;
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(loc.pathname)}`} replace />;
  if (!user.portal) return <Navigate to="/erp" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to={homeFor(user)} replace />;
  return children;
}
