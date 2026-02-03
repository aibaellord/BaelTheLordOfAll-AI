import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bael: {
          bg: "#0a0a0f",
          surface: "#12121a",
          border: "#1e1e2e",
          text: "#e0e0e0",
          muted: "#6b7280",
          primary: "#6366f1",
          secondary: "#8b5cf6",
          success: "#10b981",
          warning: "#f59e0b",
          error: "#ef4444",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
