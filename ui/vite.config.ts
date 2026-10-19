/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  base: './',
  publicDir: process.env.ZEN_PUBLIC_DIR ?? 'public',
  plugins: [react(), tailwindcss()],
  test: { environment: 'jsdom', setupFiles: ['src/test-setup.ts'], exclude: ['e2e/**', 'node_modules/**'], include: ['src/**/*.test.{ts,tsx}', 'scripts/**/*.test.ts'] },
})
