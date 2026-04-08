#!/usr/bin/env bash
# Restore postgres + minio from a backup folder produced by backup.sh.
# Usage:
#   sudo bash restore.sh /var/backups/rag-platform/20260408-031500
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <backup_dir>" >&2
  exit 1
fi
src="$1"
[[ -d "$src" ]] || { echo "Not a directory: $src" >&2; exit 1; }

REPO_DIR="${REPO_DIR:-/opt/rag-platform}"
SECRETS_FILE="/etc/rag-platform/secrets.env"
COMPOSE_FILE="$REPO_DIR/infra/prod/docker-compose.prod.yml"

DC=(docker compose -f "$COMPOSE_FILE" --env-file "$SECRETS_FILE")
# shellcheck disable=SC1090
set -a; source "$SECRETS_FILE"; set +a

read -r -p "This will OVERWRITE postgres and minio data. Continue? [y/N] " ans
[[ "$ans" == "y" || "$ans" == "Y" ]] || { echo "Aborted."; exit 1; }

echo "==> stopping app services"
"${DC[@]}" stop api worker web

if [[ -f "$src/postgres.dump" ]]; then
  echo "==> restoring postgres"
  "${DC[@]}" exec -T postgres \
    psql -U "$POSTGRES_USER" -d postgres \
    -c "DROP DATABASE IF EXISTS $POSTGRES_DB; CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER;"
  "${DC[@]}" exec -T postgres \
    pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists \
    < "$src/postgres.dump"
fi

if [[ -f "$src/minio.tgz" ]]; then
  echo "==> restoring minio bucket"
  "${DC[@]}" run --rm --entrypoint /bin/sh \
    -v "$src":/restore minio-init -c "
      mc alias set local http://minio:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD >/dev/null;
      mkdir -p /tmp/restore && tar -C /tmp/restore -xzf /restore/minio.tgz;
      mc mirror --overwrite /tmp/restore/backup local/$MINIO_BUCKET;
    "
fi

echo "==> restarting app services"
"${DC[@]}" up -d api worker web

echo "Restore done."
