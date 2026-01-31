#!/bin/bash
set -euo pipefail

BACKUP_SCRIPT="/usr/local/sbin/hr-backup.sh"
VERIFY_LOG="/srv/backups/hr/logs/verify-$(date +%Y-%m-%d_%H%M).log"

echo "Starting Backup Verification..."
echo "Log file: $VERIFY_LOG"

# 1. Run the backup job
echo "Running backup job manually..."
if $BACKUP_SCRIPT; then
    echo "✅ Backup script exited with 0"
else
    echo "❌ Backup script failed"
    exit 1
fi

# 2. Check for Mongo Archive
LATEST_ARCHIVE=$(ls -t /srv/backups/hr/mongo/hr-mongo-*.archive.gz | head -n1)
if [ -f "$LATEST_ARCHIVE" ]; then
    SIZE=$(stat -c%s "$LATEST_ARCHIVE")
    if [ "$SIZE" -gt 1000 ]; then
        echo "✅ Mongo archive exists and is non-empty ($SIZE bytes): $LATEST_ARCHIVE"
    else
        echo "❌ Mongo archive is too small ($SIZE bytes)"
        exit 1
    fi
else
    echo "❌ No mongo archive found"
    exit 1
fi

# 3. Dry-Run Restore Test
echo "Starting Restore Test (in temporary container)..."
TEST_CONTAINER="hr-restore-test-$(date +%s)"
TEST_NET="hr-restore-net-$(date +%s)"
TEST_VOL="hr-restore-vol-$(date +%s)"

cleanup() {
    echo "Cleaning up verify resources..."
    docker rm -f $TEST_CONTAINER >/dev/null 2>&1 || true
    docker volume rm $TEST_VOL >/dev/null 2>&1 || true
    docker network rm $TEST_NET >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Create isolated env
docker network create $TEST_NET >/dev/null
docker volume create $TEST_VOL >/dev/null

# Start mongo container
docker run -d --name $TEST_CONTAINER \
    --network $TEST_NET \
    -v $TEST_VOL:/data/db \
    mongo:7.0 >/dev/null

echo "Waiting for test mongo to be ready..."
sleep 5

# Restore
echo "Restoring archive to test container..."
# Stream the archive into the container
if cat "$LATEST_ARCHIVE" | docker exec -i $TEST_CONTAINER mongorestore --archive --gzip --drop; then
   echo "✅ mongorestore command succeeded"
else
   echo "❌ mongorestore command failed"
   exit 1
fi

# Verify data
echo "Verifying restored databases..."
DBS=$(docker exec $TEST_CONTAINER mongosh --quiet --eval "db.adminCommand('listDatabases').databases.map(d => d.name).join(', ')")
echo "Restored DBs: $DBS"

if [[ "$DBS" == *"hr_performance"* ]]; then
    echo "✅ Database 'hr_performance' found in restored data"
else
    echo "❌ Database 'hr_performance' NOT found"
    exit 1
fi

echo "Verification Complete. All tests passed."
