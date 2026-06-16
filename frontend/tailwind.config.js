/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Black base, console depth
        base: '#04070b',
        panel: '#08111a',
        raised: '#0b1925',
        edge: '#15303d',
        grid: '#0c1c28',
        ink: '#dceaf0',
        muted: '#5d7689',
        faint: '#33485a',
        // Brand: green + blue
        green: '#26e3a0',
        'green-dim': '#0e8f63',
        blue: '#39b6f6',
        'blue-dim': '#1c6fa8',
        // Classification semantics (harmonized with the green/blue theme)
        core: '#26e3a0',
        asym: '#39b6f6',
        tactical: '#f5b53d',
        avoid: '#ff6b7a',
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(38,227,160,0.15), 0 0 24px -8px rgba(38,227,160,0.25)',
        'glow-blue': '0 0 0 1px rgba(57,182,246,0.15), 0 0 24px -8px rgba(57,182,246,0.25)',
      },
    },
  },
  plugins: [],
}
