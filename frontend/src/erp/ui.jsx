import { useEffect } from "react";
import { Link } from "react-router-dom";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";
import { inr, num, pct } from "@/lib/format";
import { Icon } from "@/components/ui/icons";

export function usePageTitle(title, enabled = true) {
  useEffect(() => {
    if (enabled && title) document.title = `${title} | SPI ERP`;
  }, [title, enabled]);
}

export function PageHead({ title, sub, icon, actions, back, children, className }) {
  return (
    <div className={cn("mb-5 flex flex-wrap items-start justify-between gap-3", className)}>
      <div className="min-w-0">
        {back && <Link to={back[0]} className="mb-1 inline-block text-sm text-muted hover:text-fg">{back[1]}</Link>}
        <h1 className="flex items-center gap-2.5 font-display text-[22px] font-extrabold leading-tight md:text-[26px]">
          {icon && <span className="hidden h-8 w-8 shrink-0 items-center justify-center rounded-md bg-ink text-signal-bright sm:flex"><Icon name={icon} className="h-4 w-4" /></span>}
          <span className="min-w-0 break-words">{title}</span>
        </h1>
        {sub && <p className="mt-1 max-w-2xl text-sm text-muted">{sub}</p>}
        {children}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function fmtBy(fmt, v) {
  if (v === null || v === undefined) return "—";
  if (fmt === "inr") return inr(v, { compact: true });
  if (fmt === "pct") return pct(v);
  if (fmt === "int") return num(v, 0);
  if (fmt === "days") return `${num(v)} d`;
  if (fmt === "min") return `${num(v, 0)} min`;
  return typeof v === "number" ? num(v) : String(v);
}

export function Kpi({ label, value, fmt, sub, link, change, good = "up", tone, className }) {
  const up = change > 0;
  const better = change === 0 || change === null || change === undefined ? null : (good === "up" ? up : !up);
  const body = (
    <div className={cn("h-full rounded-xl border border-edge bg-surface p-4 shadow-card", link && "transition-colors hover:border-fg/25", className)}>
      <p className="text-[14px] text-muted">{label}</p>
      <p className={cn("mt-1.5 font-display text-[26px] font-extrabold leading-none tabular tracking-tight", tone === "bad" && "text-bad", tone === "good" && "text-good", tone === "warn" && "text-warn")}>{fmtBy(fmt, value)}</p>
      {(sub || change !== undefined) && (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-muted">
          {change !== undefined && change !== null && (
            <span className={cn("inline-flex items-center gap-0.5 font-medium", better === true && "text-good", better === false && "text-bad")}>
              {change > 0 ? <TrendingUp className="h-3.5 w-3.5" /> : change < 0 ? <TrendingDown className="h-3.5 w-3.5" /> : <Minus className="h-3.5 w-3.5" />}{pct(Math.abs(change), 0)}
            </span>
          )}
          {sub}
        </p>
      )}
    </div>
  );
  return link ? <Link to={link} className="block">{body}</Link> : body;
}

export function Panel({ title, sub, actions, children, className, bodyClass, id }) {
  return (
    <section id={id} className={cn("rounded-xl border border-edge bg-surface shadow-card", className)}>
      {(title || actions) && (
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-edge px-4 py-3">
          <div className="min-w-0"><h2 className="font-sans text-[16px] font-semibold tracking-normal">{title}</h2>{sub && <p className="text-xs text-muted">{sub}</p>}</div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className={cn("p-4", bodyClass)}>{children}</div>
    </section>
  );
}

// A simple table for computed screens (finance, stock, reports)
export function Table({ columns, rows, empty = "Nothing here", onRow, foot, dense, className }) {
  if (!rows?.length) return <p className="px-1 py-6 text-center text-sm text-muted">{empty}</p>;
  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="w-full text-[14px]">
        <thead className="border-b border-edge text-left text-xs text-muted">
          <tr>{columns.map((c) => <th key={c.key || c.label} scope="col" className={cn("whitespace-nowrap px-3 font-medium", dense ? "py-1.5" : "py-2", c.right && "text-right")}>{c.label}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-edge">
          {rows.map((r, i) => (
            <tr key={r.id || i} onClick={onRow ? () => onRow(r) : undefined} className={cn(onRow && "cursor-pointer hover:bg-canvas/70", r._tone === "bad" && "bg-bad/[.04]")}>
              {columns.map((c) => <td key={c.key || c.label} className={cn("px-3", dense ? "py-1.5" : "py-2.5", c.right && "whitespace-nowrap text-right tabular", c.className)}>{c.render ? c.render(r, i) : r[c.key] ?? "—"}</td>)}
            </tr>
          ))}
        </tbody>
        {foot && <tfoot className="border-t border-edge font-semibold"><tr>{columns.map((c, i) => <td key={c.key || c.label} className={cn("px-3 py-2", c.right && "text-right tabular")}>{foot[i] ?? ""}</td>)}</tr></tfoot>}
      </table>
    </div>
  );
}

export const Money = ({ v, compact, className }) => <span className={cn("tabular", className)}>{inr(v, { compact })}</span>;

export function Bar({ value, max, tone = "ink", className }) {
  const w = max ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  return <div className={cn("h-2 w-full rounded-full bg-fg/[.07]", className)}><div className={cn("h-full rounded-full", tone === "signal" ? "bg-signal" : tone === "amber" ? "bg-amber" : tone === "good" ? "bg-good" : tone === "bad" ? "bg-bad" : tone === "cable" ? "bg-cable" : "bg-ink")} style={{ width: `${w}%` }} /></div>;
}

export const RISK = { green: ["green", "On track"], amber: ["amber", "Watch"], red: ["red", "At risk"] };
