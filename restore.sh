#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-barq-assessment}"
DB_USER="${DB_USER:-barq_app}"
BACKUP_FILE="${1:-backups/barq_tasks_backup.sql}"
TARGET_DB="${2:-barq_restore_test}"

if [[ ! -s "$BACKUP_FILE" ]]; then
  echo "Backup file missing or empty: $BACKUP_FILE" >&2
  exit 1
fi

echo "Restoring $BACKUP_FILE into database: $TARGET_DB"

docker compose -p "$PROJECT" exec -T postgres \
  dropdb -U "$DB_USER" --if-exists "$TARGET_DB"

docker compose -p "$PROJECT" exec -T postgres \
  createdb -U "$DB_USER" "$TARGET_DB"

docker compose -p "$PROJECT" exec -T postgres \
  psql -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$TARGET_DB" < "$BACKUP_FILE"

echo "Restore completed successfully: $TARGET_DB"
