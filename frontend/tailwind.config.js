/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Syne', 'sans-serif'],
        body: ['DM Sans', 'sans-serif'],
        mono: ['DM Mono', 'monospace'],
      },
      colors: {
        bg: '#0A0C10',
        surface: '#141720',
        card: '#1A1E2B',
        border: '#252B3B',
        'text-primary': '#E2E8F0',
        'text-muted': '#64748B',
        accent: '#6366F1',
        'score-high': '#10B981',
        'score-mid': '#F59E0B',
        'score-low': '#EF4444',
      },
    },
  },
  plugins: [],
}
