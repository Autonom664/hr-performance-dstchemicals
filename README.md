# HR Performance Management System

A portable, self-hosted HR Performance Management web application for annual performance reviews and EDI conversations. Designed for 80-200 users with Docker-based deployment.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Environment Configuration](#environment-configuration)
- [Authentication](#authentication)
- [Security Configuration](#security-configuration)
- [Deployment](#deployment)
- [API Reference](#api-reference)
- [Staging Sanity Checks](#staging-sanity-checks)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Network                          │
├─────────────────────────────────────────────────────────────────┤
│   ┌─────────────┐              ┌─────────────┐                  │
│   │   Frontend  │◄────────────►│   Backend   │                  │
│   │   (React)   │   REST API   │  (FastAPI)  │                  │
│   │   Port 3000 │              │   Port 8001 │                  │
│   └─────────────┘              └──────┬──────┘                  │
│                                       │                          │
├───────────────────────────────────────┼─────────────────────────┤
│                        Internal Network (isolated)               │
│                                       │                          │
│                                ┌──────▼──────┐                  │
│                                │   MongoDB   │                  │
│                                │   Port 27017│                  │
│                                │  (internal) │                  │
│                                └─────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
```

**Stack:**
- **Frontend**: React 19, Tailwind CSS, shadcn/ui, Tiptap rich text editor
- **Backend**: FastAPI (Python 3.11), Motor (async MongoDB driver)
- **Database**: MongoDB 7.0 (with authentication, internal network only)
- **PDF Generation**: fpdf2

---

## Quick Start

### Prerequisites
- Docker 24+ and Docker Compose v2
- Git

### Local Development

```bash
# Clone and navigate
cd /path/to/hr-performance-app

# Copy and configure environment
cd deploy
cp .env.example .env
# Edit .env with your values (dev defaults work for local testing)

# Start services
docker-compose up -d

# Seed demo data (optional)
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

## Environment Configuration

### Required Variables

| Variable | Description | Local Default | Production |
|----------|-------------|---------------|------------|
| `MONGO_ROOT_USERNAME` | MongoDB admin username | `hrapp_dev` | Use strong username |
| `MONGO_ROOT_PASSWORD` | MongoDB admin password | (set in .env) | **Strong password required** |
| `DB_NAME` | Database name | `hr_performance` | `hr_performance` |
| `REACT_APP_BACKEND_URL` | Backend URL for frontend | `http://localhost:8001` | `https://hr-staging.dstchemicals.com` |
| `CORS_ORIGINS` | Allowed origins (comma-separated) | `http://localhost:3000` | `https://hr-staging.dstchemicals.com` |

### Authentication Variables

| Variable | Description | Local Default | Production |
|----------|-------------|---------------|------------|
| `AUTH_MODE` | `email` or `entra` | `email` | `email` |
| `SHOW_CODE_IN_RESPONSE` | Show verification code in API | `true` | **`false`** |
| `DEV_VERIFICATION_CODE` | Fixed code for testing | `123456` | (empty) |
| `SESSION_EXPIRY_HOURS` | Session lifetime | `24` | `8` |

### Cookie Security Variables

| Variable | Description | Local Default | Production |
|----------|-------------|---------------|------------|
| `COOKIE_SECURE` | Require HTTPS for cookies | `false` | **`true`** |
| `COOKIE_SAMESITE` | SameSite cookie policy | `lax` | `lax` |

### Entra SSO Variables (Scaffolded, Not Enabled)

| Variable | Description |
|----------|-------------|
| `ENTRA_TENANT_ID` | Microsoft Entra tenant ID |
| `ENTRA_CLIENT_ID` | App registration client ID |
| `ENTRA_CLIENT_SECRET` | App registration client secret |
| `ENTRA_REDIRECT_URI` | OAuth callback URL |
| `ENTRA_SCOPES` | OAuth scopes (default: `openid profile email`) |

---

## Authentication

### Email Authentication (Active)

The current authentication method uses email-based verification codes:

1. User enters email address
2. System generates 6-digit code (stored in DB, expires in 10 minutes)
3. User enters code to complete login
4. Session created with httpOnly cookie

**Development Mode:**
- Set `SHOW_CODE_IN_RESPONSE=true` to display code in UI
- Set `DEV_VERIFICATION_CODE=123456` to use a fixed code

**Production Mode:**
- `SHOW_CODE_IN_RESPONSE=false` (codes not exposed)
- `DEV_VERIFICATION_CODE=` (empty, random codes generated)
- In production, codes would be sent via email (not implemented in MVP)

### Microsoft Entra SSO (Scaffolded, Disabled)

Entra ID integration is scaffolded but disabled by default. To enable:

1. Register app in Azure Portal → Microsoft Entra ID → App registrations
2. Set redirect URI: `https://your-domain.com/api/auth/entra/callback`
3. Configure environment:
   ```env
   AUTH_MODE=entra
   ENTRA_TENANT_ID=your-tenant-id
   ENTRA_CLIENT_ID=your-client-id
   ENTRA_CLIENT_SECRET=your-secret
   ENTRA_REDIRECT_URI=https://your-domain.com/api/auth/entra/callback
   ```
4. Restart backend service

**Important:** Users must exist in the system (imported via admin panel) before they can log in via Entra. OAuth only identifies users; authorization is based on imported user data.

---

## Security Configuration

### MongoDB Security

MongoDB is configured with authentication and runs on an internal Docker network:

- **Not exposed publicly** - no port binding to host
- **Authentication required** - uses `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_PASSWORD`
- **Internal network** - only accessible by backend container

The connection string format:
```
mongodb://<username>:<password>@mongodb:27017/<database>?authSource=admin
```

### CORS Configuration

CORS is configured via the `CORS_ORIGINS` environment variable:

**Local Development:**
```env
CORS_ORIGINS=http://localhost:3000
```

**Staging (hr-staging.dstchemicals.com):**
```env
CORS_ORIGINS=https://hr-staging.dstchemicals.com
```

**Multiple origins (if needed):**
```env
CORS_ORIGINS=https://hr-staging.dstchemicals.com,https://www.hr-staging.dstchemicals.com
```

⚠️ **Never use wildcards (`*`) in staging or production.**

### Session Security

- Sessions are stored in MongoDB with expiration
- Session tokens are generated using `secrets.token_urlsafe(32)`
- Cookies are:
  - `httpOnly=true` (not accessible via JavaScript)
  - `secure=true` in production (HTTPS only)
  - `samesite=lax` (CSRF protection)
- Sessions are invalidated on logout
- Expired sessions are rejected at API level

### Authorization Model

Authorization is strictly enforced server-side:

| Role | Permissions |
|------|-------------|
| Employee | View/edit own conversation only |
| Manager | View/edit direct reports' conversations |
| Admin | Full access to all data |

Authorization checks are performed on every API request based on the imported user hierarchy, not OAuth claims.

---

## Deployment

### OVH Staging Deployment

1. **Prepare server:**
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com | sh
   
   # Clone repository
   git clone <repo-url> /opt/hr-performance
   cd /opt/hr-performance/deploy
   ```

2. **Configure environment:**
   ```bash
   cp .env.ovh.example .env
   # Edit .env with production values
   nano .env
   ```

   Required changes:
   ```env
   MONGO_ROOT_PASSWORD=<strong-password-min-32-chars>
   REACT_APP_BACKEND_URL=https://hr-staging.dstchemicals.com
   CORS_ORIGINS=https://hr-staging.dstchemicals.com
   SHOW_CODE_IN_RESPONSE=false
   COOKIE_SECURE=true
   ```

3. **Start services:**
   ```bash
   docker-compose up -d
   ```

4. **Configure reverse proxy (nginx/traefik):**
   - Frontend: proxy to `localhost:3000`
   - Backend: proxy `/api/*` to `localhost:8001`

5. **Seed initial data:**
   ```bash
   docker exec hr-backend python seed_data.py
   ```

### Reverse Proxy Configuration (nginx example)

```nginx
server {
    listen 443 ssl http2;
    server_name hr-staging.dstchemicals.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
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

The following sanity checks have been verified for staging deployment:

### 1. Authorization Isolation ✅

| Test | Result |
|------|--------|
| Employee cannot access other employee's conversation via ID | PASS - Returns 403 |
| Employee cannot access conversation via URL manipulation | PASS - Returns 403 |
| Manager cannot access non-report's conversation | PASS - Returns 403 |
| Admin can access any conversation | PASS |

### 2. Session & Cookie Security ✅

| Test | Result |
|------|--------|
| Sessions use httpOnly cookies | PASS |
| Session expiry is enforced | PASS - Expired sessions rejected |
| Logout invalidates session | PASS - Token deleted from DB |
| Cookie secure flag respects config | PASS |

### 3. Cycle Integrity ✅

| Test | Result |
|------|--------|
| Only one active cycle at a time | PASS - Activating archives others |
| Status transitions work correctly | PASS |
| Cannot create conversations without active cycle | PASS |

### 4. PDF Export Completeness ✅

| Test | Result |
|------|--------|
| PDF includes employee details | PASS |
| PDF includes manager details | PASS |
| PDF includes cycle name and dates | PASS |
| PDF includes all conversation fields | PASS |
| PDF includes status and timestamps | PASS |
| No truncated or missing fields | PASS |

### 5. Data Persistence & Restart Safety ✅

| Test | Result |
|------|--------|
| Data persists after container restart | PASS |
| Sessions handled correctly after restart | PASS |
| Application recovers cleanly | PASS |

---

## Known Limitations

1. **Email delivery not implemented** - Verification codes are displayed in UI (dev mode) or would need email service integration for production
2. **No password reset** - Users are managed via admin import only
3. **Single active cycle** - Only one performance cycle can be active at a time
4. **No email notifications** - Status changes do not trigger emails

---

## License

MIT
