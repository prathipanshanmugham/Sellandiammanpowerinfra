import { forwardRef, useState } from "react";
import * as RDialog from "@radix-ui/react-dialog";
import * as RDrop from "@radix-ui/react-dropdown-menu";
import * as RPop from "@radix-ui/react-popover";
import * as RTabs from "@radix-ui/react-tabs";
import * as RTip from "@radix-ui/react-tooltip";
import { X, Loader2, ChevronDown, Check, Inbox } from "lucide-react";
import { cn } from "@/lib/utils";

// ------------------------------------------------------------------ buttons
const BTN = {
  primary: "bg-signal text-ink hover:bg-signal-deep active:bg-signal-deep font-semibold",
  dark: "bg-ink text-white hover:bg-ink-700 font-semibold",
  outline: "border border-steel-light bg-surface text-fg hover:border-steel-dark hover:bg-canvas",
  ghost: "text-fg hover:bg-fg/5",
  danger: "bg-bad text-white hover:bg-bad/90 font-semibold",
  light: "border border-white/35 text-white hover:bg-white/10",
  link: "text-cable underline-offset-4 hover:underline px-0 h-auto",
};
// min heights, so a long translated label wraps onto a second line instead of running off a phone screen
const SIZE = { sm: "min-h-8 px-3 py-1 text-[14px] gap-1.5 rounded-md", md: "min-h-10 px-4 py-1.5 text-sm gap-2 rounded-md", lg: "min-h-12 px-6 py-2 text-[16px] gap-2 rounded-lg", icon: "h-9 w-9 rounded-md" };

export const Button = forwardRef(function Button({ variant = "primary", size = "md", loading, className, children, as: As = "button", ...p }, ref) {
  return (
    <As ref={ref} className={cn("inline-flex max-w-full select-none items-center justify-center text-center leading-tight transition-colors disabled:pointer-events-none disabled:opacity-50", BTN[variant], SIZE[size], className)}
      disabled={As === "button" ? p.disabled || loading : undefined} {...p}>
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
      {children}
    </As>
  );
});

export const IconButton = forwardRef(function IconButton({ label, className, children, ...p }, ref) {
  return (
    <button ref={ref} aria-label={label} title={label} className={cn("inline-flex h-9 w-9 items-center justify-center rounded-md text-fg/80 hover:bg-fg/5 hover:text-fg disabled:opacity-40", className)} {...p}>
      {children}
    </button>
  );
});

