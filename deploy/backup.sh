#!/bin/sh
# Nightly backup: PostgreSQL dump (every night) + catalog images (Fridays).
# Customers' try-on photos are NOT backed up on purpose (privacy; they expire).
#   backup.sh           one backup now
#   backup.sh --loop    run forever, once a day at $BACKUP_HOUR (server time)
set -eu

DIR=/backups
KEEP=${BACKUP_KEEP_DAYS:-14}

run_backup() {
    stamp=$(date +%Y%m%d-%H%M)
    mkdir -p "$DIR"
    pg_dump -Fc -f "$DIR/db-$stamp.dump.part"
    mv "$DIR/db-$stamp.dump.part" "$DIR/db-$stamp.dump"
    echo "backup: database -> db-$stamp.dump"
    if [ "$(date +%u)" = "5" ] && [ -d /media/catalog ]; then
        tar -czf "$DIR/media-$stamp.tar.gz.part" -C /media catalog
        mv "$DIR/media-$stamp.tar.gz.part" "$DIR/media-$stamp.tar.gz"
        echo "backup: catalog images -> media-$stamp.tar.gz"
    fi
    find "$DIR" -name 'db-*.dump' -mtime +"$KEEP" -delete
    find "$DIR" -name 'media-*.tar.gz' -mtime +"$((KEEP * 2))" -delete
}

if [ "${1:-}" != "--loop" ]; then
    run_backup
    exit 0
fi

HOUR=${BACKUP_HOUR:-3}
last=""
while :; do
    today=$(date +%Y%m%d)
    if [ "$(date +%H)" -ge "$HOUR" ] && [ "$last" != "$today" ]; then
        run_backup || echo "backup: FAILED" >&2
        last=$today
    fi
    sleep 600
done
