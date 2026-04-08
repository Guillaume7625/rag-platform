#!/usr/bin/env bash
# Idempotent deploy: pull, build, migrate, restart.
# Run as root on the VPS. Assumes first-setup.sh has been run at least once.
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/rag-platform}"
SECRETS_FILE="/etc/rag-platform/secrets.env"
COMPOSE_FILE="$REPO_DIR/infra/prod/docker-compose.prod.yml"

if [[ ! -f "$SECRETS_FILE" ]]; then
  echo "Missing $SECRETS_FILE. Run first-setup.sh first." >&2
  exit 1
fi

cd "$REPO_DIR"

echo "==> git pull"
git fetch --all --prune
git reset --hard origin/main

DC=(docker compose -f "$COMPOSE_FILE" --env-file "$SECRETS_FILE")

echo "==> build images"
"${DC[@]}" build --pull

echo "==> starting data services"
"${DC[@]}" up -d postgres redis qdrant minio

echo "==> waiting for postgres to be healthy"
for _ in {1..30}; do
  status=$("${DC[@]}" ps --format json postgres 2>/dev/null | jq -r '.[0].Health // "starting"' || echo "starting")
  if [[ "$status" == "healthy" ]]; then break; fi
  sleep 2
done

echo "==> running alembic migrations"
"${DC[@]}" run --rm api alembic upgrade head

echo "==> starting app services"
"${DC[@]}" up -d --remove-orphans

echo "==> pruning dangling images"
docker image prune -f >/dev/null || true

echo
echo "Deploy finished. Check status with:"
echo "  ${DC[*]} ps"
echo "  ${DC[*]} logs -f --tail=100"
