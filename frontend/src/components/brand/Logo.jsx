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
// The full-size lockup is about 240 px wide, so below 400 px (small phones) it scales down to about 195 px to leave
// room for the language and menu buttons in the header.
const SIZES = {
  full: { gap: "gap-2 min-[400px]:gap-2.5", mark: "h-[22px] min-[400px]:h-7 sm:h-8", word: "h-[9px] min-[400px]:h-[11px] sm:h-[13px]", sub: "mt-1 text-[7.5px] min-[400px]:mt-[5px] min-[400px]:text-[9.5px] sm:text-[10.5px]" },
  compact: { gap: "gap-2.5", mark: "h-6", word: "h-[10px]", sub: "mt-[5px] text-[8.5px]" },
};
export function Logo({ theme = "dark", className, compact }) {
  const c = COLORS[theme];
  const z = SIZES[compact ? "compact" : "full"];
  return (
    <span className={cn("inline-flex items-center", z.gap, className)}>
      <Mark theme={theme} className={cn("w-auto shrink-0", z.mark)} />
      <span className="flex flex-col justify-center leading-none">
        <svg viewBox={`0 0 ${WORD.w} ${WORD.h}`} className={cn("w-auto", z.word)} aria-hidden>
          <path fill={c.word} fillRule="evenodd" d={WORD.d} />
        </svg>
        <span className={cn("whitespace-nowrap font-display font-bold", z.sub)} style={{ color: c.sub, letterSpacing: "0.42em" }}>POWER INFRA</span>
      </span>
      <span className="sr-only">Sellandiamman Power Infra</span>
    </span>
  );
}
