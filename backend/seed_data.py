#!/usr/bin/env python3
"""
Seed data script for HR Performance Management app.
Run this to populate the database with demo data including passwords.

⚠️ WARNING: FOR LOCAL DEVELOPMENT ONLY - DO NOT RUN IN PRODUCTION ⚠️

Production deployment should:
1. Start with an EMPTY database
2. Create ONE admin account manually
3. Import real employee data via CSV upload in admin panel

Demo accounts (password: Demo@123456):
  - admin@company.com (Admin)
  - engineering.lead@company.com (Manager)
  - developer1@company.com (Employee)
"""

import asyncio
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import uuid
import bcrypt

load_dotenv()

mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'test_database')

client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# Default demo password - all demo users will have this password
DEMO_PASSWORD = "Demo@123456"

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Demo users with hierarchy
DEMO_USERS = [
    {
        "id": str(uuid.uuid4()),
        "email": "admin@company.com",
        "name": "Sarah Admin",
        "department": "Human Resources",
        "manager_email": None,
        "roles": ["employee", "admin"],
        "is_active": True,
        "must_change_password": False,  # Demo accounts don't require password change
    },
    {
        "id": str(uuid.uuid4()),
        "email": "cto@company.com",
        "name": "Michael Chen",
        "department": "Engineering",
        "manager_email": None,
        "roles": ["employee", "manager"],
        "is_active": True,
        "must_change_password": False,
    },
    {
        "id": str(uuid.uuid4()),
        "email": "engineering.lead@company.com",
        "name": "Emily Rodriguez",
        "department": "Engineering",
        "manager_email": "cto@company.com",
        "roles": ["employee", "manager"],
        "is_active": True,
        "must_change_password": False,
    },
    {
        "id": str(uuid.uuid4()),
        "email": "developer1@company.com",
        "name": "Alex Thompson",
        "department": "Engineering",
        "manager_email": "engineering.lead@company.com",
        "roles": ["employee"],
        "is_active": True,
        "must_change_password": False,
    },
    {
        "id": str(uuid.uuid4()),
        "email": "developer2@company.com",
        "name": "Jordan Lee",
        "department": "Engineering",
        "manager_email": "engineering.lead@company.com",
        "roles": ["employee"],
        "is_active": True,
        "must_change_password": False,
    },
    {
        "id": str(uuid.uuid4()),
        "email": "developer3@company.com",
        "name": "Sam Wilson",
        "department": "Engineering",
        "manager_email": "engineering.lead@company.com",
        "roles": ["employee"],
        "is_active": True,
        "must_change_password": False,
    },
    {
        "id": str(uuid.uuid4()),
        "email": "marketing.head@company.com",
        "name": "Lisa Martinez",
        "department": "Marketing",
        "manager_email": None,
        "roles": ["employee", "manager"],
        "is_active": True,
        "must_change_password": False,
    },
    {
        "id": str(uuid.uuid4()),
        "email": "marketing1@company.com",
        "name": "Chris Johnson",
        "department": "Marketing",
        "manager_email": "marketing.head@company.com",
        "roles": ["employee"],
        "is_active": True,
        "must_change_password": False,
    },
    {
        "id": str(uuid.uuid4()),
        "email": "marketing2@company.com",
        "name": "Taylor Brown",
        "department": "Marketing",
        "manager_email": "marketing.head@company.com",
        "roles": ["employee"],
        "is_active": True,
        "must_change_password": False,
    },
    {
        "id": str(uuid.uuid4()),
        "email": "hr.manager@company.com",
        "name": "Patricia Davis",
        "department": "Human Resources",
        "manager_email": "admin@company.com",
        "roles": ["employee", "manager"],
        "is_active": True,
        "must_change_password": False,
    },
]

# Demo cycle
DEMO_CYCLE = {
    "id": str(uuid.uuid4()),
    "name": "2025 Annual Performance Review",
    "start_date": datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat(),
    "end_date": datetime(2025, 12, 31, tzinfo=timezone.utc).isoformat(),
    "status": "active",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "updated_at": datetime.now(timezone.utc).isoformat(),
}

