import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      // Fuentes modernas y distintivas
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
        display: ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      // Paleta de colores personalizada
      colors: {
        // Colores primarios - Tema oscuro profesional
        brand: {
          50: '#ecfeff',
          100: '#cffafe',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#06b6d4',
          600: '#0891b2',
          700: '#0e7490',
          800: '#155e75',
          900: '#164e63',
          950: '#083344',
        },
        // Fondo sidebar oscuro
        sidebar: {
          DEFAULT: '#0f172a',
          hover: '#1e293b',
          active: '#334155',
          border: '#1e293b',
        },
        // Superficie de cards
        surface: {
          DEFAULT: '#ffffff',
          hover: '#f8fafc',
          muted: '#f1f5f9',
          border: '#e2e8f0',
        },
        // Acentos
        accent: {
          cyan: '#22d3ee',
          emerald: '#34d399',
          amber: '#fbbf24',
          rose: '#fb7185',
          violet: '#a78bfa',
        },
      },
      // Sombras mejoradas
      boxShadow: {
        'soft': '0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 10px 20px -2px rgba(0, 0, 0, 0.04)',
        'card': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1)',
        'card-hover': '0 10px 40px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)',
        'glow-brand': '0 0 20px rgba(6, 182, 212, 0.3)',
        'glow-success': '0 0 20px rgba(52, 211, 153, 0.3)',
        'glow-warning': '0 0 20px rgba(251, 191, 36, 0.3)',
        'glow-error': '0 0 20px rgba(251, 113, 133, 0.3)',
        'inner-glow': 'inset 0 1px 0 0 rgba(255, 255, 255, 0.05)',
      },
      // Animaciones
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'slide-in-right': 'slideInRight 0.3s ease-out',
        'pulse-soft': 'pulseSoft 2s infinite',
        'shimmer': 'shimmer 2s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideInRight: {
          '0%': { opacity: '0', transform: 'translateX(-10px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      // Border radius más consistente
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
      },
      // Backdrop blur
      backdropBlur: {
        'xs': '2px',
      },
    },
  },
  plugins: [],
}
export default config
