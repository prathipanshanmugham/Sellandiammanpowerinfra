/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  // Our own attribute, so a page that hosts the preview (and sets data-theme on <html>) can't flip our colours.
  darkMode: ["class", '[data-spi-theme="dark"]'],
  theme: {
    container: { center: true, padding: { DEFAULT: "1rem", md: "1.5rem" }, screens: { "2xl": "1240px" } },
    extend: {
      colors: {
        // Sellandiamman Estates' slate palette, with the logo's yellow as the one accent (Estates uses its red).
        // Yellow is a fill or a mark on dark; text on yellow is always ink, and yellow text never sits on white.
        ink: { DEFAULT: "#0F172A", 900: "#0B1120", 800: "#1E293B", 700: "#334155", 600: "#475569", 500: "#64748B" },
        signal: { DEFAULT: "#FFC400", deep: "#E5AE00", bright: "#FFCC1F", soft: "#FFF6D1", ink: "#6B4E00" },
        amber: { DEFAULT: "#EA580C", soft: "#FFEDD5", ink: "#9A3412" },
        steel: { DEFAULT: "#94A3B8", dark: "#64748B", light: "#CBD5E1" },
        paper: "#F8FAFC",
        line: "#E2E8F0",
        cable: { DEFAULT: "#0F172A", light: "#F1F5F9" },
        good: "#15803D", warn: "#B45309", bad: "#B91C1C",
        surface: "rgb(var(--surface) / <alpha-value>)",
        fg: "rgb(var(--fg) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)",
        edge: "rgb(var(--edge) / <alpha-value>)",
        canvas: "rgb(var(--canvas) / <alpha-value>)",
      },
      fontFamily: {
        // per-language stacks live in index.css (--font-sans / --font-display)
        display: ["var(--font-display)"],
        sans: ["var(--font-sans)"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      // a step larger than Tailwind's defaults, for easy reading
      fontSize: {
        "2xs": ["0.75rem", "1.05rem"],
        xs: ["0.8125rem", "1.2rem"],
        sm: ["0.9375rem", "1.45rem"],
        base: ["1.0625rem", "1.7rem"],
        lg: ["1.1875rem", "1.75rem"],
        xl: ["1.3125rem", "1.8rem"],
      },
      // Estates keeps corners nearly square
      borderRadius: { sm: "2px", DEFAULT: "3px", md: "3px", lg: "4px", xl: "4px", "2xl": "6px", "3xl": "8px" },
      boxShadow: { card: "0 1px 2px rgba(15,23,42,.06)", pop: "0 16px 40px -12px rgba(15,23,42,.28)" },
      keyframes: {
        energise: { from: { strokeDashoffset: "var(--len)" }, to: { strokeDashoffset: "0" } },
        glow: { "0%,100%": { opacity: ".35" }, "50%": { opacity: "1" } },
      },
      animation: { energise: "energise 2.4s cubic-bezier(.6,.05,.3,1) forwards" },
    },
  },
  plugins: [],
};
