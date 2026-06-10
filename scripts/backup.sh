#!/usr/bin/env bash
# Encrypted, timestamped backups of the trading state with retention.
#
# Backs up either the SQLite file (standalone mode) or a Postgres dump (scaled
# mode), gzips it, and - if BACKUP_PASSPHRASE is set - encrypts at rest with
# AES-256 via openssl. Old backups beyond RETENTION_DAYS are pruned.
#
# Usage:
#   BACKUP_PASSPHRASE=... ./scripts/backup.sh
#   RETENTION_DAYS=14 PG_URL=postgresql://... ./scripts/backup.sh
#
# Schedule via cron, e.g. every day at 02:00:
#   0 2 * * * BACKUP_PASSPHRASE=... /opt/ats/scripts/backup.sh >> /opt/ats/var/backup.log 2>&1
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"

if [[ -n "${PG_URL:-}" ]]; then
  OUT="$BACKUP_DIR/ats_pg_$STAMP.sql.gz"
  echo "Dumping Postgres -> $OUT"
  pg_dump "$PG_URL" | gzip -9 > "$OUT"
else
  DB_FILE="${DB_FILE:-$ROOT/var/ats.db}"
  if [[ ! -f "$DB_FILE" ]]; then
    echo "No SQLite DB at $DB_FILE; nothing to back up." >&2
    exit 0
  fi
  OUT="$BACKUP_DIR/ats_sqlite_$STAMP.db.gz"
  echo "Backing up SQLite -> $OUT"
  # .backup gives a consistent snapshot even while the server is running.
  if command -v sqlite3 >/dev/null 2>&1; then
    TMP="$(mktemp)"; sqlite3 "$DB_FILE" ".backup '$TMP'"; gzip -9 -c "$TMP" > "$OUT"; rm -f "$TMP"
  else
    gzip -9 -c "$DB_FILE" > "$OUT"
  fi
fi

# Encrypt at rest if a passphrase is provided (recommended).
if [[ -n "${BACKUP_PASSPHRASE:-}" ]]; then
  ENC="$OUT.enc"
  openssl enc -aes-256-cbc -pbkdf2 -salt -in "$OUT" -out "$ENC" -pass env:BACKUP_PASSPHRASE
  rm -f "$OUT"
  OUT="$ENC"
  echo "Encrypted -> $OUT"
fi

chmod 600 "$OUT"
echo "Pruning backups older than ${RETENTION_DAYS}d"
find "$BACKUP_DIR" -type f -name 'ats_*' -mtime +"$RETENTION_DAYS" -delete
echo "Backup complete: $OUT"
