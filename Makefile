api-dev:
	uv run --project apps/api uvicorn writer_assistance_api.main:app --reload --app-dir apps/api/src --port 8000

api-test:
	uv run --project apps/api pytest apps/api/tests -q

api-typecheck:
	uv run --project apps/api mypy apps/api/src
