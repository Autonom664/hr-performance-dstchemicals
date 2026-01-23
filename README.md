# HR Performance Management System

A portable, self-hosted HR Performance Management web application for annual performance reviews and EDI conversations. Designed for 80-200 users with Docker-based deployment.

**This system does NOT use numeric ratings.** Performance feedback is qualitative only.

**Repository:** `https://github.com/Autonom664/HR` (private)  
**Target Staging Domain:** `hr-staging.dstchemicals.com`

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [User Onboarding Flow](#user-onboarding-flow)
- [Admin Password Management](#admin-password-management)
- [Environment Variables Reference](#environment-variables-reference)
- [Performance Review Structure](#performance-review-structure)
- [Archived EDI Access](#archived-edi-access)
- [Deployment](#deployment)
- [API Reference](#api-reference)

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
git clone https://github.com/Autonom664/HR.git hr-performance
cd hr-performance/deploy

# Copy and configure environment
cp .env.example .env

# Start services
docker compose up -d

# Seed demo data (first time)
docker exec hr-backend python seed_data.py

# Access the app at http://localhost:3000
```

### Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@company.com | Demo@123456 |
| Manager | engineering.lead@company.com | Demo@123456 |
| Employee | developer1@company.com | Demo@123456 |

---

## Authentication

### Password-Based Authentication (Active)

The system uses password-based authentication:

1. **Initial Password:** Generated automatically when admin imports users
2. **First Login:** User enters email + generated password
3. **Forced Password Change:** New users MUST change their password on first login
4. **Session:** httpOnly cookie with configurable expiry

**Security Features:**
- Passwords hashed with bcrypt (never stored in plaintext)
- Strong password generation (14 characters, alphanumeric + special)
- Session tokens: `secrets.token_urlsafe(32)`
- Sessions invalidated on logout and password reset

### Microsoft Entra SSO (Scaffolded, Disabled)

Entra ID integration is scaffolded but disabled. Set `AUTH_MODE=entra` to enable (requires additional configuration). When Entra SSO is enabled, it will replace the password-based flow entirely.

---

## User Onboarding Flow

### For Administrators

1. **Prepare User Data:** Create CSV or JSON with user information
2. **Import Users:** Use Admin Dashboard → Import Users
3. **Download Credentials:** After import, download the ONE-TIME CSV containing:
   - User emails
   - Generated one-time passwords
4. **Distribute Passwords:** Use mail merge or secure channel to send passwords to users
5. **Users Login:** Users login with generated password and are forced to change it

### For Users

1. **Receive Password:** Get one-time password from administrator
2. **First Login:** Enter email and provided password
3. **Change Password:** System forces password change (min 8 characters)
4. **Access Dashboard:** After password change, access appropriate dashboard

---

## Admin Password Management

### Importing New Users

When importing users (CSV or JSON), the system:
- Creates user accounts with roles
- Generates secure random passwords (14 chars)
- Hashes passwords for storage
- Sets `must_change_password=true`
- Returns CSV with plaintext passwords (ONE-TIME download)

### Resetting Existing User Passwords

Admins can reset passwords for existing users:

1. Go to Admin Dashboard → Users tab
2. Click "Reset Passwords" button
3. Select users to reset
4. Confirm action (current passwords are invalidated immediately)
5. Download CSV with new passwords (ONE-TIME download)

**Security Implications:**
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

| Variable | Description | Local Default | Staging |
|----------|-------------|---------------|---------|
| **Database** |
| `MONGO_ROOT_USERNAME` | MongoDB admin username | `hrapp_dev` | `hrapp_prod` |
| `MONGO_ROOT_PASSWORD` | MongoDB admin password | (set in .env) | **Strong 32+ chars** |
| `DB_NAME` | Database name | `hr_performance` | `hr_performance` |
| **URLs & CORS** |
| `REACT_APP_BACKEND_URL` | Backend URL for frontend | `http://localhost:8001` | (empty) |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000` | `https://hr-staging...` |
| **Authentication** |
| `AUTH_MODE` | `password` or `entra` | `password` | `password` |
| `SESSION_EXPIRY_HOURS` | Session lifetime | `24` | `8` |
| **Cookie Security** |
| `COOKIE_SECURE` | Require HTTPS | `false` | **`true`** |
| `COOKIE_SAMESITE` | SameSite policy | `lax` | `lax` |

### Environment File Locations

| File | Purpose | Committed? |
|------|---------|------------|
| `/deploy/.env.example` | Local dev template | Yes |
| `/deploy/.env.ovh.example` | Staging template | Yes |
| `/deploy/.env` | Active config | **No** |

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

### PDF Export

PDF exports include:
- Cycle information (name, dates, status)
- Employee information (name, email, department, manager)
- All employee input sections
- Manager feedback
- Timestamps (created, updated, generated)

---

## Archived EDI Access

### Employees
- Can view ALL their own archived performance reviews
- Can see both their input and manager feedback
- Archived reviews are read-only

### Managers
- Can view archived reviews for their direct reports
- Can see both employee input and their own feedback
- Historical context for performance discussions

### Admins
- Full access to all archived reviews
- Can export PDFs of any conversation

### Identifying Active vs Archived

- Only ONE cycle can be active at a time
- When a cycle is archived, all conversations become read-only
- UI clearly distinguishes active (editable) vs archived (read-only) status

---

## Deployment

### OVH Staging Checklist

See **[agent_instructions.md](./agent_instructions.md)** for detailed manual steps.

**Summary:**
1. DNS: A record for `hr-staging.dstchemicals.com`
2. Server: Docker, nginx, certbot
3. Firewall: Only 80, 443 open
4. TLS: Let's Encrypt certificate
5. nginx: Reverse proxy configuration
6. Deploy: Clone, configure `.env`, start containers
7. Seed: Run seed script for demo data

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
| GET | `/api/cycles/all` | Get all cycles | Yes |
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
| GET | `/api/conversations/:id/pdf` | Export to PDF | Owner/Manager/Admin |

---

## Known Limitations

1. **Email Delivery:** Not implemented. Passwords distributed manually via admin CSV export.
2. **Single Active Cycle:** Only one performance cycle can be active at a time.
3. **Entra SSO:** Scaffolded but disabled (`AUTH_MODE=password`).
4. **No Numeric Ratings:** This system is intentionally qualitative-only.

---

## License

MIT
