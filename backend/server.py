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
from datetime import datetime, timezone, timedelta
import json
import csv
import io
from enum import Enum
from fpdf import FPDF
import html
import re
import aiofiles

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Auth configuration
AUTH_MODE = os.environ.get('AUTH_MODE', 'email')  # 'email' or 'entra'
DEV_VERIFICATION_CODE = os.environ.get('DEV_VERIFICATION_CODE', None) or None  # Fixed code for dev (empty string = None)
SHOW_CODE_IN_RESPONSE = os.environ.get('SHOW_CODE_IN_RESPONSE', 'false').lower() == 'true'  # Default FALSE for security
SESSION_EXPIRY_HOURS = int(os.environ.get('SESSION_EXPIRY_HOURS', '8'))  # Shorter default for security

# Cookie security settings
COOKIE_SECURE = os.environ.get('COOKIE_SECURE', 'true').lower() == 'true'  # Default TRUE for HTTPS
COOKIE_SAMESITE = os.environ.get('COOKIE_SAMESITE', 'lax')  # 'lax', 'strict', or 'none'

# Entra SSO config (scaffold - not enabled by default)
ENTRA_TENANT_ID = os.environ.get('ENTRA_TENANT_ID', '')
ENTRA_CLIENT_ID = os.environ.get('ENTRA_CLIENT_ID', '')
ENTRA_CLIENT_SECRET = os.environ.get('ENTRA_CLIENT_SECRET', '')
ENTRA_REDIRECT_URI = os.environ.get('ENTRA_REDIRECT_URI', '')
ENTRA_AUTHORITY = f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}" if ENTRA_TENANT_ID else ''
ENTRA_SCOPES = os.environ.get('ENTRA_SCOPES', 'openid profile email').split(' ')

