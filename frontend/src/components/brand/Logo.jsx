import { MARK, WORD, COLORS } from "./paths";
import { cn } from "@/lib/utils";

export function Mark({ theme = "dark", className, title = "Sellandiamman" }) {
  const c = COLORS[theme];
  return (
    <svg viewBox={`0 0 ${MARK.w} ${MARK.h}`} className={className} role="img" aria-label={title}>
      <path fill={c.s} fillRule="evenodd" d={MARK.s} />
      <path fill={c.a} fillRule="evenodd" d={MARK.a} />
    </svg>
  );
}

// Horizontal lockup: SA mark, SELLANDIAMMAN wordmark (traced from the artwork) and "Power Infra".
export function Logo({ theme = "dark", className, compact }) {
  const c = COLORS[theme];
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <Mark theme={theme} className={cn("w-auto shrink-0", compact ? "h-6" : "h-7 sm:h-8")} />
      <span className="flex flex-col justify-center leading-none">
        <svg viewBox={`0 0 ${WORD.w} ${WORD.h}`} className={cn("w-auto", compact ? "h-[10px]" : "h-[11px] sm:h-[13px]")} aria-hidden>
          <path fill={c.word} fillRule="evenodd" d={WORD.d} />
        </svg>
        <span className={cn("mt-[5px] font-display font-bold", compact ? "text-[8.5px]" : "text-[9.5px] sm:text-[10.5px]")} style={{ color: c.sub, letterSpacing: "0.42em" }}>POWER INFRA</span>
      </span>
      <span className="sr-only">Sellandiamman Power Infra</span>
    </span>
  );
}
