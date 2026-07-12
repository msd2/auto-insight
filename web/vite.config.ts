import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  server: {
    // The dev pack preview imports pack JSON from ../content (single source
    // of truth), which lives outside the Vite root — allow the repo root.
    fs: {
      allow: ['..'],
    },
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts',
  },
})
