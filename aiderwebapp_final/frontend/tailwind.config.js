/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg0: '#0d1117', bg1: '#161b22', bg2: '#1c2128', bg3: '#21262d',
        border: '#30363d', accent: '#58a6ff', green: '#3fb950',
        red: '#f85149', yellow: '#d29922', purple: '#bc8cff',
      },
      fontFamily: { mono: ['Cascadia Code','Fira Code','Consolas','monospace'] }
    }
  },
  plugins: []
}
