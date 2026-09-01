import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        ink: '#0B1220',
        canvas: '#F4F5F9',
        surface: '#FFFFFF',
        line: '#E4E7EF',
        primary: '#0F172A',
        secondary: '#1E293B',
        accent: '#EF4444',
        success: '#0F9D6E',
        warning: '#D97706',
        danger: '#DC1F31',
        brand: {
          50: '#EFF4FF',
          100: '#DCE7FF',
          200: '#B9CFFF',
          300: '#8DAEFF',
          400: '#5C86FF',
          500: '#3763FA',
          600: '#2347DE',
          700: '#1A35B0',
          800: '#182C86',
          900: '#16265E',
        },
        risk: {
          50: '#FFF1F2',
          100: '#FFE1E3',
          200: '#FFC5C9',
          300: '#FF9BA2',
          400: '#FB6672',
          500: '#F13B4A',
          600: '#DC1F31',
          700: '#B81527',
          800: '#8F1223',
          900: '#711523',
        },
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        display: ['var(--font-display)', 'var(--font-inter)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(15,23,42,0.04), 0 12px 24px -16px rgba(15,23,42,0.18)',
        'card-hover': '0 4px 10px rgba(15,23,42,0.06), 0 20px 32px -16px rgba(15,23,42,0.22)',
      },
      typography: {
        DEFAULT: {
          css: {
            color: '#1F2937',
          },
        },
      },
    },
  },
  plugins: [],
}
export default config
