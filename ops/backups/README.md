# HR System Backups

**Location:** `/srv/backups/hr`

## Directory Structure
- `mongo/`: MongoDB dumps (`.archive.gz`)
- `config/`: Configuration snapshots (docker-compose, env) and docker metadata
- `logs/`: Backup logs

## Schedule
Backups run daily at **02:15 Server Time** via systemd timer.
- Service: `hr-backup.service`
- Timer: `hr-backup.timer`

## Manual Execution
Run the backup job manually:
```bash
sudo /usr/local/sbin/hr-backup.sh
```

## Restore Procedure (MongoDB)
To restore a specific archive:

1. **Stop the application:**
   ```bash
   cd ~/apps/hr-performance-dstchemicals
   docker compose down
   ```
   *(Or just stop the backend to prevent writes)*

2. **Start just the database:**
   ```bash
   docker compose up -d hr-mongodb
   ```

3. **Perform Restore:**
   ```bash
   # From host, using the running container
   # REPLACE THE FILENAME with the one you want to restore
   docker exec -i hr-mongodb mongorestore \
       --username hrapp_prod \
       --password 'MONGO_PASSWORD' \
       --authenticationDatabase admin \
       --archive --gzip --drop < /srv/backups/hr/mongo/hr-mongo-YYYY-MM-DD_HHMM.archive.gz
   ```
   *Note: `--drop` forces overwrite of existing data.*

4. **Restart Application:**
   ```bash
   docker compose up -d
   ```

## Retention Policy
- Top-level Mongo dumps: 14 days
- Configuration snapshots: 30 days
- Cleanup runs automatically with daily backup.

## Verification
A verification script is available to test the restore process in a temporary container without affecting production:
```bash
sudo /usr/local/sbin/hr-backup-verify.sh
```
