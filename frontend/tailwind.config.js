/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Terminal-inspired color palette
        terminal: {
          bg: '#0a0a0f',
          surface: '#12121a',
          border: '#1e1e2e',
          text: '#e0e0e0',
          dim: '#6b7280',
          accent: '#7dd3fc',
          success: '#4ade80',
          warning: '#fbbf24',
          error: '#f87171',
          highlight: '#c084fc',
        }
      },
      fontFamily: {
        mono: ['IBM Plex Mono', 'Fira Code', 'Consolas', 'monospace'],
        display: ['Cinzel', 'Georgia', 'serif'],
      },
      animation: {
        'cursor-blink': 'blink 1s step-end infinite',
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        blink: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0 },
        },
        fadeIn: {
          '0%': { opacity: 0 },
          '100%': { opacity: 1 },
        },
        slideUp: {
          '0%': { opacity: 0, transform: 'translateY(10px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
