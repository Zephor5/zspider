.PHONY: services-up services-down dev test lint

services-up:
	docker compose -f docker-compose.services.yml up -d

services-down:
	docker compose -f docker-compose.services.yml down

dev:
	./scripts/dev-start.sh

test:
	./.venv/bin/python -m unittest discover -s utests -v

lint:
	./.venv/bin/python -m compileall zspider utests