# Demo conversations with NEW field structure (no ratings!)
DEMO_CONVERSATIONS = [
    {
        "employee_email": "developer1@company.com",
        "status": "in_progress",
        "previous_goals_progress": """<p>Good progress on most goals:</p>
<ul>
<li>Completed the React migration ahead of schedule</li>
<li>Test coverage increased to 75%</li>
<li>Still working on documentation improvements</li>
</ul>""",
        "status_since_last_meeting": """<p>Overall doing well. Had some challenges with the new CI/CD pipeline but resolved them.</p>""",
        "new_goals": """<ul>
<li>Lead the microservices architecture initiative</li>
<li>Obtain AWS Solutions Architect certification</li>
<li>Reach 85% test coverage</li>
</ul>""",
        "how_to_achieve_goals": """<p>Plan to:</p>
<ul>
<li>Dedicate 2 hours weekly to AWS study</li>
<li>Schedule architecture review sessions with team</li>
<li>Add tests with each PR</li>
</ul>""",
        "support_needed": """<p>Would benefit from:</p>
<ul>
<li>Budget for AWS certification exam</li>
<li>Time allocated for architecture design sessions</li>
</ul>""",
        "feedback_and_wishes": """<p>Really enjoying the technical challenges. Would love more opportunities to mentor junior developers.</p>""",
    },
    {
        "employee_email": "developer2@company.com",
        "status": "ready_for_manager",
        "previous_goals_progress": """<p>All goals achieved or exceeded:</p>
<ul>
<li>Shipped 3 major features with zero production incidents</li>
<li>Improved CI/CD pipeline - deployment time reduced by 60%</li>
<li>Built strong collaboration with QA team</li>
</ul>""",
        "status_since_last_meeting": """<p>This year has been transformative for my career growth. Feeling ready for more responsibility.</p>""",
        "new_goals": """<ul>
<li>Transition to senior developer role</li>
<li>Lead a cross-functional project</li>
<li>Improve system monitoring and alerting</li>
</ul>""",
        "how_to_achieve_goals": """<p>Taking on more complex tasks, volunteering for leadership opportunities, and studying observability best practices.</p>""",
        "support_needed": """<p>Would appreciate mentorship from a senior engineer on system design.</p>""",
        "feedback_and_wishes": """<p>Happy with the team culture. Would like to see more cross-team collaboration opportunities.</p>""",
        "manager_feedback": """<p>Jordan has shown exceptional growth this year.</p>
<p><strong>Strengths:</strong></p>
<ul>
<li>Strong technical skills and problem-solving ability</li>
<li>Excellent collaboration with team members</li>
<li>Proactive in identifying and resolving issues</li>
</ul>
<p><strong>Areas for Development:</strong></p>
<ul>
<li>Could benefit from more public speaking opportunities</li>
<li>Ready for more leadership responsibilities</li>
</ul>
<p>Recommending for promotion track.</p>""",
    },
    {
        "employee_email": "marketing1@company.com",
        "status": "completed",
        "previous_goals_progress": """<p>Exceeded all targets:</p>
<ul>
<li>Social media engagement up 150%</li>
<li>Q3 campaign was our most successful ever</li>
<li>Built partnerships with 5 key influencers</li>
</ul>""",
        "status_since_last_meeting": """<p>Feeling energized and ready to take on more strategic initiatives.</p>""",
        "new_goals": """<ul>
<li>Develop video content strategy</li>
<li>Expand into TikTok marketing</li>
<li>Improve lead conversion rate by 25%</li>
</ul>""",
        "how_to_achieve_goals": """<p>Planning to:</p>
<ul>
<li>Attend video marketing workshop</li>
<li>Research TikTok best practices</li>
<li>A/B test landing pages</li>
</ul>""",
        "support_needed": """<p>Budget for video production equipment and TikTok ads trial.</p>""",
        "feedback_and_wishes": """<p>Love the creative freedom here. Would appreciate more data analytics support.</p>""",
        "manager_feedback": """<p>Chris has exceeded expectations in all areas this year.</p>
<p>The Q3 campaign was our most successful to date, and Chris's creative direction was instrumental in its success.</p>
<p><strong>Recommendation:</strong> Ready for promotion to Senior Marketing Specialist.</p>""",
    },
]


