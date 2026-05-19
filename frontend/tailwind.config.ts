import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        slate: {
          150: '#e8ecf1',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'ui-monospace', 'monospace'],
        numeric: ['Inter', 'Tabular Nums', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'kpi-lg': ['2rem', { lineHeight: '1.1', fontWeight: '700', letterSpacing: '-0.025em' }],
        'kpi-md': ['1.5rem', { lineHeight: '1.15', fontWeight: '700', letterSpacing: '-0.02em' }],
        'kpi-sm': ['1.25rem', { lineHeight: '1.2', fontWeight: '600' }],
      },
      boxShadow: {
        'panel': '0 1px 3px 0 rgb(0 0 0 / 0.04), 0 1px 2px -1px rgb(0 0 0 / 0.04)',
        'panel-hover': '0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.04)',
        'panel-elevated': '0 4px 12px -2px rgb(0 0 0 / 0.06), 0 2px 4px -2px rgb(0 0 0 / 0.03)',
      },
      borderRadius: {
        'panel': '0.75rem',
      },
      spacing: {
        '4.5': '1.125rem',
        '13': '3.25rem',
        '15': '3.75rem',
      },
    },
  },
  plugins: [],
} satisfies Config
