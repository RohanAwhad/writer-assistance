# Writer Assistance

Writer Assistance is a local-first research and reading workspace. The current slice supports:

- creating projects
- uploading markdown resources
- reading rendered documents
- saving quote-anchored notes
- generating and reviewing AI suggestions

## Prerequisites

- `uv`
- `pnpm`

Install dependencies before working locally:

```bash
uv sync --project apps/api --group dev
pnpm install
pnpm --dir apps/web install
```

## Local Development

Start the API:

```bash
make api-dev
```

Start the web app in another terminal:

```bash
pnpm --dir apps/web dev
```

The Vite dev server proxies `/api` requests to `http://127.0.0.1:8000`.

## Smoke And E2E

The Playwright smoke flow exercises the reading-workspace slice end to end:

1. create a project
2. upload markdown
3. open the project and resource
4. add a user note
5. run AI analysis
6. accept an AI suggestion

Playwright uses an explicit smoke-only backend mode for determinism:

- `WRITER_ASSISTANCE_AI_MODE=smoke`
- `WRITER_ASSISTANCE_DATABASE_URL=sqlite+pysqlite:///$PWD/data/playwright-smoke/app.db`
- `WRITER_ASSISTANCE_STORAGE_ROOT=$PWD/data/playwright-smoke/storage`

Those values are wired into the root scripts and `playwright.config.ts`, so normal local development keeps the default runtime behavior.

Install the Playwright browser once if needed:

```bash
pnpm e2e:install
```

Run the reading-workspace smoke test:

```bash
pnpm smoke
```

Run the full Playwright suite:

```bash
pnpm e2e
```

If you want to inspect the deterministic smoke stack manually, start the same services Playwright uses:

```bash
make smoke-api
make smoke-web
```

## Verification

Run the full verification suite with:

```bash
make verify
```

Or run the exact commands individually:

```bash
uv run --project apps/api pytest apps/api/tests -q
uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src
pnpm --dir apps/web exec vitest run
pnpm --dir apps/web exec tsc --noEmit
pnpm exec playwright test
```
