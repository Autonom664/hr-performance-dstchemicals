# HR Performance Management System

A portable, self-hosted HR Performance Management web application for annual performance reviews and EDI conversations. Designed for 80-200 users with Docker-based deployment.

**This system does NOT use numeric ratings.** Performance feedback is qualitative only.

**Repository:** `https://github.com/Autonom664/hr-performance-dstchemicals` (private)  
**Production Domain:** `hr.dstchemicals.com`

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [User Onboarding Flow](#user-onboarding-flow)
- [Admin Password Management](#admin-password-management)
- [Environment Variables Reference](#environment-variables-reference)
- [URL Configuration](#url-configuration)
- [CORS Configuration](#cors-configuration)
- [Performance Review Structure](#performance-review-structure)
- [PDF Export](#pdf-export)
- [Archived EDI Access](#archived-edi-access)
- [Backup Strategy](#backup-strategy)
- [Deployment](#deployment)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)

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
```

**Stack:**
- **Frontend:** React 19, Tailwind CSS, shadcn/ui, Tiptap rich text editor
- **Backend:** FastAPI (Python 3.11), Motor (async MongoDB driver)
- **Database:** MongoDB 7.0 (with authentication, internal network only)
- **PDF Generation:** fpdf2

---

## Quick Start

### Prerequisites
- Docker 24+ and Docker Compose v2
- Git

### Local Development

```bash
# Clone repository
git clone https://github.com/Autonom664/hr-performance-dstchemicals.git
cd hr-performance-dstchemicals/deploy

# Copy and configure environment
cp .env.example .env
# Edit .env to set MONGO_ROOT_PASSWORD

# Start services
docker compose up -d

# Seed demo data (local development only - NOT for production)
docker exec hr-backend python seed_data.py

# Access the app at http://localhost:3000
```

### Demo Accounts

All demo accounts use password: `Demo@123456`

| Role | Email | Description |
|------|-------|-------------|
| Admin | admin@company.com | Full system access |
| Manager | engineering.lead@company.com | Reviews 3 direct reports |
| Employee | developer1@company.com | Standard employee |

---

## Authentication

### Password-Based Authentication (Active)

The system uses password-based authentication:

1. **Initial Password:** Generated automatically when admin imports users (14 chars, alphanumeric + special)
2. **Password Storage:** bcrypt hashed (never stored in plaintext)
3. **First Login:** User enters email + generated password
4. **Forced Password Change:** New users MUST change password on first login
5. **Session:** httpOnly cookie with configurable expiry (default: 8 hours)

**Security Features:**
- Strong password generation using `secrets` module
- bcrypt hashing with automatic salt
- Session tokens: `secrets.token_urlsafe(32)`
- Sessions invalidated on logout and password reset
- httpOnly cookies prevent XSS token theft

### Microsoft Entra SSO (Scaffolded, Disabled)

Entra ID integration is scaffolded but disabled. To enable:
1. Set `AUTH_MODE=entra` in environment
2. Configure Entra tenant, client ID, secret, and redirect URI
3. Register application in Azure Portal

When enabled, Entra SSO replaces the password-based flow entirely.

---

## User Onboarding Flow

### For Administrators

1. **Prepare User Data:** Create CSV or JSON with user information:
   ```csv
   employee_email,employee_name,manager_email,department,is_admin
   john@company.com,John Doe,manager@company.com,Engineering,false
   ```

2. **Import Users:** Admin Dashboard → Import Users → Upload CSV/JSON

3. **Download Credentials:** After import, immediately download the ONE-TIME CSV:
   - Contains: `email,one_time_password`
   - Passwords shown only once at creation
   - File auto-generates, must be downloaded before closing dialog

4. **Distribute Passwords:** Use mail merge or secure channel to send passwords

5. **Users Login:** Users login with generated password and are forced to change it

### For Users

1. **Receive Password:** Get one-time password from administrator
2. **First Login:** Enter email and provided password at login page
3. **Change Password:** System forces password change (min 8 characters)
4. **Access Dashboard:** After password change, redirected to role-appropriate dashboard

---

## Admin Password Management

### Importing New Users

When importing users (CSV or JSON), the system:
- Creates user accounts with assigned roles
- Generates secure random passwords (14 chars)
- Hashes passwords using bcrypt
- Sets `must_change_password=true`
- Returns CSV with plaintext passwords (ONE-TIME download)

### Resetting Existing User Passwords

Admins can reset passwords for existing users:

1. Go to Admin Dashboard → Users tab
2. Click "Reset Passwords" button (yellow/warning style)
3. Select users to reset (checkbox list)
4. Confirm action
5. Download CSV with new passwords (ONE-TIME download)

**What Happens:**
- Previous passwords become invalid immediately
- All user sessions are terminated
- Users must use new password on next login
- Users must change password after login with reset password

### When to Use Reset vs Re-Import

| Scenario | Action |
|----------|--------|
| User forgot password | Reset Password |
| User account compromised | Reset Password |
| Update user details (name, department) | Re-import (updates existing) |
| Add new users | Import |

---

## Environment Variables Reference

### Complete Variable List

All environment variables are configured in `/deploy/.env`. Two templates are provided:
- `.env.example` - Local development
- `.env.ovh.example` - OVH staging/production

| Variable | Description | Local Dev | OVH Staging |
|----------|-------------|-----------|-------------|
| **Database** |
| `MONGO_ROOT_USERNAME` | MongoDB admin username | `hrapp_dev` | `hrapp_prod` |
| `MONGO_ROOT_PASSWORD` | MongoDB admin password | (set any) | **Strong 32+ chars** |
| `DB_NAME` | Database name | `hr_performance` | `hr_performance` |
| **URLs** |
| `REACT_APP_BACKEND_URL` | Backend URL for frontend | `http://localhost:8001` | **empty** |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000` | `https://hr-staging.dstchemicals.com` |
| **Ports** |
| `BACKEND_PORT` | Backend internal port | `8001` | `8001` |
| `FRONTEND_PORT` | Frontend internal port | `3000` | `3000` |
| **Authentication** |
| `AUTH_MODE` | `password` or `entra` | `password` | `password` |
| `SESSION_EXPIRY_HOURS` | Session lifetime | `24` | `8` |
| **Cookie Security** |
| `COOKIE_SECURE` | Require HTTPS | `false` | **`true`** |
| `COOKIE_SAMESITE` | SameSite policy | `lax` | `lax` |
| **Entra SSO (optional)** |
| `ENTRA_TENANT_ID` | Azure tenant ID | (empty) | (empty) |
| `ENTRA_CLIENT_ID` | App client ID | (empty) | (empty) |
| `ENTRA_CLIENT_SECRET` | App client secret | (empty) | (empty) |
| `ENTRA_REDIRECT_URI` | OAuth callback URL | (empty) | (empty) |

### File Locations and Security

| File | Purpose | Committed? | Contains Secrets? |
|------|---------|------------|-------------------|
| `/deploy/.env.example` | Local dev template | ✅ Yes | No |
| `/deploy/.env.ovh.example` | OVH template | ✅ Yes | No |
| `/deploy/.env` | Active config | ❌ **Never** | **Yes** |

**On OVH Server:** Real secrets live in `/opt/hr-performance/deploy/.env` (never committed)

---

## URL Configuration

### How Frontend Reaches Backend

The frontend determines the backend URL based on `REACT_APP_BACKEND_URL`:

| Scenario | REACT_APP_BACKEND_URL | Frontend Behavior |
|----------|----------------------|-------------------|
| **Local dev** (no nginx) | `http://localhost:8001` | Direct cross-origin calls |
| **OVH staging** (nginx) | **empty** | Relative `/api` paths |
| **OVH production** (nginx) | **empty** | Relative `/api` paths |

### Why Empty in OVH?

In staging/production with nginx reverse proxy:
- Frontend is served from `https://hr-staging.dstchemicals.com`
- Backend is proxied at `https://hr-staging.dstchemicals.com/api/*`
- Frontend uses relative `/api` paths → Same origin, no CORS issues
- Simpler cookie handling (SameSite works naturally)

### Local Development Without Nginx

For local development with docker-compose (no nginx):
- Set `REACT_APP_BACKEND_URL=http://localhost:8001`
- Frontend makes cross-origin requests to backend
- CORS must include `http://localhost:3000`

---

## CORS Configuration

### How CORS Works

Backend parses `CORS_ORIGINS` as comma-separated list:
```
CORS_ORIGINS=http://localhost:3000,https://hr-staging.dstchemicals.com
```

Rules:
- Whitespace is trimmed automatically
- Empty values are filtered out
- Wildcard `*` triggers warning and disables credentials
- No wildcard allowed in staging/production

### Correct Values by Environment

| Environment | CORS_ORIGINS |
|-------------|--------------|
| Local dev | `http://localhost:3000` |
| OVH staging | `https://hr-staging.dstchemicals.com` |

### Common CORS Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| "CORS error" in console | Origin not in allowed list | Add origin to CORS_ORIGINS |
| Credentials not sent | Wildcard `*` used | Use explicit origin |
| Cookies not set | Different origins | Use same-origin deployment |

---

## Performance Review Structure

### Employee Input Fields

The employee fills out three sections:

**1. Status Since Last Meeting**
- a) How have your previous goals progressed?
- General status update (optional)

**2. New Goals and How to Achieve Them**
- a) What are your key goals for the next 1–3 months?
- b) How are you going to achieve them?
- c) What support or learning do you need?

**3. Feedback and Wishes for the Future**
- Open text for feedback, suggestions, wishes

### Manager Input Field

Managers provide a single rich-text feedback field:
- **Your Feedback:** Qualitative assessment, strengths, areas for improvement, recommendations

**No numeric ratings are used anywhere in the system.**

---

## PDF Export

### What PDFs Include

- **Cycle Information:** Name, date range, status
- **Employee Information:** Name, email, department, manager
- **Employee Input:** All three sections with rich text preserved (converted to plain text)
- **Manager Feedback:** Full feedback text
- **Timestamps:** Created, updated, PDF generated time

### How to Export

**Via UI:**
- Employee Dashboard: "Export PDF" button
- Manager Dashboard: "Export PDF" button when viewing employee
- Works for both active and archived conversations

**Via API:**
```bash
curl -o review.pdf "https://hr-staging.dstchemicals.com/api/conversations/{id}/pdf?token={session_token}"
```

### Testing PDF Generation

```bash
# Login and get token
TOKEN=$(curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@company.com","password":"Demo@123456"}' | \
  jq -r '.token')

# Get a conversation ID
CONV_ID=$(curl -s "$API_URL/api/conversations/me" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.id')

# Export PDF
curl -o test.pdf "$API_URL/api/conversations/$CONV_ID/pdf?token=$TOKEN"

# Verify
file test.pdf  # Should show: PDF document
```

### Platform Notes

- PDF generation uses fpdf2 (pure Python, no system dependencies)
- Works in all environments (local, Docker, OVH)
- Rich text HTML is converted to plain text for PDF

---

## Archived EDI Access

### Who Can See What

| Role | Active Cycle | Archived Cycles |
|------|--------------|-----------------|
| Employee | Own conversation (edit) | Own conversations (read-only) |
| Manager | Reports' conversations (edit feedback) | Reports' conversations (read-only) |
| Admin | All conversations | All conversations |

### How Archiving Works

1. Only ONE cycle can be active at a time
2. Admin archives active cycle: Status → "archived"
3. All conversations in archived cycle become read-only
4. API enforces read-only (not just UI)
5. PDF export still works for archived conversations

### UI Indicators

- Active conversations: Green status badge, edit forms enabled
- Archived conversations: Yellow "Archived" badge, all fields read-only

---

## Backup Strategy

**Backups are REQUIRED in staging/production.**

See [agent_instructions.md](./agent_instructions.md) for detailed backup procedures:
- `mongodump` command for full database backup
- Suggested rotation schedule
- Storage recommendations

---

## Deployment

### OVH Staging Deployment

See **[agent_instructions.md](./agent_instructions.md)** for complete manual steps:

1. DNS: A record for `hr-staging.dstchemicals.com`
2. Server: Docker, nginx, certbot installed
3. Firewall: Only ports 80, 443 open
4. TLS: Let's Encrypt certificate
5. nginx: Reverse proxy configuration
6. Deploy: Clone, configure `.env`, start containers
7. Seed: Run seed script for demo data
8. Backup: Configure MongoDB backups

---

## API Reference

### Authentication

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/login` | Login with email/password | No |
| POST | `/api/auth/change-password` | Change password | Yes |
| GET | `/api/auth/me` | Get current user | Yes |
| POST | `/api/auth/logout` | Logout | Yes |

### Admin

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/admin/users/import` | Import users (JSON) | Admin |
| POST | `/api/admin/users/import/csv` | Import users (CSV) | Admin |
| POST | `/api/admin/users/reset-passwords` | Reset user passwords | Admin |
| GET | `/api/admin/users` | List all users | Admin |
| POST | `/api/admin/cycles` | Create cycle | Admin |
| GET | `/api/admin/cycles` | List all cycles | Admin |
| PATCH | `/api/admin/cycles/:id` | Update cycle status | Admin |

### Employee

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/cycles/active` | Get active cycle | Yes |
| GET | `/api/conversations/me` | Get my active conversation | Yes |
| PUT | `/api/conversations/me` | Update my conversation | Yes |
| GET | `/api/conversations/me/history` | Get my archived conversations | Yes |
| GET | `/api/conversations/:id` | Get specific conversation | Yes |

### Manager

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/manager/reports` | List direct reports | Manager |
| GET | `/api/manager/conversations/:email` | Get report's conversation | Manager |
| PUT | `/api/manager/conversations/:email` | Update report's conversation | Manager |
| GET | `/api/manager/reports/:email/history` | Get report's history | Manager |

### Export

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/conversations/:id/pdf?token=...` | Export to PDF | Owner/Manager/Admin |

### Health

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/health` | Health check | No |

---

## Troubleshooting

### Common Issues

| Issue | Check | Fix |
|-------|-------|-----|
| Can't login | Password correct? First login? | Use generated password, then change |
| CORS errors | CORS_ORIGINS matches frontend URL? | Update CORS_ORIGINS in .env |
| PDF 401 error | Token expired? | Re-login, try again |
| MongoDB connection failed | Credentials match? | Check MONGO_ROOT_PASSWORD |
| Frontend shows blank | REACT_APP_BACKEND_URL correct? | Check URL config for environment |

### Checking Logs

```bash
# Docker deployment
docker compose logs backend --tail 100
docker compose logs frontend --tail 100
docker compose logs mongodb --tail 100

# nginx (OVH)
sudo tail -f /var/log/nginx/hr-staging.error.log
```

### Verifying Services

```bash
# Health check
curl https://hr-staging.dstchemicals.com/api/health

# Expected response:
{"status":"healthy","auth_mode":"password","version":"2.0.0"}
```

---

## Known Limitations

1. **Email Delivery:** Not implemented. Passwords distributed manually via admin CSV export.
2. **Single Active Cycle:** Only one performance cycle can be active at a time.
3. **Entra SSO:** Scaffolded but disabled (`AUTH_MODE=password`).
4. **No Numeric Ratings:** This system is intentionally qualitative-only.

---

## License

MIT
