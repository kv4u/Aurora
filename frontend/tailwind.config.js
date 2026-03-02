/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        aurora: {
          50: "#f0f7ff",
          100: "#e0efff",
          200: "#b8dbff",
          300: "#7abfff",
          400: "#3399ff",
          500: "#0077e6",
          600: "#005bb5",
          700: "#004494",
          800: "#003070",
          900: "#001d4d",
          950: "#001233",
        },
        profit: {
          light: "#22c55e",
          DEFAULT: "#16a34a",
          dark: "#15803d",
        },
        loss: {
          light: "#ef4444",
          DEFAULT: "#dc2626",
          dark: "#b91c1c",
        },
        circuit: {
          yellow: "#eab308",
          orange: "#f97316",
          red: "#ef4444",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "glow": "glow 2s ease-in-out infinite alternate",
      },
      keyframes: {
        glow: {
          "0%": { boxShadow: "0 0 5px rgba(0, 119, 230, 0.3)" },
          "100%": { boxShadow: "0 0 20px rgba(0, 119, 230, 0.6)" },
        },
      },
    },
  },
  plugins: [],
};
