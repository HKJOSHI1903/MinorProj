import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// While developing, the Vue app runs on port 5173 and forwards every /api call
// to the Python server on port 8000 (override with API_URL).
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: {
      '/api': process.env.API_URL || 'http://127.0.0.1:8000',
    },
  },
  build: {
    chunkSizeWarningLimit: 800,
  },
})
