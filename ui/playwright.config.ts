import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: 'e2e',
  projects: [{ name: 'preview', use: { baseURL: 'http://localhost:4173/' } }],
  webServer: {
    command: 'node scripts/snapshot.ts --vault test/fixture-vault && vite build && vite preview --port 4173 --strictPort',
    url: 'http://localhost:4173/',
    reuseExistingServer: false,
    timeout: 120_000,
  },
})