# Create the main app
app = FastAPI(title="HR Performance Management API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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

# ============ MODELS ============
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = ""
    department: Optional[str] = ""
    manager_email: Optional[EmailStr] = None
    roles: List[UserRole] = [UserRole.EMPLOYEE]
    is_active: bool = True

class UserCreate(UserBase):
    pass

class User(UserBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
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

class CycleCreate(CycleBase):
    pass

class Cycle(CycleBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Ratings(BaseModel):
    performance: Optional[int] = Field(None, ge=1, le=5)
    collaboration: Optional[int] = Field(None, ge=1, le=5)
    growth: Optional[int] = Field(None, ge=1, le=5)

class ConversationBase(BaseModel):
    cycle_id: str
    employee_email: EmailStr
    manager_email: Optional[EmailStr] = None
    meeting_date: Optional[datetime] = None
    employee_self_review: Optional[str] = ""
    manager_review: Optional[str] = ""
    goals_next_period: Optional[str] = ""
    ratings: Optional[Ratings] = Field(default_factory=Ratings)
    status: ConversationStatus = ConversationStatus.NOT_STARTED

class ConversationCreate(BaseModel):
    cycle_id: str
    employee_email: EmailStr

class Conversation(ConversationBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    updated_by_email: Optional[EmailStr] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EmployeeConversationUpdate(BaseModel):
    employee_self_review: Optional[str] = None
    goals_next_period: Optional[str] = None
    status: Optional[ConversationStatus] = None

class ManagerConversationUpdate(BaseModel):
    manager_review: Optional[str] = None
    meeting_date: Optional[datetime] = None
    ratings: Optional[Ratings] = None
    status: Optional[ConversationStatus] = None

# Session model
class Session(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_email: EmailStr
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Verification code model
class VerificationCode(BaseModel):
    email: EmailStr
    code: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============ AUTH HELPER FUNCTIONS ============
def generate_verification_code() -> str:
    """Generate a 6-digit verification code."""
    if DEV_VERIFICATION_CODE:
        return DEV_VERIFICATION_CODE
    return str(secrets.randbelow(900000) + 100000)

def generate_session_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(32)

async def get_current_user(request: Request) -> Optional[User]:
    """Get current user from session cookie or header."""
    session_token = request.cookies.get("session_token")
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
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
    """Require authentication."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

async def require_admin(request: Request) -> User:
    """Require admin role."""
    user = await require_auth(request)
    if UserRole.ADMIN not in user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def require_manager(request: Request) -> User:
    """Require manager or admin role."""
    user = await require_auth(request)
    if UserRole.MANAGER not in user.roles and UserRole.ADMIN not in user.roles:
        raise HTTPException(status_code=403, detail="Manager access required")
    return user

# ============ AUTH ROUTES ============
class EmailStartRequest(BaseModel):
    email: EmailStr

class EmailStartResponse(BaseModel):
    message: str
    code: Optional[str] = None  # Only shown if SHOW_CODE_IN_RESPONSE is true

@api_router.post("/auth/email/start", response_model=EmailStartResponse)
async def auth_email_start(request: EmailStartRequest):
    """Start email authentication - generate verification code."""
    email = request.email.lower()
    
    # Check if user exists
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please contact your administrator.")
    
    # Generate code
    code = generate_verification_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    # Store code
    await db.verification_codes.delete_many({"email": email})
    await db.verification_codes.insert_one({
        "email": email,
        "code": code,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    response = {"message": "Verification code sent"}
    if SHOW_CODE_IN_RESPONSE:
        response["code"] = code
    
    return response

class EmailVerifyRequest(BaseModel):
    email: EmailStr
    code: str

class AuthResponse(BaseModel):
    user: User
    message: str

@api_router.post("/auth/email/verify")
async def auth_email_verify(request: EmailVerifyRequest, response: Response):
    """Verify email code and create session."""
    email = request.email.lower()
    
    # Find verification code
    code_doc = await db.verification_codes.find_one({
        "email": email,
        "code": request.code,
        "expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}
    }, {"_id": 0})
    
    if not code_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    
    # Get user
    user_doc = await db.users.find_one({"email": email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user_doc.get("is_active", True):
        raise HTTPException(status_code=403, detail="User account is inactive")
    
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
    
    # Delete used code
    await db.verification_codes.delete_many({"email": email})
    
    # Set cookie with security settings from environment
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=SESSION_EXPIRY_HOURS * 3600
    )
    
    return {"user": User(**user_doc), "message": "Login successful", "token": session_token}

@api_router.get("/auth/me")
async def auth_me(user: User = Depends(require_auth)):
    """Get current authenticated user."""
    return user

@api_router.post("/auth/logout")
async def auth_logout(request: Request, response: Response):
    """Logout and invalidate session."""
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.sessions.delete_many({"session_token": session_token})
    
    response.delete_cookie("session_token")
    return {"message": "Logged out successfully"}

# ============ ENTRA SSO ROUTES (SCAFFOLD) ============
if AUTH_MODE == "entra":
    try:
        import msal
        
        msal_app = msal.ConfidentialClientApplication(
            ENTRA_CLIENT_ID,
            authority=ENTRA_AUTHORITY,
            client_credential=ENTRA_CLIENT_SECRET
        )
        
        @api_router.get("/auth/entra/login")
        async def auth_entra_login():
            """Start Entra SSO login flow."""
            auth_url = msal_app.get_authorization_request_url(
                ENTRA_SCOPES,
                redirect_uri=ENTRA_REDIRECT_URI
            )
            return {"auth_url": auth_url}
        
        @api_router.get("/auth/entra/callback")
        async def auth_entra_callback(code: str, response: Response):
            """Handle Entra SSO callback."""
            result = msal_app.acquire_token_by_authorization_code(
                code,
                scopes=ENTRA_SCOPES,
                redirect_uri=ENTRA_REDIRECT_URI
            )
            
            if "error" in result:
                raise HTTPException(status_code=400, detail=result.get("error_description", "Authentication failed"))
            
            # Extract email from token
            email = result.get("id_token_claims", {}).get("preferred_username", "").lower()
            if not email:
                email = result.get("id_token_claims", {}).get("email", "").lower()
            
            if not email:
                raise HTTPException(status_code=400, detail="Could not extract email from token")
            
            # Check if user exists in our system
            user_doc = await db.users.find_one({"email": email}, {"_id": 0})
            if not user_doc:
                raise HTTPException(status_code=403, detail="User not found in HR system. Please contact your administrator.")
            
            if not user_doc.get("is_active", True):
                raise HTTPException(status_code=403, detail="User account is inactive")
            
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
                secure=True,
                samesite="lax",
                max_age=SESSION_EXPIRY_HOURS * 3600
            )
            
            return {"user": User(**user_doc), "message": "Login successful"}
        
        @api_router.post("/auth/entra/logout")
        async def auth_entra_logout(request: Request, response: Response):
            """Logout from Entra SSO."""
            await auth_logout(request, response)
            logout_url = f"{ENTRA_AUTHORITY}/oauth2/v2.0/logout"
            return {"message": "Logged out", "logout_url": logout_url}
            
    except ImportError:
        logger.warning("MSAL not installed, Entra SSO not available")

# ============ ADMIN ROUTES ============
@api_router.post("/admin/users/import")
async def admin_import_users(
    users_data: List[UserImportItem],
    user: User = Depends(require_admin)
):
    """Import users from JSON. Admin only."""
    imported = 0
    updated = 0
    errors = []
    
    for item in users_data:
        try:
            email = item.employee_email.lower()
            
            roles = [UserRole.EMPLOYEE]
            if item.is_admin:
                roles.append(UserRole.ADMIN)
            
            # Check if user is a manager of anyone
            manager_of = await db.users.find_one({"manager_email": email}, {"_id": 0})
            if manager_of or (item.manager_email is None):
                # Will be set as manager when we process all users
                pass
            
            user_doc = {
                "email": email,
                "name": item.employee_name or "",
                "department": item.department or "",
                "manager_email": item.manager_email.lower() if item.manager_email else None,
                "roles": [r.value for r in roles],
                "is_active": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            existing = await db.users.find_one({"email": email})
            if existing:
                await db.users.update_one({"email": email}, {"$set": user_doc})
                updated += 1
            else:
                user_doc["id"] = str(uuid.uuid4())
                user_doc["created_at"] = datetime.now(timezone.utc).isoformat()
                await db.users.insert_one(user_doc)
                imported += 1
                
        except Exception as e:
            errors.append({"email": item.employee_email, "error": str(e)})
    
    # Second pass: set manager role for anyone who is a manager
    async for u in db.users.find({}, {"_id": 0}):
        if u.get("manager_email"):
            manager = await db.users.find_one({"email": u["manager_email"]}, {"_id": 0})
            if manager and UserRole.MANAGER.value not in manager.get("roles", []):
                new_roles = list(set(manager.get("roles", []) + [UserRole.MANAGER.value]))
                await db.users.update_one(
                    {"email": u["manager_email"]},
                    {"$set": {"roles": new_roles}}
                )
    
    return {
        "imported": imported,
        "updated": updated,
        "errors": errors,
        "message": f"Import complete: {imported} new, {updated} updated"
    }

@api_router.post("/admin/users/import/csv")
async def admin_import_users_csv(
    file: UploadFile = File(...),
    user: User = Depends(require_admin)
):
    """Import users from CSV file. Admin only."""
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

@api_router.get("/admin/users", response_model=List[User])
async def admin_get_users(user: User = Depends(require_admin)):
    """Get all users. Admin only."""
    users = await db.users.find({}, {"_id": 0}).to_list(1000)
    return [User(**u) for u in users]

@api_router.post("/admin/cycles", response_model=Cycle)
async def admin_create_cycle(
    cycle_data: CycleCreate,
    user: User = Depends(require_admin)
):
    """Create a new performance cycle. Admin only."""
    cycle = Cycle(
        **cycle_data.model_dump(),
        id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    doc = cycle.model_dump()
    doc['start_date'] = doc['start_date'].isoformat()
    doc['end_date'] = doc['end_date'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.cycles.insert_one(doc)
    return cycle

@api_router.get("/admin/cycles", response_model=List[Cycle])
async def admin_get_cycles(user: User = Depends(require_admin)):
    """Get all cycles. Admin only."""
    cycles = await db.cycles.find({}, {"_id": 0}).to_list(100)
    return [Cycle(**c) for c in cycles]

@api_router.patch("/admin/cycles/{cycle_id}")
async def admin_update_cycle(
    cycle_id: str,
    status: CycleStatus,
    user: User = Depends(require_admin)
):
    """Update cycle status (activate/archive). Admin only."""
    # If activating, deactivate other active cycles
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
    return Cycle(**cycle)

# ============ APP ROUTES ============
@api_router.get("/cycles/active")
async def get_active_cycle(user: User = Depends(require_auth)):
    """Get the current active cycle."""
    cycle = await db.cycles.find_one({"status": CycleStatus.ACTIVE.value}, {"_id": 0})
    if not cycle:
        return None
    return Cycle(**cycle)

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
        # Auto-create conversation for user
        user_doc = await db.users.find_one({"email": user.email}, {"_id": 0})
        conv = Conversation(
            cycle_id=cycle["id"],
            employee_email=user.email,
            manager_email=user_doc.get("manager_email") if user_doc else None
        )
        doc = conv.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        if doc.get('meeting_date'):
            doc['meeting_date'] = doc['meeting_date'].isoformat()
        await db.conversations.insert_one(doc)
        conversation = doc
    
    return Conversation(**conversation)

@api_router.put("/conversations/me")
async def update_my_conversation(
    update: EmployeeConversationUpdate,
    user: User = Depends(require_auth)
):
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
    
    # Check if already completed
    if conversation.get("status") == ConversationStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Cannot update completed conversation")
    
    update_data = {}
    if update.employee_self_review is not None:
        update_data["employee_self_review"] = update.employee_self_review
    if update.goals_next_period is not None:
        update_data["goals_next_period"] = update.goals_next_period
    if update.status is not None:
        # Employee can only set to in_progress or ready_for_manager
        if update.status not in [ConversationStatus.IN_PROGRESS, ConversationStatus.READY_FOR_MANAGER]:
            raise HTTPException(status_code=400, detail="Invalid status transition")
        update_data["status"] = update.status.value
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["updated_by_email"] = user.email
    
    await db.conversations.update_one(
        {"cycle_id": cycle["id"], "employee_email": user.email},
        {"$set": update_data}
    )
    
    conversation = await db.conversations.find_one({
        "cycle_id": cycle["id"],
        "employee_email": user.email
    }, {"_id": 0})
    
    return Conversation(**conversation)

# ============ MANAGER ROUTES ============
@api_router.get("/manager/reports")
async def get_manager_reports(user: User = Depends(require_manager)):
    """Get list of direct reports for current manager."""
    cycle = await db.cycles.find_one({"status": CycleStatus.ACTIVE.value}, {"_id": 0})
    
    # Find all users who have this user as manager
    reports = await db.users.find({"manager_email": user.email}, {"_id": 0}).to_list(100)
    
    result = []
    for report in reports:
        report_data = User(**report).model_dump()
        
        # Get conversation status if cycle exists
        if cycle:
            conv = await db.conversations.find_one({
                "cycle_id": cycle["id"],
                "employee_email": report["email"]
            }, {"_id": 0})
            
            if conv:
                report_data["conversation_status"] = conv.get("status", ConversationStatus.NOT_STARTED.value)
                report_data["conversation_id"] = conv.get("id")
            else:
                report_data["conversation_status"] = ConversationStatus.NOT_STARTED.value
                report_data["conversation_id"] = None
        
        result.append(report_data)
    
    return result

@api_router.get("/manager/conversations/{employee_email}")
async def get_report_conversation(
    employee_email: str,
    user: User = Depends(require_manager)
):
    """Get a direct report's conversation."""
    employee_email = employee_email.lower()
    
    # Verify this is a direct report (unless admin)
    if UserRole.ADMIN not in user.roles:
        report = await db.users.find_one({
            "email": employee_email,
            "manager_email": user.email
        }, {"_id": 0})
        if not report:
            raise HTTPException(status_code=403, detail="Not authorized to view this conversation")
    
    cycle = await db.cycles.find_one({"status": CycleStatus.ACTIVE.value}, {"_id": 0})
    if not cycle:
        raise HTTPException(status_code=404, detail="No active cycle found")
    
    conversation = await db.conversations.find_one({
        "cycle_id": cycle["id"],
        "employee_email": employee_email
    }, {"_id": 0})
    
    if not conversation:
        # Auto-create conversation
        employee = await db.users.find_one({"email": employee_email}, {"_id": 0})
        conv = Conversation(
            cycle_id=cycle["id"],
            employee_email=employee_email,
            manager_email=employee.get("manager_email") if employee else user.email
        )
        doc = conv.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        if doc.get('meeting_date'):
            doc['meeting_date'] = doc['meeting_date'].isoformat()
        await db.conversations.insert_one(doc)
        conversation = doc
    
    # Also return employee info
    employee = await db.users.find_one({"email": employee_email}, {"_id": 0})
    
    return {
        "conversation": Conversation(**conversation),
        "employee": User(**employee) if employee else None
    }

@api_router.put("/manager/conversations/{employee_email}")
async def update_report_conversation(
    employee_email: str,
    update: ManagerConversationUpdate,
    user: User = Depends(require_manager)
):
    """Update a direct report's conversation (manager fields only)."""
    employee_email = employee_email.lower()
    
    # Verify this is a direct report (unless admin)
    if UserRole.ADMIN not in user.roles:
        report = await db.users.find_one({
            "email": employee_email,
            "manager_email": user.email
        }, {"_id": 0})
        if not report:
            raise HTTPException(status_code=403, detail="Not authorized to update this conversation")
    
    cycle = await db.cycles.find_one({"status": CycleStatus.ACTIVE.value}, {"_id": 0})
    if not cycle:
        raise HTTPException(status_code=404, detail="No active cycle found")
    
    conversation = await db.conversations.find_one({
        "cycle_id": cycle["id"],
        "employee_email": employee_email
    }, {"_id": 0})
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    update_data = {}
    if update.manager_review is not None:
        update_data["manager_review"] = update.manager_review
    if update.meeting_date is not None:
        update_data["meeting_date"] = update.meeting_date.isoformat()
    if update.ratings is not None:
        update_data["ratings"] = update.ratings.model_dump()
    if update.status is not None:
        update_data["status"] = update.status.value
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["updated_by_email"] = user.email
    
    await db.conversations.update_one(
        {"cycle_id": cycle["id"], "employee_email": employee_email},
        {"$set": update_data}
    )
    
    conversation = await db.conversations.find_one({
        "cycle_id": cycle["id"],
        "employee_email": employee_email
    }, {"_id": 0})
    
    return Conversation(**conversation)

# ============ PDF EXPORT ============
def strip_html_tags(text):
    """Remove HTML tags and convert to plain text."""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', ' ', text)
    # Decode HTML entities
    clean = html.unescape(clean)
    # Clean up whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

class PDFReport(FPDF):
    def __init__(self, title):
        super().__init__()
        self.title = title
        
    def header(self):
        # Header background
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

@api_router.get("/conversations/{conversation_id}/pdf")
async def export_conversation_pdf(
    conversation_id: str,
    user: User = Depends(require_auth)
):
    """Export conversation to PDF."""
    conversation = await db.conversations.find_one({"id": conversation_id}, {"_id": 0})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check authorization
    is_owner = conversation.get("employee_email") == user.email
    is_manager = conversation.get("manager_email") == user.email
    is_admin = UserRole.ADMIN in user.roles
    
    if not (is_owner or is_manager or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to view this conversation")
    
    # Get cycle and employee info
    cycle = await db.cycles.find_one({"id": conversation["cycle_id"]}, {"_id": 0})
    employee = await db.users.find_one({"email": conversation["employee_email"]}, {"_id": 0})
    manager = await db.users.find_one({"email": conversation.get("manager_email")}, {"_id": 0}) if conversation.get("manager_email") else None
    
    # Create PDF
    cycle_name = cycle.get('name', 'Performance Conversation') if cycle else 'Performance Conversation'
    pdf = PDFReport(cycle_name)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Reset text color after header
    pdf.set_text_color(0, 0, 0)
    
    # Employee Info Section
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(0, 122, 255)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, 'Employee Information', ln=True, fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', '', 10)
    pdf.ln(3)
    
    employee_name = employee.get('name', '') if employee else ''
    employee_email = conversation['employee_email']
    department = employee.get('department', 'N/A') if employee else 'N/A'
    manager_name = manager.get('name', conversation.get('manager_email', 'N/A')) if manager else conversation.get('manager_email', 'N/A')
    meeting_date = conversation.get('meeting_date', 'Not scheduled')
    status = conversation.get('status', 'not_started').replace('_', ' ').title()
    
    pdf.cell(40, 6, 'Employee:', 0)
    pdf.cell(0, 6, f"{employee_name} ({employee_email})", ln=True)
    pdf.cell(40, 6, 'Department:', 0)
    pdf.cell(0, 6, department, ln=True)
    pdf.cell(40, 6, 'Manager:', 0)
    pdf.cell(0, 6, str(manager_name), ln=True)
    pdf.cell(40, 6, 'Meeting Date:', 0)
    pdf.cell(0, 6, str(meeting_date), ln=True)
    pdf.cell(40, 6, 'Status:', 0)
    pdf.cell(0, 6, status, ln=True)
    pdf.ln(8)
    
    # Self Review Section
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(0, 255, 148)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, 'Employee Self-Review', ln=True, fill=True)
    pdf.set_font('Helvetica', '', 10)
    pdf.ln(3)
    self_review = strip_html_tags(conversation.get('employee_self_review', '')) or 'No content provided.'
    pdf.multi_cell(0, 6, self_review)
    pdf.ln(8)
    
    # Goals Section
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(0, 122, 255)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, 'Goals for Next Period', ln=True, fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', '', 10)
    pdf.ln(3)
    goals = strip_html_tags(conversation.get('goals_next_period', '')) or 'No goals defined.'
    pdf.multi_cell(0, 6, goals)
    pdf.ln(8)
    
    # Manager Review Section
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(255, 193, 7)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, 'Manager Review', ln=True, fill=True)
    pdf.set_font('Helvetica', '', 10)
    pdf.ln(3)
    manager_review = strip_html_tags(conversation.get('manager_review', '')) or 'No review provided.'
    pdf.multi_cell(0, 6, manager_review)
    pdf.ln(8)
    
    # Ratings Section
    ratings = conversation.get('ratings', {})
    if ratings and any(ratings.values()):
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(128, 128, 128)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, 'Ratings', ln=True, fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Helvetica', '', 10)
        pdf.ln(3)
        
        if ratings.get('performance'):
            pdf.cell(50, 6, 'Performance:', 0)
            pdf.cell(0, 6, f"{ratings['performance']} / 5", ln=True)
        if ratings.get('collaboration'):
            pdf.cell(50, 6, 'Collaboration:', 0)
            pdf.cell(0, 6, f"{ratings['collaboration']} / 5", ln=True)
        if ratings.get('growth'):
            pdf.cell(50, 6, 'Growth:', 0)
            pdf.cell(0, 6, f"{ratings['growth']} / 5", ln=True)
        pdf.ln(5)
    
    # Footer info
    pdf.ln(10)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 5, f"Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", ln=True)
    pdf.cell(0, 5, f"Last updated by: {conversation.get('updated_by_email', 'N/A')}", ln=True)
    
    # Output PDF
    pdf_bytes = pdf.output()
    
    filename = f"performance_review_{conversation['employee_email'].split('@')[0]}_{cycle_name.replace(' ', '_')}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ============ HEALTH CHECK ============
@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "auth_mode": AUTH_MODE}

@api_router.get("/")
async def root():
    return {"message": "HR Performance Management API", "version": "1.0.0"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db_client():
    """Create indexes on startup."""
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
