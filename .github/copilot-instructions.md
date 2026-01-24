# HR Performance Management - AI Agent Instructions

## System Overview
A self-hosted HR performance review web app using **password-based authentication only** (no SSO in production). Stack: React 19 + FastAPI + MongoDB. Designed for 80-200 users with Docker deployment.

**Critical constraint:** NO numeric ratings. All feedback is qualitative using rich text editors (Tiptap).

## Architecture & Key Flows

### Service Boundaries
- **Frontend (port 3000):** React SPA with cookie-based sessions, uses relative `/api` paths in same-origin deployments
- **Backend (port 8001):** FastAPI with Motor async MongoDB driver, enforces role-based access control via `require_auth/require_admin/require_manager` decorators
- **Database:** MongoDB 7.0 with authentication, internal network only (never exposed publicly)
- **Deployment:** Docker Compose with nginx reverse proxy for TLS termination (ports 80/443 only exposed in production)

### Authentication Pattern
Session tokens stored in both cookies AND localStorage. The `AuthContext` provides `axiosInstance` with automatic token injection via interceptors. All API routes use `Depends(require_auth)` to validate sessions against MongoDB `sessions` collection.

**First-time login:** Admin imports users via CSV → backend generates secure 14-char passwords → users must change password on first login (`must_change_password` flag). Admins can reset passwords and re-download the generated credentials CSV.

### Performance Review Structure
**Employee form (6 fields, 3 sections):**
1. Status since last meeting
2. Goals: `previous_goals_progress`, `new_goals`, `how_to_achieve_goals`, `support_needed`
3. `feedback_and_wishes`

**Manager form:** Single `manager_feedback` field only (no ratings field exists).

**Conversation statuses:** `not_started` → `in_progress` → `ready_for_manager` → `completed`

### Cycle Management
Only **one active cycle** at a time. States: `draft` → `active` → `archived`. 

**Critical behavior:** Archived cycles are READ-ONLY. API blocks modifications by checking `cycle.status == 'active'` before allowing PUT operations. Frontend disables editors and shows history tabs for archived data.

## Developer Workflows

### Local Development
```bash
cd deploy
docker compose up -d
docker exec hr-backend python seed_data.py  # Demo accounts with password Demo@123456
```
Frontend auto-reloads via Craco. Backend hot-reloads via `uvicorn --reload`.

### Seeding Demo Data
[seed_data.py](backend/seed_data.py) creates 3-tier hierarchy (Admin → CTO → Engineering Lead → Developers) with demo conversations. All demo users use password `Demo@123456` and `must_change_password: false`.

### Deployment to OVH (hr.dstchemicals.com)
Follow [agent_instructions.md](agent_instructions.md) for nginx setup, TLS with certbot, and firewall rules. Backend/frontend bind to `127.0.0.1` only; nginx proxies external traffic.

**Production deployment:** Deploy with empty database. Create ONE admin account manually (no demo data). HR imports employee data via CSV after deployment.

## Project-Specific Conventions

### API Patterns
- **Role enforcement:** Use `Depends(require_admin)` or `Depends(require_manager)` instead of manual role checks
- **Email normalization:** Always `.lower()` email addresses before DB queries
- **Timestamps:** UTC ISO format strings (MongoDB doesn't store native datetime objects here)
- **Password hashing:** bcrypt with auto-generated salt

### Frontend Patterns
- **Rich text editors:** All feedback fields use `RichTextEditor` component (Tiptap with Bold/Italic/Underline/Lists only, no headings/code blocks)
- **API calls:** Always use `axiosInstance` from `useAuth()` context, never plain axios
- **Role checks:** Use `isAdmin()`, `isManager()`, `isEmployee()` helpers from AuthContext
- **Routing:** `ProtectedRoute` wrapper validates authentication + role requirements per route

### Data Model Specifics
- **Users:** `roles` is an array (can be `["employee", "manager"]` simultaneously)
- **Conversations:** Linked to cycles via `cycle_id`, employee via `employee_email`. NO foreign key constraints (MongoDB)
- **PDF export:** Uses fpdf2, strips HTML tags with regex before rendering. API endpoint provides session token via query param for browser downloads.

## Integration Points

### CORS Configuration
Backend `CORS_ORIGINS` must be explicit (no wildcards in production). Set to frontend domain like `https://hr.dstchemicals.com`.

### Environment Variables
- **Same-origin deployment:** `REACT_APP_BACKEND_URL=""` (frontend uses relative `/api` paths)
- **Cross-origin deployment:** `REACT_APP_BACKEND_URL=https://api.example.com` (full URL)
- **Session security:** `COOKIE_SECURE=true`, `COOKIE_SAMESITE=lax` in production

### External Dependencies
No email service (passwords distributed via CSV). Entra SSO scaffolded in code but disabled (`AUTH_MODE=password`)—this is a future enhancement project.

## Common Gotchas
- **Manager hierarchy:** Managers can only edit feedback for direct reports (checked via `manager_email` field). Admins bypass this and can view/edit all conversations.
- **Archived cycle writes:** Frontend disables editors, but API is the enforcement point (check `cycle.status` before updates).
- **Completed conversations:** Cannot be edited even if cycle is active (status check in PUT endpoints).
- **Password generation:** Use `generate_secure_password()` helper (14 chars, alphanumeric + special). Never store plaintext.

## Key Files
- [backend/server.py](backend/server.py) - All API routes, models, auth logic
- [frontend/src/contexts/AuthContext.js](frontend/src/contexts/AuthContext.js) - Session management, axios config
- [deploy/docker-compose.yml](deploy/docker-compose.yml) - Container orchestration, network isolation
- [README.md](README.md) - Complete user/admin documentation
- [memory/PRD.md](memory/PRD.md) - Requirements and implementation status
