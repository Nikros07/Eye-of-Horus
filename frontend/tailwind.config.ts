import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#05070A",
          900: "#080B10",
          850: "#0A0E14",
          800: "#0D121A",
          700: "#121822",
          600: "#1A222E",
          500: "#242D3B",
        },
        border: {
          DEFAULT: "rgba(255,255,255,0.08)",
          strong: "rgba(255,255,255,0.14)",
          faint: "rgba(255,255,255,0.05)",
        },
        text: {
          primary: "#E9ECF2",
          secondary: "#9AA3B2",
          // Lightened from #5D6674 (~3.5:1 on the app background, below the
          // 4.5:1 WCAG AA floor for normal text) to ~5.3:1 — this token is
          // used for uppercase labels and meta text everywhere, so it was
          // the single highest-impact contrast fix in the app.
          tertiary: "#7C8598",
          // Was referenced as `text-text-faint` in AlertTicker but never
          // defined here, so Tailwind silently dropped the class and those
          // three spots rendered in the inherited (bright) text-primary
          // color instead of the intended subdued tone.
          faint: "#59626E",
        },
        gold: {
          DEFAULT: "#D8B36C",
          bright: "#EACB8C",
          dim: "#8A6F42",
        },
        danger: {
          DEFAULT: "#E5555C",
          bright: "#F17178",
          dim: "#7A2E32",
        },
        info: {
          DEFAULT: "#5B8DEF",
          bright: "#82AAF5",
          dim: "#2E4A82",
        },
        signal: {
          DEFAULT: "#8B7FE8",
          bright: "#AEA4F2",
          dim: "#4A4380",
        },
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Inter",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "SF Mono",
          "Menlo",
          "Consolas",
          "Liberation Mono",
          "monospace",
        ],
      },
      boxShadow: {
        card: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 20px 60px -20px rgba(0,0,0,0.6)",
        "card-hover": "0 1px 0 0 rgba(255,255,255,0.06) inset, 0 30px 80px -20px rgba(0,0,0,0.75)",
        glow: "0 0 40px -10px rgba(216,179,108,0.35)",
      },
      backgroundImage: {
        "radial-fade": "radial-gradient(circle at 50% 0%, rgba(216,179,108,0.08), transparent 60%)",
        "grid-lines":
          "linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)",
      },
      keyframes: {
        pulseRing: {
          "0%": { transform: "scale(0.6)", opacity: "0.8" },
          "100%": { transform: "scale(2.4)", opacity: "0" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        floatY: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-4px)" },
        },
      },
      animation: {
        pulseRing: "pulseRing 2.4s cubic-bezier(0.2,0.6,0.4,1) infinite",
        shimmer: "shimmer 2.5s linear infinite",
        floatY: "floatY 6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
