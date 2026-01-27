# Production Deployment Checklist

## Pre-Deployment

- [x] Repository cloned to `~/apps/hr-performance-dstchemicals` on OVH server
- [x] Docker and Docker Compose installed
- [x] nginx installed and configured
- [x] DNS A record for `hr.dstchemicals.com` points to 57.129.111.133
- [x] Strong MongoDB password generated (32+ characters)
- [x] `.env` file created from `.env.ovh.example` with production values

## Security Configuration

- [x] Firewall configured (UFW enabled, only ports 22, 80, 443 open)
- [x] TLS certificate obtained via Let's Encrypt (expires 2026-04-24)
- [x] `COOKIE_SECURE=true` in `.env`
- [x] `CORS_ORIGINS=https://hr.dstchemicals.com` in `.env`
- [x] nginx security headers configured (X-Frame-Options, HSTS, etc.)

## Application Deployment

- [ ] Containers built and started: `docker compose up -d --build`
- [ ] All containers healthy: `docker compose ps`
- [ ] Backend health check passes: `curl https://hr.dstchemicals.com/api/health`
- [ ] Admin account created (ONE account only)
- [ ] Login tested with admin credentials
- [ ] **NO demo data seeded** (production uses real employee data)

## Post-Deployment Testing

- [ ] Admin panel loads and displays users (sorted alphabetically by name)
- [ ] Admin can create/edit performance review cycles
- [ ] Admin can reset passwords for multiple users
- [ ] Managers can see their direct reports and submitted reviews
- [ ] Employees can view manager name/email on dashboard
- [ ] Employees can save drafts and submit reviews to managers
- [ ] Conversations in draft status (`in_progress`) are only visible to the employee

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

## SSL/TLS Configuration Details

### Certificate Management

**Certificate location:**
- Fullchain: `/etc/letsencrypt/live/hr.dstchemicals.com/fullchain.pem`
- Private key: `/etc/letsencrypt/live/hr.dstchemicals.com/privkey.pem`
- Expires: 2026-04-24 (90-day validity)

**Auto-renewal:**
- Managed by certbot systemd timer
- Runs twice daily (check: `systemctl list-timers | grep certbot`)
- Test renewal: `sudo certbot renew --dry-run`

**Manual renewal (if needed):**
```bash
sudo certbot renew
sudo systemctl reload nginx
```

### Nginx Configuration

**Main config:** `/etc/nginx/sites-enabled/hr.dstchemicals.com`

**Key features:**
- HTTPS on port 443 (IPv4 and IPv6)
- HTTP to HTTPS redirect (301 Permanent)
- Reverse proxy to Docker containers:
  - Frontend: `http://127.0.0.1:3000/`
  - Backend: `http://127.0.0.1:8001/api/`
- Security headers:
  - HSTS: `max-age=86400` (1 day, increase to 31536000 after testing)
  - X-Frame-Options: SAMEORIGIN
  - X-Content-Type-Options: nosniff
  - X-XSS-Protection: 1; mode=block
  - Referrer-Policy: strict-origin-when-cross-origin
- Proxy headers for backend (X-Forwarded-Proto, X-Forwarded-For, etc.)

**Verify configuration:**
```bash
sudo nginx -t                    # Test syntax
sudo systemctl reload nginx      # Apply changes (no downtime)
curl -I https://hr.dstchemicals.com/  # Check headers
```

**Backup config before changes:**
```bash
sudo cp /etc/nginx/sites-enabled/hr.dstchemicals.com \
        /etc/nginx/sites-available/hr.dstchemicals.com.backup-$(date +%Y%m%d)
```

---

## Important Notes

1. **Never commit `.env` files** - Contains production credentials
2. **No demo data in production** - seed_data.py is for local development only
3. **Single admin account** - Created manually, not via seed script
4. **Employee data** - Imported by HR via CSV after deployment
5. **Backups** - Automated daily at 2 AM, retained for 7 days
