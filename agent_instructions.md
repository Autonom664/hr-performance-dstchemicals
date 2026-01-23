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
COOKIE_SECURE=true
AUTH_MODE=password
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
sudo certbot renew --dry-run
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
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 32k;
        proxy_busy_buffers_size 64k;
    }

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

## Post-Deployment: User Onboarding

### First-Time Setup

1. **Login as Admin:** Use `admin@company.com` / `Demo@123456`
2. **Change Admin Password:** The admin account has `must_change_password=false` for demo, but you should change it manually
3. **Import Real Users:**
   - Prepare CSV: `employee_email,employee_name,manager_email,department,is_admin`
   - Go to Admin → Import Users
   - Download the one-time credentials CSV
4. **Distribute Passwords:** Send passwords securely to users
5. **Create Production Cycle:** Admin → Cycles → New Cycle → Activate

### Security Recommendations

- Change all demo passwords after initial setup
- Use strong MONGO_ROOT_PASSWORD (32+ chars)
- Keep credentials CSV secure and delete after distribution
- Monitor `/var/log/nginx/hr-staging.error.log` for issues

---

## Troubleshooting

### Check Ports
```bash
sudo ss -tlnp | grep -E '8001|3000'
# Should show 127.0.0.1 binding only
```

### Check Logs
```bash
docker compose logs backend --tail 100
docker compose logs frontend --tail 100
sudo tail -f /var/log/nginx/hr-staging.error.log
```

### Restart Services
```bash
sudo systemctl restart nginx
cd /opt/hr-performance/deploy && docker compose restart
```

---

## Updating the Application

```bash
cd /opt/hr-performance
git pull origin main
cd deploy
docker compose down
docker compose up -d --build
docker compose logs -f
```
