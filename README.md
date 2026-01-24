# HR Performance Management System

Self-hosted HR performance and EDI review app for 80–200 users. All feedback is qualitative (no numeric ratings). Stack: React 19 + FastAPI + MongoDB, deployed with Docker Compose behind nginx.

---

## Contents

- Overview and guarantees
- Architecture and deployment
- Data model and business rules
- Authentication and roles
- Frontend flows
- Admin workflows
- Manager and employee workflows
- PDF export
- Environment and configuration
- Operations (deploy, backup, troubleshoot)
- API surface
- Known limits

---

## Overview and Guarantees

- Qualitative-only: no rating fields exist in API, DB, or UI.
- Single active cycle at a time; archiving is enforced server-side and makes conversations read-only.
- Completed conversations cannot be edited (even if cycle active).
- Role-based access on every route; cookies + bearer token required.
- Same-origin in staging/prod (relative `/api`); CORS only for explicit origins.

---

## Architecture and Deployment

```
Browser ── nginx (443/80, TLS, /api proxy) ── Frontend (:3000, localhost) ── Backend (:8001, localhost) ── MongoDB (internal)
```

- Containers bind to 127.0.0.1; only nginx is public. MongoDB is never exposed.
- PDF generation uses pure Python fpdf2 (no extra system deps beyond build-essential already installed in the backend image).
- Docker Compose services: `mongodb`, `backend` (FastAPI), `frontend` (React build served by nginx). See deploy/docker-compose.yml.
- Health: GET `/api/health` → `{ "status": "healthy", "auth_mode": "password", "version": "2.0.0" }`.

---

## Data Model and Business Rules

- Users: `{ email, name, department, manager_email, roles[], is_active, must_change_password, password_hash }` (roles can include both manager and employee).
- Cycles: `{ id, name, start_date, end_date, status }` with statuses `draft | active | archived`; only one active at a time (activating archives previous active).
- Conversations (per employee per cycle): employee fields `status_since_last_meeting`, `previous_goals_progress`, `new_goals`, `how_to_achieve_goals`, `support_needed`, `feedback_and_wishes`; manager field `manager_feedback`; status `not_started | in_progress | ready_for_manager | completed`.
- Authorization per conversation: owner, their manager, or admin.
- Archived cycles: read-only enforced by API; UI also disables editors. Completed conversations: no further edits allowed.

---

## Authentication and Roles

- Mode: password-only (`AUTH_MODE=password`); Entra SSO scaffolded but disabled.
- Passwords: generated 14 chars on import; bcrypt hashing; no plaintext storage.
- Sessions: session token stored as httpOnly cookie plus localStorage copy; expiry `SESSION_EXPIRY_HOURS` (default 8). Logout/delete/reset invalidates sessions.
- First login: `must_change_password=true` forces password change (min 8 chars).
- Roles: `employee`, `manager`, `admin`; managers auto-added if referenced as `manager_email` during import.

Key endpoints:
- POST `/api/auth/login`, `/api/auth/change-password`, `/api/auth/logout`
- GET `/api/auth/me`

---

## Frontend Flows (React 19)

- Routes: `/login`, `/employee`, `/manager`, `/manager/review/:employeeEmail`, `/admin`; guarded by role-aware `ProtectedRoute`.
- Editor: Tiptap with Bold/Italic/Underline + bullet/ordered lists only (no headings/code); used for all qualitative fields.
- Backend URL selection: if `REACT_APP_BACKEND_URL` is empty → relative `/api` (recommended for nginx same-origin). If set → appends `/api` and uses cross-origin.
- Session handling: axios instance injects Bearer token from localStorage; cookies carry the same token for server validation.

---

## Admin Workflows

- Import users (JSON): POST `/api/admin/users/import`.
- Import users (CSV): POST `/api/admin/users/import/csv`.
- Reset passwords: POST `/api/admin/users/reset-passwords` (one-time CSV with new passwords; sessions invalidated).
- List users: GET `/api/admin/users` (excludes password_hash).
- Cycles: POST `/api/admin/cycles`; PATCH `/api/admin/cycles/{id}?status=active|archived`; GET `/api/admin/cycles`.
- Import/reset return a one-time CSV of credentials; download immediately.

