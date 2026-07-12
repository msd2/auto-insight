.PHONY: dev-db dev-api dev-web dev test test-api test-web lint lint-api lint-web fmt

dev-db:
	docker compose up -d db

dev-api:
	cd api && uv run uvicorn autoinsight.main:app --reload

dev-web:
	cd web && npm run dev

dev: dev-db
	@echo "db up — run 'make dev-api' and 'make dev-web' in separate terminals"

test: test-api test-web

test-api:
	cd api && uv run pytest

test-web:
	cd web && npm test

lint: lint-api lint-web

lint-api:
	cd api && uv run ruff check . && uv run ruff format --check . && uv run mypy

lint-web:
	cd web && npm run lint && npm run typecheck && npm run fmt:check

fmt:
	cd api && uv run ruff check --fix . && uv run ruff format .
	cd web && npm run fmt
