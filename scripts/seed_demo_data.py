"""
MongoDB Atlas Demo Data Seeder
Talent Management & Career Growth Platform

Seeds realistic, enterprise-grade demo dataset:
- 1 Super Administrator (admin@demo.com)
- 2 HR Administrators (hr@demo.com, hr2@demo.com)
- 5 Managers (manager@demo.com .. manager5@demo.com)
- 30 Employees (employee@demo.com .. employee29@demo.com)
- 10 Departments
- 25 Technical & Soft Skills
- 40 Employee Goals
- 30 Performance Assessments
- 20 Career Development Plans
- 15 Training Programs
- 30 Feedback & Performance Reviews
- 20 Notifications
- Organization configurations and governance settings

Idempotent: Uses upserts / existing checks so it can run repeatedly without duplicates.
Default Demo Password: Demo@2026!
"""

from __future__ import annotations
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.db import get_db, init_db, is_mock_mode, check_db_health
from services.core import hash_password

DEMO_ORG_ID = "ORG-TALENT-01"
DEMO_ORG_NAME = "Talent Growth Technologies"
DEMO_PASSWORD = "Demo@2026!"


def seed_demo_dataset() -> Dict[str, int]:
    """Populates MongoDB Atlas with complete enterprise talent intelligence demo records."""
    db = get_db()
    init_db()

    pwd_hash, salt = hash_password(DEMO_PASSWORD)
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    counts: Dict[str, int] = {}

    print("=" * 70)
    print("MONGODB ATLAS ENTERPRISE DEMO DATA SEEDER")
    print("=" * 70)
    print(f"Target Database: {db.name}")

    # --------------------------------------------------------------------------
    # 1. Organization Record
    # --------------------------------------------------------------------------
    db.organizations.update_one(
        {"org_id": DEMO_ORG_ID},
        {"$setOnInsert": {
            "id": 1,
            "org_id": DEMO_ORG_ID,
            "name": DEMO_ORG_NAME,
            "contact_email": "contact@talentgrowth.com",
            "official_email": "admin@demo.com",
            "status": "Active",
            "created_at": now_iso,
            "updated_at": now_iso
        }},
        upsert=True
    )
    counts["organizations"] = db.organizations.count_documents({})

    # --------------------------------------------------------------------------
    # 2. 10 Enterprise Departments
    # --------------------------------------------------------------------------
    departments_data = [
        {"id": 1, "name": "Engineering", "budget": 850000.0, "head_employee_id": "MGR001"},
        {"id": 2, "name": "Product Management", "budget": 450000.0, "head_employee_id": "MGR002"},
        {"id": 3, "name": "Data & Analytics", "budget": 520000.0, "head_employee_id": "MGR003"},
        {"id": 4, "name": "Cloud & DevOps", "budget": 600000.0, "head_employee_id": "MGR004"},
        {"id": 5, "name": "Cyber Security", "budget": 400000.0, "head_employee_id": "MGR004"},
        {"id": 6, "name": "Human Resources", "budget": 300000.0, "head_employee_id": "HR001"},
        {"id": 7, "name": "Finance & Operations", "budget": 380000.0, "head_employee_id": "HR002"},
        {"id": 8, "name": "Marketing & Growth", "budget": 420000.0, "head_employee_id": "MGR002"},
        {"id": 9, "name": "Design & UX", "budget": 350000.0, "head_employee_id": "MGR005"},
        {"id": 10, "name": "Sales & Customer Success", "budget": 650000.0, "head_employee_id": "MGR002"}
    ]
    for dept in departments_data:
        db.departments.update_one(
            {"org_id": DEMO_ORG_ID, "name": dept["name"]},
            {"$set": {
                "id": dept["id"],
                "org_id": DEMO_ORG_ID,
                "name": dept["name"],
                "budget": dept["budget"],
                "head_employee_id": dept["head_employee_id"],
                "updated_at": now_iso
            }, "$setOnInsert": {"created_at": now_iso}},
            upsert=True
        )
    counts["departments"] = db.departments.count_documents({})

    # --------------------------------------------------------------------------
    # 3. 25 Core Skills (Technical & Soft Skills)
    # --------------------------------------------------------------------------
    skills_data = [
        {"id": 1, "name": "Python", "category": "Technical", "description": "Core backend language, data structures, and APIs"},
        {"id": 2, "name": "JavaScript", "category": "Technical", "description": "Modern ECMAScript, event loop, and asynchronous logic"},
        {"id": 3, "name": "React", "category": "Technical", "description": "Frontend UI component design, hooks, and state management"},
        {"id": 4, "name": "Node.js", "category": "Technical", "description": "Server-side runtime, microservices, and asynchronous I/O"},
        {"id": 5, "name": "SQL", "category": "Technical", "description": "Relational query optimization, indexing, and data modeling"},
        {"id": 6, "name": "MongoDB", "category": "Technical", "description": "NoSQL document store, aggregation pipelines, and sharding"},
        {"id": 7, "name": "Docker & Containers", "category": "Technical", "description": "Containerization, multi-stage builds, and microservices packaging"},
        {"id": 8, "name": "Kubernetes", "category": "Technical", "description": "Container orchestration, cluster scaling, and ingress routing"},
        {"id": 9, "name": "Cloud Architecture", "category": "Technical", "description": "AWS/GCP/Azure multi-region distributed system engineering"},
        {"id": 10, "name": "System Design", "category": "Technical", "description": "High-availability, fault-tolerant enterprise architectures"},
        {"id": 11, "name": "REST APIs", "category": "Technical", "description": "API contract design, OpenAPI specs, and microservices integration"},
        {"id": 12, "name": "Git & Version Control", "category": "Tool", "description": "Distributed branching, trunk-based development, and code review"},
        {"id": 13, "name": "CI/CD Pipelines", "category": "Technical", "description": "Automated testing, continuous deployment, and infrastructure as code"},
        {"id": 14, "name": "Microservices Architecture", "category": "Technical", "description": "Decoupled domain services, event streaming, and API gateways"},
        {"id": 15, "name": "Data Modeling", "category": "Technical", "description": "Enterprise schema design, normalization, and graph models"},
        {"id": 16, "name": "Performance Optimization", "category": "Technical", "description": "Query profiling, memory diagnostics, and caching strategies"},
        {"id": 17, "name": "Unit Testing & QA", "category": "Technical", "description": "Test automation, pytest, mock fixtures, and regression pipelines"},
        {"id": 18, "name": "GraphQL", "category": "Technical", "description": "Schema definition, resolvers, and federation query optimization"},
        {"id": 19, "name": "Security & Governance", "category": "Domain", "description": "RBAC, OAuth2, encryption standards, and compliance audits"},
        {"id": 20, "name": "Machine Learning", "category": "Technical", "description": "Feature engineering, predictive modeling, and model evaluation"},
        {"id": 21, "name": "Problem Solving", "category": "Soft Skill", "description": "Analytical problem breakdown and strategic root cause analysis"},
        {"id": 22, "name": "Technical Communication", "category": "Soft Skill", "description": "Cross-functional executive articulation and design document writing"},
        {"id": 23, "name": "Engineering Leadership", "category": "Leadership", "description": "Staff engineer roadmap execution and engineering delivery"},
        {"id": 24, "name": "Agile & Scrum Delivery", "category": "Domain", "description": "Sprint planning, backlog grooming, and velocity tracking"},
        {"id": 25, "name": "Mentorship", "category": "Leadership", "description": "Coaching junior and mid-level engineers for high growth"}
    ]
    for sk in skills_data:
        db.skills.update_one(
            {"name": sk["name"]},
            {"$set": {
                "id": sk["id"],
                "name": sk["name"],
                "category": sk["category"],
                "description": sk["description"],
                "updated_at": now_iso
            }, "$setOnInsert": {"created_at": now_iso}},
            upsert=True
        )
    counts["skills"] = db.skills.count_documents({})

    # --------------------------------------------------------------------------
    # 4. 1 Super Admin + 2 HR Admins + 5 Managers + 30 Employees = 38 Users & Employees
    # --------------------------------------------------------------------------
    user_roster = [
        # Super Admin
        {
            "id": 1, "emp_id": "SA001", "name": "Siddharth Verma", "email": "admin@demo.com",
            "role": "super_admin", "dept": "Executive", "title": "Chief Technology Officer & Super Admin",
            "exp": 14.5, "manager_id": None, "skills": "System Design, Cloud Architecture, Engineering Leadership, Security & Governance"
        },
        # 2 HR Admins
        {
            "id": 2, "emp_id": "HR001", "name": "Sarah Jenkins", "email": "hr@demo.com",
            "role": "admin", "dept": "Human Resources", "title": "Director of Talent & People Operations",
            "exp": 10.0, "manager_id": "SA001", "skills": "Technical Communication, Agile & Scrum Delivery, Mentorship, Security & Governance"
        },
        {
            "id": 3, "emp_id": "HR002", "name": "David Miller", "email": "hr2@demo.com",
            "role": "admin", "dept": "Human Resources", "title": "VP of People & Culture",
            "exp": 12.0, "manager_id": "SA001", "skills": "Technical Communication, Engineering Leadership, Mentorship, Problem Solving"
        },
        # 5 Managers
        {
            "id": 4, "emp_id": "MGR001", "name": "Elena Rostova", "email": "manager@demo.com",
            "role": "manager", "dept": "Engineering", "title": "Senior Engineering Manager",
            "exp": 11.5, "manager_id": "SA001", "skills": "Python, System Design, Engineering Leadership, CI/CD Pipelines, Microservices Architecture"
        },
        {
            "id": 5, "emp_id": "MGR002", "name": "Marcus Vance", "email": "manager2@demo.com",
            "role": "manager", "dept": "Product Management", "title": "Director of Product Management",
            "exp": 9.5, "manager_id": "SA001", "skills": "Agile & Scrum Delivery, Technical Communication, Problem Solving, Data Modeling"
        },
        {
            "id": 6, "emp_id": "MGR003", "name": "Rachel Green", "email": "manager3@demo.com",
            "role": "manager", "dept": "Data & Analytics", "title": "Data Engineering Lead",
            "exp": 8.0, "manager_id": "MGR001", "skills": "Python, SQL, MongoDB, Machine Learning, Data Modeling, Performance Optimization"
        },
        {
            "id": 7, "emp_id": "MGR004", "name": "Liam O'Connor", "email": "manager4@demo.com",
            "role": "manager", "dept": "Cloud & DevOps", "title": "Cloud Infrastructure Lead",
            "exp": 8.5, "manager_id": "MGR001", "skills": "Docker & Containers, Kubernetes, Cloud Architecture, CI/CD Pipelines, Security & Governance"
        },
        {
            "id": 8, "emp_id": "MGR005", "name": "Sophia Chen", "email": "manager5@demo.com",
            "role": "manager", "dept": "Design & UX", "title": "Lead Design & UX Architect",
            "exp": 7.5, "manager_id": "MGR002", "skills": "React, JavaScript, Technical Communication, Problem Solving, Mentorship"
        },
        # 30 Employees across departments
        {
            "id": 11, "emp_id": "EMP011", "name": "Alex Morgan", "email": "employee@demo.com",
            "role": "employee", "dept": "Engineering", "title": "Senior Cloud Architect",
            "exp": 6.5, "manager_id": "MGR001", "skills": "Python, Docker & Containers, Kubernetes, Cloud Architecture, System Design"
        },
        {"id": 12, "emp_id": "EMP012", "name": "Priya Sharma", "email": "employee1@demo.com", "role": "employee", "dept": "Engineering", "title": "Senior Backend Engineer", "exp": 5.0, "manager_id": "MGR001", "skills": "Python, SQL, REST APIs, Microservices Architecture, Unit Testing & QA"},
        {"id": 13, "emp_id": "EMP013", "name": "Ethan Wright", "email": "employee2@demo.com", "role": "employee", "dept": "Engineering", "title": "Full Stack Engineer", "exp": 4.0, "manager_id": "MGR001", "skills": "JavaScript, React, Node.js, SQL, REST APIs"},
        {"id": 14, "emp_id": "EMP014", "name": "Ananya Roy", "email": "employee3@demo.com", "role": "employee", "dept": "Product Management", "title": "Technical Product Manager", "exp": 4.5, "manager_id": "MGR002", "skills": "Agile & Scrum Delivery, Technical Communication, Data Modeling, Problem Solving"},
        {"id": 15, "emp_id": "EMP015", "name": "Carlos Gomez", "email": "employee4@demo.com", "role": "employee", "dept": "Cloud & DevOps", "title": "DevOps Engineer", "exp": 3.5, "manager_id": "MGR004", "skills": "Docker & Containers, Kubernetes, CI/CD Pipelines, Cloud Architecture"},
        {"id": 16, "emp_id": "EMP016", "name": "Amina Yusuf", "email": "employee5@demo.com", "role": "employee", "dept": "Data & Analytics", "title": "Senior Data Scientist", "exp": 5.5, "manager_id": "MGR003", "skills": "Python, SQL, Machine Learning, Data Modeling, Performance Optimization"},
        {"id": 17, "emp_id": "EMP017", "name": "Lucas Silva", "email": "employee6@demo.com", "role": "employee", "dept": "Engineering", "title": "Frontend Engineer", "exp": 3.0, "manager_id": "MGR005", "skills": "JavaScript, React, GraphQL, Problem Solving, Unit Testing & QA"},
        {"id": 18, "emp_id": "EMP018", "name": "Zoe Bennett", "email": "employee7@demo.com", "role": "employee", "dept": "Cyber Security", "title": "Security Analyst", "exp": 4.0, "manager_id": "MGR004", "skills": "Security & Governance, Cloud Architecture, Problem Solving, Technical Communication"},
        {"id": 19, "emp_id": "EMP019", "name": "Vikram Malhotra", "email": "employee8@demo.com", "role": "employee", "dept": "Engineering", "title": "Software Engineer II", "exp": 3.5, "manager_id": "MGR001", "skills": "Python, SQL, REST APIs, Git & Version Control"},
        {"id": 20, "emp_id": "EMP020", "name": "Chloe Martin", "email": "employee9@demo.com", "role": "employee", "dept": "Marketing & Growth", "title": "Growth Marketing Specialist", "exp": 3.0, "manager_id": "MGR002", "skills": "Problem Solving, Technical Communication, Data Modeling, SQL"},
        {"id": 21, "emp_id": "EMP021", "name": "Daniel Kim", "email": "employee10@demo.com", "role": "employee", "dept": "Finance & Operations", "title": "Financial Operations Analyst", "exp": 4.5, "manager_id": "HR002", "skills": "Problem Solving, SQL, Data Modeling, Technical Communication"},
        {"id": 22, "emp_id": "EMP022", "name": "Fatima Al-Sayed", "email": "employee11@demo.com", "role": "employee", "dept": "Human Resources", "title": "Talent Development Specialist", "exp": 3.5, "manager_id": "HR001", "skills": "Technical Communication, Mentorship, Problem Solving, Agile & Scrum Delivery"},
        {"id": 23, "emp_id": "EMP023", "name": "Gabriel Santos", "email": "employee12@demo.com", "role": "employee", "dept": "Sales & Customer Success", "title": "Enterprise Solutions Consultant", "exp": 5.0, "manager_id": "MGR002", "skills": "Technical Communication, Problem Solving, REST APIs, Cloud Architecture"},
        {"id": 24, "emp_id": "EMP024", "name": "Hannah Abbott", "email": "employee13@demo.com", "role": "employee", "dept": "Design & UX", "title": "UI/UX Designer", "exp": 3.0, "manager_id": "MGR005", "skills": "React, JavaScript, Problem Solving, Technical Communication"},
        {"id": 25, "emp_id": "EMP025", "name": "Isaac Newton", "email": "employee14@demo.com", "role": "employee", "dept": "Engineering", "title": "Backend Software Engineer", "exp": 2.5, "manager_id": "MGR001", "skills": "Python, SQL, REST APIs, Docker & Containers"},
        {"id": 26, "emp_id": "EMP026", "name": "Jessica Taylor", "email": "employee15@demo.com", "role": "employee", "dept": "Data & Analytics", "title": "BI & Analytics Engineer", "exp": 4.0, "manager_id": "MGR003", "skills": "SQL, Python, Data Modeling, Performance Optimization"},
        {"id": 27, "emp_id": "EMP027", "name": "Kavita Reddy", "email": "employee16@demo.com", "role": "employee", "dept": "Engineering", "title": "Systems Integration Engineer", "exp": 4.5, "manager_id": "MGR001", "skills": "Node.js, REST APIs, Microservices Architecture, Docker & Containers"},
        {"id": 28, "emp_id": "EMP028", "name": "Liam Murphy", "email": "employee17@demo.com", "role": "employee", "dept": "Cloud & DevOps", "title": "Site Reliability Engineer", "exp": 4.0, "manager_id": "MGR004", "skills": "Kubernetes, Docker & Containers, CI/CD Pipelines, Performance Optimization"},
        {"id": 29, "emp_id": "EMP029", "name": "Maya Lin", "email": "employee18@demo.com", "role": "employee", "dept": "Product Management", "title": "Associate Product Manager", "exp": 2.0, "manager_id": "MGR002", "skills": "Agile & Scrum Delivery, Technical Communication, Problem Solving"},
        {"id": 30, "emp_id": "EMP030", "name": "Noah Williams", "email": "employee19@demo.com", "role": "employee", "dept": "Cyber Security", "title": "Information Security Engineer", "exp": 5.0, "manager_id": "MGR004", "skills": "Security & Governance, Cloud Architecture, CI/CD Pipelines, System Design"},
        {"id": 31, "emp_id": "EMP031", "name": "Olivia Davis", "email": "employee20@demo.com", "role": "employee", "dept": "Human Resources", "title": "People Operations Coordinator", "exp": 2.5, "manager_id": "HR001", "skills": "Technical Communication, Problem Solving, Mentorship"},
        {"id": 32, "emp_id": "EMP032", "name": "Patrick Stewart", "email": "employee21@demo.com", "role": "employee", "dept": "Engineering", "title": "Staff Backend Engineer", "exp": 7.0, "manager_id": "MGR001", "skills": "Python, System Design, Microservices Architecture, Cloud Architecture, Mentorship"},
        {"id": 33, "emp_id": "EMP033", "name": "Quinn Fabray", "email": "employee22@demo.com", "role": "employee", "dept": "Marketing & Growth", "title": "Digital Growth Specialist", "exp": 3.5, "manager_id": "MGR002", "skills": "Technical Communication, Data Modeling, Problem Solving"},
        {"id": 34, "emp_id": "EMP034", "name": "Rohan Joshi", "email": "employee23@demo.com", "role": "employee", "dept": "Engineering", "title": "API Platform Engineer", "exp": 3.5, "manager_id": "MGR001", "skills": "Python, REST APIs, GraphQL, SQL, Docker & Containers"},
        {"id": 35, "emp_id": "EMP035", "name": "Samantha Jones", "email": "employee24@demo.com", "role": "employee", "dept": "Sales & Customer Success", "title": "Customer Success Manager", "exp": 4.0, "manager_id": "MGR002", "skills": "Technical Communication, Problem Solving, Mentorship"},
        {"id": 36, "emp_id": "EMP036", "name": "Tariq Mansoor", "email": "employee25@demo.com", "role": "employee", "dept": "Data & Analytics", "title": "Data Pipeline Engineer", "exp": 3.0, "manager_id": "MGR003", "skills": "Python, SQL, MongoDB, Performance Optimization"},
        {"id": 37, "emp_id": "EMP037", "name": "Uma Thurman", "email": "employee26@demo.com", "role": "employee", "dept": "Design & UX", "title": "Product Designer", "exp": 3.0, "manager_id": "MGR005", "skills": "React, JavaScript, Technical Communication, Problem Solving"},
        {"id": 38, "emp_id": "EMP038", "name": "Victor Hugo", "email": "employee27@demo.com", "role": "employee", "dept": "Finance & Operations", "title": "Financial Systems Analyst", "exp": 5.0, "manager_id": "HR002", "skills": "SQL, Problem Solving, Data Modeling, Security & Governance"},
        {"id": 39, "emp_id": "EMP039", "name": "Wendy Darling", "email": "employee28@demo.com", "role": "employee", "dept": "Engineering", "title": "Junior Software Engineer", "exp": 1.5, "manager_id": "MGR001", "skills": "Python, Git & Version Control, REST APIs, Problem Solving"},
        {"id": 40, "emp_id": "EMP040", "name": "Xavier Woods", "email": "employee29@demo.com", "role": "employee", "dept": "Cloud & DevOps", "title": "Cloud Platform Engineer", "exp": 3.5, "manager_id": "MGR004", "skills": "Docker & Containers, Kubernetes, Cloud Architecture, CI/CD Pipelines"}
    ]

    for u in user_roster:
        # Upsert User
        db.users.update_one(
            {"email": u["email"]},
            {"$set": {
                "id": u["id"],
                "name": u["name"],
                "email": u["email"],
                "password_hash": pwd_hash,
                "salt": salt,
                "role": u["role"],
                "employee_id": u["emp_id"],
                "org_id": DEMO_ORG_ID,
                "org_name": DEMO_ORG_NAME,
                "account_type": "Organization",
                "department": u["dept"],
                "job_title": u["title"],
                "status": "Active",
                "date_joined": "2023-04-15",
                "updated_at": now_iso
            }, "$setOnInsert": {"created_at": now_iso}},
            upsert=True
        )

        # Upsert Employee
        db.employees.update_one(
            {"employee_id": u["emp_id"]},
            {"$set": {
                "id": u["id"],
                "employee_id": u["emp_id"],
                "user_id": u["id"],
                "org_id": DEMO_ORG_ID,
                "name": u["name"],
                "email": u["email"],
                "phone": "+1 (555) 019-2834",
                "department": u["dept"],
                "designation": u["title"],
                "joining_date": "2023-04-15",
                "employment_status": "Active",
                "years_experience": u["exp"],
                "primary_skills": u["skills"],
                "manager_id": u["manager_id"],
                "account_status": "Active",
                "created_by": 1,
                "updated_at": now_iso
            }, "$setOnInsert": {"created_at": now_iso}},
            upsert=True
        )

        # Add Employee Skills portfolio
        skill_names = [s.strip() for s in u["skills"].split(",") if s.strip()]
        for idx, s_name in enumerate(skill_names, 1):
            prof = "Expert" if u["exp"] >= 7.0 else ("Advanced" if u["exp"] >= 4.0 else "Intermediate")
            db.employee_skills.update_one(
                {"employee_id": u["emp_id"], "skill_name": s_name},
                {"$set": {
                    "employee_id": u["emp_id"],
                    "org_id": DEMO_ORG_ID,
                    "skill_name": s_name,
                    "proficiency": prof,
                    "years_experience": min(u["exp"], 5.0),
                    "verified": True,
                    "updated_at": now_iso
                }, "$setOnInsert": {"id": u["id"] * 100 + idx, "created_at": now_iso}},
                upsert=True
            )

    counts["users"] = db.users.count_documents({})
    counts["employees"] = db.employees.count_documents({})
    counts["employee_skills"] = db.employee_skills.count_documents({})

    # --------------------------------------------------------------------------
    # 5. 40 Employee Goals
    # --------------------------------------------------------------------------
    goal_templates = [
        ("Design Microservices Architecture", "Architect domain-driven microservices to isolate monolithic payment bottlenecks.", "Technical", "2026-12-15", "Completed", 100),
        ("Achieve AWS Solutions Architect Certification", "Complete AWS Certified Solutions Architect Professional exam.", "Certification", "2026-11-30", "In Progress", 85),
        ("Implement Automated CI/CD Canary Deployments", "Introduce automated canary rollouts with Prometheus metrics validation.", "DevOps", "2026-10-31", "Completed", 100),
        ("Publish Internal API Standards & Guidelines", "Standardize OpenAPI 3.0 contracts and error handling patterns for all services.", "Leadership", "2026-12-31", "In Progress", 60),
        ("Mentor Junior Engineers on Distributed Systems", "Conduct bi-weekly architectural review sessions with junior developers.", "Mentorship", "2026-12-20", "On Track", 75),
    ]
    goal_counter = 1
    # Distribute across employees
    for emp_doc in db.employees.find().limit(20):
        emp_id = emp_doc["employee_id"]
        for g_title, g_desc, g_cat, g_target, g_status, g_pct in goal_templates[:2]:
            db.goals.update_one(
                {"employee_id": emp_id, "title": g_title},
                {"$set": {
                    "id": goal_counter,
                    "employee_id": emp_id,
                    "org_id": DEMO_ORG_ID,
                    "title": g_title,
                    "description": g_desc,
                    "category": g_cat,
                    "target_date": g_target,
                    "status": g_status,
                    "progress_pct": g_pct,
                    "updated_at": now_iso
                }, "$setOnInsert": {"created_at": now_iso}},
                upsert=True
            )
            goal_counter += 1
    counts["goals"] = db.goals.count_documents({})

    # --------------------------------------------------------------------------
    # 6. 30 Performance Assessments
    # --------------------------------------------------------------------------
    assess_counter = 1
    for emp_doc in db.employees.find({"role": {"$ne": "super_admin"}}).limit(30):
        emp_id = emp_doc["employee_id"]
        db.assessments.update_one(
            {"employee_id": emp_id},
            {"$set": {
                "id": assess_counter,
                "employee_id": emp_id,
                "org_id": DEMO_ORG_ID,
                "skill_name": "Core Technical Delivery",
                "score": 4.5 if emp_doc.get("years_experience", 0) >= 4.0 else 4.0,
                "rating": "Exceeds Expectations" if emp_doc.get("years_experience", 0) >= 4.0 else "Meets Expectations",
                "evaluator": "Elena Rostova (Engineering Manager)",
                "feedback": "Demonstrates outstanding consistency in delivering scalable solutions with rigorous testing.",
                "evaluated_at": "2026-10-15",
                "updated_at": now_iso
            }, "$setOnInsert": {"created_at": now_iso}},
            upsert=True
        )
        assess_counter += 1
    counts["assessments"] = db.assessments.count_documents({})

    # --------------------------------------------------------------------------
    # 7. 20 Career Development Plans
    # --------------------------------------------------------------------------
    career_counter = 1
    for emp_doc in db.employees.find().limit(20):
        emp_id = emp_doc["employee_id"]
        db.career_goals.update_one(
            {"employee_id": emp_id},
            {"$set": {
                "id": career_counter,
                "employee_id": emp_id,
                "org_id": DEMO_ORG_ID,
                "target_role": "Lead Cloud Architect" if "Cloud" in emp_doc.get("designation", "") else "Principal Software Engineer",
                "target_level": "Level 4 (Executive Technical Staff)",
                "target_timeline": "6-12 Months",
                "motivation": "Aspire to drive organizational technical vision, mentor architects, and deliver multi-region distributed backends.",
                "readiness_score": 85.0,
                "status": "Active",
                "updated_at": now_iso
            }, "$setOnInsert": {"created_at": now_iso}},
            upsert=True
        )
        career_counter += 1
    counts["career_goals"] = db.career_goals.count_documents({})

    # --------------------------------------------------------------------------
    # 8. 15 Training Programs
    # --------------------------------------------------------------------------
    training_courses = [
        ("Enterprise System Design & Architecture", "Talent Growth Academy", "System Design", 100, 96.0, "Completed"),
        ("Kubernetes & Cloud Infrastructure in Production", "Cloud Native Foundation", "Kubernetes", 85, 88.0, "In Progress"),
        ("Advanced React & State Architecture", "Frontend Masters", "React", 100, 92.0, "Completed"),
        ("Microservices Patterns with Distributed Tracing", "O'Reilly Learning", "Microservices Architecture", 60, 80.0, "In Progress"),
        ("Executive Technical Communication & Roadmaps", "Harvard Business Publishing", "Technical Communication", 100, 95.0, "Completed"),
    ]
    train_counter = 1
    for emp_doc in db.employees.find().limit(15):
        emp_id = emp_doc["employee_id"]
        course = training_courses[(train_counter - 1) % len(training_courses)]
        db.training.update_one(
            {"employee_id": emp_id, "course_title": course[0]},
            {"$set": {
                "id": train_counter,
                "employee_id": emp_id,
                "org_id": DEMO_ORG_ID,
                "course_title": course[0],
                "provider": course[1],
                "target_skill": course[2],
                "status": course[5],
                "completion_pct": course[3],
                "score": course[4],
                "enrolled_date": "2026-08-01",
                "completion_date": "2026-10-15" if course[5] == "Completed" else None,
                "updated_at": now_iso
            }, "$setOnInsert": {"created_at": now_iso}},
            upsert=True
        )
        train_counter += 1
    counts["training"] = db.training.count_documents({})

    # --------------------------------------------------------------------------
    # 9. 30 Feedback & Performance Review Records
    # --------------------------------------------------------------------------
    fb_counter = 1
    for emp_doc in db.employees.find().limit(30):
        emp_id = emp_doc["employee_id"]
        db.feedback.update_one(
            {"employee_id": emp_id},
            {"$set": {
                "id": fb_counter,
                "employee_id": emp_id,
                "org_id": DEMO_ORG_ID,
                "reviewer_name": "Elena Rostova",
                "reviewer_role": "Engineering Manager",
                "performance_score": 4.8,
                "strengths": "Deep architectural judgment, proactive ownership, and high mentorship capability.",
                "areas_for_improvement": "Continue expanding executive cross-functional design review participation.",
                "review_date": "2026-10-15",
                "updated_at": now_iso
            }, "$setOnInsert": {"created_at": now_iso}},
            upsert=True
        )
        fb_counter += 1
    counts["feedback"] = db.feedback.count_documents({})

    # --------------------------------------------------------------------------
    # 10. 20 Notifications
    # --------------------------------------------------------------------------
    for i in range(1, 21):
        db.notifications.update_one(
            {"id": i},
            {"$set": {
                "id": i,
                "user_id": (i % 5) + 1,
                "org_id": DEMO_ORG_ID,
                "title": f"Workforce Update #{i}",
                "message": "Quarterly skill matrix verification review has been published.",
                "category": "Announcement",
                "is_read": (i % 2 == 0),
                "created_at": now_iso
            }},
            upsert=True
        )
    counts["notifications"] = db.notifications.count_documents({})

    # --------------------------------------------------------------------------
    # 11. Organization Configuration Collections
    # --------------------------------------------------------------------------
    configs = {
        "organization_settings": {"company_name": DEMO_ORG_NAME, "allow_self_registration": True, "require_approval": False},
        "organization_career_config": {"enable_ai_coaching": True, "benchmark_model": "10-role-standard"},
        "organization_employee_config": {"auto_assign_emp_id": True, "id_prefix": "EMP"},
        "organization_notification_config": {"email_welcome_enabled": True, "digest_frequency": "weekly"},
        "organization_pdf_config": {"primary_color": "#0F172A", "accent_color": "#1E40AF", "header_title": DEMO_ORG_NAME},
        "organization_performance_config": {"rating_scale": "5-point", "review_cycle": "semi-annual"},
        "organization_security_config": {"password_min_length": 8, "session_timeout_minutes": 60, "mfa_required": False},
        "organization_training_config": {"auto_suggest_courses": True, "provider_whitelist": ["Talent Growth Academy", "O'Reilly"]}
    }
    for cfg_col, cfg_data in configs.items():
        db[cfg_col].update_one(
            {"org_id": DEMO_ORG_ID},
            {"$set": {**cfg_data, "org_id": DEMO_ORG_ID, "updated_at": now_iso}, "$setOnInsert": {"created_at": now_iso}},
            upsert=True
        )
        counts[cfg_col] = db[cfg_col].count_documents({})

    # --------------------------------------------------------------------------
    # 12. Invitation Codes & Membership Requests
    # --------------------------------------------------------------------------
    db.invitation_codes.update_one(
        {"code": "GROWTH2026"},
        {"$set": {
            "id": 1,
            "org_id": DEMO_ORG_ID,
            "code": "GROWTH2026",
            "role": "employee",
            "max_uses": 50,
            "used_count": 12,
            "expires_at": "2027-01-01",
            "status": "Active",
            "created_by": "HR001",
            "updated_at": now_iso
        }, "$setOnInsert": {"created_at": now_iso}},
        upsert=True
    )
    counts["invitation_codes"] = db.invitation_codes.count_documents({})

    # 17. Sync sequence counters to prevent collision on subsequent user registrations
    for seq_name, max_val in [
        ("users", 45), ("employees", 45), ("departments", 15), ("skills", 35),
        ("employee_skills", 200), ("goals", 50), ("assessments", 50),
        ("career_goals", 30), ("training", 25), ("feedback", 40), ("notifications", 30)
    ]:
        db.counters.update_one({"_id": seq_name}, {"$max": {"seq": max_val}}, upsert=True)

    print("\nDEMO DATA SEEDING SUMMARY:")
    for k, v in counts.items():
        print(f"  - {k}: {v} records")
    print("=" * 70)
    print("SUCCESS: All demo collections seeded and ready for production verification!")
    print("DEMO CREDENTIALS FOR TESTING:")
    print("  - Super Admin : admin@demo.com    / Demo@2026!")
    print("  - HR Admin    : hr@demo.com       / Demo@2026!")
    print("  - Manager     : manager@demo.com  / Demo@2026!")
    print("  - Employee    : employee@demo.com / Demo@2026!")
    print("=" * 70)
    return counts


if __name__ == "__main__":
    seed_demo_dataset()