// ------------------------------------------------------------------ inputs
const FIELD = "w-full rounded-md border border-edge bg-surface px-3 text-fg placeholder:text-muted/70 focus:border-ink focus:outline-none focus:ring-2 focus:ring-signal/70 disabled:bg-canvas disabled:text-muted";
export const Input = forwardRef(function Input({ className, ...p }, ref) {
  return <input ref={ref} className={cn(FIELD, "h-10", className)} {...p} />;
});
export const Textarea = forwardRef(function Textarea({ className, rows = 3, ...p }, ref) {
  return <textarea ref={ref} rows={rows} className={cn(FIELD, "py-2 leading-relaxed", className)} {...p} />;
});
export const Select = forwardRef(function Select({ className, options = [], placeholder, children, ...p }, ref) {
  return (
    <div className="relative">
      <select ref={ref} className={cn(FIELD, "h-10 appearance-none pe-9", className)} {...p}>
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute end-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
    </div>
  );
});
export function Checkbox({ checked, onChange, label, className, id, disabled }) {
  return (
    <label className={cn("inline-flex cursor-pointer items-start gap-2.5 text-sm", disabled && "cursor-not-allowed opacity-60", className)} htmlFor={id}>
      <span className="relative mt-0.5 inline-flex">
        <input id={id} type="checkbox" className="peer sr-only" checked={!!checked} onChange={(e) => onChange?.(e.target.checked)} disabled={disabled} />
        <span className="flex h-[18px] w-[18px] items-center justify-center rounded border border-edge bg-surface peer-checked:border-signal peer-checked:bg-signal peer-focus-visible:ring-2 peer-focus-visible:ring-ink/50">
          {checked && <Check className="h-3 w-3 text-ink" strokeWidth={3} />}
        </span>
      </span>
      {label && <span className="leading-snug">{label}</span>}
    </label>
  );
}
export function Switch({ checked, onChange, label, disabled }) {
  return (
    <button type="button" role="switch" aria-checked={!!checked} disabled={disabled} onClick={() => onChange?.(!checked)}
      className="inline-flex items-center gap-2.5 text-sm disabled:opacity-50">
      <span className={cn("relative h-5 w-9 shrink-0 rounded-full transition-colors", checked ? "bg-signal" : "bg-steel")}>
        <span className={cn("absolute left-0 top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform", checked ? "translate-x-[18px]" : "translate-x-0.5")} />
      </span>
      {label}
    </button>
  );
}
export function Field({ label, hint, error, required, children, className, htmlFor }) {
  return (
    <div className={cn("min-w-0", className)}>
      {label && <label className="field-label" htmlFor={htmlFor}>{label}{required && <span className="text-bad"> *</span>}</label>}
      {children}
      {error ? <p className="mt-1 text-xs text-bad">{error}</p> : hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
    </div>
  );
}

// ------------------------------------------------------------------ display
const TONE = {
  gray: "bg-fg/[.06] text-fg/85", blue: "bg-signal-soft text-signal-ink", amber: "bg-amber-soft text-amber-ink", green: "bg-good/10 text-good",
  red: "bg-bad/10 text-bad", violet: "bg-[#EEEAFB] text-[#5B3FB8]", teal: "bg-[#E2F4F2] text-[#0F6B63]", ink: "bg-ink text-white", signal: "bg-signal text-ink",
};
export function Badge({ tone = "gray", className, children, dot }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium", TONE[tone] || TONE.gray, className)}>
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}
export function Card({ className, children, ...p }) {
  return <div className={cn("rounded-lg border border-edge bg-surface shadow-card", className)} {...p}>{children}</div>;
}
export function CardHead({ title, sub, actions, className }) {
  return (
    <div className={cn("flex items-start justify-between gap-3 border-b border-edge px-4 py-3", className)}>
      <div className="min-w-0">
        <h3 className="truncate font-sans text-[16px] font-semibold tracking-normal">{title}</h3>
        {sub && <p className="mt-0.5 text-xs text-muted">{sub}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}
export function Spinner({ className, label = "Loading" }) {
  return <span role="status" aria-label={label} className={cn("inline-flex items-center gap-2 text-sm text-muted", className)}><Loader2 className="h-4 w-4 animate-spin" />{label !== "Loading" && label}</span>;
}
export function Skeleton({ className }) { return <div className={cn("animate-pulse rounded-md bg-fg/[.07]", className)} />; }
export function Empty({ icon: Icon = Inbox, title, text, action, className }) {
  return (
    <div className={cn("flex flex-col items-center justify-center px-6 py-12 text-center", className)}>
      <Icon className="mb-3 h-8 w-8 text-steel" aria-hidden />
      <p className="font-medium text-fg">{title}</p>
      {text && <p className="mt-1 max-w-sm text-sm text-muted">{text}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
export function Alert({ tone = "amber", title, children, className, icon: Icon }) {
  const t = { amber: "border-amber/50 bg-amber-soft/70 text-amber-ink", red: "border-bad/30 bg-bad/5 text-bad", blue: "border-signal/25 bg-signal-soft text-signal-ink", green: "border-good/30 bg-good/5 text-good", gray: "border-edge bg-canvas text-fg/80" }[tone];
  return (
    <div className={cn("flex gap-3 rounded-lg border px-4 py-3 text-sm", t, className)} role="status">
      {Icon && <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />}
      <div className="min-w-0">{title && <p className="font-semibold">{title}</p>}<div className={title ? "mt-0.5 opacity-90" : ""}>{children}</div></div>
    </div>
  );
}
export function Progress({ value = 0, className, tone = "ink" }) {
  return (
    <div className={cn("h-1.5 w-full overflow-hidden rounded-full bg-fg/10", className)} role="progressbar" aria-valuenow={Math.round(value)} aria-valuemin={0} aria-valuemax={100}>
      <div className={cn("h-full rounded-full", tone === "signal" ? "bg-signal" : tone === "amber" ? "bg-amber" : tone === "good" ? "bg-good" : tone === "bad" ? "bg-bad" : "bg-ink")} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}
export function Kbd({ children }) { return <kbd className="rounded border border-edge bg-canvas px-1.5 py-0.5 font-sans text-[12px] text-muted">{children}</kbd>; }

// ------------------------------------------------------------------ overlays
export function Dialog({ open, onOpenChange, title, description, children, footer, wide, className }) {
  return (
    <RDialog.Root open={open} onOpenChange={onOpenChange}>
      <RDialog.Portal>
        <RDialog.Overlay className="fixed inset-0 z-50 bg-ink/50 backdrop-blur-[2px]" />
        <RDialog.Content className={cn("fixed left-1/2 top-1/2 z-50 flex max-h-[92vh] w-[calc(100vw-24px)] -translate-x-1/2 -translate-y-1/2 flex-col rounded-xl bg-surface shadow-pop focus:outline-none", wide ? "max-w-3xl" : "max-w-lg", className)}>
          <div className="flex items-start justify-between gap-4 border-b border-edge px-5 py-4">
            <div>
              <RDialog.Title className="font-display text-lg font-bold">{title}</RDialog.Title>
              {description ? <RDialog.Description className="mt-1 text-sm text-muted">{description}</RDialog.Description> : <RDialog.Description className="sr-only">{title}</RDialog.Description>}
            </div>
            <RDialog.Close asChild><IconButton label="Close"><X className="h-4 w-4" /></IconButton></RDialog.Close>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>
          {footer && <div className="flex flex-wrap items-center justify-end gap-2 border-t border-edge px-5 py-3">{footer}</div>}
        </RDialog.Content>
      </RDialog.Portal>
    </RDialog.Root>
  );
}
export function Sheet({ open, onOpenChange, title, description, children, footer, side = "right", className }) {
  return (
    <RDialog.Root open={open} onOpenChange={onOpenChange}>
      <RDialog.Portal>
        <RDialog.Overlay className="fixed inset-0 z-50 bg-ink/40" />
        <RDialog.Content className={cn("fixed inset-y-0 z-50 flex w-full flex-col bg-surface shadow-pop focus:outline-none sm:max-w-2xl", side === "right" ? "end-0" : "start-0", className)}>
          <div className="flex items-start justify-between gap-4 border-b border-edge px-5 py-4" style={{ paddingTop: "max(1rem, env(safe-area-inset-top))" }}>
            <div className="min-w-0">
              <RDialog.Title className="truncate font-display text-lg font-bold">{title}</RDialog.Title>
              {description ? <RDialog.Description className="mt-0.5 text-sm text-muted">{description}</RDialog.Description> : <RDialog.Description className="sr-only">{title}</RDialog.Description>}
            </div>
            <RDialog.Close asChild><IconButton label="Close"><X className="h-4 w-4" /></IconButton></RDialog.Close>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>
          {footer && <div className="flex flex-wrap items-center justify-end gap-2 border-t border-edge px-5 py-3" style={{ paddingBottom: "max(.75rem, env(safe-area-inset-bottom))" }}>{footer}</div>}
        </RDialog.Content>
      </RDialog.Portal>
    </RDialog.Root>
  );
}
export function Confirm({ open, onOpenChange, title, text, confirmLabel = "Confirm", tone = "primary", onConfirm, reason, reasonLabel = "Reason" }) {
  const [busy, setBusy] = useState(false);
  const [why, setWhy] = useState("");
  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) setWhy(""); onOpenChange(v); }} title={title} description={text}
      footer={<>
        <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
        <Button variant={tone === "danger" ? "danger" : "primary"} loading={busy} disabled={reason && !why.trim()}
          onClick={async () => { setBusy(true); try { await onConfirm(why); onOpenChange(false); setWhy(""); } finally { setBusy(false); } }}>{confirmLabel}</Button>
      </>}>
      {reason ? <Field label={reasonLabel} required><Textarea value={why} onChange={(e) => setWhy(e.target.value)} autoFocus /></Field> : <p className="text-sm text-muted">This can't be undone.</p>}
    </Dialog>
  );
}

export const Menu = RDrop.Root;
export const MenuTrigger = RDrop.Trigger;
export function MenuContent({ children, align = "end", className }) {
  return (
    <RDrop.Portal>
      <RDrop.Content align={align} sideOffset={6} className={cn("z-50 min-w-[200px] rounded-lg border border-edge bg-surface p-1 shadow-pop", className)}>{children}</RDrop.Content>
    </RDrop.Portal>
  );
}
export function MenuItem({ children, onSelect, className, danger, disabled }) {
  return (
    <RDrop.Item disabled={disabled} onSelect={onSelect} className={cn("flex cursor-pointer select-none items-center gap-2 rounded-md px-2.5 py-2 text-sm outline-none data-[disabled]:opacity-40 data-[highlighted]:bg-fg/5", danger && "text-bad", className)}>
      {children}
    </RDrop.Item>
  );
}
export const MenuSeparator = () => <RDrop.Separator className="my-1 h-px bg-edge" />;
export const MenuLabel = ({ children }) => <RDrop.Label className="px-2.5 py-1.5 text-xs text-muted">{children}</RDrop.Label>;

export const Popover = RPop.Root;
export const PopoverTrigger = RPop.Trigger;
export function PopoverContent({ children, className, align = "start" }) {
  return <RPop.Portal><RPop.Content align={align} sideOffset={6} className={cn("z-50 w-72 rounded-lg border border-edge bg-surface p-3 shadow-pop", className)}>{children}</RPop.Content></RPop.Portal>;
}

export function Tabs({ value, onValueChange, tabs, children, className, listClassName }) {
  return (
    <RTabs.Root value={value} onValueChange={onValueChange} className={className}>
      <RTabs.List className={cn("scrollbar-thin -mx-1 flex gap-1 overflow-x-auto border-b border-edge px-1", listClassName)}>
        {tabs.map((t) => (
          <RTabs.Trigger key={t.value} value={t.value}
            className="relative -mb-px flex shrink-0 items-center gap-1.5 whitespace-nowrap border-b-2 border-transparent px-3 py-2.5 text-sm text-muted hover:text-fg data-[state=active]:border-signal data-[state=active]:font-semibold data-[state=active]:text-fg">
            {t.label}{t.count !== undefined && t.count !== null && <span className="rounded-full bg-fg/[.07] px-1.5 text-[12px] font-medium text-muted">{t.count}</span>}
          </RTabs.Trigger>
        ))}
      </RTabs.List>
      {children}
    </RTabs.Root>
  );
}
export const TabPanel = ({ value, children, className }) => <RTabs.Content value={value} className={cn("pt-4 focus:outline-none", className)}>{children}</RTabs.Content>;

export function Tip({ text, children }) {
  return (
    <RTip.Provider delayDuration={250}>
      <RTip.Root>
        <RTip.Trigger asChild>{children}</RTip.Trigger>
        <RTip.Portal><RTip.Content sideOffset={6} className="z-50 max-w-xs rounded-md bg-ink px-2.5 py-1.5 text-xs text-white shadow-pop">{text}</RTip.Content></RTip.Portal>
      </RTip.Root>
    </RTip.Provider>
  );
}
