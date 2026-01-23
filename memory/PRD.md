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

## Core Requirements (Implemented)

### Authentication
- Password-based login with email and password
- Secure password generation on user import (14 chars, alphanumeric + special)
- bcrypt password hashing (never stored in plaintext)
- First-time login forces password change (`must_change_password` flag)
- Session management with httpOnly cookies
- Entra SSO scaffolded (disabled via `AUTH_MODE=password`)

### Performance Review Structure

**Employee Input (3 Sections):**
1. **Status Since Last Meeting**
   - a) How have your previous goals progressed?
   - General status update (optional)

2. **New Goals and How to Achieve Them**
   - a) What are your key goals for the next 1–3 months?
   - b) How are you going to achieve them?
   - c) What support or learning do you need?

3. **Feedback and Wishes for the Future**
   - Open text field

**Manager Input:**
- Single "Your Feedback" rich text field
- NO numeric ratings

### Admin Functions
- User import via CSV or JSON
- Password generation with one-time CSV export
- Password reset with one-time CSV export
- Cycle management (Draft/Active/Archived)

### Historical/Archived Access
- Employees: View all their archived reviews
- Managers: View archived reviews for direct reports
- Admins: Full access to all archived data
- Only ONE active cycle allowed
- Archived cycles are READ-ONLY at API level

---

## What's Been Implemented (2025-01-23)

### Major Refactoring Completed
✅ **Password-Based Authentication**
- Replaced email verification code flow with password login
- Implemented forced password change on first login
- Admin CSV export for generated passwords
- Admin password reset functionality

✅ **Ratings Completely Removed**
- No rating fields in data model
- No rating UI components
- No ratings in PDF exports
- API explicitly returns `ratings: false`

✅ **New Employee Input Structure**
- 3 sections with specific questions
- Rich text editors for all fields
- Structured layout matching requirements

✅ **Manager Single Feedback Field**
- Removed ratings selectors
- Single "Your Feedback" rich text field

✅ **Historical/Archived Access**
- History tab for employees
- History tab for managers viewing reports
- Read-only archived conversation views
- PDF export for archived conversations

### Infrastructure
✅ Docker Compose setup for deployment
✅ MongoDB with authentication
✅ nginx reverse proxy configuration
✅ Same-origin API calls for production

### Documentation
✅ README.md - Complete system documentation
✅ agent_instructions.md - OVH deployment guide

---

## Technical Architecture

```
/app/
├── backend/
│   ├── server.py          # FastAPI application
│   ├── seed_data.py       # Demo data seeder
│   ├── requirements.txt
│   ├── tests/
│   │   └── test_hr_performance.py
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── contexts/AuthContext.js
│   │   ├── pages/
│   │   │   ├── LoginPage.js
│   │   │   ├── EmployeeDashboard.js
│   │   │   ├── ManagerDashboard.js
│   │   │   └── AdminPage.js
│   │   └── components/
│   ├── package.json
│   └── .env
├── deploy/
│   ├── docker-compose.yml
│   ├── .env.example
│   └── .env.ovh.example
├── README.md
└── agent_instructions.md
```

### Key Data Models

**User:**
```json
{
  "email": "string (unique)",
  "name": "string",
  "department": "string",
  "manager_email": "string (nullable)",
  "roles": ["employee", "manager", "admin"],
  "password_hash": "string (bcrypt)",
  "must_change_password": "boolean",
  "is_active": "boolean"
}
```

**Conversation (New Structure):**
```json
{
  "cycle_id": "string",
  "employee_email": "string",
  "manager_email": "string",
  "status": "not_started|in_progress|ready_for_manager|completed",
  
  "previous_goals_progress": "string (rich text)",
  "status_since_last_meeting": "string (rich text)",
  "new_goals": "string (rich text)",
  "how_to_achieve_goals": "string (rich text)",
  "support_needed": "string (rich text)",
  "feedback_and_wishes": "string (rich text)",
  
  "manager_feedback": "string (rich text)"
}
```

---

## Test Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@company.com | Demo@123456 |
| Manager | engineering.lead@company.com | Demo@123456 |
| Employee | developer1@company.com | Demo@123456 |

---

## Prioritized Backlog

### P0 - Critical (Completed)
- ✅ Password-based authentication
- ✅ Remove all ratings
- ✅ New employee input structure
- ✅ Manager single feedback field
- ✅ Historical/archived access

### P1 - Important (Future)
- Enable Entra SSO when organization ready
- Email notifications for status changes
- Batch operations in admin panel

### P2 - Nice to Have
- 360-degree feedback
- Calibration features
- Analytics dashboard
- Multi-language support
- Audit log viewer

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| AUTH_MODE | `password` or `entra` | password |
| MONGO_ROOT_PASSWORD | MongoDB password | (required) |
| CORS_ORIGINS | Allowed origins | (required) |
| COOKIE_SECURE | HTTPS cookies | false (true for prod) |
| SESSION_EXPIRY_HOURS | Session lifetime | 8 |

---

## Deployment Notes

- See `README.md` for complete deployment instructions
- See `agent_instructions.md` for OVH-specific manual tasks
- MongoDB: Internal network only, no public exposure
- Ports 8001/3000: Bound to localhost, nginx proxies

---

*Last Updated: 2025-01-23*
