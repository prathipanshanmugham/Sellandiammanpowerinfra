#!/usr/bin/env bash
# Take a backup immediately (in addition to the nightly one).
set -euo pipefail
cd "$(dirname "$0")/.."
d=$(date +%Y-%m-%d-%H%M)
db=$(grep -E '^DB_NAME=' .env 2>/dev/null | cut -d= -f2 || true); db=${db:-sellandiammanpowerinfra}
docker compose exec -T mongo mongodump --db="$db" --archive --gzip > "backups/db-$d.gz"
docker compose exec -T backend tar -czf - -C /app/uploads . > "backups/uploads-$d.tgz"
echo "Saved backups/db-$d.gz and backups/uploads-$d.tgz — copy them off the server."
