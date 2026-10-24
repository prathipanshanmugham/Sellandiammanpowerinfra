// The staff menu: special screens first in each section, then every list this role may open (from /api/meta).
export const SPECIAL = {
  Home: [
    { to: "/erp", label: "Dashboard", icon: "gauge", end: true, need: ["dashboard", "r"] },
    { to: "/erp/ceo", label: "CEO view", icon: "activity", need: ["ceo", "r"] },
    { to: "/erp/approvals", label: "Approvals", icon: "stamp", need: ["approvals", "r"], badge: "approvals" },
    { to: "/erp/calendar", label: "Expiry calendar", icon: "calendar-clock", need: ["dashboard", "r"] },
    { to: "/erp/reports", label: "Reports", icon: "file-spreadsheet", need: ["reports", "r"] },
    { to: "/erp/tools", label: "Calculators", icon: "calculator", need: ["calculators", "r"] },
  ],
  Sales: [
    { to: "/erp/crm", label: "Pipeline", icon: "route", need: ["crm", "r"] },
    { to: "/erp/marketing", label: "Marketing results", icon: "megaphone", need: ["marketing", "r"] },
  ],
  Stores: [{ to: "/erp/stores", label: "Stock on hand", icon: "boxes", need: ["stores", "r"] }],
  "Service & AMC": [{ to: "/erp/service", label: "Service desk", icon: "life-buoy", need: ["service", "r"] }],
  Finance: [{ to: "/erp/finance", label: "Finance overview", icon: "landmark", need: ["finance", "r"] }],
  Documents: [{ to: "/erp/vault", label: "Password vault", icon: "file-lock-2", need: ["vault", "r"] }],
  Website: [{ to: "/erp/website", label: "Website editor", icon: "newspaper", need: ["cms", "r"] }],
  Settings: [
    { to: "/erp/settings", label: "Company settings", icon: "cog", need: ["settings", "r"] },
    { to: "/erp/users", label: "Users & roles", icon: "users-round", need: ["users", "r"] },
    { to: "/erp/audit", label: "Activity log", icon: "list-checks", need: ["audit", "r"] },
  ],
};
// Lists that read better without their own menu entry (reached from their parent record)
const HIDE = new Set(["approvals", "vendor_quotes", "stock_moves", "credit_notes", "handovers"]);

export function buildNav(meta, user) {
  if (!meta || !user) return [];
  const can = (m, a) => (user.permissions?.[m] || "").includes(a);
  const sections = [];
  for (const name of meta.nav_order) {
    const items = (SPECIAL[name] || []).filter((x) => !x.need || can(...x.need)).map((x) => ({ ...x, special: true }));
    for (const [k, e] of Object.entries(meta.entities)) {
      if (e.nav !== name || HIDE.has(k) || !(e.perm || "").includes("r")) continue;
      items.push({ to: `/erp/e/${k}`, label: e.plural, icon: e.icon, key: k });
    }
    if (items.length) sections.push({ name, items });
  }
  return sections;
}

// The special screen (if any) for this address, so the layout can show "no access" instead of a broken page
export function specialFor(pathname) {
  const all = Object.values(SPECIAL).flat();
  return all.find((x) => x.to === pathname) || all.filter((x) => x.to !== "/erp" && pathname.startsWith(`${x.to}/`)).sort((a, b) => b.to.length - a.to.length)[0] || null;
}
