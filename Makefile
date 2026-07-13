.PHONY: dev dev-frontend types test-api lint-api

dev:
	uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

dev-frontend:
	cd frontend && npm run dev

types:
	cd frontend && npx openapi-typescript http://localhost:8000/openapi.json \
		-o src/api/schema.d.ts
	@echo "Done: frontend/src/api/schema.d.ts"

test-api:
	pytest api/tests/ -v

lint-api:
	ruff check api/ && mypy api/ --ignore-missing-imports
