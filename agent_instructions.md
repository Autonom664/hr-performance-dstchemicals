# OVH Deployment Instructions

This document contains tasks that **cannot be completed inside Emergent** and must be performed manually on the OVH server.

**Target Domain:** `hr-staging.dstchemicals.com`  
**Repository:** `https://github.com/Autonom664/HR` (private)

---

## Pre-Deployment Checklist

- [ ] DNS A record configured
- [ ] Server has Docker, nginx, certbot installed
- [ ] Firewall allows only ports 22, 80, 443
- [ ] TLS certificate obtained
- [ ] nginx reverse proxy configured
- [ ] Application deployed and running
- [ ] Demo data seeded
- [ ] Backup strategy configured

---

## 1. DNS Configuration

Create an A record pointing to your OVH server IP:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | hr-staging | `YOUR_OVH_SERVER_IP` | 3600 |

**Verify:**
```bash
dig hr-staging.dstchemicals.com +short
# Should return your OVH server IP
```

---

## 2. Server Preparation

SSH to your OVH server and run:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in for group changes

# Install nginx
sudo apt install -y nginx

# Install certbot for TLS
sudo apt install -y certbot python3-certbot-nginx

# Create application directory
sudo mkdir -p /opt/hr-performance
sudo chown $USER:$USER /opt/hr-performance
```

---

## 3. Firewall Configuration

```bash
# Allow SSH (do this first!)
sudo ufw allow ssh

# Allow HTTP and HTTPS only
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Verify
sudo ufw status
```

**Expected output:**
```
Status: active
To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

⚠️ **Ports 8001 (backend) and 3000 (frontend) should NOT be open.** nginx proxies all traffic.

---

## 4. Clone Repository and Configure

```bash
cd /opt/hr-performance

# Clone the private repo
git clone https://github.com/Autonom664/HR.git .

# Navigate to deploy directory
cd deploy

# Copy environment template
cp .env.ovh.example .env

# Generate strong MongoDB password
openssl rand -base64 32

# Edit configuration
nano .env
```

**Required .env changes:**
```bash
# Set the generated strong password
MONGO_ROOT_PASSWORD=<paste-generated-password-here>

# Verify these settings (should already be correct):
REACT_APP_BACKEND_URL=
CORS_ORIGINS=https://hr-staging.dstchemicals.com
COOKIE_SECURE=true
AUTH_MODE=password
```

---

## 5. TLS Certificate

```bash
# Stop nginx temporarily
sudo systemctl stop nginx

# Obtain certificate (standalone mode)
sudo certbot certonly --standalone -d hr-staging.dstchemicals.com

# Certificate paths:
# /etc/letsencrypt/live/hr-staging.dstchemicals.com/fullchain.pem
# /etc/letsencrypt/live/hr-staging.dstchemicals.com/privkey.pem

# Start nginx
sudo systemctl start nginx

# Test auto-renewal
sudo certbot renew --dry-run
```

---

## 6. nginx Configuration

Create nginx site configuration:

```bash
sudo nano /etc/nginx/sites-available/hr-staging
```

**Paste this configuration:**

```nginx
# HTTP -> HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name hr-staging.dstchemicals.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name hr-staging.dstchemicals.com;

    ssl_certificate /etc/letsencrypt/live/hr-staging.dstchemicals.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hr-staging.dstchemicals.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # Frontend
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_cache_bypass $http_upgrade;
    }

    access_log /var/log/nginx/hr-staging.access.log;
    error_log /var/log/nginx/hr-staging.error.log;
}
```

**Enable the site:**
```bash
sudo ln -s /etc/nginx/sites-available/hr-staging /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

---

## 7. Start Application

```bash
cd /opt/hr-performance/deploy

# Build and start containers
docker compose up -d --build

# Check container status
docker compose ps

# View logs
docker compose logs -f

# Seed demo data (first time only)
docker exec hr-backend python seed_data.py
```

---

## 8. Verification

```bash
# Test health endpoint
curl -s https://hr-staging.dstchemicals.com/api/health
# Expected: {"status":"healthy","auth_mode":"password","version":"2.0.0"}

