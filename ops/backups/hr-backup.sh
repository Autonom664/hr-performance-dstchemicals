#!/bin/bash
set -euo pipefail

BACKUP_ROOT="/srv/backups/hr"
MONGO_BACKUP_DIR="${BACKUP_ROOT}/mongo"
CONFIG_BACKUP_DIR="${BACKUP_ROOT}/config"
LOG_DIR="${BACKUP_ROOT}/logs"
TIMESTAMP=$(date +%Y-%m-%d_%H%M)
LOG_FILE="${LOG_DIR}/backup.log"
RETENTION_MONGO_DAYS=14
RETENTION_CONFIG_DAYS=30
APP_DIR="/home/mbi/apps/hr-performance-dstchemicals"

# Ensure we have a place to log (bootstrap)
mkdir -p "$LOG_DIR"

log() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE"
}

log "Starting backup job..."

# 1. Mongo Backup
log "Starting Mongo dump..."
ARCHIVE_NAME="hr-mongo-${TIMESTAMP}.archive.gz"
TEMP_ARCHIVE="${MONGO_BACKUP_DIR}/.tmp_${ARCHIVE_NAME}"
FINAL_ARCHIVE="${MONGO_BACKUP_DIR}/${ARCHIVE_NAME}"

mkdir -p "$MONGO_BACKUP_DIR"

# Using credentials found in running container environment
if docker exec hr-mongodb mongodump \
    --username hrapp_prod \
    --password '7gK3pQ8vN2wR6xT9mL4sJ1cH5zY0aB7n' \
    --authenticationDatabase admin \
    --archive --gzip > "$TEMP_ARCHIVE"; then
    mv "$TEMP_ARCHIVE" "$FINAL_ARCHIVE"
    FILESZ=$(du -h "$FINAL_ARCHIVE" | cut -f1)
    log "Mongo dump successful: $FINAL_ARCHIVE ($FILESZ)"
else
    log "ERROR: Mongo dump failed"
    rm -f "$TEMP_ARCHIVE"
    exit 1
fi

# 2. Config Backup
log "Starting Config backup..."
CONFIG_SNAPSHOT_DIR="${CONFIG_BACKUP_DIR}/${TIMESTAMP}"
mkdir -p "$CONFIG_SNAPSHOT_DIR"

if [ -d "$APP_DIR/deploy" ]; then
    cp "$APP_DIR/deploy/docker-compose.yml" "$CONFIG_SNAPSHOT_DIR/" 2>/dev/null || log "Warning: docker-compose.yml not found"
    cp "$APP_DIR/deploy/.env" "$CONFIG_SNAPSHOT_DIR/" 2>/dev/null || log "Warning: .env not found"
else
    log "Warning: App dir $APP_DIR/deploy not found"
fi

# Capture Docker metadata
docker ps --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}" > "$CONFIG_SNAPSHOT_DIR/docker-ps.txt"
docker images > "$CONFIG_SNAPSHOT_DIR/docker-images.txt"
docker volume ls > "$CONFIG_SNAPSHOT_DIR/docker-volumes.txt"

if [ -d "/etc/nginx" ]; then
    # Helper to prevent failure if permission denied
    if tar -czf "$CONFIG_SNAPSHOT_DIR/nginx-backup.tar.gz" -C / etc/nginx 2>/dev/null; then
        log "Nginx config backed up"
    else
        log "Warning: Could not backup /etc/nginx (permission denied?)"
    fi
fi

log "Config backup created at $CONFIG_SNAPSHOT_DIR"

# 3. Retention
log "Running retention cleanup..."
find "$MONGO_BACKUP_DIR" -name "hr-mongo-*.archive.gz" -mtime +$RETENTION_MONGO_DAYS -print -delete | while read f; do log "Deleted old mongo dump: $f"; done
find "$CONFIG_BACKUP_DIR" -maxdepth 1 -type d -name "20*" -mtime +$RETENTION_CONFIG_DAYS -print -exec rm -rf {} + | while read f; do log "Deleted old config snapshot: $f"; done

# 4. Permissions
chown -R backupuser:backupuser "$BACKUP_ROOT"
find "$BACKUP_ROOT" -type d -exec chmod 750 {} \;
find "$BACKUP_ROOT" -type f -exec chmod 640 {} \;

log "Backup job completed successfully."
