#!/bin/sh
# Nightly at about 02:30 IST: database dump and uploaded files, kept for KEEP_DAYS days.
while true; do
  now=$(date -u +%H%M)
  if [ "$now" = "2100" ]; then
    d=$(date -u +%Y-%m-%d)
    mongodump --uri="mongodb://mongo:27017/${DB_NAME}" --archive="/backups/db-$d.gz" --gzip && echo "db backup $d ok"
    tar -czf "/backups/uploads-$d.tgz" -C /uploads . && echo "uploads backup $d ok"
    find /backups -name 'db-*.gz' -mtime +"${KEEP_DAYS:-30}" -delete
    find /backups -name 'uploads-*.tgz' -mtime +"${KEEP_DAYS:-30}" -delete
    sleep 61
  fi
  sleep 30
done