async def seed_database():
    """Seed the database with demo data."""
    print("🌱 Starting database seed...")
    
    # Clear existing data
    print("  Clearing existing data...")
    await db.users.delete_many({})
    await db.cycles.delete_many({})
    await db.conversations.delete_many({})
    await db.sessions.delete_many({})
    await db.verification_codes.delete_many({})
    
    # Hash the demo password once
    hashed_password = hash_password(DEMO_PASSWORD)
    
    # Insert users with hashed passwords
    print("  Inserting demo users...")
    now = datetime.now(timezone.utc).isoformat()
    for user in DEMO_USERS:
        user["password_hash"] = hashed_password
        user["created_at"] = now
        user["updated_at"] = now
        await db.users.insert_one(user)
    print(f"  ✓ Inserted {len(DEMO_USERS)} users")
    
    # Insert cycle
    print("  Inserting demo cycle...")
    await db.cycles.insert_one(DEMO_CYCLE)
    print(f"  ✓ Inserted cycle: {DEMO_CYCLE['name']}")
    
    # Insert conversations with NEW field structure
    print("  Inserting demo conversations...")
    for conv_data in DEMO_CONVERSATIONS:
        user = await db.users.find_one({"email": conv_data["employee_email"]})
        conv = {
            "id": str(uuid.uuid4()),
            "cycle_id": DEMO_CYCLE["id"],
            "employee_email": conv_data["employee_email"],
            "manager_email": user.get("manager_email") if user else None,
            # New employee fields
            "previous_goals_progress": conv_data.get("previous_goals_progress", ""),
            "status_since_last_meeting": conv_data.get("status_since_last_meeting", ""),
            "new_goals": conv_data.get("new_goals", ""),
            "how_to_achieve_goals": conv_data.get("how_to_achieve_goals", ""),
            "support_needed": conv_data.get("support_needed", ""),
            "feedback_and_wishes": conv_data.get("feedback_and_wishes", ""),
            # Manager field
            "manager_feedback": conv_data.get("manager_feedback", ""),
            # Status
            "status": conv_data.get("status", "not_started"),
            "updated_by_email": conv_data["employee_email"],
            "created_at": now,
            "updated_at": now,
        }
        await db.conversations.insert_one(conv)
    print(f"  ✓ Inserted {len(DEMO_CONVERSATIONS)} conversations")
    
    # Create indexes
    print("  Creating indexes...")
    await db.users.create_index("email", unique=True)
    await db.conversations.create_index([("cycle_id", 1), ("employee_email", 1)], unique=True)
    await db.conversations.create_index([("cycle_id", 1), ("manager_email", 1)])
    await db.cycles.create_index("status")
    await db.sessions.create_index("session_token")
    await db.sessions.create_index("expires_at")
    print("  ✓ Indexes created")
    
    print("\n✅ Database seeded successfully!")
    print("\n" + "="*50)
    print("📋 DEMO ACCOUNTS")
    print("="*50)
    print(f"Password for all accounts: {DEMO_PASSWORD}")
    print("")
    print("  👤 Admin:      admin@company.com")
    print("  👤 Manager:    engineering.lead@company.com")
    print("  👤 Employee:   developer1@company.com")
    print("="*50)
    print("\n💡 Note: In production, users receive generated passwords via admin import.")
    print("   Demo accounts have must_change_password=False for convenience.")


if __name__ == "__main__":
    asyncio.run(seed_database())
