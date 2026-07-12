.PHONY: dev types test-api lint-api

dev:
	uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

types:
	@echo "Fetching OpenAPI schema..."
	curl -sf http://localhost:8000/openapi.json -o /tmp/openapi.json
	@echo "Generating TypeScript types..."
	npx openapi-typescript /tmp/openapi.json -o frontend/src/api/schema.d.ts
	@echo "Done: frontend/src/api/schema.d.ts"

test-api:
	pytest api/tests/ -v

lint-api:
	ruff check api/ && mypy api/ --ignore-missing-imports
