/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0d1117",
        panel: "#161b22",
        border: "#30363d",
        accent: "#38bdf8",
        muted: "#8b949e",
      }
    },
  },
  plugins: [],
}
