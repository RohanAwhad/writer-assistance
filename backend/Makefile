.PHONY: setup run test typecheck lint reset-db

setup:
	uv sync

run:
	uv run uvicorn app.main:app --reload

test:
	uv run pytest

typecheck:
	uv run mypy app tests

lint:
	uv run ruff check app tests

reset-db:
	rm -f data/writer-assistance.db
