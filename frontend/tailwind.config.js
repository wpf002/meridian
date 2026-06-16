/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        base: '#0b0e14',
        panel: '#121722',
        edge: '#222a39',
        ink: '#e6e9ef',
        muted: '#8a93a6',
        // Classification palette — same semantics as the terminal UI
        core: '#34d399',
        asym: '#22d3ee',
        tactical: '#fbbf24',
        avoid: '#f87171',
        accent: '#7c93ff',
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
