import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // npm runs from the repo root, so keep Vite's cache in the root node_modules too.
  cacheDir: '../node_modules/.vite',
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
