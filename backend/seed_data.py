#!/usr/bin/env python3
"""
Seed data script for HR Performance Management app.
Run this to populate the database with demo data.
"""

import asyncio
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import uuid

load_dotenv()

mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'test_database')

client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

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
    },
    {
        "id": str(uuid.uuid4()),
        "email": "cto@company.com",
        "name": "Michael Chen",
        "department": "Engineering",
        "manager_email": None,
        "roles": ["employee", "manager"],
        "is_active": True,
    },
    {
        "id": str(uuid.uuid4()),
        "email": "engineering.lead@company.com",
        "name": "Emily Rodriguez",
        "department": "Engineering",
        "manager_email": "cto@company.com",
        "roles": ["employee", "manager"],
        "is_active": True,
    },
    {
        "id": str(uuid.uuid4()),
        "email": "developer1@company.com",
        "name": "Alex Thompson",
        "department": "Engineering",
        "manager_email": "engineering.lead@company.com",
        "roles": ["employee"],
        "is_active": True,
    },
    {
        "id": str(uuid.uuid4()),
        "email": "developer2@company.com",
        "name": "Jordan Lee",
        "department": "Engineering",
        "manager_email": "engineering.lead@company.com",
        "roles": ["employee"],
        "is_active": True,
    },
    {
        "id": str(uuid.uuid4()),
        "email": "developer3@company.com",
        "name": "Sam Wilson",
        "department": "Engineering",
        "manager_email": "engineering.lead@company.com",
        "roles": ["employee"],
        "is_active": True,
    },
    {
        "id": str(uuid.uuid4()),
        "email": "marketing.head@company.com",
        "name": "Lisa Martinez",
        "department": "Marketing",
        "manager_email": None,
        "roles": ["employee", "manager"],
        "is_active": True,
    },
    {
        "id": str(uuid.uuid4()),
        "email": "marketing1@company.com",
        "name": "Chris Johnson",
        "department": "Marketing",
        "manager_email": "marketing.head@company.com",
        "roles": ["employee"],
        "is_active": True,
    },
    {
        "id": str(uuid.uuid4()),
        "email": "marketing2@company.com",
        "name": "Taylor Brown",
        "department": "Marketing",
        "manager_email": "marketing.head@company.com",
        "roles": ["employee"],
        "is_active": True,
    },
    {
        "id": str(uuid.uuid4()),
        "email": "hr.manager@company.com",
        "name": "Patricia Davis",
        "department": "Human Resources",
        "manager_email": "admin@company.com",
        "roles": ["employee", "manager"],
        "is_active": True,
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

# Demo conversations (sample data)
DEMO_CONVERSATIONS = [
    {
        "employee_email": "developer1@company.com",
        "status": "in_progress",
        "employee_self_review": """<p><strong>Key Accomplishments:</strong></p>
<ul>
<li>Successfully delivered the new authentication system ahead of schedule</li>
<li>Mentored two junior developers on React best practices</li>
<li>Reduced API response time by 40% through optimization</li>
</ul>
<p><strong>Challenges Overcome:</strong></p>
<p>Navigated complex legacy code migration while maintaining 100% uptime.</p>""",
        "goals_next_period": """<p><strong>Technical Goals:</strong></p>
<ul>
<li>Lead the microservices architecture initiative</li>
<li>Obtain AWS Solutions Architect certification</li>
<li>Implement comprehensive test coverage (>80%)</li>
</ul>
<p><strong>Professional Development:</strong></p>
<ul>
<li>Present at team knowledge sharing sessions monthly</li>
<li>Take on more code review responsibilities</li>
</ul>""",
    },
    {
        "employee_email": "developer2@company.com",
        "status": "ready_for_manager",
        "employee_self_review": """<p>This year has been transformative for my career growth.</p>
<p><strong>Highlights:</strong></p>
<ul>
<li>Shipped 3 major features with zero production incidents</li>
<li>Improved CI/CD pipeline reducing deployment time by 60%</li>
<li>Built strong collaboration with the QA team</li>
</ul>""",
        "goals_next_period": """<ul>
<li>Transition to senior developer role</li>
<li>Lead a cross-functional project</li>
<li>Improve system monitoring and alerting</li>
</ul>""",
        "manager_review": """<p>Jordan has shown exceptional growth this year.</p>
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
</ul>""",
        "ratings": {
            "performance": 4,
            "collaboration": 5,
            "growth": 4,
        },
    },
    {
        "employee_email": "marketing1@company.com",
        "status": "completed",
        "employee_self_review": """<p><strong>Campaign Results:</strong></p>
<ul>
<li>Increased social media engagement by 150%</li>
<li>Successfully launched Q3 product campaign</li>
<li>Built partnerships with 5 key influencers</li>
</ul>""",
        "goals_next_period": """<ul>
<li>Develop video content strategy</li>
<li>Expand into TikTok marketing</li>
<li>Improve lead conversion rate by 25%</li>
</ul>""",
        "manager_review": """<p>Chris has exceeded expectations in all areas this year.</p>
<p>The Q3 campaign was our most successful to date, and Chris's creative direction was instrumental in its success.</p>
<p><strong>Recommendation:</strong> Ready for promotion to Senior Marketing Specialist.</p>""",
        "ratings": {
            "performance": 5,
            "collaboration": 4,
            "growth": 5,
        },
        "meeting_date": datetime.now(timezone.utc).isoformat(),
    },
]


async def seed_database():
    """Seed the database with demo data."""
    print("🌱 Starting database seed...")
    
    # Clear existing data (optional - comment out to preserve data)
    print("  Clearing existing data...")
    await db.users.delete_many({})
    await db.cycles.delete_many({})
    await db.conversations.delete_many({})
    await db.sessions.delete_many({})
    await db.verification_codes.delete_many({})
    
    # Insert users
    print("  Inserting demo users...")
    now = datetime.now(timezone.utc).isoformat()
    for user in DEMO_USERS:
        user["created_at"] = now
        user["updated_at"] = now
        await db.users.insert_one(user)
    print(f"  ✓ Inserted {len(DEMO_USERS)} users")
    
    # Insert cycle
    print("  Inserting demo cycle...")
    await db.cycles.insert_one(DEMO_CYCLE)
    print(f"  ✓ Inserted cycle: {DEMO_CYCLE['name']}")
    
    # Insert conversations
    print("  Inserting demo conversations...")
    for conv_data in DEMO_CONVERSATIONS:
        user = await db.users.find_one({"email": conv_data["employee_email"]})
        conv = {
            "id": str(uuid.uuid4()),
            "cycle_id": DEMO_CYCLE["id"],
            "employee_email": conv_data["employee_email"],
            "manager_email": user.get("manager_email") if user else None,
            "meeting_date": conv_data.get("meeting_date"),
            "employee_self_review": conv_data.get("employee_self_review", ""),
            "manager_review": conv_data.get("manager_review", ""),
            "goals_next_period": conv_data.get("goals_next_period", ""),
            "ratings": conv_data.get("ratings", {}),
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
    print("  ✓ Indexes created")
    
    print("\n✅ Database seeded successfully!")
    print("\n📋 Demo Accounts:")
    print("  Admin:      admin@company.com")
    print("  Manager:    engineering.lead@company.com")
    print("  Employee:   developer1@company.com")
    print("\n💡 Tip: Verification codes are displayed in the UI when SHOW_CODE_IN_RESPONSE=true")


if __name__ == "__main__":
    asyncio.run(seed_database())
