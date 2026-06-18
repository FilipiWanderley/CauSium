import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // ── CauSium Brand Palette ──────────────────────────────────────────────
        navy: {
          DEFAULT: '#001B2A',
          50: '#e6f0f5',
          100: '#cce1eb',
          200: '#99c3d7',
          300: '#66a5c3',
          400: '#3387af',
          500: '#00699b',
          600: '#00547c',
          700: '#003f5e',
          800: '#001B2A',
          900: '#001424',
          950: '#000d19',
        },
        slate: {
          struct: '#334155', // Slate estrutural - elementos estruturais
          150: '#e8ecf1',
        },
        gray: {
          cool: '#64748B', // Cool Gray - labels, legendas, eixos
          light: '#E5E7EB', // Light Gray - fundos, divisórias
        },
        teal: {
          DEFAULT: '#0FA287',
          50: '#e6f7f4',
          100: '#cceee9',
          200: '#99dddd',
          300: '#66ccd1',
          400: '#33bbc5',
          500: '#0FA287',
          600: '#0d826c',
          700: '#0a6151',
          800: '#084136',
          900: '#05211b',
        },
        brand: {
          50: '#e6f7f4',
          100: '#cceee9',
          200: '#99dddd',
          300: '#66ccd1',
          400: '#33bbc5',
          500: '#0FA287',
          600: '#0d826c',
          700: '#0a6151',
          800: '#084136',
          900: '#05211b',
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
        'panel-hover': '0 4px 12px -2px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.05)',
        'panel-elevated': '0 8px 24px -4px rgb(0 0 0 / 0.1), 0 4px 8px -2px rgb(0 0 0 / 0.06)',
        'card-premium': '0 2px 8px -2px rgb(0 27 42 / 0.06), 0 1px 3px -1px rgb(0 27 42 / 0.04)',
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
