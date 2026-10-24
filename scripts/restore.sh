#!/usr/bin/env bash
# Restore a database dump and (optionally) the uploaded files:  ./scripts/restore.sh backups/db-<date>.gz [backups/uploads-<date>.tgz]
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f "${1:-}" ] || { echo "Usage: $0 <db.gz> [uploads.tgz]"; exit 1; }
db=$(grep -E '^DB_NAME=' .env 2>/dev/null | cut -d= -f2 || true); db=${db:-sellandiammanpowerinfra}
read -r -p "This replaces the current data in '$db'. Type RESTORE to continue: " ok
[ "$ok" = "RESTORE" ] || exit 1
docker compose exec -T mongo mongorestore --drop --nsInclude="$db.*" --archive --gzip < "$1"
if [ -n "${2:-}" ]; then docker compose exec -T backend sh -c 'tar -xzf - -C /app/uploads' < "$2"; fi
docker compose restart backend
echo "Restored."
