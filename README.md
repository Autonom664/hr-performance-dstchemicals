# HR Performance Management System

A portable HR Performance Management web app for yearly performance conversations (EDI). Designed for ~80-200 users with self-hosting capability via Docker.

## Features

- **Employee Dashboard**: Self-review editor, goals setting, status tracking
- **Manager Dashboard**: View team reviews, provide feedback, set ratings
- **Admin Panel**: User import (CSV/JSON), cycle management
- **PDF Export**: Clean, professional PDF generation of reviews
- **Email Authentication**: Secure email-based login with verification codes
- **Entra SSO Ready**: Scaffolded for Microsoft Entra ID (Azure AD) integration

## Tech Stack

- **Frontend**: React 19 + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI (Python 3.11)
- **Database**: MongoDB 7.0
- **PDF Generation**: WeasyPrint

## Quick Start (Development)

### Prerequisites
- Node.js 20+
- Python 3.11+
- MongoDB (local or Docker)

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python seed_data.py  # Load demo data
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend Setup
```bash
cd frontend
yarn install
yarn start
```

## Docker Deployment

### Local Development
```bash
cd deploy
cp .env.example .env
docker-compose up -d
```

### OVH Production
```bash
cd deploy
cp .env.ovh.example .env
# Edit .env with your domain and settings
docker-compose -f docker-compose.yml up -d
```

## Demo Accounts

After running `seed_data.py`:
- **Admin**: admin@company.com
- **Manager**: engineering.lead@company.com
- **Employee**: developer1@company.com

Verification codes are displayed in the UI when `SHOW_CODE_IN_RESPONSE=true`.

## API Endpoints

### Authentication
- `POST /api/auth/email/start` - Start email login
- `POST /api/auth/email/verify` - Verify code and login
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - Logout

### Admin (requires admin role)
- `POST /api/admin/users/import` - Import users (JSON)
- `POST /api/admin/users/import/csv` - Import users (CSV)
- `GET /api/admin/users` - List all users
- `POST /api/admin/cycles` - Create cycle
- `PATCH /api/admin/cycles/:id` - Update cycle status

### App
- `GET /api/cycles/active` - Get active cycle
- `GET /api/conversations/me` - Get my conversation
- `PUT /api/conversations/me` - Update my conversation

### Manager
- `GET /api/manager/reports` - Get direct reports
- `GET /api/manager/conversations/:email` - Get report's conversation
- `PUT /api/manager/conversations/:email` - Update report's conversation

### Export
- `GET /api/conversations/:id/pdf` - Export to PDF

## Enabling Entra SSO

1. Register an app in Microsoft Entra ID (Azure Portal)
2. Set redirect URI to: `https://your-domain.com/api/auth/entra/callback`
3. Get your Tenant ID, Client ID, and Client Secret
4. Update environment variables:
   ```
   AUTH_MODE=entra
   ENTRA_TENANT_ID=your-tenant-id
   ENTRA_CLIENT_ID=your-client-id
   ENTRA_CLIENT_SECRET=your-client-secret
   ENTRA_REDIRECT_URI=https://your-domain.com/api/auth/entra/callback
   ```
5. Restart the backend service

**Important**: Users must be imported into the system first. OAuth login only identifies users; authorization is always based on the imported user mapping.

## User Import Format

### JSON
```json
[
  {
    "employee_email": "john@company.com",
    "employee_name": "John Doe",
    "manager_email": "manager@company.com",
    "department": "Engineering",
    "is_admin": false
  }
]
```

### CSV
```csv
employee_email,employee_name,manager_email,department,is_admin
john@company.com,John Doe,manager@company.com,Engineering,false
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URL` | MongoDB connection string | `mongodb://localhost:27017` |
| `DB_NAME` | Database name | `hr_performance` |
| `AUTH_MODE` | `email` or `entra` | `email` |
| `DEV_VERIFICATION_CODE` | Fixed code for dev | (random) |
| `SHOW_CODE_IN_RESPONSE` | Show code in API response | `true` |
| `SESSION_EXPIRY_HOURS` | Session duration | `24` |
| `ENTRA_*` | Microsoft Entra SSO config | (empty) |

## License

MIT
