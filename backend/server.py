from fastapi import FastAPI, APIRouter, HTTPException, Depends, Response, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
import secrets
import hashlib
import bcrypt
from datetime import datetime, timezone, timedelta
import json
import csv
import io
from enum import Enum
from fpdf import FPDF
import html
import re

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Auth configuration
AUTH_MODE = os.environ.get('AUTH_MODE', 'password')  # 'password' or 'entra'
SESSION_EXPIRY_HOURS = int(os.environ.get('SESSION_EXPIRY_HOURS', '8'))

# Cookie security settings
COOKIE_SECURE = os.environ.get('COOKIE_SECURE', 'true').lower() == 'true'
COOKIE_SAMESITE = os.environ.get('COOKIE_SAMESITE', 'lax')

# Entra SSO config (scaffold - not enabled by default)
ENTRA_TENANT_ID = os.environ.get('ENTRA_TENANT_ID', '')
ENTRA_CLIENT_ID = os.environ.get('ENTRA_CLIENT_ID', '')
ENTRA_CLIENT_SECRET = os.environ.get('ENTRA_CLIENT_SECRET', '')
ENTRA_REDIRECT_URI = os.environ.get('ENTRA_REDIRECT_URI', '')
ENTRA_AUTHORITY = f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}" if ENTRA_TENANT_ID else ''
ENTRA_SCOPES = os.environ.get('ENTRA_SCOPES', 'openid profile email').split(' ')

# Create the main app
app = FastAPI(title="HR Performance Management API")
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============ ENUMS ============
class CycleStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"

class ConversationStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    READY_FOR_MANAGER = "ready_for_manager"
    COMPLETED = "completed"

