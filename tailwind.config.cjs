/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./templates/**/*.html', './static/js/**/*.js'],
  corePlugins: { preflight: false },
  theme: {
    extend: {
      colors: { warehouse: { navy: '#12213a', teal: '#0d8d77', canvas: '#f5f7fa' } },
      fontFamily: { sans: ['Be Vietnam Pro', 'Segoe UI', 'sans-serif'] },
    },
  },
  plugins: [],
};
