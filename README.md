# HR Performance Management System

A portable, self-hosted HR Performance Management web application for annual performance reviews and EDI conversations. Designed for 80-200 users with Docker-based deployment.

**Repository:** `https://github.com/Autonom664/HR` (private)  
**Target Staging Domain:** `hr-staging.dstchemicals.com`

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Finding & Configuring Environment Variables](#finding--configuring-environment-variables)
- [Environment Variables Reference](#environment-variables-reference)
- [Authentication](#authentication)
- [Security Configuration](#security-configuration)
- [Deployment](#deployment)
- [Reverse Proxy Configuration](#reverse-proxy-configuration)
- [API Reference](#api-reference)
- [Staging Sanity Checks](#staging-sanity-checks)
- [Known Limitations](#known-limitations)

---

## Architecture Overview

```
                    ┌─────────────────────────────────────────┐
                    │           OVH Server                     │
                    │                                          │
    Internet        │   ┌─────────────────────────────────┐   │
        │           │   │         nginx (ports 80/443)     │   │
        │           │   │   - TLS termination              │   │
        ▼           │   │   - HTTP→HTTPS redirect          │   │
   ┌─────────┐      │   │   - Reverse proxy                │   │
   │ Browser │◄────►│   └─────────────┬───────────────────┘   │
   └─────────┘      │                 │                        │
                    │    ┌────────────┴────────────┐          │
                    │    │                         │          │
                    │    ▼                         ▼          │
                    │ ┌──────────┐          ┌──────────┐      │
                    │ │ Frontend │          │ Backend  │      │
                    │ │ :3000    │          │ :8001    │      │
                    │ │ (local)  │          │ (local)  │      │
                    │ └──────────┘          └────┬─────┘      │
                    │                            │            │
                    │                     ┌──────▼─────┐      │
                    │                     │  MongoDB   │      │
                    │                     │  (internal)│      │
                    │                     └────────────┘      │
                    └─────────────────────────────────────────┘

Port Exposure:
- Public:  80 (nginx→HTTPS redirect), 443 (nginx→TLS)
- Private: 127.0.0.1:3000 (frontend), 127.0.0.1:8001 (backend)
- Internal: MongoDB (no host port binding)
```

**Stack:**
- **Frontend:** React 19, Tailwind CSS, shadcn/ui, Tiptap rich text editor
- **Backend:** FastAPI (Python 3.11), Motor (async MongoDB driver)
- **Database:** MongoDB 7.0 (with authentication, internal network only)
- **PDF Generation:** fpdf2
- **Reverse Proxy:** nginx (TLS termination, routing)

---

## Quick Start

### Prerequisites
- Docker 24+ and Docker Compose v2
- Git

### Local Development

```bash
# Clone repository
git clone https://github.com/Autonom664/HR.git hr-performance
cd hr-performance/deploy

# Copy and configure environment
cp .env.example .env
# Edit .env - defaults work for local testing

# Start services
docker compose up -d

# Seed demo data (first time)
docker exec hr-backend python seed_data.py

# Access the app
# Frontend: http://localhost:3000
# Backend API: http://localhost:8001/api
```

### Demo Accounts (after seeding)

| Role | Email | Notes |
|------|-------|-------|
| Admin | admin@company.com | Full system access |
| Manager | engineering.lead@company.com | Team reviews |
| Employee | developer1@company.com | Self-review only |

---

## Finding & Configuring Environment Variables

### Repository Structure

```
/deploy/
├── .env.example        # Template for LOCAL development (committed)
├── .env.ovh.example    # Template for OVH staging/production (committed)
├── .env                # YOUR actual values (NOT committed, in .gitignore)
├── docker-compose.yml  # Docker services configuration
├── backend/
│   └── Dockerfile
└── frontend/
    └── Dockerfile
```

### Template Files (Safe to Commit)

| File | Purpose | Contains Secrets? |
|------|---------|-------------------|
| `/deploy/.env.example` | Local development template | No (placeholders only) |
| `/deploy/.env.ovh.example` | OVH staging template | No (placeholders only) |

### Actual Configuration (Never Commit)

| File | Purpose | Location |
|------|---------|----------|
| `/deploy/.env` | Active configuration | Created from template, contains real values |

### How to Configure

**Local Development:**
```bash
cd deploy
cp .env.example .env
# Edit .env with your values (defaults mostly work)
```

**OVH Staging:**
```bash
cd /opt/hr-performance/deploy
cp .env.ovh.example .env
nano .env
# Set MONGO_ROOT_PASSWORD to a strong random value
# Other values are pre-configured for staging
```

---

## Environment Variables Reference

### Complete Variable List

| Variable | Description | Local Default | OVH Staging |
|----------|-------------|---------------|-------------|
| **Database** |
| `MONGO_ROOT_USERNAME` | MongoDB admin username | `hrapp_dev` | `hrapp_prod` |
| `MONGO_ROOT_PASSWORD` | MongoDB admin password | (set in .env) | **Strong password (32+ chars)** |
| `DB_NAME` | Database name | `hr_performance` | `hr_performance` |
| **URLs & CORS** |
| `REACT_APP_BACKEND_URL` | Backend URL for frontend | `http://localhost:8001` | (empty) - uses relative `/api` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000` | `https://hr-staging.dstchemicals.com` |
| **Ports** |
| `BACKEND_PORT` | Backend container port | `8001` | `8001` |
| `FRONTEND_PORT` | Frontend container port | `3000` | `3000` |
| **Authentication** |
| `AUTH_MODE` | Auth method: `email` or `entra` | `email` | `email` |
| `SHOW_CODE_IN_RESPONSE` | Show verification code in API | `true` | **`false`** |
| `DEV_VERIFICATION_CODE` | Fixed code for testing | `123456` | (empty) |
| `SESSION_EXPIRY_HOURS` | Session lifetime in hours | `24` | `8` |
| **Cookie Security** |
| `COOKIE_SECURE` | Require HTTPS for cookies | `false` | **`true`** |
| `COOKIE_SAMESITE` | SameSite cookie policy | `lax` | `lax` |
| **Entra SSO (scaffolded)** |
| `ENTRA_TENANT_ID` | Microsoft Entra tenant ID | (empty) | (empty) |
| `ENTRA_CLIENT_ID` | App registration client ID | (empty) | (empty) |
| `ENTRA_CLIENT_SECRET` | App registration secret | (empty) | (empty) |
| `ENTRA_REDIRECT_URI` | OAuth callback URL | (empty) | `https://hr-staging.dstchemicals.com/api/auth/entra/callback` |
| `ENTRA_SCOPES` | OAuth scopes | `openid profile email` | `openid profile email` |

### Critical Security Settings for Staging/Production

```env
# These MUST be set correctly for staging:
MONGO_ROOT_PASSWORD=<strong-random-password-32-chars>
REACT_APP_BACKEND_URL=                    # Empty = uses /api
CORS_ORIGINS=https://hr-staging.dstchemicals.com
SHOW_CODE_IN_RESPONSE=false               # NEVER true in staging
COOKIE_SECURE=true                        # ALWAYS true with HTTPS
```

---

## Authentication

### Email Authentication (Active)

Current authentication uses email-based verification codes:

1. User enters email address
2. System generates 6-digit code (stored in DB, expires in 10 minutes)
3. User enters code to complete login
4. Session created with httpOnly cookie

**Development Mode:**
- `SHOW_CODE_IN_RESPONSE=true` displays code in UI
- `DEV_VERIFICATION_CODE=123456` uses fixed code

**Staging/Production Mode:**
- `SHOW_CODE_IN_RESPONSE=false` - codes not exposed
- `DEV_VERIFICATION_CODE=` empty - random codes generated
- Note: Email delivery not implemented; use admin import for users

### Microsoft Entra SSO (Scaffolded, Disabled)

Entra ID integration is scaffolded but disabled by default. See `/deploy/.env.ovh.example` for configuration instructions.

---

## Security Configuration

### Port Exposure Model

| Component | Local Dev | OVH Staging | Notes |
|-----------|-----------|-------------|-------|
| nginx | N/A | 80, 443 (public) | TLS termination |
| Frontend | 3000 (public) | 127.0.0.1:3000 | nginx proxies |
| Backend | 8001 (public) | 127.0.0.1:8001 | nginx proxies |
| MongoDB | internal only | internal only | Never exposed |

### MongoDB Security

- **Not exposed publicly** - no host port binding
- **Authentication required** - uses `MONGO_ROOT_USERNAME/PASSWORD`
- **Internal network** - only accessible by backend container

### Session Security

- Sessions stored in MongoDB with expiration
- Session tokens: `secrets.token_urlsafe(32)`
- Cookies: `httpOnly=true`, `secure=true` (staging), `samesite=lax`
- Sessions invalidated on logout
- Expired sessions rejected at API level

---

## Deployment

### OVH Staging Deployment Checklist

See **[agent_instructions.md](./agent_instructions.md)** for detailed OVH-specific commands and configurations that cannot be done inside Emergent.

**Summary of required OVH manual tasks:**

1. **DNS:** Create A record for `hr-staging.dstchemicals.com`
2. **Server prep:** Install Docker, nginx, certbot
3. **Firewall:** Open only ports 80 and 443
4. **TLS:** Obtain Let's Encrypt certificate
5. **nginx:** Configure reverse proxy (see below)
6. **Deploy:** Clone repo, configure `.env`, start containers
7. **Verify:** Test health endpoint and login flow

### Docker Compose Usage

**Local Development:**
```bash
cd deploy
cp .env.example .env
docker compose up -d
```

**OVH Staging:**
```bash
cd /opt/hr-performance/deploy
cp .env.ovh.example .env
nano .env  # Set MONGO_ROOT_PASSWORD
docker compose up -d --build
```

---

## Reverse Proxy Configuration

### nginx Configuration for OVH

**File location:** `/etc/nginx/sites-available/hr-staging`

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
    # CRITICAL: location /api/ with trailing slash, proxy_pass also with /api/
    location /api/ {
        proxy_pass http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        
        # Required proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        
        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts for PDF export (can take longer)
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
        
        # Buffering
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
        
        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_cache_bypass $http_upgrade;
    }

    # Logging
    access_log /var/log/nginx/hr-staging.access.log;
    error_log /var/log/nginx/hr-staging.error.log;
}
```

### Frontend API Communication

The frontend uses **same-origin API calls** via nginx reverse proxy:

- `REACT_APP_BACKEND_URL` is empty in staging
- Frontend makes requests to relative `/api/*` paths
- nginx proxies `/api/*` to backend at `127.0.0.1:8001`
- No localhost URLs embedded in production builds

**How it works:**
```
Browser → https://hr-staging.dstchemicals.com/api/health
         → nginx → http://127.0.0.1:8001/api/health
                 → backend responds
```

---

## API Reference

### Authentication Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/email/start` | Start email login | No |
| POST | `/api/auth/email/verify` | Verify code, get session | No |
| GET | `/api/auth/me` | Get current user | Yes |
| POST | `/api/auth/logout` | Invalidate session | Yes |

### Admin Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/admin/users/import` | Import users (JSON) | Admin |
| POST | `/api/admin/users/import/csv` | Import users (CSV) | Admin |
| GET | `/api/admin/users` | List all users | Admin |
| POST | `/api/admin/cycles` | Create cycle | Admin |
| GET | `/api/admin/cycles` | List all cycles | Admin |
| PATCH | `/api/admin/cycles/:id` | Update cycle status | Admin |

### Employee Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/cycles/active` | Get active cycle | Yes |
| GET | `/api/conversations/me` | Get my conversation | Yes |
| PUT | `/api/conversations/me` | Update my conversation | Yes |

### Manager Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/manager/reports` | List direct reports | Manager |
| GET | `/api/manager/conversations/:email` | Get report's conversation | Manager |
| PUT | `/api/manager/conversations/:email` | Update report's conversation | Manager |

### Export Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/conversations/:id/pdf` | Export conversation to PDF | Owner/Manager/Admin |

---

## Staging Sanity Checks

Verified on **2026-01-23**:

### 1. Authorization Isolation ✅

| Test | Result |
|------|--------|
| Employee cannot access other employee's conversation | ✅ 403 Forbidden |
| Employee cannot access manager endpoints | ✅ 403 Forbidden |
| Manager cannot access non-report's conversation | ✅ 403 Forbidden |
| Admin can access any conversation | ✅ 200 OK |

### 2. Session & Cookie Security ✅

| Test | Result |
|------|--------|
| Sessions use httpOnly cookies | ✅ Verified |
| Secure cookie attributes | ✅ SameSite=lax |
| Invalid token rejection | ✅ 401 Unauthorized |
| Logout invalidates session | ✅ Token deleted |

### 3. Cycle Integrity ✅

| Test | Result |
|------|--------|
| Only one active cycle at a time | ✅ Previous archived |
| Status transitions work | ✅ Draft→Active→Archived |

### 4. PDF Export ✅

| Test | Result |
|------|--------|
| Includes all fields | ✅ Verified |
| Includes timestamps | ✅ Verified |

### 5. Data Persistence ✅

| Test | Result |
|------|--------|
| Data persists after restart | ✅ Verified |
| Sessions valid after restart | ✅ Verified |

---

## Known Limitations

1. **Email delivery not implemented** - Verification codes displayed in UI (dev mode only)
2. **No password reset** - Users managed via admin import
3. **Single active cycle** - Only one performance cycle active at a time
4. **Entra SSO** - Scaffolded but not enabled (set `AUTH_MODE=entra` to enable)

---

## License

MIT