# Test login with demo account
curl -s -X POST https://hr-staging.dstchemicals.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@company.com","password":"Demo@123456"}'
# Expected: JSON with user info and token
```

---

## 9. MongoDB Backup Strategy

### Manual Backup

```bash
# Create backup directory
mkdir -p /opt/hr-performance/backups

# Full database backup
docker exec hr-mongodb mongodump \
  --username hrapp_prod \
  --password "YOUR_MONGO_PASSWORD" \
  --authenticationDatabase admin \
  --db hr_performance \
  --archive=/data/db/backup-$(date +%Y%m%d-%H%M%S).archive

# Copy backup from container
docker cp hr-mongodb:/data/db/backup-*.archive /opt/hr-performance/backups/

# Clean up container backup
docker exec hr-mongodb rm /data/db/backup-*.archive
```

### Automated Daily Backup (cron)

```bash
# Create backup script
sudo nano /opt/hr-performance/backup.sh
```

**Script content:**
```bash
#!/bin/bash
BACKUP_DIR=/opt/hr-performance/backups
DATE=$(date +%Y%m%d-%H%M%S)
MONGO_PASSWORD="YOUR_MONGO_PASSWORD"

# Create backup
docker exec hr-mongodb mongodump \
  --username hrapp_prod \
  --password "$MONGO_PASSWORD" \
  --authenticationDatabase admin \
  --db hr_performance \
  --archive=/data/db/backup-$DATE.archive

# Copy to host
docker cp hr-mongodb:/data/db/backup-$DATE.archive $BACKUP_DIR/

# Clean container backup
docker exec hr-mongodb rm /data/db/backup-$DATE.archive

# Keep only last 7 days
find $BACKUP_DIR -name "backup-*.archive" -mtime +7 -delete
```

```bash
# Make executable
chmod +x /opt/hr-performance/backup.sh

# Add to cron (daily at 2 AM)
crontab -e
# Add line: 0 2 * * * /opt/hr-performance/backup.sh
```

### Restore from Backup

```bash
# Copy backup to container
docker cp /opt/hr-performance/backups/backup-YYYYMMDD.archive hr-mongodb:/data/db/

# Restore
docker exec hr-mongodb mongorestore \
  --username hrapp_prod \
  --password "YOUR_MONGO_PASSWORD" \
  --authenticationDatabase admin \
  --archive=/data/db/backup-YYYYMMDD.archive
```

### Backup Storage Recommendations

1. **Local:** Keep 7 days of backups in `/opt/hr-performance/backups`
2. **Offsite:** Copy weekly backups to separate storage (S3, another server, etc.)
3. **Test Restores:** Periodically verify backups can be restored

---

## 10. Updating the Application

```bash
cd /opt/hr-performance
git pull origin main
cd deploy
docker compose down
docker compose up -d --build
docker compose logs -f
```

---

## 11. Post-Deployment: User Setup

### Replace Demo Data with Real Users

1. **Login as Admin:** `admin@company.com` / `Demo@123456`
2. **Change Admin Password:** Profile → Change Password
3. **Import Real Users:**
   - Prepare CSV with employee data
   - Admin → Import Users
   - Download credentials CSV (ONE-TIME)
4. **Distribute Passwords:** Send securely to employees
5. **Create Production Cycle:** Admin → Cycles → New Cycle → Activate

---

## Troubleshooting

### Check Container Status
```bash
cd /opt/hr-performance/deploy
docker compose ps
docker compose logs backend --tail 100
docker compose logs frontend --tail 100
docker compose logs mongodb --tail 100
```

### Check nginx
```bash
sudo nginx -t
sudo tail -f /var/log/nginx/hr-staging.error.log
```

### Check Ports (should be localhost only)
```bash
sudo ss -tlnp | grep -E '8001|3000'
# Should show 127.0.0.1 binding only
```

### Restart Services
```bash
sudo systemctl restart nginx
cd /opt/hr-performance/deploy && docker compose restart
```

---

## Security Checklist

- [ ] MONGO_ROOT_PASSWORD is strong (32+ chars)
- [ ] `.env` file is NOT in git
- [ ] Firewall blocks direct access to 8001/3000
- [ ] COOKIE_SECURE=true
- [ ] CORS_ORIGINS is exact domain (no wildcards)
- [ ] Demo passwords changed after setup
- [ ] Backup cron configured and tested
