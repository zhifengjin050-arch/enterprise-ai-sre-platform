/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      colors: {
        canvas: 'rgb(var(--canvas) / <alpha-value>)',
        chrome: 'rgb(var(--chrome) / <alpha-value>)',
        surface: {
          DEFAULT: 'rgb(var(--surface) / <alpha-value>)',
          2: 'rgb(var(--surface-2) / <alpha-value>)',
        },
        line: 'rgb(var(--line) / <alpha-value>)',
        /* ink 不用 alpha 通道写法，避免浅色模式下文字算成近透明 */
        ink: {
          DEFAULT: 'rgb(var(--ink))',
          muted: 'rgb(var(--ink-muted))',
        },
        dark: {
          50: 'rgb(var(--ink) / <alpha-value>)',
          100: 'rgb(var(--canvas) / <alpha-value>)',
          200: 'rgb(var(--surface) / <alpha-value>)',
          300: 'rgb(var(--surface-2) / <alpha-value>)',
          400: 'rgb(var(--line) / <alpha-value>)',
          500: 'rgb(var(--ink-muted) / <alpha-value>)',
          600: 'rgb(var(--ink-muted) / <alpha-value>)',
          700: 'rgb(var(--ink-muted) / <alpha-value>)',
          800: 'rgb(var(--ink) / <alpha-value>)',
          900: 'rgb(var(--ink) / <alpha-value>)',
        },
        primary: {
          500: 'rgb(var(--primary) / <alpha-value>)',
          600: 'rgb(var(--primary-600) / <alpha-value>)',
          700: 'rgb(var(--primary-700) / <alpha-value>)',
        },
        success: 'rgb(var(--success) / <alpha-value>)',
        warning: 'rgb(var(--warning) / <alpha-value>)',
        danger: 'rgb(var(--danger) / <alpha-value>)',
        critical: 'rgb(var(--danger) / <alpha-value>)',
        info: 'rgb(var(--primary) / <alpha-value>)',
      },
      borderRadius: {
        DEFAULT: '8px',
      },
    },
  },
  plugins: [],
}