class UserRole(str, Enum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    ADMIN = "admin"

# ============ PASSWORD UTILS ============
def generate_secure_password(length: int = 16) -> str:
    """Generate a secure random password (12-16 chars, alphanumeric + special)."""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_session_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(32)

# ============ MODELS ============
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = ""
    department: Optional[str] = ""
    manager_email: Optional[EmailStr] = None
    roles: List[UserRole] = [UserRole.EMPLOYEE]
    is_active: bool = True

class User(UserBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    must_change_password: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserImportItem(BaseModel):
    employee_email: EmailStr
    employee_name: Optional[str] = ""
    manager_email: Optional[EmailStr] = None
    department: Optional[str] = ""
    is_admin: Optional[bool] = False

class CycleBase(BaseModel):
    name: str
    start_date: datetime
    end_date: datetime
    status: CycleStatus = CycleStatus.DRAFT

class Cycle(CycleBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# NEW: Updated conversation model with new employee fields (NO RATINGS)
class ConversationBase(BaseModel):
    cycle_id: str
    employee_email: EmailStr
    manager_email: Optional[EmailStr] = None
    # Employee section fields (new structure)
    status_since_last_meeting: Optional[str] = ""  # Section 1: Status since last meeting
    previous_goals_progress: Optional[str] = ""    # 1a: How have your previous goals progressed?
    new_goals: Optional[str] = ""                   # Section 2: New goals
    how_to_achieve_goals: Optional[str] = ""       # 2b: How are you going to achieve them?
    support_needed: Optional[str] = ""             # 2c: What support or learning do you need?
    feedback_and_wishes: Optional[str] = ""        # Section 3: Feedback and wishes for the future
    # Manager section
    manager_feedback: Optional[str] = ""           # Manager's feedback (renamed from manager_review)
    # Status tracking
    status: ConversationStatus = ConversationStatus.NOT_STARTED

class Conversation(ConversationBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    updated_by_email: Optional[EmailStr] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EmployeeConversationUpdate(BaseModel):
    status_since_last_meeting: Optional[str] = None
    previous_goals_progress: Optional[str] = None
    new_goals: Optional[str] = None
    how_to_achieve_goals: Optional[str] = None
    support_needed: Optional[str] = None
    feedback_and_wishes: Optional[str] = None
    status: Optional[ConversationStatus] = None

class ManagerConversationUpdate(BaseModel):
    manager_feedback: Optional[str] = None
    status: Optional[ConversationStatus] = None

# ============ AUTH HELPERS ============
async def get_current_user(request: Request) -> Optional[User]:
    """Get current user from session cookie, header, or query parameter."""
    session_token = request.cookies.get("session_token")
    
    # Try Authorization header
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    # Try query parameter (for PDF downloads via browser)
    if not session_token:
        session_token = request.query_params.get("token")
    
    if not session_token:
        return None
    
    session = await db.sessions.find_one({
        "session_token": session_token,
        "expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}
    }, {"_id": 0})
    
    if not session:
        return None
    
    user = await db.users.find_one({"email": session["user_email"]}, {"_id": 0})
    if not user:
        return None
    
    return User(**user)

async def require_auth(request: Request) -> User:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

async def require_admin(request: Request) -> User:
    user = await require_auth(request)
    if UserRole.ADMIN not in user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def require_manager(request: Request) -> User:
    user = await require_auth(request)
    if UserRole.MANAGER not in user.roles and UserRole.ADMIN not in user.roles:
        raise HTTPException(status_code=403, detail="Manager access required")
    return user

# ============ AUTH ROUTES (PASSWORD-BASED) ============
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@api_router.post("/auth/login")
async def auth_login(request: LoginRequest, response: Response):
    """Login with email and password."""
    email = request.email.lower()
    
    user_doc = await db.users.find_one({"email": email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user_doc.get("is_active", True):
        raise HTTPException(status_code=403, detail="User account is inactive")
    
    password_hash = user_doc.get("password_hash")
    if not password_hash or not verify_password(request.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create session
    session_token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_EXPIRY_HOURS)
    
    await db.sessions.insert_one({
        "id": str(uuid.uuid4()),
        "user_email": email,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=SESSION_EXPIRY_HOURS * 3600
    )
    
    user = User(**user_doc)
    return {
        "user": user,
        "must_change_password": user_doc.get("must_change_password", False),
        "token": session_token
    }

@api_router.post("/auth/change-password")
async def auth_change_password(request: ChangePasswordRequest, user: User = Depends(require_auth)):
    """Change password (required on first login)."""
    user_doc = await db.users.find_one({"email": user.email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(request.current_password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    
    new_hash = hash_password(request.new_password)
    await db.users.update_one(
        {"email": user.email},
        {"$set": {
            "password_hash": new_hash,
            "must_change_password": False,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Password changed successfully"}

@api_router.get("/auth/me")
async def auth_me(user: User = Depends(require_auth)):
    user_doc = await db.users.find_one({"email": user.email}, {"_id": 0})
    return {
        **User(**user_doc).model_dump(),
        "must_change_password": user_doc.get("must_change_password", False)
    }

@api_router.post("/auth/logout")
async def auth_logout(request: Request, response: Response):
    session_token = request.cookies.get("session_token")
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if session_token:
        await db.sessions.delete_many({"session_token": session_token})
    
    response.delete_cookie("session_token", secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE)
    return {"message": "Logged out successfully"}

# ============ ADMIN: USER IMPORT WITH PASSWORD GENERATION ============
class ImportResult(BaseModel):
    imported: int
    updated: int
    errors: List[dict]
    message: str
    credentials_csv: Optional[str] = None  # Base64 or direct CSV content for download

@api_router.post("/admin/users/import")
async def admin_import_users(
    users_data: List[UserImportItem],
    user: User = Depends(require_admin)
):
    """Import users from JSON. Generates one-time passwords for new users."""
    imported = 0
    updated = 0
    errors = []
    new_credentials = []  # Store email:password for CSV export
    
    for item in users_data:
        try:
            email = item.employee_email.lower()
            roles = [UserRole.EMPLOYEE]
            if item.is_admin:
                roles.append(UserRole.ADMIN)
            
            existing = await db.users.find_one({"email": email})
            
            if existing:
                # Update existing user (don't change password)
                await db.users.update_one({"email": email}, {"$set": {
                    "name": item.employee_name or existing.get("name", ""),
                    "department": item.department or existing.get("department", ""),
                    "manager_email": item.manager_email.lower() if item.manager_email else None,
                    "roles": [r.value for r in roles],
                    "is_active": True,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }})
                updated += 1
            else:
                # New user: generate password
                plain_password = generate_secure_password(14)
                password_hash = hash_password(plain_password)
                
                user_doc = {
                    "id": str(uuid.uuid4()),
                    "email": email,
                    "name": item.employee_name or "",
                    "department": item.department or "",
                    "manager_email": item.manager_email.lower() if item.manager_email else None,
                    "roles": [r.value for r in roles],
                    "is_active": True,
                    "password_hash": password_hash,
                    "must_change_password": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                await db.users.insert_one(user_doc)
                new_credentials.append({"email": email, "password": plain_password})
                imported += 1
                
        except Exception as e:
            errors.append({"email": item.employee_email, "error": str(e)})
    
    # Second pass: set manager role
    async for u in db.users.find({}, {"_id": 0}):
        if u.get("manager_email"):
            manager = await db.users.find_one({"email": u["manager_email"]}, {"_id": 0})
            if manager and UserRole.MANAGER.value not in manager.get("roles", []):
                new_roles = list(set(manager.get("roles", []) + [UserRole.MANAGER.value]))
                await db.users.update_one({"email": u["manager_email"]}, {"$set": {"roles": new_roles}})
    
    # Generate CSV for new credentials (one-time)
    credentials_csv = None
    if new_credentials:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["email", "one_time_password"])
        for cred in new_credentials:
            writer.writerow([cred["email"], cred["password"]])
        credentials_csv = output.getvalue()
    
    return {
        "imported": imported,
        "updated": updated,
        "errors": errors,
        "message": f"Import complete: {imported} new users, {updated} updated",
        "credentials_csv": credentials_csv
    }

@api_router.post("/admin/users/import/csv")
async def admin_import_users_csv(file: UploadFile = File(...), user: User = Depends(require_admin)):
    """Import users from CSV file."""
    content = await file.read()
    content_str = content.decode('utf-8')
    
    reader = csv.DictReader(io.StringIO(content_str))
    users_data = []
    
    for row in reader:
        users_data.append(UserImportItem(
            employee_email=row.get('employee_email', ''),
            employee_name=row.get('employee_name', ''),
            manager_email=row.get('manager_email', '') or None,
            department=row.get('department', ''),
            is_admin=row.get('is_admin', '').lower() in ('true', '1', 'yes')
        ))
    
    return await admin_import_users(users_data, user)

# ============ ADMIN: PASSWORD RESET ============
class PasswordResetRequest(BaseModel):
    emails: List[EmailStr]

@api_router.post("/admin/users/reset-password")
async def admin_reset_password_single(email: str, user: User = Depends(require_admin)):
    """Reset password for a single user and return the new one-time password."""
    email = email.lower()
    user_doc = await db.users.find_one({"email": email})
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate new password
    plain_password = generate_secure_password(14)
    password_hash = hash_password(plain_password)
    
    # Update user - invalidate current sessions
    await db.users.update_one({"email": email}, {"$set": {
        "password_hash": password_hash,
        "must_change_password": True,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }})
    
    # Invalidate all sessions for this user
    await db.sessions.delete_many({"user_email": email})
    
    return {
        "email": email,
        "one_time_password": plain_password,
        "message": f"Password reset for {email}. User must change on next login."
    }

@api_router.delete("/admin/users/{email}")
async def admin_delete_user(email: str, user: User = Depends(require_admin)):
    """Delete a user from the system (admin only). Also deletes their conversations and sessions."""
    # Check if user exists
    target_user = await db.users.find_one({"email": email}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete all conversations where user is employee or manager
    conversations_result = await db.conversations.delete_many({
        "$or": [
            {"employee_email": email},
            {"manager_email": email}
        ]
    })
    
    # Delete all sessions
    sessions_result = await db.sessions.delete_many({"email": email})
    
    # Delete the user
    delete_result = await db.users.delete_one({"email": email})
    
    return {
        "message": f"User {email} deleted successfully",
        "conversations_deleted": conversations_result.deleted_count,
        "sessions_deleted": sessions_result.deleted_count
    }

@api_router.post("/admin/users/reset-passwords")
async def admin_reset_passwords(request: PasswordResetRequest, user: User = Depends(require_admin)):
    """Generate new one-time passwords for selected users."""
    reset_credentials = []
    errors = []
    
    for email in request.emails:
        email = email.lower()
        user_doc = await db.users.find_one({"email": email})
        
        if not user_doc:
            errors.append({"email": email, "error": "User not found"})
            continue
        
        # Generate new password
        plain_password = generate_secure_password(14)
        password_hash = hash_password(plain_password)
        
        # Update user - invalidate current sessions
        await db.users.update_one({"email": email}, {"$set": {
            "password_hash": password_hash,
            "must_change_password": True,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }})
        
        # Invalidate all sessions for this user
        await db.sessions.delete_many({"user_email": email})
        
        reset_credentials.append({"email": email, "password": plain_password})
    
    # Generate CSV
    credentials_csv = None
    if reset_credentials:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["email", "new_one_time_password", "note"])
        for cred in reset_credentials:
            writer.writerow([cred["email"], cred["password"], "Previous password invalidated. User must change on next login."])
        credentials_csv = output.getvalue()
    
    return {
        "reset_count": len(reset_credentials),
        "errors": errors,
        "credentials_csv": credentials_csv,
        "message": f"Reset passwords for {len(reset_credentials)} users"
    }

@api_router.get("/admin/users")
async def admin_get_users(user: User = Depends(require_admin)):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return users

@api_router.post("/admin/cycles")
async def admin_create_cycle(cycle_data: CycleBase, user: User = Depends(require_admin)):
    cycle = Cycle(**cycle_data.model_dump(), id=str(uuid.uuid4()))
    doc = cycle.model_dump()
    doc['start_date'] = doc['start_date'].isoformat()
    doc['end_date'] = doc['end_date'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.cycles.insert_one(doc)
    return cycle

@api_router.get("/admin/cycles")
async def admin_get_cycles(user: User = Depends(require_admin)):
    cycles = await db.cycles.find({}, {"_id": 0}).to_list(100)
    return cycles

@api_router.patch("/admin/cycles/{cycle_id}")
async def admin_update_cycle(cycle_id: str, status: CycleStatus, user: User = Depends(require_admin)):
    if status == CycleStatus.ACTIVE:
        await db.cycles.update_many(
            {"status": CycleStatus.ACTIVE.value},
            {"$set": {"status": CycleStatus.ARCHIVED.value, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    result = await db.cycles.update_one(
        {"id": cycle_id},
        {"$set": {"status": status.value, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Cycle not found")
    
    cycle = await db.cycles.find_one({"id": cycle_id}, {"_id": 0})
    return cycle

@api_router.delete("/admin/cycles/{cycle_id}")
async def admin_delete_cycle(cycle_id: str, user: User = Depends(require_admin)):
    """Delete a cycle from the system (admin only). Also deletes all conversations in that cycle."""
    # Check if cycle exists
    cycle = await db.cycles.find_one({"id": cycle_id}, {"_id": 0})
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    
    # Delete all conversations in this cycle
    conversations_result = await db.conversations.delete_many({"cycle_id": cycle_id})
    
    # Delete the cycle
    delete_result = await db.cycles.delete_one({"id": cycle_id})
    
    return {
        "message": f"Cycle '{cycle.get('name', cycle_id)}' deleted successfully",
        "conversations_deleted": conversations_result.deleted_count
    }

# ============ CYCLES ============
@api_router.get("/cycles/active")
async def get_active_cycle(user: User = Depends(require_auth)):
    cycle = await db.cycles.find_one({"status": CycleStatus.ACTIVE.value}, {"_id": 0})
    return cycle

@api_router.get("/cycles/all")
async def get_all_cycles(user: User = Depends(require_auth)):
    """Get all cycles for history view."""
    cycles = await db.cycles.find({}, {"_id": 0}).sort("start_date", -1).to_list(100)
    return cycles

# ============ EMPLOYEE CONVERSATIONS ============
@api_router.get("/conversations/me")
async def get_my_conversation(user: User = Depends(require_auth)):
    """Get current user's conversation for active cycle."""
    cycle = await db.cycles.find_one({"status": CycleStatus.ACTIVE.value}, {"_id": 0})
    if not cycle:
        raise HTTPException(status_code=404, detail="No active cycle found")
    
    conversation = await db.conversations.find_one({
        "cycle_id": cycle["id"],
        "employee_email": user.email
    }, {"_id": 0})
    
    if not conversation:
        user_doc = await db.users.find_one({"email": user.email}, {"_id": 0})
        conv = Conversation(cycle_id=cycle["id"], employee_email=user.email,
                           manager_email=user_doc.get("manager_email") if user_doc else None)
        doc = conv.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.conversations.insert_one(doc)
        conversation = doc
    
    return conversation

@api_router.get("/conversations/me/history")
async def get_my_conversation_history(user: User = Depends(require_auth)):
    """Get all archived conversations for current user."""
    conversations = await db.conversations.find(
        {"employee_email": user.email},
        {"_id": 0}
    ).to_list(100)
    
    # Enrich with cycle info
    result = []
    for conv in conversations:
        cycle = await db.cycles.find_one({"id": conv["cycle_id"]}, {"_id": 0})
        result.append({
            **conv,
            "cycle": cycle
        })
    
    return sorted(result, key=lambda x: x.get("cycle", {}).get("start_date", ""), reverse=True)

@api_router.get("/conversations/{conversation_id}")
async def get_conversation_by_id(conversation_id: str, user: User = Depends(require_auth)):
    """Get a specific conversation (for viewing archived)."""
    conversation = await db.conversations.find_one({"id": conversation_id}, {"_id": 0})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check authorization
    is_owner = conversation.get("employee_email") == user.email
    is_manager = conversation.get("manager_email") == user.email
    is_admin = UserRole.ADMIN in user.roles
    
    if not (is_owner or is_manager or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    cycle = await db.cycles.find_one({"id": conversation["cycle_id"]}, {"_id": 0})
    employee = await db.users.find_one({"email": conversation["employee_email"]}, {"_id": 0, "password_hash": 0})
    
    return {
        "conversation": conversation,
        "cycle": cycle,
        "employee": employee,
        "is_archived": cycle.get("status") == CycleStatus.ARCHIVED.value if cycle else True
    }

@api_router.put("/conversations/me")
async def update_my_conversation(update: EmployeeConversationUpdate, user: User = Depends(require_auth)):
    """Update current user's conversation (employee fields only)."""
    cycle = await db.cycles.find_one({"status": CycleStatus.ACTIVE.value}, {"_id": 0})
    if not cycle:
        raise HTTPException(status_code=404, detail="No active cycle found")
    
    conversation = await db.conversations.find_one({
        "cycle_id": cycle["id"],
        "employee_email": user.email
    }, {"_id": 0})
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation.get("status") == ConversationStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Cannot update completed conversation")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat(), "updated_by_email": user.email}
    
    for field in ["status_since_last_meeting", "previous_goals_progress", "new_goals", 
                  "how_to_achieve_goals", "support_needed", "feedback_and_wishes"]:
        value = getattr(update, field, None)
        if value is not None:
            update_data[field] = value
    
    if update.status is not None:
        if update.status not in [ConversationStatus.IN_PROGRESS, ConversationStatus.READY_FOR_MANAGER]:
            raise HTTPException(status_code=400, detail="Invalid status transition")
        update_data["status"] = update.status.value
    
    await db.conversations.update_one(
        {"cycle_id": cycle["id"], "employee_email": user.email},
        {"$set": update_data}
    )
    
    return await db.conversations.find_one({"cycle_id": cycle["id"], "employee_email": user.email}, {"_id": 0})

# ============ MANAGER ROUTES ============
@api_router.get("/manager/reports")
async def get_manager_reports(user: User = Depends(require_manager)):
    cycle = await db.cycles.find_one({"status": CycleStatus.ACTIVE.value}, {"_id": 0})
    reports = await db.users.find({"manager_email": user.email}, {"_id": 0, "password_hash": 0}).to_list(100)
    
    result = []
    for report in reports:
        report_data = {**report}
        if cycle:
            # Only show conversations that are not in draft status (drafts are private to employee)
            conv = await db.conversations.find_one({
                "cycle_id": cycle["id"],
                "employee_email": report["email"],
                "status": {"$ne": ConversationStatus.DRAFT.value}  # Don't show drafts to managers
            }, {"_id": 0})
            report_data["conversation_status"] = conv.get("status", ConversationStatus.NOT_STARTED.value) if conv else ConversationStatus.NOT_STARTED.value
            report_data["conversation_id"] = conv.get("id") if conv else None
        result.append(report_data)
    
    return result

@api_router.get("/manager/reports/{employee_email}/history")
async def get_report_history(employee_email: str, user: User = Depends(require_manager)):
    """Get all conversations for a direct report (including archived). Excludes drafts."""
    employee_email = employee_email.lower()
    
    if UserRole.ADMIN not in user.roles:
        report = await db.users.find_one({"email": employee_email, "manager_email": user.email}, {"_id": 0})
        if not report:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    # Don't show draft conversations to managers - they're private until submitted
    conversations = await db.conversations.find({
        "employee_email": employee_email,
        "status": {"$ne": ConversationStatus.DRAFT.value}
    }, {"_id": 0}).to_list(100)
    
    result = []
    for conv in conversations:
        cycle = await db.cycles.find_one({"id": conv["cycle_id"]}, {"_id": 0})
        result.append({**conv, "cycle": cycle})
    
    return sorted(result, key=lambda x: x.get("cycle", {}).get("start_date", ""), reverse=True)

@api_router.get("/manager/conversations/{employee_email}")
async def get_report_conversation(employee_email: str, user: User = Depends(require_manager)):
    """Get a direct report's conversation for active cycle."""
    employee_email = employee_email.lower()
    
    if UserRole.ADMIN not in user.roles:
        report = await db.users.find_one({"email": employee_email, "manager_email": user.email}, {"_id": 0})
        if not report:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    cycle = await db.cycles.find_one({"status": CycleStatus.ACTIVE.value}, {"_id": 0})
    if not cycle:
        raise HTTPException(status_code=404, detail="No active cycle found")
    
    conversation = await db.conversations.find_one({
        "cycle_id": cycle["id"],
        "employee_email": employee_email
    }, {"_id": 0})
    
    if not conversation:
        employee = await db.users.find_one({"email": employee_email}, {"_id": 0})
        conv = Conversation(cycle_id=cycle["id"], employee_email=employee_email,
                           manager_email=employee.get("manager_email") if employee else user.email)
        doc = conv.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.conversations.insert_one(doc)
        conversation = doc
    
    employee = await db.users.find_one({"email": employee_email}, {"_id": 0, "password_hash": 0})
    return {"conversation": conversation, "employee": employee}

@api_router.put("/manager/conversations/{employee_email}")
async def update_report_conversation(employee_email: str, update: ManagerConversationUpdate, user: User = Depends(require_manager)):
    """Update a direct report's conversation (manager feedback only)."""
    employee_email = employee_email.lower()
    
    if UserRole.ADMIN not in user.roles:
        report = await db.users.find_one({"email": employee_email, "manager_email": user.email}, {"_id": 0})
        if not report:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    cycle = await db.cycles.find_one({"status": CycleStatus.ACTIVE.value}, {"_id": 0})
    if not cycle:
        raise HTTPException(status_code=404, detail="No active cycle found")
    
    conversation = await db.conversations.find_one({
        "cycle_id": cycle["id"],
        "employee_email": employee_email
    }, {"_id": 0})
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat(), "updated_by_email": user.email}
    
    if update.manager_feedback is not None:
        update_data["manager_feedback"] = update.manager_feedback
    if update.status is not None:
        update_data["status"] = update.status.value
    
    await db.conversations.update_one(
        {"cycle_id": cycle["id"], "employee_email": employee_email},
        {"$set": update_data}
    )
    
    return await db.conversations.find_one({"cycle_id": cycle["id"], "employee_email": employee_email}, {"_id": 0})

# ============ PDF EXPORT ============
def strip_html_tags(text):
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = html.unescape(clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

class PDFReport(FPDF):
    def __init__(self, title):
        super().__init__()
        self.title = title
        
    def header(self):
        self.set_fill_color(26, 26, 46)
        self.rect(0, 0, 210, 35, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 15, self.title, ln=True, align='C')
        self.ln(10)
        
    def footer(self):
        self.set_y(-15)
        self.set_text_color(128, 128, 128)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')
    
    def section_header(self, text, r, g, b):
        self.set_font('Helvetica', 'B', 11)
        self.set_fill_color(r, g, b)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, text, ln=True, fill=True)
        self.set_text_color(0, 0, 0)
        self.set_font('Helvetica', '', 10)
        self.ln(2)
    
    def subsection(self, label, content):
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(60, 60, 60)
        self.cell(0, 6, label, ln=True)
        self.set_font('Helvetica', '', 10)
        self.set_text_color(0, 0, 0)
        content_clean = strip_html_tags(content) or "No response provided."
        self.multi_cell(0, 5, content_clean)
        self.ln(3)

@api_router.get("/conversations/{conversation_id}/pdf")
async def export_conversation_pdf(conversation_id: str, user: User = Depends(require_auth)):
    """Export conversation to PDF."""
    conversation = await db.conversations.find_one({"id": conversation_id}, {"_id": 0})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    is_owner = conversation.get("employee_email") == user.email
    is_manager = conversation.get("manager_email") == user.email
    is_admin = UserRole.ADMIN in user.roles
    
    if not (is_owner or is_manager or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    cycle = await db.cycles.find_one({"id": conversation["cycle_id"]}, {"_id": 0})
    employee = await db.users.find_one({"email": conversation["employee_email"]}, {"_id": 0})
    manager = await db.users.find_one({"email": conversation.get("manager_email")}, {"_id": 0}) if conversation.get("manager_email") else None
    
    cycle_name = cycle.get('name', 'EDI Conversation') if cycle else 'EDI Conversation'
    pdf = PDFReport(cycle_name)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_text_color(0, 0, 0)
    
    # Cycle Info
    pdf.section_header('Cycle Information', 100, 100, 100)
    pdf.cell(40, 6, 'Cycle:', 0)
    pdf.cell(0, 6, cycle_name, ln=True)
    if cycle:
        pdf.cell(40, 6, 'Period:', 0)
        pdf.cell(0, 6, f"{str(cycle.get('start_date', ''))[:10]} to {str(cycle.get('end_date', ''))[:10]}", ln=True)
        pdf.cell(40, 6, 'Status:', 0)
        pdf.cell(0, 6, cycle.get('status', 'N/A').title(), ln=True)
    pdf.ln(5)
    
    # Employee Info
    pdf.section_header('Employee Information', 0, 122, 255)
    pdf.cell(40, 6, 'Employee:', 0)
    employee_name = f"{employee.get('name', '')} ({conversation['employee_email']})" if employee and employee.get('name') else conversation['employee_email']
    pdf.cell(0, 6, employee_name or 'N/A', ln=True)
    pdf.cell(40, 6, 'Department:', 0)
    pdf.cell(0, 6, employee.get('department', 'N/A') if employee else 'N/A', ln=True)
    pdf.cell(40, 6, 'Manager:', 0)
    manager_name = manager.get('name') if manager and manager.get('name') else conversation.get('manager_email', 'N/A')
    pdf.cell(0, 6, manager_name or 'N/A', ln=True)
    pdf.cell(40, 6, 'Review Status:', 0)
    pdf.cell(0, 6, conversation.get('status', 'not_started').replace('_', ' ').title(), ln=True)
    pdf.ln(5)
    
    # Employee Section 1: Status since last meeting
    pdf.section_header('1. Status Since Last Meeting', 0, 180, 120)
    pdf.subsection('How have your previous goals progressed?', conversation.get('previous_goals_progress', ''))
    pdf.subsection('General status update:', conversation.get('status_since_last_meeting', ''))
    
    # Employee Section 2: New Goals
    pdf.section_header('2. New Goals and How to Achieve Them', 0, 150, 200)
    pdf.subsection('Key goals for the next 1-3 months:', conversation.get('new_goals', ''))
    pdf.subsection('How are you going to achieve them?', conversation.get('how_to_achieve_goals', ''))
    pdf.subsection('Support or learning needed:', conversation.get('support_needed', ''))
    
    # Employee Section 3: Feedback
    pdf.section_header('3. Feedback and Wishes for the Future', 100, 100, 200)
    content = strip_html_tags(conversation.get('feedback_and_wishes', '')) or "No response provided."
    pdf.multi_cell(0, 5, content)
    pdf.ln(5)
    
    # Manager Feedback
    pdf.section_header('Manager Feedback', 255, 150, 50)
    manager_content = strip_html_tags(conversation.get('manager_feedback', '')) or "No feedback provided."
    pdf.multi_cell(0, 5, manager_content)
    pdf.ln(5)
    
    # Timestamps
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 5, f"Created: {str(conversation.get('created_at', 'N/A'))[:19]}", ln=True)
    pdf.cell(0, 5, f"Last Updated: {str(conversation.get('updated_at', 'N/A'))[:19]} by {conversation.get('updated_by_email', 'N/A')}", ln=True)
    pdf.cell(0, 5, f"PDF Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}", ln=True)
    
    # Generate PDF bytes - fpdf2 output() returns bytes directly
    pdf_bytes = pdf.output()
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode('latin-1')
    
    filename = f"EDI_{conversation['employee_email'].split('@')[0]}_{cycle_name.replace(' ', '_')}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ============ HEALTH CHECK ============
@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "auth_mode": AUTH_MODE, "version": "2.0.0"}

@api_router.get("/")
async def root():
    return {"message": "HR Performance Management API", "version": "2.0.0", "ratings": False}

# Include router and middleware
app.include_router(api_router)

# Parse CORS origins - strip whitespace and filter empty values
cors_origins_raw = os.environ.get('CORS_ORIGINS', '')
cors_origins = [origin.strip() for origin in cors_origins_raw.split(',') if origin.strip()]

# Validate: no wildcards allowed when credentials are used
if '*' in cors_origins:
    logger.warning("CORS wildcard '*' detected - this is NOT secure with credentials. Use explicit origins.")
    cors_origins = ['*']  # If wildcard specified, use it (but log warning)

if not cors_origins:
    logger.warning("No CORS_ORIGINS specified - defaulting to same-origin only")
    cors_origins = []

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True if cors_origins and '*' not in cors_origins else False,
    allow_origins=cors_origins if cors_origins else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db_client():
    try:
        await db.users.create_index("email", unique=True)
        await db.conversations.create_index([("cycle_id", 1), ("employee_email", 1)], unique=True)
        await db.conversations.create_index([("cycle_id", 1), ("manager_email", 1)])
        await db.cycles.create_index("status")
        await db.sessions.create_index("session_token")
        await db.sessions.create_index("expires_at")
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
