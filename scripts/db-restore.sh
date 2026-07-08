#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE="${1:?Usage: $0 <backup-file>}"
CONTAINER="${2:-signoz-metastore-postgres-0}"
DB_USER="signoz"
DB_NAME="signoz"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Restoring SigNoz Postgres DB from ${BACKUP_FILE} ..."
docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE"
echo "Restore complete!"
