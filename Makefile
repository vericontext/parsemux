.PHONY: dev install test lint serve ui docker

# Development install with all available parsers + dev tools
dev:
	uv pip install -e ".[pymupdf,kreuzberg,serve,cli,mcp,dev]"

# Minimal install
install:
	uv pip install -e ".[pymupdf,kreuzberg,cli]"

# Full install (all parsers)
install-full:
	uv pip install -e ".[full,dev]"

test:
	pytest -v

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff format src/ tests/

# Start API server with UI
serve:
	parsemux serve --ui

# Docker
docker:
	docker compose up --build

docker-full:
	docker compose --profile full up --build
