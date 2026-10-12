/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // warm off-white backgrounds
        ivory: { 50: "#FEFDFB", 100: "#FAF8F3", 200: "#F3EFE6", 300: "#E9E3D6" },
        // deep emerald (primary accent)
        brand: {
          50: "#EEF6F1", 100: "#D9EBE0", 200: "#B5D6C2", 300: "#8DBBA0", 400: "#5A9A78",
          500: "#2F7D5B", 600: "#146A4A", 700: "#0F5A3F", 800: "#0C4A34", 900: "#0A3B2A",
        },
        // muted sage (secondary accent)
        sage: {
          100: "#E8EFEA", 200: "#D3DFD7", 300: "#B9CBBE", 400: "#9DB5A4",
          500: "#7F9C88", 600: "#667F6F",
        },
        // dark charcoal text
        ink: { 900: "#1B201D", 700: "#2D3430", 600: "#444C47", 500: "#5E6761", 400: "#7C857F" },
        // thin green-tinted borders
        line: { DEFAULT: "#E1E9E3", strong: "#CBD8CF" },
      },
      fontFamily: {
        sans: [
          "Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif",
        ],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(15, 60, 40, 0.04), 0 1px 1px rgba(15, 60, 40, 0.03)",
        pop: "0 8px 24px rgba(15, 60, 40, 0.10), 0 2px 6px rgba(15, 60, 40, 0.06)",
      },
    },
  },
  plugins: [],
};
