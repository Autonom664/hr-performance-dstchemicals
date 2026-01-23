# HR Performance Management System - PRD

## Original Problem Statement
Build a portable HR Performance Management web app for yearly EDI/performance conversations (~80 users now, scalable to ~200). Must be self-hostable with Docker + docker-compose on OVH.

**Key Constraints:**
- Password-based authentication (email verification removed)
- NO numeric ratings - qualitative feedback only
- Entra SSO scaffolded but disabled
- Docker-based deployment for OVH

## User Personas
1. **Admin** - HR administrator who imports users, manages cycles, manages passwords
2. **Manager** - Reviews direct reports, provides qualitative feedback
3. **Employee** - Completes self-reviews using structured form, views manager feedback

---

## Implementation Status (2025-01-23) - PRODUCTION READY

### ✅ All Features Complete

**Authentication System:**
- Password-based login with email and password
- Secure password generation on user import (14 chars, alphanumeric + special)
- bcrypt password hashing
- First-time login forces password change
- Admin CSV export for generated passwords (one-time download)
- Admin password reset with CSV export

**Performance Review Structure:**
- Employee 3-section form (Status, Goals, Feedback)
- Manager single feedback field (no ratings)
- Rich text editors throughout

**Cycle Management:**
- Create/activate/archive cycles
- Only one active cycle at a time
- Archived cycles are read-only (API enforced)

**Historical Access:**
- Employees view own archived reviews
- Managers view reports' archived reviews
- PDF export for active and archived

**PDF Export:**
- All employee fields included
- Manager feedback included
- Cycle metadata and timestamps

---

## Technical Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 19, Tailwind CSS, shadcn/ui, Tiptap |
| Backend | FastAPI (Python 3.11), Motor |
| Database | MongoDB 7.0 |
| PDF | fpdf2 |
| Deployment | Docker Compose, nginx |

---

## Test Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@company.com | Demo@123456 |
| Manager | engineering.lead@company.com | Demo@123456 |
| Employee | developer1@company.com | Demo@123456 |

---

## Final Validation Results

**Backend Tests:** 24/24 passed (100%)
**Frontend Tests:** All UI flows verified
**PDF Generation:** Confirmed working
**Archived Read-Only:** API enforced

---

## Next Steps (OVH Deployment)

1. Follow `agent_instructions.md` for OVH server setup
2. Configure DNS, TLS, nginx
3. Deploy with docker-compose
4. Seed demo data
5. Import real users
6. Configure backup cron job

---

## Files Reference

| File | Purpose |
|------|---------|
| `/README.md` | Complete system documentation |
| `/agent_instructions.md` | OVH manual deployment steps |
| `/deploy/docker-compose.yml` | Container orchestration |
| `/deploy/.env.example` | Local dev template |
| `/deploy/.env.ovh.example` | OVH staging template |
| `/backend/server.py` | FastAPI application |
| `/backend/seed_data.py` | Demo data seeder |

---

## Known Limitations

1. Email delivery not implemented (passwords distributed via CSV)
2. Single active cycle only
3. Entra SSO scaffolded but disabled

---

*Last Updated: 2025-01-23 - Production Ready*
