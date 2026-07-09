import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Forwards to the FastAPI backend during dev. In production the same
      // service serves both the API and this build, so no proxy is needed there.
      '/api': 'http://localhost:8000',
    },
  },
})
