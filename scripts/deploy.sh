#!/usr/bin/env bash
# One-command update for the live server:  powerinfra-deploy        (or: powerinfra-deploy <branch>)
# Backs up, pulls the latest code from git, rebuilds, waits until the site answers, and says how to roll back.
# Installed on the server as /usr/local/bin/powerinfra-deploy:
#   install -m 755 /opt/sellandiammanpowerinfra/scripts/deploy.sh /usr/local/bin/powerinfra-deploy
# FORCE=1 powerinfra-deploy   rebuilds even when there is nothing new (e.g. after editing backend/.env).
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/sellandiammanpowerinfra}"
SITE="https://www.sellandiammanpowerinfra.com"
LOCAL="http://127.0.0.1:8090"
BRANCH="${1:-main}"

say() { printf '\n\033[1;33m==> %s\033[0m\n' "$*"; }
cd "$APP_DIR"

OLD=$(git rev-parse --short HEAD)
say "Checking for new code ($BRANCH, now at $OLD)"
git fetch --quiet origin "$BRANCH"
INCOMING=$(git rev-parse --short "origin/$BRANCH")
if [ "$OLD" = "$INCOMING" ] && [ "${FORCE:-0}" != "1" ]; then
  echo "Already up to date ($OLD). Nothing to rebuild. To rebuild anyway: FORCE=1 powerinfra-deploy"
  exit 0
fi

say "Backing up the database and uploads"
./scripts/backup-now.sh || { echo "The backup failed, so nothing was changed."; exit 1; }

say "Updating the code"
git checkout --quiet "$BRANCH"
if ! git merge --ff-only --quiet "origin/$BRANCH"; then
  echo "Files on the server were changed by hand, so git can't update cleanly. See them with: cd $APP_DIR && git status"
  exit 1
fi
NEW=$(git rev-parse --short HEAD)
[ "$OLD" != "$NEW" ] && git --no-pager log --oneline "$OLD..$NEW" | head -20

say "Building and restarting (a few minutes)"
docker compose up -d --build --remove-orphans

say "Waiting for the site to answer"
for i in $(seq 1 40); do
  if out=$(curl -fsS "$LOCAL/api/health" 2>/dev/null) && printf '%s' "$out" | grep -q '"ok":true'; then
    echo "$out"
    break
  fi
  if [ "$i" -eq 40 ]; then
    echo "The site didn't come back within 2 minutes. Last backend log lines:"
    docker compose logs --tail 60 backend || true
    echo
    echo "To go back to the previous version:  cd $APP_DIR && git reset --hard $OLD && docker compose up -d --build"
    exit 1
  fi
  sleep 3
done

docker image prune -f >/dev/null 2>&1 || true
say "Done: $OLD -> $NEW is live at $SITE"
echo "If something looks wrong:  cd $APP_DIR && git reset --hard $OLD && docker compose up -d --build"
