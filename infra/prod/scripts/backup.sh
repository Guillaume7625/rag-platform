#!/usr/bin/env bash
# Nightly backup of postgres + qdrant + minio.
# Cron suggestion (root):
#   15 3 * * *  /opt/rag-platform/infra/prod/scripts/backup.sh >> /var/log/rag-backup.log 2>&1
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/rag-platform}"
SECRETS_FILE="/etc/rag-platform/secrets.env"
COMPOSE_FILE="$REPO_DIR/infra/prod/docker-compose.prod.yml"
BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/rag-platform}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

stamp=$(date +%Y%m%d-%H%M%S)
out="$BACKUP_ROOT/$stamp"
mkdir -p "$out"

DC=(docker compose -f "$COMPOSE_FILE" --env-file "$SECRETS_FILE")

# shellcheck disable=SC1090
set -a; source "$SECRETS_FILE"; set +a

echo "==> [$(date -Is)] postgres dump"
"${DC[@]}" exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom \
  > "$out/postgres.dump"

echo "==> qdrant snapshot"
# Trigger a snapshot via the HTTP API on the internal network.
"${DC[@]}" exec -T qdrant \
  curl -s -X POST "http://localhost:6333/collections/${QDRANT_COLLECTION:-rag_chunks}/snapshots" \
  > "$out/qdrant-snapshot.json" || echo "(qdrant collection not yet created)"

echo "==> minio mirror"
"${DC[@]}" run --rm --entrypoint /bin/sh minio-init -c "
  mc alias set local http://minio:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD >/dev/null;
  mc mirror --quiet --overwrite local/$MINIO_BUCKET /tmp/backup;
  tar -C /tmp -czf /tmp/minio.tgz backup;
  cat /tmp/minio.tgz
" > "$out/minio.tgz" || true

echo "==> pruning backups older than $RETENTION_DAYS days"
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime "+$RETENTION_DAYS" -exec rm -rf {} +

echo "Backup written to $out"
