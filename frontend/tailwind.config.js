/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    container: { center: true, padding: { DEFAULT: "1rem", md: "1.5rem" }, screens: { "2xl": "1240px" } },
    extend: {
      colors: {
        // monochrome: cool near-black to white, with one electric blue accent
        ink: { DEFAULT: "#0E1013", 900: "#08090B", 800: "#16191D", 700: "#1F2328", 600: "#2C3137", 500: "#4A5058" },
        signal: { DEFAULT: "#0B5CFF", deep: "#0047D6", bright: "#5B95FF", soft: "#EAF1FF", ink: "#0A3DA8" },
        amber: { DEFAULT: "#E09B00", soft: "#FFF4D9", ink: "#6B4500" },
        steel: { DEFAULT: "#A3A8AF", dark: "#7A8088", light: "#D5D8DC" },
        paper: "#F3F4F6",
        line: "#DDE0E4",
        cable: { DEFAULT: "#0047D6", light: "#EAF1FF" },
        good: "#1B7A4B", warn: "#9A5B00", bad: "#B42318",
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
      boxShadow: { card: "0 1px 2px rgba(14,16,19,.06), 0 1px 1px rgba(14,16,19,.04)", pop: "0 16px 40px -10px rgba(14,16,19,.30)" },
      keyframes: {
        energise: { from: { strokeDashoffset: "var(--len)" }, to: { strokeDashoffset: "0" } },
        glow: { "0%,100%": { opacity: ".35" }, "50%": { opacity: "1" } },
      },
      animation: { energise: "energise 2.4s cubic-bezier(.6,.05,.3,1) forwards" },
    },
  },
  plugins: [],
};
