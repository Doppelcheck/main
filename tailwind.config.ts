import type { Config } from "tailwindcss";

export default {
  content: [
    "./entrypoints/**/*.{ts,tsx,html}",
    "./lib/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0e1116",
        paper: "#fafaf7",
        accent: "#1a4d8c",
        agree: "#1f7a3a",
        disagree: "#b3261e",
        unrelated: "#6b6b6b",
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
