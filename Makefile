api-dev:
	uv run --project apps/api uvicorn writer_assistance_api.main:app --reload --port 8000

api-test:
	uv run --project apps/api pytest apps/api/tests -q

api-typecheck:
	uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src

web-test:
	pnpm --dir apps/web exec vitest run

web-typecheck:
	pnpm --dir apps/web exec tsc --noEmit

smoke-api:
	pnpm smoke:api

smoke-web:
	pnpm smoke:web

smoke-install:
	pnpm e2e:install

smoke-test:
	pnpm smoke

verify:
	uv run --project apps/api pytest apps/api/tests -q
	uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src
	pnpm --dir apps/web exec vitest run
	pnpm --dir apps/web exec tsc --noEmit
	pnpm exec playwright test
