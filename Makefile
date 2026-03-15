PYTHON ?= python3.9
VENV ?= .venv
PYTHON_BIN := $(VENV)/bin/python
PIP_BIN := $(VENV)/bin/pip
CONSTRAINTS ?= constraints/py39.txt

.PHONY: services-up services-down venv install dev run-web run-dispatcher run-crawler bootstrap-admin test lint docs

services-up:
	docker compose -f docker-compose.services.yml up -d

services-down:
	docker compose -f docker-compose.services.yml down

$(PYTHON_BIN):
	$(PYTHON) -m venv $(VENV)

venv: $(PYTHON_BIN)
	$(PIP_BIN) install --upgrade pip
	$(PIP_BIN) install -r requirements_dev.txt -c $(CONSTRAINTS)

install: venv

dev:
	./scripts/dev-start.sh

run-web: venv
	$(PYTHON_BIN) -m zspider.web

run-dispatcher: venv
	$(PYTHON_BIN) -m zspider.dispatcher

run-crawler: venv
	$(PYTHON_BIN) -m zspider.crawler

bootstrap-admin: venv
	@if [ -z "$(ADMIN_USERNAME)" ] || [ -z "$(ADMIN_PASSWORD)" ]; then \
		echo "Usage: make bootstrap-admin ADMIN_USERNAME=<name> ADMIN_PASSWORD=<password>"; \
		exit 1; \
	fi
	$(PYTHON_BIN) -m zspider.bootstrap_admin --username "$(ADMIN_USERNAME)" --password "$(ADMIN_PASSWORD)"

test: venv
	$(PYTHON_BIN) -m unittest discover -s utests -v

lint: venv
	$(PYTHON_BIN) -m compileall zspider utests

docs:
	$(MAKE) -C docs html
