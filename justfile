set shell := ["bash", "-cu"]

compose := "docker compose -f infra/docker-compose.yml --env-file infra/env/api.env"

up:
    {{compose}} up -d

down:
    {{compose}} down

logs:
    {{compose}} logs -f --tail=200

build:
    {{compose}} build

migrate:
    {{compose}} exec api alembic upgrade head

seed:
    {{compose}} exec api python -m app.scripts.seed

test:
    {{compose}} exec api pytest -q
    {{compose}} exec worker pytest -q

fmt:
    {{compose}} exec api ruff format app tests
    {{compose}} exec worker ruff format app tests

lint:
    {{compose}} exec api ruff check app tests
    {{compose}} exec worker ruff check app tests

clean:
    {{compose}} down -v
