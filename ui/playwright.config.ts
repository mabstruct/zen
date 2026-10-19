import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { defineConfig } from '@playwright/test'

const site = join(tmpdir(), 'zen-ui-export-site')

export default defineConfig({
  testDir: 'e2e',
  projects: [
    { name: 'preview', use: { baseURL: 'http://localhost:4173/' } },
    { name: 'export-subpath', use: { baseURL: 'http://localhost:4174/zen/' } },
  ],
  webServer: [
    {
      command: 'node scripts/snapshot.ts --vault test/fixture-vault && vite build && vite preview --port 4173 --strictPort',
      url: 'http://localhost:4173/',
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `node scripts/export.ts ${site}/zen --yes --vault test/fixture-vault && npx serve ${site} -l 4174`,
      url: 'http://localhost:4174/zen/',
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
})
