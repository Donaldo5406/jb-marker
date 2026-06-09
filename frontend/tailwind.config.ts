import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    container: { center: true, padding: "40px", screens: { "2xl": "1440px" } },
    extend: {
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
      colors: {
        surface: {
          DEFAULT: "#fdf8f8",
          dim: "#ddd9d8",
          bright: "#fdf8f8",
          "container-lowest": "#ffffff",
          "container-low": "#f7f3f2",
          container: "#f1edec",
          "container-high": "#ebe7e6",
          "container-highest": "#e5e2e1",
        },
        "on-surface": { DEFAULT: "#1c1b1b", variant: "#444748" },
        outline: { DEFAULT: "#747878", variant: "#c4c7c7" },
        primary: { DEFAULT: "#000000", container: "#1c1b1b" },
        "on-primary": "#ffffff",
        secondary: { DEFAULT: "#5e5e5e", container: "#e1dfdf" },
        "on-secondary": "#ffffff",
        error: { DEFAULT: "#ba1a1a", container: "#ffdad6" },
        "on-error": "#ffffff",
        background: "#fdf8f8",
        severity: {
          critical: "#ba1a1a",
          "critical-bg": "#fdeceb",
          "critical-fg": "#8c1414",
          warning: "#9a6212",
          "warning-bg": "#fbf1df",
          "warning-fg": "#6b4410",
          ok: "#1f7a4d",
          "ok-bg": "#e7f4ec",
          "ok-fg": "#155f3a",
          info: "#2563eb",
          "info-bg": "#eaf0fe",
          "info-fg": "#1a47b8",
        },
      },
      fontSize: {
        h1: ["64px", { lineHeight: "1.1", letterSpacing: "-0.02em", fontWeight: "600" }],
        h2: ["40px", { lineHeight: "1.2", letterSpacing: "-0.01em", fontWeight: "500" }],
        h3: ["24px", { lineHeight: "1.3", fontWeight: "500" }],
        "body-lg": ["16px", { lineHeight: "1.6" }],
        "body-sm": ["14px", { lineHeight: "1.6" }],
        caption: ["12px", { lineHeight: "1.4", letterSpacing: "0.02em", fontWeight: "600" }],
      },
      borderRadius: {
        sm: "0.25rem",
        DEFAULT: "0.5rem",
        md: "0.75rem",
        lg: "1rem",
        xl: "1.5rem",
        full: "9999px",
      },
      spacing: { gutter: "24px", "margin-x": "40px", header: "72px" },
      maxWidth: { container: "1440px" },
      boxShadow: { ambient: "0 0 40px rgba(0,0,0,0.02)" },
      backdropBlur: { glass: "20px" },
      keyframes: {
        "fade-in-up": { from: { opacity: "0", transform: "translateY(8px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        "rail-shimmer": { "0%": { transform: "translateX(-100%)" }, "100%": { transform: "translateX(100%)" } },
      },
      animation: {
        "fade-in-up": "fade-in-up 0.3s ease-out both",
        "rail-shimmer": "rail-shimmer 1.2s ease-in-out infinite",
      },
    },
  },
  plugins: [tailwindcssAnimate],
};

export default config;
