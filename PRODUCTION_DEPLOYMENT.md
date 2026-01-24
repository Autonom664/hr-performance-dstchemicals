# Production Deployment Checklist

## Pre-Deployment

- [ ] Repository cloned to `/opt/hr-performance` on OVH server
- [ ] Docker and Docker Compose installed
- [ ] nginx installed and configured
- [ ] DNS A record for `hr.dstchemicals.com` points to server IP
- [ ] Strong MongoDB password generated (32+ characters)
- [ ] `.env` file created from `.env.ovh.example` with production values

## Security Configuration

- [ ] Firewall configured (only ports 22, 80, 443 open)
- [ ] TLS certificate obtained via certbot
- [ ] `COOKIE_SECURE=true` in `.env`
- [ ] `CORS_ORIGINS=https://hr.dstchemicals.com` in `.env`
- [ ] nginx security headers configured (X-Frame-Options, etc.)

## Application Deployment

- [ ] Containers built and started: `docker compose up -d --build`
- [ ] All containers healthy: `docker compose ps`
- [ ] Backend health check passes: `curl https://hr.dstchemicals.com/api/health`
- [ ] Admin account created (ONE account only)
- [ ] Login tested with admin credentials
- [ ] **NO demo data seeded** (production uses real employee data)

## Post-Deployment

- [ ] MongoDB backup script configured
- [ ] Cron job for daily backups set up (2 AM)
- [ ] Test manual backup and restore process
- [ ] SSL certificate auto-renewal configured
- [ ] Monitoring/logging configured (optional but recommended)

## Production Data Import

After deployment is verified:

- [ ] Admin logs into https://hr.dstchemicals.com
- [ ] HR imports employee CSV data via admin panel
- [ ] Verify users can login with generated passwords
- [ ] Create first performance review cycle
- [ ] Test employee/manager workflows

## Rollback Plan

If issues occur:

```bash
# Stop containers
docker compose down

# Restore from backup
docker cp /opt/hr-performance/backups/backup-YYYYMMDD.archive hr-mongodb:/data/db/
docker exec hr-mongodb mongorestore \
  --username hrapp_prod \
  --password "MONGO_PASSWORD" \
  --authenticationDatabase admin \
  --archive=/data/db/backup-YYYYMMDD.archive

# Restart with previous version
git checkout <previous-commit>
docker compose up -d --build
```

## Support Contacts

- **Technical Issues:** [Your IT contact]
- **HR Questions:** [HR contact]
- **Database Backups:** Located in `/opt/hr-performance/backups/`

---

## Important Notes

1. **Never commit `.env` files** - Contains production credentials
2. **No demo data in production** - seed_data.py is for local development only
3. **Single admin account** - Created manually, not via seed script
4. **Employee data** - Imported by HR via CSV after deployment
5. **Backups** - Automated daily at 2 AM, retained for 7 days
