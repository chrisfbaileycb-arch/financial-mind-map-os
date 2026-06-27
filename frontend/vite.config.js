import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, the UI runs on Vite's port and proxies API calls to the FastAPI
// server. In production, `vite build` emits to dist/, which the API serves.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
