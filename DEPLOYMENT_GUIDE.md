# Production Deployment Guide

## Deployed Changes (January 27, 2026)

**Features:**
- ✅ Single user password reset endpoint (`/admin/users/reset-password`)
- ✅ Admin dashboard UI for individual password resets
- ✅ Fixed PDF export functionality

**GitHub Commit:** `e59766a`
**Branch:** `main`

---

## Deploy to OVH Production Server

SSH to the OVH server and run these commands:

```bash
# Navigate to application directory
cd /opt/hr-performance

# Pull latest changes from GitHub
git pull origin main

# Navigate to deployment directory
cd deploy

# Stop running containers
docker compose down

# Rebuild and start containers
docker compose up -d --build

# Check container status
docker compose ps

# Follow logs (Ctrl+C to exit)
docker compose logs -f
```

---

## Verification

After deployment, verify the system is healthy:

```bash
# Check API health
curl https://hr.dstchemicals.com/api/health

# Expected response:
# {"status":"healthy","auth_mode":"password","version":"2.0.0"}

# Check frontend
# Open browser: https://hr.dstchemicals.com
```

---

## New Feature: Single User Password Reset

In the Admin Dashboard → Users Tab:
1. Click the **key icon button** in the Actions column for any user
2. A dialog displays the newly generated one-time password
3. Copy and share the password with the user
4. User logs in and must change password on first login

---

## Bug Fixes

### PDF Export
- Fixed fpdf2 output handling for PDF downloads
- PDF export now works correctly for all conversations

---

## Rollback Procedure (if needed)

If issues occur, rollback to the previous version:

```bash
cd /opt/hr-performance

# View recent commits
git log --oneline -5

# Checkout previous commit
git checkout <previous-commit-hash>

# Rebuild containers
cd deploy
docker compose down
docker compose up -d --build
```

---

## Timeline

- **Developed:** January 27, 2026
- **Tested:** Locally verified
- **GitHub:** Pushed to main branch
- **Production:** Ready to deploy

---

## Support

For issues or questions, check:
- Backend logs: `docker compose logs backend`
- Frontend logs: `docker compose logs frontend`
- Database logs: `docker compose logs mongodb`

