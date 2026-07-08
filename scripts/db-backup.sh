#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${1:-signoz-metastore-postgres-0}"
DB_USER="signoz"
DB_NAME="signoz"
OUTPUT_DIR="${2:-./backups}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="${OUTPUT_DIR}/signoz-backup-${TIMESTAMP}.sql"

mkdir -p "$OUTPUT_DIR"
echo "Backing up SigNoz Postgres DB (${CONTAINER}) to ${BACKUP_FILE} ..."
docker exec "$CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --clean --if-exists > "$BACKUP_FILE" 2>&1
echo "Backup complete: ${BACKUP_FILE} ($(du -h "$BACKUP_FILE" | cut -f1))"
