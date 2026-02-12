/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // CSIO Brand Colors
        primary: {
          50: '#e6f3ff',
          100: '#b3daff',
          200: '#80c1ff',
          300: '#4da8ff',
          400: '#1a90ff',
          500: '#0077e6',
          600: '#0066cc',
          700: '#0055b3',
          800: '#004499',
          900: '#003380',
        },
        secondary: {
          50: '#f0f4f8',
          100: '#d9e2ec',
          200: '#bcccdc',
          300: '#9fb3c8',
          400: '#829ab1',
          500: '#627d98',
          600: '#486581',
          700: '#334e68',
          800: '#243b53',
          900: '#16213e',
        },
        dark: {
          50: '#3d3d4e',
          100: '#35354a',
          200: '#2d2d42',
          300: '#25253a',
          400: '#1d1d32',
          500: '#1a1a2e',
          600: '#15152a',
          700: '#101026',
          800: '#0b0b22',
          900: '#06061e',
        },
        accent: {
          blue: '#00d4ff',
          purple: '#8b5cf6',
          green: '#10b981',
          orange: '#f59e0b',
          red: '#ef4444',
        },
      },

      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Outfit', 'system-ui', 'sans-serif'],
        mono: ['Fira Code', 'monospace'],
      },

      boxShadow: {
        'glow-sm': '0 0 10px rgba(26, 144, 255, 0.3)',
        'glow': '0 0 20px rgba(26, 144, 255, 0.4)',
        'glow-lg': '0 0 30px rgba(26, 144, 255, 0.5)',
        'inner-glow': 'inset 0 0 20px rgba(26, 144, 255, 0.2)',
      },

      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-slow': 'bounce 3s infinite',
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.5s ease-out',
        'slide-down': 'slideDown 0.5s ease-out',
        'blob': 'blob 7s infinite',
      },

      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        blob: {
          '0%': {
            transform: 'translate(0px, 0px) scale(1)',
          },
          '33%': {
            transform: 'translate(30px, -50px) scale(1.1)',
          },
          '66%': {
            transform: 'translate(-20px, 20px) scale(0.9)',
          },
          '100%': {
            transform: 'translate(0px, 0px) scale(1)',
          },
        },
      },

      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
};
