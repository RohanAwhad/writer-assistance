import { defineConfig } from '@playwright/test';

const smokeApiBaseUrl = 'http://127.0.0.1:8001';

export default defineConfig({
  testDir: './apps/web/e2e',
  fullyParallel: false,
  retries: 0,
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command:
        'rm -rf data/playwright-smoke && mkdir -p data/playwright-smoke && WRITER_ASSISTANCE_DATABASE_URL="sqlite+pysqlite:///$PWD/data/playwright-smoke/app.db" WRITER_ASSISTANCE_STORAGE_ROOT="$PWD/data/playwright-smoke/storage" WRITER_ASSISTANCE_AI_MODE=smoke uv run --project apps/api uvicorn writer_assistance_api.main:app --host 127.0.0.1 --port 8001',
      url: `${smokeApiBaseUrl}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `WRITER_ASSISTANCE_API_BASE_URL=${smokeApiBaseUrl} pnpm --dir apps/web exec vite --host 127.0.0.1 --port 4173 --strictPort`,
      url: 'http://127.0.0.1:4173',
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
