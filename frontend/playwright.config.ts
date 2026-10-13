import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './browser', testMatch: '**/*.e2e.ts', workers: 1, fullyParallel: false,
  timeout: 45000, reporter: [['list'], ['json', { outputFile: `${process.env.QA_EVIDENCE_DIR || '../docs/development/evidence/2026-10-10'}/browser-results.json` }]],
  use: { baseURL: 'http://127.0.0.1:15173', channel: 'msedge', headless: true,
    launchOptions: { chromiumSandbox: true }, trace: 'off', screenshot: 'only-on-failure' },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1440, height: 1000 } } },
    { name: 'tablet', use: { viewport: { width: 768, height: 1024 } } },
    { name: 'mobile', use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
})
