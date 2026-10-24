/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    container: { center: true, padding: { DEFAULT: "1rem", md: "1.5rem" }, screens: { "2xl": "1240px" } },
    extend: {
      colors: {
        ink: { DEFAULT: "#0A1626", 900: "#06101D", 800: "#0E1D31", 700: "#16283F", 600: "#22374F", 500: "#3A4D66" },
        signal: { DEFAULT: "#FFC400", deep: "#E0A800", soft: "#FFF4CC", ink: "#5C4300" },
        steel: { DEFAULT: "#A9ADB3", dark: "#80858C", light: "#D4D7DB" },
        paper: "#F4F6F9",
        line: "#D6DCE4",
        cable: { DEFAULT: "#1E4D7B", light: "#E8F0F8" },
        good: "#1F7A4D", warn: "#B26B00", bad: "#B42318",
        surface: "rgb(var(--surface) / <alpha-value>)",
        fg: "rgb(var(--fg) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)",
        edge: "rgb(var(--edge) / <alpha-value>)",
        canvas: "rgb(var(--canvas) / <alpha-value>)",
      },
      fontFamily: {
        display: ["Montserrat", "Noto Sans Tamil", "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ["Inter", "Noto Sans Tamil", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      fontSize: { "2xs": ["0.6875rem", "1rem"] },
      boxShadow: { card: "0 1px 2px rgba(10,22,38,.06), 0 1px 1px rgba(10,22,38,.04)", pop: "0 12px 32px -8px rgba(10,22,38,.28)" },
      keyframes: {
        energise: { from: { strokeDashoffset: "var(--len)" }, to: { strokeDashoffset: "0" } },
        glow: { "0%,100%": { opacity: ".35" }, "50%": { opacity: "1" } },
      },
      animation: { energise: "energise 2.4s cubic-bezier(.6,.05,.3,1) forwards" },
    },
  },
  plugins: [],
};
