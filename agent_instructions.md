# OVH Deployment Instructions

This document contains tasks that **cannot be completed inside Emergent** and must be performed manually on the OVH server.

**Target Domain:** `hr-staging.dstchemicals.com`  
**Repository:** `https://github.com/Autonom664/HR` (private)

---

## Pre-Deployment Checklist

### 1. DNS Configuration (OVH DNS Panel or Domain Registrar)

Create an A record pointing to your OVH server IP:

```
Type: A
Name: hr-staging
Value: <YOUR_OVH_SERVER_IP>
TTL: 3600
```

**Verify DNS propagation:**
```bash
dig hr-staging.dstchemicals.com +short
# Should return your OVH server IP
```

---

### 2. Server Preparation (SSH to OVH Server)

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

### 3. Firewall Configuration (UFW)

```bash
# Allow SSH (important: do this first!)
sudo ufw allow ssh

# Allow HTTP and HTTPS only
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Verify rules
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

⚠️ **IMPORTANT:** Ports 8001 (backend) and 3000 (frontend) should NOT be open. Nginx proxies all traffic.

---

### 4. Clone Repository and Configure

```bash
cd /opt/hr-performance

# Clone the private repo (requires GitHub access)
git clone https://github.com/Autonom664/HR.git .

# Or if using deploy key:
git clone git@github.com:Autonom664/HR.git .

# Navigate to deploy directory
cd deploy

# Copy environment template
cp .env.ovh.example .env

# Edit with production values
nano .env
```

**Required .env changes:**
```env
# Generate a strong password (32+ chars)
MONGO_ROOT_PASSWORD=<generate-with: openssl rand -base64 32>

# These should already be correct in template:
REACT_APP_BACKEND_URL=
CORS_ORIGINS=https://hr-staging.dstchemicals.com
SHOW_CODE_IN_RESPONSE=false
COOKIE_SECURE=true
```

---

### 5. TLS Certificate (Let's Encrypt)

```bash
# Stop nginx temporarily
sudo systemctl stop nginx

# Obtain certificate
sudo certbot certonly --standalone -d hr-staging.dstchemicals.com

# Certificate will be saved to:
# /etc/letsencrypt/live/hr-staging.dstchemicals.com/fullchain.pem
# /etc/letsencrypt/live/hr-staging.dstchemicals.com/privkey.pem

# Start nginx
sudo systemctl start nginx
```

**Set up auto-renewal:**
```bash
# Test renewal
sudo certbot renew --dry-run

# Certbot automatically creates a cron job for renewal
```

---

### 6. Nginx Configuration

Create the nginx site configuration:

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
    
    # Redirect all HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name hr-staging.dstchemicals.com;

    # TLS certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/hr-staging.dstchemicals.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hr-staging.dstchemicals.com/privkey.pem;
    
    # Modern TLS configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Backend API - proxy to localhost:8001
    # IMPORTANT: Preserve /api prefix in proxy_pass
    location /api/ {
        proxy_pass http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        
        # Required proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        
        # WebSocket support (if needed)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts for PDF export (can take longer)
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
        
        # Buffering for large responses
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 32k;
        proxy_busy_buffers_size 64k;
    }

    # Frontend - proxy to localhost:3000
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        
        # Required proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        
        # WebSocket support for hot reload (dev) / React Router
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Cache control for static assets
        proxy_cache_bypass $http_upgrade;
    }

    # Logging
    access_log /var/log/nginx/hr-staging.access.log;
    error_log /var/log/nginx/hr-staging.error.log;
}
```

**Enable the site:**
```bash
# Create symlink to enable site
sudo ln -s /etc/nginx/sites-available/hr-staging /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

---

### 7. Start Application

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

### 8. Verification

```bash
# Test health endpoint via nginx proxy
curl -s https://hr-staging.dstchemicals.com/api/health

# Expected: {"status":"healthy","auth_mode":"email"}

# Test HTTP redirect
curl -I http://hr-staging.dstchemicals.com
# Expected: 301 redirect to https://

# Check container logs for errors
docker compose logs backend --tail 50
```

---

## Quick Reference: Environment Variables

| Variable | Where to Set | OVH Staging Value |
|----------|--------------|-------------------|
| `MONGO_ROOT_PASSWORD` | `/opt/hr-performance/deploy/.env` | Strong random password |
| `REACT_APP_BACKEND_URL` | `/opt/hr-performance/deploy/.env` | (empty - uses /api) |
| `CORS_ORIGINS` | `/opt/hr-performance/deploy/.env` | `https://hr-staging.dstchemicals.com` |
| `SHOW_CODE_IN_RESPONSE` | `/opt/hr-performance/deploy/.env` | `false` |
| `COOKIE_SECURE` | `/opt/hr-performance/deploy/.env` | `true` |

---

## Troubleshooting

### Check if ports are bound correctly
```bash
# Backend should be on 127.0.0.1:8001 only
sudo ss -tlnp | grep 8001
# Expected: 127.0.0.1:8001

# Frontend should be on 127.0.0.1:3000 only  
sudo ss -tlnp | grep 3000
# Expected: 127.0.0.1:3000
```

### Check nginx logs
```bash
sudo tail -f /var/log/nginx/hr-staging.error.log
```

### Check container logs
```bash
docker compose logs backend --tail 100
docker compose logs frontend --tail 100
```

### Restart services
```bash
# Restart nginx
sudo systemctl restart nginx

# Restart docker containers
cd /opt/hr-performance/deploy
docker compose restart
```

---

## Updating the Application

```bash
cd /opt/hr-performance

# Pull latest changes
git pull origin main

# Rebuild and restart
cd deploy
docker compose down
docker compose up -d --build

# Check logs
docker compose logs -f
```

---

## Rollback Procedure

```bash
cd /opt/hr-performance

# View recent commits
git log --oneline -10

# Rollback to specific commit
git checkout <commit-hash>

# Rebuild
cd deploy
docker compose down
docker compose up -d --build
```
