#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/mtp-newsletter}"
BACKUP_DIR="${APP_DIR}/backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DB_PATH="${APP_DIR}/data/newsletter.db"
OUTPUT_DIR="${APP_DIR}/output"
ARCHIVE="${BACKUP_DIR}/newsletter_backup_${TIMESTAMP}.tar.gz"

mkdir -p "${BACKUP_DIR}"

if [[ ! -f "${DB_PATH}" ]]; then
  echo "DB file missing: ${DB_PATH}"
  exit 1
fi

tar -czf "${ARCHIVE}" -C "${APP_DIR}" data/newsletter.db output

find "${BACKUP_DIR}" -type f -name "newsletter_backup_*.tar.gz" -mtime +14 -delete

echo "Backup created: ${ARCHIVE}"
