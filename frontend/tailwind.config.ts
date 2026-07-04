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
      // Inter(라틴·숫자) 우선, 한글은 Pretendard로 폴백 — Inter에 한글 글리프가 없어 자연 분담.
      // Pretendard @font-face는 globals.css 번들 서체 블록(에디터 공용) 재사용.
      fontFamily: { sans: ["var(--font-inter)", "Inter", "Pretendard", "system-ui", "sans-serif"] },
      colors: {
        // 값은 globals.css :root의 RGB 트리플릿 변수 — 토큰명은 불변, 팔레트만 교체 가능.
        surface: {
          DEFAULT: "rgb(var(--color-surface) / <alpha-value>)",
          dim: "rgb(var(--color-surface-dim) / <alpha-value>)",
          bright: "rgb(var(--color-surface-bright) / <alpha-value>)",
          "container-lowest": "rgb(var(--color-surface-container-lowest) / <alpha-value>)",
          "container-low": "rgb(var(--color-surface-container-low) / <alpha-value>)",
          container: "rgb(var(--color-surface-container) / <alpha-value>)",
          "container-high": "rgb(var(--color-surface-container-high) / <alpha-value>)",
          "container-highest": "rgb(var(--color-surface-container-highest) / <alpha-value>)",
        },
        "on-surface": {
          DEFAULT: "rgb(var(--color-on-surface) / <alpha-value>)",
          variant: "rgb(var(--color-on-surface-variant) / <alpha-value>)",
        },
        outline: {
          DEFAULT: "rgb(var(--color-outline) / <alpha-value>)",
          variant: "rgb(var(--color-outline-variant) / <alpha-value>)",
        },
        primary: {
          DEFAULT: "rgb(var(--color-primary) / <alpha-value>)",
          container: "rgb(var(--color-primary-container) / <alpha-value>)",
        },
        "on-primary": "rgb(var(--color-on-primary) / <alpha-value>)",
        secondary: {
          DEFAULT: "rgb(var(--color-secondary) / <alpha-value>)",
          container: "rgb(var(--color-secondary-container) / <alpha-value>)",
        },
        "on-secondary": "rgb(var(--color-on-secondary) / <alpha-value>)",
        accent: {
          DEFAULT: "rgb(var(--color-accent) / <alpha-value>)",
          container: "rgb(var(--color-accent-container) / <alpha-value>)",
        },
        error: {
          DEFAULT: "rgb(var(--color-error) / <alpha-value>)",
          container: "rgb(var(--color-error-container) / <alpha-value>)",
        },
        "on-error": "rgb(var(--color-on-error) / <alpha-value>)",
        background: "rgb(var(--color-background) / <alpha-value>)",
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
          info: "#0067b6",
          "info-bg": "#e5f1fa",
          "info-fg": "#00477e",
        },
      },
      fontSize: {
        h1: ["64px", { lineHeight: "1.1", letterSpacing: "-0.01em", fontWeight: "600" }],
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
      boxShadow: {
        // 색조 그림자(브랜드 뉴트럴이 쿨톤이라 순흑 대신 잉크 네이비 rgba 5,29,73).
        // 2겹(접지 + 확산)으로 사실적 깊이. ambient는 레거시 소프트 글로우(보존).
        ambient: "0 0 40px rgba(0,0,0,0.02)",
        "elev-1": "0 1px 2px rgba(5,29,73,0.04), 0 2px 8px rgba(5,29,73,0.06)",
        "elev-2": "0 2px 4px rgba(5,29,73,0.05), 0 8px 20px rgba(5,29,73,0.08)",
        "elev-3": "0 4px 10px rgba(5,29,73,0.06), 0 14px 32px rgba(5,29,73,0.12)",
        "elev-4": "0 10px 24px rgba(5,29,73,0.10), 0 28px 64px rgba(5,29,73,0.18)",
      },
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
