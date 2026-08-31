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
        primary: '#0F172A',
        secondary: '#1E293B',
        accent: '#EF4444',
        success: '#10B981',
        warning: '#F59E0B',
        danger: '#EF4444',
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
