"""
Seed Script for MongoDB Atlas - Talent Management & Career Growth Platform
Populates all 15 MongoDB collections with high-quality, realistic enterprise sample data:
- 2 HR/Admin users
- 5 Managers
- 30 Employees
- 10 Departments
- 25 Technical and Soft Skills
- 40 Employee Goals
- 30 Performance Assessments
- 20 Career Development Plans
- 15 Training Programs
- 30 Feedback Records
- 20 Notifications
- Membership Requests, Invitation Codes, Email Logs, and Organization Settings
"""

from __future__ import annotations
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.db import get_db, init_mongo_indexes, check_db_health, is_mock_mode, save_mock_store
from services.core import hash_password


def seed_mongodb():
    print("=" * 75)
    print("🌱 SEEDING MONGODB ATLAS: Talent Management & Career Growth Platform")
    print("=" * 75)

    db = get_db()
    health = check_db_health()
    print(f"Connected Engine: {health['engine']}")
    print(f"Target Database:  {health['database']}")
    print(f"Host Endpoint:    {health['host']}")
    print(f"Emulated Mode:    {health['mock_mode']}\n")

    # Ensure indexes are established
    print("Ensuring unique and compound indexes...")
    init_mongo_indexes()

    org_id = "ORG-TALENT-01"
    now_iso = datetime.now(timezone.utc).isoformat()

    # --------------------------------------------------------------------------
    # 1. ORGANIZATION SETTINGS
    # --------------------------------------------------------------------------
    print("1. Seeding organization_settings collection...")
    db.organization_settings.delete_many({"org_id": org_id})
    db.organization_settings.insert_one({
        "org_id": org_id,
        "name": "TalentGrowth Enterprise Technologies",
        "org_name": "TalentGrowth Enterprise Technologies",
        "official_email": "hr@talentgrowth.com",
        "contact_number": "+1 (555) 019-2834",
        "address": "100 Innovation Way, Suite 400, San Francisco, CA 94105",
        "website": "https://www.talentgrowth.com",
        "industry": "Enterprise Software & Cloud Platforms",
        "description": "Enterprise-grade talent intelligence, succession planning, and workforce growth platform.",
        "status": "Active",
        "logo_base64": "",
        "theme_color": "Navy & Teal",
        "created_at": now_iso,
        "updated_at": now_iso
    })

    # --------------------------------------------------------------------------
    # 2. DEPARTMENTS (10 Departments)
    # --------------------------------------------------------------------------
    print("2. Seeding departments collection (10 departments)...")
    db.departments.delete_many({})
    departments_data = [
        {"department_id": "DEP001", "name": "Engineering", "head_id": "EMP003", "budget": 750000.0, "description": "Platform architecture, frontend/backend engineering, and distributed systems."},
        {"department_id": "DEP002", "name": "Product Management", "head_id": "EMP004", "budget": 400000.0, "description": "Product strategy, user personas, roadmaps, and business alignment."},
        {"department_id": "DEP003", "name": "Data Science & AI", "head_id": "EMP005", "budget": 600000.0, "description": "Machine learning, LLM fine-tuning, predictive modeling, and data pipelines."},
        {"department_id": "DEP004", "name": "UI/UX Design", "head_id": "EMP006", "budget": 350000.0, "description": "Design systems, user experience research, interaction design, and usability."},
        {"department_id": "DEP005", "name": "Quality Assurance", "head_id": "EMP007", "budget": 300000.0, "description": "Automated regression testing, load testing, and continuous verification."},
        {"department_id": "DEP006", "name": "Human Resources", "head_id": "EMP002", "budget": 250000.0, "description": "Talent acquisition, employee enablement, benefits, and culture."},
        {"department_id": "DEP007", "name": "DevOps & Cloud Infrastructure", "head_id": "EMP003", "budget": 500000.0, "description": "Cloud orchestration, Kubernetes, CI/CD, and site reliability."},
        {"department_id": "DEP008", "name": "Information Security", "head_id": "EMP003", "budget": 450000.0, "description": "Application security, penetration testing, compliance, and threat mitigation."},
        {"department_id": "DEP009", "name": "Marketing & Growth", "head_id": "EMP004", "budget": 350000.0, "description": "Product marketing, client acquisition, brand advocacy, and outbound reach."},
        {"department_id": "DEP010", "name": "Finance & Operations", "head_id": "EMP001", "budget": 400000.0, "description": "Financial planning, accounting, operational efficiency, and auditing."}
    ]
    for d in departments_data:
        d["org_id"] = org_id
        d["created_at"] = now_iso
    db.departments.insert_many(departments_data)

    # --------------------------------------------------------------------------
    # 3. SKILLS (25 Technical and Soft Skills)
    # --------------------------------------------------------------------------
    print("3. Seeding skills collection (25 skills)...")
    db.skills.delete_many({})
    skills_data = [
        # Technical (15)
        {"id": 1, "name": "Python", "category": "Technical", "description": "Backend services, data analysis, scripting, and web frameworks (FastAPI/Django)."},
        {"id": 2, "name": "React.js", "category": "Technical", "description": "Modern component architectures, hooks, state management, and responsive frontends."},
        {"id": 3, "name": "TypeScript", "category": "Technical", "description": "Type-safe JavaScript for scalable frontend and Node.js applications."},
        {"id": 4, "name": "Docker & Containers", "category": "Technical", "description": "Container packaging, multi-stage builds, and local development environments."},
        {"id": 5, "name": "Kubernetes", "category": "Technical", "description": "Container orchestration, ingress controllers, microservice deployments, and scaling."},
        {"id": 6, "name": "AWS Cloud Services", "category": "Technical", "description": "EC2, S3, RDS, Lambda, ECS, and cloud infrastructure management."},
        {"id": 7, "name": "MongoDB & NoSQL", "category": "Technical", "description": "Document schema modeling, aggregation pipelines, indexing, and Atlas operations."},
        {"id": 8, "name": "Machine Learning & PyTorch", "category": "Technical", "description": "Model architecture, deep learning, PyTorch workflows, and evaluation."},
        {"id": 9, "name": "Node.js", "category": "Technical", "description": "Asynchronous backend runtimes, REST/GraphQL APIs, and microservices."},
        {"id": 10, "name": "GraphQL APIs", "category": "Technical", "description": "Schema definition, queries, mutations, resolvers, and federation."},
        {"id": 11, "name": "CI/CD Automation", "category": "Technical", "description": "GitHub Actions, GitLab CI, automated test runs, and release deployment pipelines."},
        {"id": 12, "name": "System Architecture & Microservices", "category": "Technical", "description": "Distributed systems, event-driven design, caching, and resiliency patterns."},
        {"id": 13, "name": "Go Programming", "category": "Technical", "description": "High-concurrency systems, low-latency microservices, and network tooling."},
        {"id": 14, "name": "Terraform & IaC", "category": "Technical", "description": "Declarative infrastructure as code, cloud provisioning, and state management."},
        {"id": 15, "name": "Cybersecurity & SecOps", "category": "Technical", "description": "OWASP defense, threat modeling, vulnerability scanning, and IAM governance."},
        # Soft Skills & Leadership (10)
        {"id": 16, "name": "Agile Project Management", "category": "Soft Skills", "description": "Sprint planning, backlog grooming, velocity tracking, and Scrum facilitation."},
        {"id": 17, "name": "Technical Leadership & Mentorship", "category": "Soft Skills", "description": "Guiding junior engineers, code review quality, and technical vision."},
        {"id": 18, "name": "Strategic Roadmapping", "category": "Soft Skills", "description": "Translating business goals into actionable engineering deliverables and milestones."},
        {"id": 19, "name": "Cross-functional Collaboration", "category": "Soft Skills", "description": "Seamless communication across engineering, product, design, and operations."},
        {"id": 20, "name": "Critical Problem Solving", "category": "Soft Skills", "description": "Analytical root cause identification and strategic incident remediation."},
        {"id": 21, "name": "Stakeholder Communication", "category": "Soft Skills", "description": "Presenting complex technical concepts to executive and non-technical partners."},
        {"id": 22, "name": "Data-Driven Decision Making", "category": "Soft Skills", "description": "Using metrics, KPIs, and user telemetry to inform development priorities."},
        {"id": 23, "name": "Conflict Resolution", "category": "Soft Skills", "description": "De-escalating team tensions and aligning divergent viewpoints productively."},
        {"id": 24, "name": "Public Speaking & Presentation", "category": "Soft Skills", "description": "Delivering compelling architecture reviews, demos, and tech talks."},
        {"id": 25, "name": "Performance Coaching", "category": "Soft Skills", "description": "Conducting 1-on-1s, goal alignment, and career path progression guidance."}
    ]
    for s in skills_data:
        s["created_at"] = now_iso
    db.skills.insert_many(skills_data)

    # --------------------------------------------------------------------------
    # 4. USERS & EMPLOYEES (2 HR/Admins, 5 Managers, 30 Employees)
    # --------------------------------------------------------------------------
    print("4. Seeding users and employees (2 Admins, 5 Managers, 30 Employees)...")
    db.users.delete_many({})
    db.employees.delete_many({})

    # Hash default password with bcrypt
    default_pwd_hash, default_salt = hash_password("TalentGrowth@2025!")

    # Define Admins and Managers
    leadership_roster = [
        # Admins (2)
        {"id": 1, "name": "Eleanor Vance", "email": "admin@talentgrowth.com", "role": "admin", "emp_id": "EMP001", "dept": "Finance & Operations", "title": "VP of Operations & Administrator", "exp": 12.0, "mgr_id": None},
        {"id": 2, "name": "Marcus Sterling", "email": "hr.lead@talentgrowth.com", "role": "admin", "emp_id": "EMP002", "dept": "Human Resources", "title": "Head of People & Talent Strategy", "exp": 10.5, "mgr_id": "EMP001"},
        # Managers (5)
        {"id": 3, "name": "David Chen", "email": "manager.eng@talentgrowth.com", "role": "manager", "emp_id": "EMP003", "dept": "Engineering", "title": "Engineering Director", "exp": 11.0, "mgr_id": "EMP001"},
        {"id": 4, "name": "Sarah Jenkins", "email": "manager.product@talentgrowth.com", "role": "manager", "emp_id": "EMP004", "dept": "Product Management", "title": "VP of Product", "exp": 9.5, "mgr_id": "EMP001"},
        {"id": 5, "name": "Vikram Patel", "email": "manager.data@talentgrowth.com", "role": "manager", "emp_id": "EMP005", "dept": "Data Science & AI", "title": "Head of AI & Data Systems", "exp": 10.0, "mgr_id": "EMP001"},
        {"id": 6, "name": "Elena Rostova", "email": "manager.design@talentgrowth.com", "role": "manager", "emp_id": "EMP006", "dept": "UI/UX Design", "title": "Design Director", "exp": 9.0, "mgr_id": "EMP001"},
        {"id": 7, "name": "Robert Taylor", "email": "manager.qa@talentgrowth.com", "role": "manager", "emp_id": "EMP007", "dept": "Quality Assurance", "title": "QA Director", "exp": 8.5, "mgr_id": "EMP003"},
    ]

    # Define 30 Employees (EMP011 to EMP040)
    employee_roster = [
        {"id": 11, "emp_id": "EMP011", "name": "Alex Morgan", "email": "emp011@talentgrowth.com", "dept": "Engineering", "title": "Senior Backend Engineer", "exp": 6.5, "mgr_id": "EMP003", "skills": "Python, Docker & Containers, PostgreSQL, System Architecture"},
        {"id": 12, "emp_id": "EMP012", "name": "Priya Sharma", "email": "emp012@talentgrowth.com", "dept": "Engineering", "title": "Frontend Lead", "exp": 7.0, "mgr_id": "EMP003", "skills": "React.js, TypeScript, GraphQL APIs, UI/UX Design"},
        {"id": 13, "emp_id": "EMP013", "name": "Marcus Reynolds", "email": "emp013@talentgrowth.com", "dept": "Engineering", "title": "Full Stack Engineer", "exp": 4.0, "mgr_id": "EMP003", "skills": "Node.js, React.js, Python, MongoDB"},
        {"id": 14, "emp_id": "EMP014", "name": "Sophia Chen", "email": "emp014@talentgrowth.com", "dept": "Product Management", "title": "Senior Product Manager", "exp": 6.0, "mgr_id": "EMP004", "skills": "Strategic Roadmapping, Agile Project Management, Data-Driven Decision Making"},
        {"id": 15, "emp_id": "EMP015", "name": "Carlos Gomez", "email": "emp015@talentgrowth.com", "dept": "Product Management", "title": "Associate Product Manager", "exp": 2.5, "mgr_id": "EMP004", "skills": "User Stories, Agile, Market Research, JIRA"},
        {"id": 16, "emp_id": "EMP016", "name": "Jordan Lee", "email": "emp016@talentgrowth.com", "dept": "Data Science & AI", "title": "Principal ML Engineer", "exp": 8.5, "mgr_id": "EMP005", "skills": "Machine Learning & PyTorch, Python, LLM Tuning, Model Serving"},
        {"id": 17, "emp_id": "EMP017", "name": "Emily Watson", "email": "emp017@talentgrowth.com", "dept": "Data Science & AI", "title": "Senior Data Scientist", "exp": 5.5, "mgr_id": "EMP005", "skills": "Python, Statistical Modeling, SQL, Feature Engineering"},
        {"id": 18, "emp_id": "EMP018", "name": "Aisha Khan", "email": "emp018@talentgrowth.com", "dept": "UI/UX Design", "title": "Lead UX Designer", "exp": 6.0, "mgr_id": "EMP006", "skills": "Design Systems, Figma, User Research, Wireframing"},
        {"id": 19, "emp_id": "EMP019", "name": "Lucas Silva", "email": "emp019@talentgrowth.com", "dept": "UI/UX Design", "title": "Interaction Designer", "exp": 3.5, "mgr_id": "EMP006", "skills": "Prototyping, Usability Testing, Visual Design, HTML/CSS"},
        {"id": 20, "emp_id": "EMP020", "name": "Olivia Taylor", "email": "emp020@talentgrowth.com", "dept": "Quality Assurance", "title": "Senior SDET", "exp": 5.0, "mgr_id": "EMP007", "skills": "Playwright, Python, API Automation, CI/CD"},
        {"id": 21, "emp_id": "EMP021", "name": "Liam Brown", "email": "emp021@talentgrowth.com", "dept": "Quality Assurance", "title": "QA Automation Engineer", "exp": 3.0, "mgr_id": "EMP007", "skills": "Cypress, Selenium, Postman, Performance Testing"},
        {"id": 22, "emp_id": "EMP022", "name": "Chloe Dubois", "email": "emp022@talentgrowth.com", "dept": "Human Resources", "title": "Talent Acquisition Partner", "exp": 4.5, "mgr_id": "EMP002", "skills": "Technical Sourcing, Candidate Experience, Interview Coaching"},
        {"id": 23, "emp_id": "EMP023", "name": "Noah Davis", "email": "emp023@talentgrowth.com", "dept": "Human Resources", "title": "People Operations Specialist", "exp": 3.0, "mgr_id": "EMP002", "skills": "Employee Onboarding, HRIS, Benefits Administration"},
        {"id": 24, "emp_id": "EMP024", "name": "Isabella Martinez", "email": "emp024@talentgrowth.com", "dept": "DevOps & Cloud Infrastructure", "title": "Senior Cloud Architect", "exp": 8.0, "mgr_id": "EMP003", "skills": "Kubernetes, AWS Cloud Services, Terraform, Microservices"},
        {"id": 25, "emp_id": "EMP025", "name": "Ethan Wilson", "email": "emp025@talentgrowth.com", "dept": "DevOps & Cloud Infrastructure", "title": "DevOps Engineer", "exp": 4.0, "mgr_id": "EMP003", "skills": "Docker, CI/CD Automation, Linux, Helm"},
        {"id": 26, "emp_id": "EMP026", "name": "Maya Patel", "email": "emp026@talentgrowth.com", "dept": "Information Security", "title": "Senior AppSec Engineer", "exp": 6.0, "mgr_id": "EMP003", "skills": "OWASP, Vulnerability Assessment, Threat Modeling, Python"},
        {"id": 27, "emp_id": "EMP027", "name": "Oliver Green", "email": "emp027@talentgrowth.com", "dept": "Information Security", "title": "Security Compliance Analyst", "exp": 3.5, "mgr_id": "EMP003", "skills": "SOC2, ISO 27001, Access Control, Auditing"},
        {"id": 28, "emp_id": "EMP028", "name": "Ava Campbell", "email": "emp028@talentgrowth.com", "dept": "Marketing & Growth", "title": "Product Marketing Lead", "exp": 5.5, "mgr_id": "EMP004", "skills": "Content Marketing, Product Launch, Competitive Intelligence"},
        {"id": 29, "emp_id": "EMP029", "name": "Leo Anderson", "email": "emp029@talentgrowth.com", "dept": "Marketing & Growth", "title": "Growth Marketing Specialist", "exp": 3.0, "mgr_id": "EMP004", "skills": "SEO, Analytics, User Acquisition, Campaign Optimization"},
        {"id": 30, "emp_id": "EMP030", "name": "Mia Thomas", "email": "emp030@talentgrowth.com", "dept": "Finance & Operations", "title": "Senior Financial Analyst", "exp": 6.0, "mgr_id": "EMP001", "skills": "Financial Modeling, Forecasting, Budget Allocation, Excel"},
        {"id": 31, "emp_id": "EMP031", "name": "Jack White", "email": "emp031@talentgrowth.com", "dept": "Engineering", "title": "Cloud Database Engineer", "exp": 4.5, "mgr_id": "EMP003", "skills": "MongoDB, PostgreSQL, Database Sharding, Performance Tuning"},
        {"id": 32, "emp_id": "EMP032", "name": "Harper Lewis", "email": "emp032@talentgrowth.com", "dept": "Engineering", "title": "Mobile Engineer", "exp": 4.0, "mgr_id": "EMP003", "skills": "React Native, TypeScript, iOS/Android SDKs"},
        {"id": 33, "emp_id": "EMP033", "name": "Daniel Hall", "email": "emp033@talentgrowth.com", "dept": "Data Science & AI", "title": "Data Platform Engineer", "exp": 5.0, "mgr_id": "EMP005", "skills": "Apache Spark, Kafka, Data Warehousing, Python"},
        {"id": 34, "emp_id": "EMP034", "name": "Amelia Clark", "email": "emp034@talentgrowth.com", "dept": "UI/UX Design", "title": "Senior User Researcher", "exp": 5.0, "mgr_id": "EMP006", "skills": "Qualitative Research, Persona Mapping, Journey Mapping"},
        {"id": 35, "emp_id": "EMP035", "name": "Mason Allen", "email": "emp035@talentgrowth.com", "dept": "Quality Assurance", "title": "Performance Test Engineer", "exp": 4.0, "mgr_id": "EMP007", "skills": "k6, JMeter, Distributed Load Testing, Monitoring"},
        {"id": 36, "emp_id": "EMP036", "name": "Evelyn Young", "email": "emp036@talentgrowth.com", "dept": "Human Resources", "title": "Learning & Development Specialist", "exp": 4.0, "mgr_id": "EMP002", "skills": "Training Design, Workshop Facilitation, Competency Frameworks"},
        {"id": 37, "emp_id": "EMP037", "name": "Logan Wright", "email": "emp037@talentgrowth.com", "dept": "DevOps & Cloud Infrastructure", "title": "Site Reliability Engineer", "exp": 5.0, "mgr_id": "EMP003", "skills": "Prometheus, Grafana, Incident Response, Chaos Engineering"},
        {"id": 38, "emp_id": "EMP038", "name": "Charlotte Scott", "email": "emp038@talentgrowth.com", "dept": "Information Security", "title": "Threat Intelligence Analyst", "exp": 4.5, "mgr_id": "EMP003", "skills": "SIEM, Incident Response, Log Analysis, Zero Trust"},
        {"id": 39, "emp_id": "EMP039", "name": "Benjamin King", "email": "emp039@talentgrowth.com", "dept": "Marketing & Growth", "title": "Content Strategy Specialist", "exp": 3.5, "mgr_id": "EMP004", "skills": "Technical Copywriting, Product Documentation, Social Strategy"},
        {"id": 40, "emp_id": "EMP040", "name": "Harper Hill", "email": "emp040@talentgrowth.com", "dept": "Finance & Operations", "title": "Operations & Payroll Accountant", "exp": 4.0, "mgr_id": "EMP001", "skills": "Payroll Compliance, Operational Auditing, ERP Systems"}
    ]

    all_users = []
    all_employees = []

    # Insert leadership
    for leader in leadership_roster:
        all_users.append({
            "id": leader["id"],
            "name": leader["name"],
            "email": leader["email"],
            "password_hash": default_pwd_hash,
            "salt": default_salt,
            "role": leader["role"],
            "employee_id": leader["emp_id"],
            "org_id": org_id,
            "account_type": "Organization",
            "department": leader["dept"],
            "job_title": leader["title"],
            "status": "Active",
            "date_joined": "2023-01-10",
            "created_at": now_iso
        })
        all_employees.append({
            "id": leader["id"],
            "employee_id": leader["emp_id"],
            "org_id": org_id,
            "user_id": leader["id"],
            "name": leader["name"],
            "email": leader["email"],
            "phone": "+1 (555) 010-000" + str(leader["id"]),
            "department": leader["dept"],
            "designation": leader["title"],
            "joining_date": "2023-01-10",
            "employment_status": "Active",
            "years_experience": leader["exp"],
            "primary_skills": "Executive Leadership, Strategic Planning, Talent Mentorship",
            "account_status": "Active",
            "manager_id": leader["mgr_id"],
            "created_at": now_iso,
            "updated_at": now_iso
        })

    # Insert 30 employees
    for emp in employee_roster:
        all_users.append({
            "id": emp["id"],
            "name": emp["name"],
            "email": emp["email"],
            "password_hash": default_pwd_hash,
            "salt": default_salt,
            "role": "employee",
            "employee_id": emp["emp_id"],
            "org_id": org_id,
            "account_type": "Organization",
            "department": emp["dept"],
            "job_title": emp["title"],
            "status": "Active",
            "date_joined": "2023-04-15",
            "created_at": now_iso
        })
        all_employees.append({
            "id": emp["id"],
            "employee_id": emp["emp_id"],
            "org_id": org_id,
            "user_id": emp["id"],
            "name": emp["name"],
            "email": emp["email"],
            "phone": "+1 (555) 020-00" + str(emp["id"]),
            "department": emp["dept"],
            "designation": emp["title"],
            "joining_date": "2023-04-15",
            "employment_status": "Active",
            "years_experience": emp["exp"],
            "primary_skills": emp["skills"],
            "account_status": "Active",
            "manager_id": emp["mgr_id"],
            "created_at": now_iso,
            "updated_at": now_iso
        })

    db.users.insert_many(all_users)
    db.employees.insert_many(all_employees)

    # --------------------------------------------------------------------------
    # 5. EMPLOYEE SKILLS
    # --------------------------------------------------------------------------
    print("5. Seeding employee_skills collection...")
    db.employee_skills.delete_many({})
    emp_skills_data = []
    skill_names_tech = ["Python", "React.js", "TypeScript", "Docker & Containers", "Kubernetes", "AWS Cloud Services", "MongoDB & NoSQL", "CI/CD Automation"]
    skill_names_soft = ["Agile Project Management", "Technical Leadership & Mentorship", "Critical Problem Solving", "Cross-functional Collaboration", "Stakeholder Communication"]

    idx = 1
    for emp in employee_roster:
        # Give each employee 2-3 technical skills and 1-2 soft skills
        t_skills = [skill_names_tech[(emp["id"] + i) % len(skill_names_tech)] for i in range(3)]
        s_skills = [skill_names_soft[(emp["id"] + j) % len(skill_names_soft)] for j in range(2)]

        for sname in t_skills:
            prof = "Expert" if emp["exp"] >= 6 else ("Advanced" if emp["exp"] >= 4 else "Intermediate")
            emp_skills_data.append({
                "id": idx,
                "employee_id": emp["emp_id"],
                "org_id": org_id,
                "user_id": emp["id"],
                "skill_name": sname,
                "category": "Technical",
                "proficiency_level": prof,
                "years_exp": round(emp["exp"] * 0.8, 1),
                "verified": 1,
                "last_updated": now_iso
            })
            idx += 1

        for sname in s_skills:
            emp_skills_data.append({
                "id": idx,
                "employee_id": emp["emp_id"],
                "org_id": org_id,
                "user_id": emp["id"],
                "skill_name": sname,
                "category": "Soft Skills",
                "proficiency_level": "Advanced" if emp["exp"] >= 5 else "Intermediate",
                "years_exp": round(emp["exp"] * 0.7, 1),
                "verified": 1,
                "last_updated": now_iso
            })
            idx += 1

    db.employee_skills.insert_many(emp_skills_data)

    # --------------------------------------------------------------------------
    # 6. GOALS (40 Goals)
    # --------------------------------------------------------------------------
    print("6. Seeding goals collection (40 employee goals)...")
    db.goals.delete_many({})
    goal_templates = [
        ("Deliver Microservices Migration", "Refactor monolith endpoints into decoupled Go/Python microservices.", "2025-06-30", 75, "In Progress"),
        ("Kubernetes Cluster Hardening", "Implement network policies, RBAC security gates, and automated image scanning.", "2025-04-15", 100, "Completed"),
        ("Improve End-to-End Test Automation", "Expand Playwright test suites to reach 90% core flow code coverage.", "2025-05-31", 50, "In Progress"),
        ("Optimize Atlas Query Performance", "Conduct explain-plan analysis on slow MongoDB collections and build compound indexes.", "2025-03-31", 100, "Completed"),
        ("Adopt Design Tokens in UI Framework", "Migrate all legacy CSS variables to unified cross-platform design tokens.", "2025-07-31", 25, "In Progress"),
        ("Launch Employee Career Pathing Portal", "Finalize enterprise succession planning workflows and role readiness matrix.", "2025-05-15", 75, "In Progress"),
        ("Zero-Trust IAM Policy Audit", "Review least-privilege roles across AWS production and staging clusters.", "2025-04-30", 100, "Completed"),
        ("Implement Predictive Retention Modeling", "Develop churn forecasting algorithm with PyTorch using historical metrics.", "2025-08-31", 50, "In Progress"),
        ("Complete SOC2 Type II Certification", "Gather evidence logs, security access reviews, and remediation artifacts.", "2025-06-15", 75, "In Progress"),
        ("Technical Mentorship Onboarding Sprint", "Coach 2 junior engineers through code review standards and production deploy flows.", "2025-03-15", 100, "Completed")
    ]
    goals_data = []
    g_id = 1
    for i in range(40):
        emp = employee_roster[i % len(employee_roster)]
        tmpl = goal_templates[i % len(goal_templates)]
        goals_data.append({
            "id": g_id,
            "user_id": emp["id"],
            "employee_id": emp["emp_id"],
            "org_id": org_id,
            "title": f"{tmpl[0]} (Phase {1 + (i // 10)})",
            "description": tmpl[1],
            "target_date": tmpl[2],
            "progress": tmpl[3],
            "status": tmpl[4],
            "created_at": now_iso,
            "updated_at": now_iso
        })
        g_id += 1
    db.goals.insert_many(goals_data)

    # --------------------------------------------------------------------------
    # 7. ASSESSMENTS (30 Assessments)
    # --------------------------------------------------------------------------
    print("7. Seeding assessments collection (30 assessments)...")
    db.assessments.delete_many({})
    assessments_data = []
    assess_skills = [
        ("Python Architecture", "Technical", 92.5),
        ("React.js State & Performance", "Technical", 88.0),
        ("Kubernetes Pod Scheduling", "Technical", 85.0),
        ("System Architecture Design", "Technical", 94.0),
        ("MongoDB Query Optimization", "Technical", 90.0),
        ("Agile Scrum Leadership", "Soft Skills", 89.5),
        ("CI/CD Automation Pipelines", "Technical", 91.0),
        ("Cross-functional Alignment", "Soft Skills", 87.0),
        ("Cybersecurity AppSec Review", "Technical", 95.0),
        ("Strategic Product Roadmapping", "Soft Skills", 93.0)
    ]
    for i in range(30):
        emp = employee_roster[i % len(employee_roster)]
        askill = assess_skills[i % len(assess_skills)]
        score_val = round(askill[2] - (i % 5) * 1.5, 1)
        assessments_data.append({
            "id": i + 1,
            "user_id": emp["id"],
            "employee_id": emp["emp_id"],
            "org_id": org_id,
            "category": askill[1],
            "skill_name": askill[0],
            "score": score_val,
            "max_score": 100.0,
            "passed": 1 if score_val >= 70.0 else 0,
            "notes": f"Evaluation verified by technical evaluation committee. Strong proficiency demonstrated in {askill[0]}.",
            "created_at": now_iso
        })
    db.assessments.insert_many(assessments_data)

    # --------------------------------------------------------------------------
    # 8. CAREER GOALS / DEVELOPMENT PLANS (20 Plans)
    # --------------------------------------------------------------------------
    print("8. Seeding career_goals collection (20 career development plans)...")
    db.career_goals.delete_many({})
    career_plans_templates = [
        ("Senior Backend Engineer", "Lead Cloud Architect", "Principal", "6-12 months", "Target transition into distributed architecture oversight and cloud strategy."),
        ("Frontend Lead", "Engineering Manager", "Lead", "1-2 years", "Shift into engineering team leadership, headcount forecasting, and execution."),
        ("Full Stack Engineer", "Senior Full Stack Architect", "Senior", "6-12 months", "Deepen event-driven microservices expertise and modern data schemas."),
        ("Senior Product Manager", "Director of Product Strategy", "Director", "1-2 years", "Own multi-product portfolio roadmaps and executive revenue alignment."),
        ("Associate Product Manager", "Product Manager", "Mid-Level", "3-6 months", "Drive end-to-end user story lifecycle and customer sprint discovery."),
        ("Principal ML Engineer", "Head of AI Research & Platforms", "Director", "1-2 years", "Scale company-wide generative AI models and data governance frameworks."),
        ("Senior Data Scientist", "Lead AI Research Scientist", "Lead", "6-12 months", "Publish proprietary LLM benchmarks and drive autonomous agent tooling."),
        ("Lead UX Designer", "Head of Product Design", "Director", "1-2 years", "Lead cross-platform design system and global design research."),
        ("Interaction Designer", "Senior UX/UI Designer", "Senior", "6-12 months", "Advance high-fidelity design prototyping and accessibility compliance."),
        ("Senior SDET", "QA Architecture Manager", "Lead", "6-12 months", "Orchestrate multi-region automated testing and quality gates.")
    ]
    career_goals_data = []
    for i in range(20):
        emp = employee_roster[i]
        tmpl = career_plans_templates[i % len(career_plans_templates)]
        prog_vals = [25, 50, 75, 100]
        status_vals = ["In Progress", "In Progress", "In Progress", "Completed"]
        career_goals_data.append({
            "id": i + 1,
            "user_id": emp["id"],
            "employee_id": emp["emp_id"],
            "org_id": org_id,
            "title": f"Advancement to {tmpl[1]}",
            "current_role": emp["title"],
            "target_role": tmpl[1],
            "target_level": tmpl[2],
            "target_timeline": tmpl[3],
            "target_designation": tmpl[1],
            "description": tmpl[4],
            "target_date": "2025-12-31",
            "progress": prog_vals[i % 4],
            "status": status_vals[i % 4],
            "action_items": [
                {"item": "Complete advanced architecture certification", "done": True},
                {"item": "Lead quarterly technical milestone design review", "done": i % 2 == 0},
                {"item": "Conduct 2 cross-functional mentoring cycles", "done": False}
            ],
            "created_at": now_iso,
            "updated_at": now_iso
        })
    db.career_goals.insert_many(career_goals_data)

    # --------------------------------------------------------------------------
    # 9. TRAINING (15 Programs)
    # --------------------------------------------------------------------------
    print("9. Seeding training collection (15 programs)...")
    db.training.delete_many({})
    training_programs = [
        {"training_id": "TRN001", "course_name": "Advanced Cloud Architecture on AWS", "category": "Technical", "provider": "AWS Enterprise Academy", "duration_hours": 40, "target_skill": "AWS Cloud Services"},
        {"training_id": "TRN002", "course_name": "Production Microservices with Go and Kubernetes", "category": "Technical", "provider": "Cloud Native Academy", "duration_hours": 36, "target_skill": "Kubernetes"},
        {"training_id": "TRN003", "course_name": "Deep Learning & LLM Fine-Tuning with PyTorch", "category": "Technical", "provider": "Stanford Online Enterprise", "duration_hours": 50, "target_skill": "Machine Learning & PyTorch"},
        {"training_id": "TRN004", "course_name": "Full Stack React & TypeScript Mastery", "category": "Technical", "provider": "Frontend Masters", "duration_hours": 30, "target_skill": "React.js"},
        {"training_id": "TRN005", "course_name": "Modern MongoDB Data Modeling & Aggregation", "category": "Technical", "provider": "MongoDB University", "duration_hours": 24, "target_skill": "MongoDB & NoSQL"},
        {"training_id": "TRN006", "course_name": "Secure Coding & OWASP Top 10 Defense", "category": "Technical", "provider": "Snyk Learning", "duration_hours": 20, "target_skill": "Cybersecurity & SecOps"},
        {"training_id": "TRN007", "course_name": "Terraform Enterprise Infrastructure as Code", "category": "Technical", "provider": "HashiCorp Learning", "duration_hours": 28, "target_skill": "Terraform & IaC"},
        {"training_id": "TRN008", "course_name": "CI/CD Pipeline Automation with GitHub Actions", "category": "Technical", "provider": "Internal Academy", "duration_hours": 18, "target_skill": "CI/CD Automation"},
        {"training_id": "TRN009", "course_name": "Agile Product Leadership & Roadmapping", "category": "Leadership", "provider": "Pragmatic Institute", "duration_hours": 25, "target_skill": "Agile Project Management"},
        {"training_id": "TRN010", "course_name": "Design Systems at Scale with Figma", "category": "Design", "provider": "Nielsen Norman Group", "duration_hours": 24, "target_skill": "UI/UX Design"},
        {"training_id": "TRN011", "course_name": "Test Automation Architectures with Playwright", "category": "QA", "provider": "Ministry of Testing", "duration_hours": 22, "target_skill": "Quality Assurance"},
        {"training_id": "TRN012", "course_name": "Strategic Talent Management & People Analytics", "category": "HR", "provider": "SHRM Enterprise", "duration_hours": 30, "target_skill": "Human Resources"},
        {"training_id": "TRN013", "course_name": "Executive Communication & Stakeholder Influence", "category": "Soft Skills", "provider": "Harvard ManageMentor", "duration_hours": 16, "target_skill": "Stakeholder Communication"},
        {"training_id": "TRN014", "course_name": "Conflict Resolution & High-Performing Teams", "category": "Soft Skills", "provider": "Internal Academy", "duration_hours": 12, "target_skill": "Conflict Resolution"},
        {"training_id": "TRN015", "course_name": "Enterprise Data Privacy & SOC2 Compliance", "category": "Compliance", "provider": "ComplianceOne", "duration_hours": 10, "target_skill": "Cybersecurity & SecOps"}
    ]
    for idx, tp in enumerate(training_programs):
        emp = employee_roster[idx % len(employee_roster)]
        tp["id"] = idx + 1
        tp["employee_id"] = emp["emp_id"]
        tp["org_id"] = org_id
        tp["status"] = "Completed" if idx % 2 == 0 else "In Progress"
        tp["score"] = 92.0 if idx % 2 == 0 else 0.0
        tp["target_completion_date"] = "2025-06-30"
        tp["created_at"] = now_iso
    db.training.insert_many(training_programs)

    # --------------------------------------------------------------------------
    # 10. FEEDBACK / PERFORMANCE REVIEWS (30 Records)
    # --------------------------------------------------------------------------
    print("10. Seeding feedback collection (30 feedback records)...")
    db.feedback.delete_many({})
    feedback_data = []
    feedback_notes = [
        ("Exceptional contribution to the distributed architecture revamp. Demonstrates strong technical leadership.", "Scalable systems design, cross-team mentoring", "Continue delegating operational tasks to junior team members.", 4.8),
        ("Consistent high delivery cadence. Maintained zero critical defects on all production deployments.", "Attention to detail, proactive testing", "Take on larger technical roadmapping ownership.", 4.6),
        ("Outstanding product vision and user empathy. Significantly improved sprint delivery clarity.", "User story precision, stakeholder transparency", "Deepen data analytics usage in feature prioritization.", 4.7),
        ("Transformed our cloud orchestration reliability. Reduced deployment downtime by 40%.", "Infrastructure automation, Kubernetes proficiency", "Document incident response playbooks for tier-1 support.", 4.9),
        ("Drove design token harmonization across web and mobile surfaces with high aesthetic polish.", "Component library design, empathy for end-users", "Conduct earlier UX syncs with backend engineering leads.", 4.5)
    ]
    for i in range(30):
        emp = employee_roster[i]
        tmpl = feedback_notes[i % len(feedback_notes)]
        feedback_data.append({
            "id": i + 1,
            "employee_id": emp["emp_id"],
            "org_id": org_id,
            "reviewer_id": emp["mgr_id"],
            "review_period": "2024 Annual Review Cycle",
            "performance_score": tmpl[3],
            "rating": tmpl[3],
            "achievements": tmpl[0],
            "strengths": tmpl[1],
            "improvements": tmpl[2],
            "manager_feedback": f"Annual review confirmed by {emp['mgr_id']}. Consistent high performance and alignment with core organizational values.",
            "comments": tmpl[0],
            "created_at": now_iso,
            "updated_at": now_iso
        })
    db.feedback.insert_many(feedback_data)

    # --------------------------------------------------------------------------
    # 11. NOTIFICATIONS (20 Notifications)
    # --------------------------------------------------------------------------
    print("11. Seeding notifications collection (20 notifications)...")
    db.notifications.delete_many({})
    notif_templates = [
        ("Annual Performance Review Complete", "Your manager has recorded your annual performance review and competency evaluation."),
        ("Quarterly Milestone Target Due", "Your career goal milestone 'Microservices Architecture Review' is due in 14 days."),
        ("New Skill Assessment Verified", "Your technical competency assessment for Python has been successfully verified."),
        ("Training Program Assigned", "You have been enrolled in 'Advanced Cloud Architecture on AWS' with 40 learning hours."),
        ("Goal Progress Update Requested", "Please verify your progress updates on active sprint goals before month-end.")
    ]
    notifications_data = []
    for i in range(20):
        emp = employee_roster[i]
        tmpl = notif_templates[i % len(notif_templates)]
        notifications_data.append({
            "notification_id": i + 1,
            "user_id": emp["id"],
            "recipient_email": emp["email"],
            "title": tmpl[0],
            "message": tmpl[1],
            "status": "unread" if i % 2 == 0 else "read",
            "org_id": org_id,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=i)).isoformat()
        })
    db.notifications.insert_many(notifications_data)

    # --------------------------------------------------------------------------
    # 12. MEMBERSHIP REQUESTS
    # --------------------------------------------------------------------------
    print("12. Seeding membership_requests collection...")
    db.membership_requests.delete_many({})
    db.membership_requests.insert_many([
        {
            "id": 1,
            "user_id": 11,
            "org_id": org_id,
            "user_name": "Alex Morgan",
            "user_email": "emp011@talentgrowth.com",
            "department": "Engineering",
            "designation": "Senior Backend Engineer",
            "status": "Approved",
            "reviewed_by": 1,
            "reviewed_at": now_iso,
            "created_at": now_iso
        },
        {
            "id": 2,
            "user_id": 14,
            "org_id": org_id,
            "user_name": "Sophia Chen",
            "user_email": "emp014@talentgrowth.com",
            "department": "Product Management",
            "designation": "Senior Product Manager",
            "status": "Approved",
            "reviewed_by": 1,
            "reviewed_at": now_iso,
            "created_at": now_iso
        }
    ])

    # --------------------------------------------------------------------------
    # 13. INVITATION CODES
    # --------------------------------------------------------------------------
    print("13. Seeding invitation_codes collection...")
    db.invitation_codes.delete_many({})
    db.invitation_codes.insert_many([
        {
            "id": 1,
            "org_id": org_id,
            "code_hash": "inv_code_hash_engineering_2025",
            "code_prefix": "ENG-2025",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
            "max_uses": 50,
            "used_count": 12,
            "status": "Active",
            "created_by": "admin@talentgrowth.com",
            "created_at": now_iso
        },
        {
            "id": 2,
            "org_id": org_id,
            "code_hash": "inv_code_hash_product_2025",
            "code_prefix": "PRD-2025",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
            "max_uses": 30,
            "used_count": 8,
            "status": "Active",
            "created_by": "admin@talentgrowth.com",
            "created_at": now_iso
        }
    ])

    # --------------------------------------------------------------------------
    # 14. EMAIL LOGS
    # --------------------------------------------------------------------------
    print("14. Seeding email_logs collection...")
    db.email_logs.delete_many({})
    db.email_logs.insert_many([
        {
            "id": 1,
            "to_email": "emp011@talentgrowth.com",
            "user_name": "Alex Morgan",
            "role": "employee",
            "org_name": "TalentGrowth Enterprise Technologies",
            "subject": "Welcome to TalentGrowth Platform",
            "message_type": "welcome",
            "status": "sent",
            "error_message": None,
            "created_at": now_iso
        },
        {
            "id": 2,
            "to_email": "emp012@talentgrowth.com",
            "user_name": "Priya Sharma",
            "role": "employee",
            "org_name": "TalentGrowth Enterprise Technologies",
            "subject": "Welcome to TalentGrowth Platform",
            "message_type": "welcome",
            "status": "sent",
            "error_message": None,
            "created_at": now_iso
        }
    ])

    # Persist mock store if running in development/mock mode
    save_mock_store()

    print("\n" + "=" * 75)
    print("✅ MONGODB ATLAS SEEDING COMPLETED SUCCESSFULLY!")
    print("=" * 75)
    final_health = check_db_health()
    print("Collection Document Counts:")
    for cname, count in sorted(final_health["counts"].items()):
        print(f"  • {cname.ljust(25)}: {count} documents")
    print("=" * 75)


if __name__ == "__main__":
    seed_mongodb()
