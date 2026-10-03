/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Flat editorial palette. Nothing outside these five + borders.
        paper: "#EFE7D6",
        surface: "#E4D8C0",
        ink: "#2E1F14",
        rust: "#B4451F",
        ochre: "#C8922A",
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        sans: ["'IBM Plex Sans'", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "ui-monospace", "monospace"],
      },
      maxWidth: {
        page: "76rem",
      },
    },
  },
  plugins: [],
};
