# HR Performance Management System - PRD

## Original Problem Statement
Build a portable HR Performance Management web app for yearly EDI/performance conversations (~80 users now, scalable to ~200). Must be self-hostable with Docker + docker-compose on OVH.

## User Personas
1. **Admin** - HR administrator who imports users, manages cycles, has full system access
2. **Manager** - Reviews direct reports, provides feedback and ratings
3. **Employee** - Completes self-reviews, sets goals, views manager feedback

## Core Requirements (Static)
- Email-only authentication with verification codes (MVP)
- Microsoft Entra SSO scaffolded for future enablement
- Performance cycle management (Draft/Active/Archived)
- Conversation workflow with status tracking
- Rich text editing for reviews
- PDF export of conversations
- Role-based access control
- Docker-compose deployment ready

## What's Been Implemented (2026-01-23)
✅ Backend (FastAPI + MongoDB)
- Auth abstraction layer with email mode
- Entra SSO scaffolded (AUTH_MODE env toggle)
- All CRUD endpoints for users, cycles, conversations
- PDF generation with fpdf2
- CSV/JSON user import
- Role-based permissions

✅ Frontend (React + Tailwind + shadcn/ui)
- Login page with email verification flow
- Employee dashboard with Tiptap rich text editor
- Manager dashboard with reports list and review detail
- Admin page with users/cycles management
- Dark theme (Deep Obsidian) design
- Responsive layout

✅ Infrastructure
- docker-compose.yml for deployment
- .env templates for local and OVH
- README with deployment instructions
- Seed data script with demo users

## Prioritized Backlog (P0/P1/P2)

### P0 - Critical (Not Implemented)
- None - MVP complete

### P1 - Important (Future)
- Enable Entra SSO when ready
- Email notifications for status changes
- Batch operations in admin panel
- Direct reports hierarchy visualization

### P2 - Nice to Have
- 360-degree feedback
- Calibration features
- Analytics dashboard
- Multi-language support
- Audit log viewer

## Next Tasks
1. Deploy to OVH (follow README instructions)
2. Import actual user data via CSV
3. Create production performance cycle
4. Test with real users
5. Enable Entra SSO when organization ready

---

## Security Hardening Update (2026-01-23)

### Changes Made
1. **MongoDB Security**
   - Removed public port exposure (internal network only)
   - Added authentication with MONGO_ROOT_USERNAME/PASSWORD
   - Connection string updated with credentials

2. **CORS Hardening**
   - Removed wildcard CORS (*)
   - CORS_ORIGINS must be explicitly set

3. **Session Security**
   - SHOW_CODE_IN_RESPONSE defaults to `false`
   - COOKIE_SECURE defaults to `true`
   - Session cookies are httpOnly, SameSite=lax
   - Logout properly invalidates tokens

4. **PDF Export Enhanced**
   - Added cycle information section (name, dates, status)
   - Added timestamps section (created_at, updated_at, updated_by)
   - Added conversation ID for audit trail

5. **Docker Compose Updated**
   - Internal network for MongoDB
   - Required environment variables with validation
   - Proper health checks

### Verified Sanity Checks
- ✅ Authorization isolation (employee/manager/admin boundaries)
- ✅ Session & cookie security (httpOnly, secure flags)
- ✅ Cycle integrity (single active cycle)
- ✅ PDF completeness (all fields included)
- ✅ Data persistence (survives restarts)

### Deployment Target
- hr-staging.dstchemicals.com