---

## Manager Workflows

- Reports list (active cycle status/id): GET `/api/manager/reports`.
- Current conversation for a report (creates if missing): GET `/api/manager/conversations/{employee_email}`.
- Update manager feedback/status: PUT `/api/manager/conversations/{employee_email}`.
- History for a report (incl. archived): GET `/api/manager/reports/{email}/history`.

---

## Employee Workflows

- Get or auto-create active conversation: GET `/api/conversations/me`.
- Update employee fields and optionally set status to `in_progress` or `ready_for_manager`: PUT `/api/conversations/me`.
- History: GET `/api/conversations/me/history`.
- View archived (read-only): GET `/api/conversations/{id}`.

---

## PDF Export

- Endpoint: GET `/api/conversations/{id}/pdf?token=...` (owner/manager/admin).
- Content: cycle info, employee info, all employee fields, manager feedback, timestamps; HTML stripped to plaintext.
- Works for active and archived conversations; served as attachment.

---

## Environment and Configuration

- Templates: `/deploy/.env.example` (dev) and `/deploy/.env.ovh.example` (staging/prod). Real secrets go in `/deploy/.env` (not committed) or `/opt/hr-performance/deploy/.env` on server.
- Key vars: `MONGO_ROOT_USERNAME`, `MONGO_ROOT_PASSWORD` (required), `DB_NAME`, `CORS_ORIGINS` (no wildcards in prod), `AUTH_MODE=password`, `SESSION_EXPIRY_HOURS`, `COOKIE_SECURE`, `COOKIE_SAMESITE`, `REACT_APP_BACKEND_URL` (empty for same-origin), `BACKEND_PORT`, `FRONTEND_PORT`.
- Same-origin staging/prod: leave `REACT_APP_BACKEND_URL` empty; set `CORS_ORIGINS` to site origin; `COOKIE_SECURE=true`, `COOKIE_SAMESITE=lax`.

---

## Deployment

Local dev quick start:
```
cd hr-performance-dstchemicals/deploy
cp .env.example .env  # set MONGO_ROOT_PASSWORD
docker compose up -d
docker exec hr-backend python seed_data.py  # demo only, never prod
# App http://localhost:3000, API http://localhost:8001
```

OVH staging/prod (summary; see agent_instructions.md for full steps):
1) DNS to host; open only 80/443. 2) Install Docker, nginx, certbot. 3) Place .env with strong creds. 4) `docker compose up -d` from `deploy`. 5) nginx proxies `/` and `/api` to frontend/backend. 6) No demo seed in prod; create one admin manually then import users. 7) Configure MongoDB backups.

---

## Backup and Operations

- MongoDB backups are required in staging/prod; use `mongodump` as outlined in agent_instructions.md; store off-box with rotation.
- Logs: `docker compose logs backend|frontend|mongodb --tail 100`; nginx logs on host.
- Health check: curl `https://<domain>/api/health`.

Common issues:
- CORS/auth: ensure same-origin or correct `CORS_ORIGINS` and `REACT_APP_BACKEND_URL`.
- Cookies missing: must use HTTPS with `COOKIE_SECURE=true` and same-origin.
- PDF 401: token expired → re-login.
- Completed or archived edits blocked by design.

---

## API Surface (high level)

- Auth: POST `/api/auth/login`, `/api/auth/change-password`, `/api/auth/logout`; GET `/api/auth/me`.
- Admin: import/reset/list users; create/list/patch cycles.
- Employee: get/update own conversation; history; fetch archived by id.
- Manager: reports list; get/update report conversation; history.
- Export: GET `/api/conversations/{id}/pdf?token=...`.
- Health: GET `/api/health`.

---

## Known Limits

- Email delivery not implemented; credentials distributed via CSV.
- Single active cycle only.
- Entra SSO disabled (scaffold only).
- No numeric ratings anywhere in system.
