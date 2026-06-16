import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, proxy /api to the FastAPI backend so the frontend calls it same-origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8800', changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
