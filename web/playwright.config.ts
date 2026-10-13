import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:5198', browserName: 'chromium', trace: 'retain-on-failure' },
  webServer: [
    { command: '..\\.venv\\Scripts\\python.exe ../scripts/serve_phase2_fixtures.py', url: 'http://127.0.0.1:8828/api/v1/agregados-ibge/health/', reuseExistingServer: false },
    { command: 'npm run dev -- --port 5198', url: 'http://127.0.0.1:5198', env: { VITE_BACKEND_PROXY_TARGET: 'http://127.0.0.1:8828' }, reuseExistingServer: false },
  ],
})
