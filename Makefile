SHELL := /bin/bash
COMPOSE := docker compose -f infra/docker-compose.yml --env-file infra/env/api.env

.PHONY: up down logs build ps restart migrate seed test fmt lint clean

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f --tail=200

restart:
	$(COMPOSE) restart api worker web

migrate:
	$(COMPOSE) exec api alembic upgrade head

seed:
	$(COMPOSE) exec api python -m app.scripts.seed

test:
	$(COMPOSE) exec api pytest -q
	$(COMPOSE) exec worker pytest -q

fmt:
	$(COMPOSE) exec api ruff format app tests
	$(COMPOSE) exec worker ruff format app tests
	cd apps/web && npm run format || true

lint:
	$(COMPOSE) exec api ruff check app tests
	$(COMPOSE) exec worker ruff check app tests
	cd apps/web && npm run lint || true

clean:
	$(COMPOSE) down -v
