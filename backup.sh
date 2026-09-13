#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-barq-assessment}"
DB_USER="${DB_USER:-barq_app}"
DB_NAME="${DB_NAME:-barq_tasks}"
BACKUP_DIR="${BACKUP_DIR:-backups}"
OUTPUT="${1:-${BACKUP_DIR}/barq_tasks_backup.sql}"

mkdir -p "$(dirname "$OUTPUT")"

echo "Creating PostgreSQL backup: $OUTPUT"

docker compose -p "$PROJECT" exec -T postgres \
  pg_dump -U "$DB_USER" -d "$DB_NAME" > "$OUTPUT"

test -s "$OUTPUT"

echo "Backup completed successfully: $OUTPUT"
