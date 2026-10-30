import pytest
import tempfile
import os
import sys
from pathlib import Path
from datetime import date

# Ensure root directory is on sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Set temporary database path for tests
temp_db_dir = tempfile.mkdtemp()
os.environ["DATABASE_PATH"] = str(Path(temp_db_dir) / "test_talentgrowth_full.db")

from services.core import (
    init_db, register, login, get_user_by_id, get_profile, save_profile,
    list_skills, add_skill, delete_skill, add_assessment, get_assessments,
    save_progress, get_progress, profile_completion, gap_analysis,
    recommendations, profile_analysis, role_match, export_user_data,
    add_employee, get_employees, get_employee_by_id, update_employee, delete_employee,
    add_performance_review, get_performance_reviews, get_department_performance_summary,
    add_employee_skill, get_employee_skills, delete_employee_skill, get_employee_skill_gaps,
    add_goal, get_goals, get_goal_by_id, update_goal, update_goal_progress, delete_goal, get_goal_stats,
    add_training_record, get_training_records,
    bulk_import_employees_df, get_sample_employee_csv,
    create_organization, get_organization, list_organizations,
    get_organization_by_name, generate_unique_org_id, verify_and_activate_hr_admin,
    generate_invitation_code, list_invitation_codes, revoke_invitation_code, validate_invitation_code, use_invitation_code,
    deactivate_employee, get_all_designations,
    get_org_dashboard_stats, get_employee_dashboard_data,
    hash_password, verify_password,
    get_resume, save_resume, import_skills_to_resume, format_resume_as_text, generate_resume_pdf,
    validate_url, validate_date_range
)
from services.reports import create_report
from services.email_service import build_welcome_email_content, send_welcome_email

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

# ----------------- Auth & RBAC Tests -----------------

def test_register_and_login_with_roles():
    # Admin registration
    ok, msg = register("Admin User", "admin_test@company.com", "AdminPassword123", role="admin", employee_id="ADM01")
    assert ok is True
    admin_user = login("admin_test@company.com", "AdminPassword123")
    assert admin_user is not None
    assert admin_user["role"] == "admin"
    assert admin_user["employee_id"] == "ADM01"

    # Employee registration
    ok_emp, _ = register("Emp User", "emp_test@company.com", "EmpPassword123", role="employee", employee_id="EMP999")
    assert ok_emp is True
    emp_user = login("emp_test@company.com", "EmpPassword123")
    assert emp_user is not None
    assert emp_user["role"] == "employee"

    # Duplicate registration
    ok_dup, _ = register("Duplicate", "admin_test@company.com", "Password123")
    assert ok_dup is False

def test_register_validations():
    # Empty name
    ok, msg = register("", "t1@company.com", "Password123")
    assert ok is False
    assert "name is required" in msg.lower()

    # Invalid email
    ok, msg = register("Test User", "invalid-email", "Password123")
    assert ok is False
    assert "valid email" in msg.lower()

    # Short password
    ok, msg = register("Test User", "t2@company.com", "short")
    assert ok is False
    assert "at least 8 characters" in msg.lower()

# ----------------- Employee Management Tests (Day 3 Feature) -----------------

def test_add_and_get_employees():
    ok, msg = add_employee(
        employee_id="EMP501",
        name="Elena Fisher",
        department="Engineering",
        designation="Lead Security Engineer",
        years_experience=6.5,
        primary_skills="Python, Cryptography, Linux, AWS",
        email="elena.f@company.com",
        phone="+1-555-5001",
        employment_status="Active"
    )
    assert ok is True

    emp = get_employee_by_id("EMP501")
    assert emp is not None
    assert emp["name"] == "Elena Fisher"
    assert emp["department"] == "Engineering"
    assert emp["years_experience"] == 6.5
    assert emp["email"] == "elena.f@company.com"

def test_reject_duplicate_employee_id_and_email():
    add_employee("EMP502", "Worker One", "Sales", "Sales Lead", 3.0, "Negotiation", email="w1@company.com")
    
    # Duplicate ID
    ok1, msg1 = add_employee("EMP502", "Worker Two", "Sales", "Rep", 2.0, "Cold Calling", email="w2@company.com")
    assert ok1 is False
    assert "already exists" in msg1.lower()

    # Duplicate Email
    ok2, msg2 = add_employee("EMP503", "Worker Three", "Sales", "Rep", 2.0, "Cold Calling", email="w1@company.com")
    assert ok2 is False
    assert "already exists" in msg2.lower()

def test_reject_invalid_employee_inputs():
    # Empty fields
    assert add_employee("", "Name", "Dept", "Desig", 2.0, "Skills")[0] is False
    assert add_employee("EMP504", "", "Dept", "Desig", 2.0, "Skills")[0] is False
    assert add_employee("EMP504", "Name", "", "Desig", 2.0, "Skills")[0] is False
    assert add_employee("EMP504", "Name", "Dept", "", 2.0, "Skills")[0] is False
    assert add_employee("EMP504", "Name", "Dept", "Desig", 2.0, "")[0] is False

    # Negative experience
    assert add_employee("EMP504", "Name", "Dept", "Desig", -1.0, "Skills")[0] is False
    # Absurd experience
    assert add_employee("EMP504", "Name", "Dept", "Desig", 70.0, "Skills")[0] is False

def test_update_and_delete_employee():
    add_employee("EMP505", "Original Name", "Engineering", "Dev", 2.0, "Python")
    
    # Update
    ok_u, _ = update_employee(
        employee_id="EMP505",
        name="Updated Name",
        department="Data & Analytics",
        designation="Senior Dev",
        years_experience=4.0,
        primary_skills="Python, SQL",
        employment_status="Active"
    )
    assert ok_u is True
    updated = get_employee_by_id("EMP505")
    assert updated["name"] == "Updated Name"
    assert updated["department"] == "Data & Analytics"

    # Delete
    ok_d, _ = delete_employee("EMP505")
    assert ok_d is True
    assert get_employee_by_id("EMP505") is None

# ----------------- Performance Reviews Tests -----------------

def test_performance_review_lifecycle():
    add_employee("EMP506", "Review Subject", "Engineering", "Staff Engineer", 8.0, "Architecture, Go, Python")
    
    # Add Review
    ok_rev, msg_rev = add_performance_review(
        employee_id="EMP506",
        review_period="Q1 2026",
        performance_score=4.7,
        achievements="Redesigned core message queue processing architecture.",
        strengths="Distributed architecture, technical mentorship.",
        improvements="More documentation on edge cases.",
        manager_feedback="Exceptional performance, recommended for promotion."
    )
    assert ok_rev is True

    # Validate Score bounds
    assert add_performance_review("EMP506", "Q2 2026", 0.5)[0] is False
    assert add_performance_review("EMP506", "Q2 2026", 5.5)[0] is False

    # Retrieve reviews
    revs = get_performance_reviews("EMP506")
    assert len(revs) == 1
    assert revs[0]["performance_score"] == 4.7
    assert revs[0]["review_period"] == "Q1 2026"

    # Summary
    dept_summary = get_department_performance_summary()
    assert len(dept_summary) > 0

# ----------------- Skills & Competency Matrix Tests -----------------

def test_employee_skills_and_gaps():
    add_employee("EMP507", "Skill User", "Engineering", "Developer", 2.0, "Python, Git")
    
    # Add skills
    ok_s, _ = add_employee_skill("EMP507", "Python", "Advanced", "Technical", 3.0)
    assert ok_s is True
    ok_s2, _ = add_employee_skill("EMP507", "Docker", "Intermediate", "Technical", 1.5)
    assert ok_s2 is True

    skills = get_employee_skills("EMP507")
    assert any(s["skill_name"] == "Python" for s in skills)
    assert any(s["skill_name"] == "Docker" for s in skills)

    # Gap Analysis against Senior Software Engineer
    gap_data = get_employee_skill_gaps("EMP507", "Senior Software Engineer")
    assert "gaps" in gap_data
    assert "match_percentage" in gap_data
    assert gap_data["match_percentage"] > 0
    assert len(gap_data["recommended_training"]) > 0

# ----------------- Training Records Tests -----------------

def test_training_records():
    add_employee("EMP508", "Trainee User", "Engineering", "Junior Dev", 1.0, "Python")
    
    ok_t, _ = add_training_record(
        employee_id="EMP508",
        course_name="Modern Microservices with Docker",
        target_skill="Docker",
        provider="Internal Academy",
        target_completion_date="2026-11-30",
        status="Enrolled"
    )
    assert ok_t is True

    trainings = get_training_records("EMP508")
    assert len(trainings) == 1
    assert trainings[0]["course_name"] == "Modern Microservices with Docker"

# ----------------- Career Goal Tracking Tests (Weekend Assignment) -----------------

def test_career_goals_crud_and_overdue():
    register("Goal Tracker", "goal_test@company.com", "Password123")
    user = login("goal_test@company.com", "Password123")
    uid = user["id"]

    # Active goal
    ok_g, _ = add_goal(
        user_id=uid,
        title="Pass Kubernetes CKA",
        description="Complete all labs and mock exams.",
        target_date="2026-12-31",
        progress=50,
        target_designation="DevOps / Cloud Engineer"
    )
    assert ok_g is True

    # Discrete progress validation
    assert add_goal(uid, "Invalid Progress Goal", "Desc", "2026-12-31", 33)[0] is False

    goals = get_goals(user_id=uid)
    assert len(goals) == 1
    assert goals[0]["progress"] == 50
    assert goals[0]["status"] == "In Progress"

    # Update progress to 100% (Completed)
    gid = goals[0]["id"]
    ok_up, _ = update_goal_progress(gid, uid, 100)
    assert ok_up is True
    updated = get_goal_by_id(gid, uid)
    assert updated["status"] == "Completed"

    # Delete goal
    ok_del, _ = delete_goal(gid, uid)
    assert ok_del is True
    assert get_goal_by_id(gid, uid) is None

# ----------------- Reports & Export Tests -----------------

def test_report_and_export():
    profile = {
        "name": "Alex Morgan",
        "job_title": "Full Stack Engineer",
        "department": "Engineering",
        "years_experience": 3.5,
        "summary": "Full stack engineer passionate about scalable systems.",
        "target_role": "Senior Software Engineer"
    }
    skills = [
        {"name": "Python", "category": "Technical", "proficiency": "Advanced", "years": 3.5},
        {"name": "SQL", "category": "Technical", "proficiency": "Intermediate", "years": 3.0}
    ]
    analysis = profile_analysis(profile, skills)
    gaps = gap_analysis("Senior Software Engineer", skills)
    recs = recommendations(profile, skills)
    goals = [{"title": "Learn Kubernetes", "target_designation": "Senior Dev", "target_date": "2026-12-01", "progress": 50, "status": "In Progress"}]
    reviews = [{"review_period": "2025 Annual", "performance_score": 4.5, "achievements": "High throughput architecture", "strengths": "Fast learner", "manager_feedback": "Great work"}]

    pdf_bytes = create_report(profile, skills, analysis, gaps, recs, [], [], goals, reviews)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")

def test_ravi_kumar_development_journey():
    # 1. Employee registration & directory
    emp = get_employee_by_id("EMP107")
    assert emp is not None
    assert emp["name"] == "Ravi Kumar"
    assert emp["department"] == "IT"
    assert emp["designation"] == "Junior Python Developer"

    # 2. Performance review
    reviews = get_performance_reviews("EMP107")
    assert len(reviews) >= 1
    assert reviews[0]["performance_score"] == 3.8
    assert "SQL" in reviews[0]["improvements"]

    # 3. Skill gap analysis for Senior Python Developer
    gap_data = get_employee_skill_gaps("EMP107", "Senior Python Developer")
    assert gap_data["match_percentage"] > 0
    sql_gap = next((g for g in gap_data["gaps"] if g["skill"] == "SQL"), None)
    comm_gap = next((g for g in gap_data["gaps"] if g["skill"] == "Communication"), None)
    assert sql_gap is not None and sql_gap["priority"] == "High"
    assert comm_gap is not None and comm_gap["priority"] == "High"

    # 4. Training assignments
    trainings = get_training_records("EMP107")
    assert any(t["target_skill"] == "SQL" for t in trainings)
    assert any(t["target_skill"] == "Communication" for t in trainings)

    # 5. Career goals
    user = login("ravi@company.com", "Password123")
    assert user is not None
    goals = get_goals(user["id"])
    assert any("Senior Python Developer" in g["title"] for g in goals)

def test_bulk_employee_import():
    import io
    import pandas as pd
    sample_csv = get_sample_employee_csv()
    df = pd.read_csv(io.StringIO(sample_csv))
    result = bulk_import_employees_df(df)
    assert result["total"] == 5
    assert result["success_count"] == 5
    assert result["skipped_count"] == 0

    # Verify EMP301 and EMP302 were inserted
    emp1 = get_employee_by_id("EMP301")
    assert emp1 is not None
    assert emp1["name"] == "Kavita Sharma"
    emp2 = get_employee_by_id("EMP302")
    assert emp2 is not None
    assert emp2["name"] == "Sita Rao"

    # Second import should skip duplicates
    result_dup = bulk_import_employees_df(df)
    assert result_dup["success_count"] == 0
    assert result_dup["skipped_count"] == 5

# ----------------- AI Career Coach & Resume Reviewer Tests -----------------

def test_ai_coach_offline_guidance(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    from services.ai_coach import generate_ai_coaching_guidance
    profile = {
        "job_title": "Software Engineer",
        "years_experience": 3.5,
        "department": "Engineering",
        "career_goal": "Lead a platform engineering team"
    }
    skills = [
        {"name": "Python", "proficiency": "Advanced"},
        {"name": "SQL", "proficiency": "Intermediate"}
    ]
    gaps = [
        {"skill": "System Architecture", "gap": 2, "priority": "High"},
        {"skill": "Kubernetes", "gap": 1, "priority": "Medium"}
    ]
    res = generate_ai_coaching_guidance(
        user_name="Priya Patel",
        question="How can I prepare for a Lead Engineer promotion?",
        profile=profile,
        skills=skills,
        target_role="Senior Software Engineer",
        gap_data=gaps,
        api_key=None
    )
    assert res["source"] == "offline_rules"
    assert "Priya Patel" in res["content"]
    assert "System Architecture" in res["content"]
    assert "90-Day" in res["content"]

def test_ai_resume_audit_offline(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    from services.ai_coach import analyze_resume_with_ai
    profile = {
        "job_title": "Backend Developer",
        "years_experience": 4.0
    }
    resume_text = """
    Priya Patel - Software Engineer
    Developed REST APIs using Python and Flask.
    Managed SQLite database schemas and improved query speed.
    Collaborated with frontend developers on UI integration.
    """
    target_skills = ["Python", "SQL", "Docker", "Kubernetes", "Microservices"]
    audit = analyze_resume_with_ai(
        resume_text=resume_text,
        target_role="Senior Software Engineer",
        target_skills=target_skills,
        profile=profile,
        api_key=None
    )
    assert audit["source"] == "rule_based_engine"
    assert isinstance(audit["ats_score"], int)
    assert audit["ats_score"] > 0
    assert "Python" in audit["detected_keywords"] or "python" in [k.lower() for k in audit["detected_keywords"]]
    assert len(audit["bullet_optimizations"]) > 0
    assert "rewritten_bullet" in audit["bullet_optimizations"][0]
    assert len(audit["strong_action_verbs_found"]) > 0


# ==============================================================================
# FEATURE ENHANCEMENT TESTS: INDIVIDUAL SKILLS, WELCOME EMAIL, ORG ISOLATION
# ==============================================================================

def test_1_employee_registration_triggers_welcome_email(monkeypatch):
    """Scenario 1: A new employee registers and receives a welcome email."""
    dispatched_emails = []

    def mock_send(to_email, user_name, role="employee", org_name="Talent Growth", app_url=None):
        dispatched_emails.append({
            "email": to_email,
            "name": user_name,
            "role": role,
            "org_name": org_name,
            "app_url": app_url
        })
        return True, "Mock email dispatched"

    monkeypatch.setattr("services.core.send_welcome_email", mock_send)

    ok, msg = register(
        name="Clara Oswald",
        email="clara.oswald@tardis.org",
        password="Password123",
        role="employee",
        employee_id="EMP-CLARA",
        org_id="ORG-TARDIS-01",
        org_name="TARDIS Industries",
        department="Operations",
        job_title="Time Systems Engineer",
        primary_skills="Python, SQL, Chrono-Analysis",
        years_experience=3.5,
        app_url="https://talent-growth.vercel.app"
    )

    assert ok is True
    assert len(dispatched_emails) == 1
    call = dispatched_emails[0]
    assert call["email"] == "clara.oswald@tardis.org"
    assert call["name"] == "Clara Oswald"
    assert call["role"] == "employee"
    assert call["org_name"] == "TARDIS Industries"
    assert "https://" in call["app_url"]

    # Verify email template generation
    text_ver, html_ver = build_welcome_email_content("Clara Oswald", "employee", "TARDIS Industries", "https://talent-growth.vercel.app")
    assert "Welcome to Talent Growth!" in text_ver
    assert "TARDIS Industries" in text_ver
    assert "Clara Oswald" in html_ver
    assert "Employee" in html_ver

def test_2_employee_appears_in_correct_org_hr_employee_list():
    """Scenario 2: The employee appears in the correct organization's HR employee list."""
    create_organization("ORG-ALPHA-CORP", "Alpha Global")
    create_organization("ORG-BETA-CORP", "Beta Dynamics")

    register("Arthur Dent", "arthur@alphacorp.com", "Password123", role="employee", employee_id="EMP-ALPHA-01", org_id="ORG-ALPHA-CORP", department="Logistics", job_title="Supply Lead")
    register("Ford Prefect", "ford@betacorp.com", "Password123", role="employee", employee_id="EMP-BETA-01", org_id="ORG-BETA-CORP", department="Research", job_title="Field Researcher")

    # HR in Alpha Corp views employees
    alpha_emps = get_employees(org_id="ORG-ALPHA-CORP")
    alpha_ids = [e["employee_id"] for e in alpha_emps]
    assert "EMP-ALPHA-01" in alpha_ids
    assert "EMP-BETA-01" not in alpha_ids

    # Verify display fields
    alpha_emp = next(e for e in alpha_emps if e["employee_id"] == "EMP-ALPHA-01")
    assert alpha_emp["name"] == "Arthur Dent"
    assert alpha_emp["email"] == "arthur@alphacorp.com"
    assert alpha_emp["department"] == "Logistics"
    assert alpha_emp["designation"] == "Supply Lead"
    assert alpha_emp["employment_status"] == "Active"

def test_3_skills_assessments_stored_separately_for_each_employee():
    """Scenario 3: Skills assessments are stored separately for each employee without shared data."""
    # Register two employees in the same organization
    register("Developer Uno", "uno@isolated.com", "Password123", role="employee", employee_id="EMP-ISO-01", org_id="ORG-ISOLATED", primary_skills="Python")
    register("Developer Dos", "dos@isolated.com", "Password123", role="employee", employee_id="EMP-ISO-02", org_id="ORG-ISOLATED", primary_skills="SQL")

    # Add custom skill and assessment for Uno
    add_employee_skill("EMP-ISO-01", "FastAPI", "Expert", "Technical", years_exp=4.0, org_id="ORG-ISOLATED")
    add_assessment(employee_id="EMP-ISO-01", org_id="ORG-ISOLATED", category="Technical", skill_name="FastAPI", score=96.0, notes="Built high-throughput payment APIs")

    # Add custom skill and assessment for Dos
    add_employee_skill("EMP-ISO-02", "Kubernetes", "Intermediate", "Tools", years_exp=2.0, org_id="ORG-ISOLATED")
    add_assessment(employee_id="EMP-ISO-02", org_id="ORG-ISOLATED", category="Tools", skill_name="Kubernetes", score=68.0, notes="Cluster admin certification")

    # Verify Uno has FastAPI and no Kubernetes
    uno_skills = get_employee_skills("EMP-ISO-01", org_id="ORG-ISOLATED")
    uno_skill_names = [s["skill_name"] for s in uno_skills]
    assert "FastAPI" in uno_skill_names
    assert "Kubernetes" not in uno_skill_names

    # Verify Dos has Kubernetes and no FastAPI
    dos_skills = get_employee_skills("EMP-ISO-02", org_id="ORG-ISOLATED")
    dos_skill_names = [s["skill_name"] for s in dos_skills]
    assert "Kubernetes" in dos_skill_names
    assert "FastAPI" not in dos_skill_names

    # Verify assessments isolation
    uno_ass = get_assessments(employee_id="EMP-ISO-01", org_id="ORG-ISOLATED")
    assert len(uno_ass) == 1
    assert uno_ass[0]["skill_name"] == "FastAPI"
    assert uno_ass[0]["score"] == 96.0

    dos_ass = get_assessments(employee_id="EMP-ISO-02", org_id="ORG-ISOLATED")
    assert len(dos_ass) == 1
    assert dos_ass[0]["skill_name"] == "Kubernetes"
    assert dos_ass[0]["score"] == 68.0

    # Clean initial state when a new employee joins
    register("Developer Tres", "tres@isolated.com", "Password123", role="employee", employee_id="EMP-ISO-03", org_id="ORG-ISOLATED", primary_skills="Leadership")
    tres_ass = get_assessments(employee_id="EMP-ISO-03", org_id="ORG-ISOLATED")
    assert len(tres_ass) == 0  # Fresh profile, never copied from Uno or Dos

def test_4_and_5_strict_cross_organization_isolation():
    """Scenario 4 & 5: HR Administrator A cannot access Org B, and HR Administrator B cannot access Org A."""
    create_organization("ORG-ACME-CORP", "Acme Corporation")
    create_organization("ORG-WAYNE-ENT", "Wayne Enterprises")

    # HR Admin A and Employees in Org A
    register("Acme HR Admin", "hr@acme.com", "AdminPassword123", role="admin", employee_id="HR-ACME-01", org_id="ORG-ACME-CORP")
    register("Wile Coyote", "coyote@acme.com", "Password123", role="employee", employee_id="EMP-ACME-01", org_id="ORG-ACME-CORP", department="R&D", job_title="Pyrotechnics Engineer")

    # HR Admin B and Employees in Org B
    register("Wayne HR Admin", "hr@wayne.com", "AdminPassword123", role="admin", employee_id="HR-WAYNE-01", org_id="ORG-WAYNE-ENT")
    register("Bruce Wayne", "bruce@wayne.com", "Password123", role="employee", employee_id="EMP-WAYNE-01", org_id="ORG-WAYNE-ENT", department="Executive", job_title="Managing Director")

    # Add reviews in both orgs
    add_performance_review("EMP-ACME-01", "2025 Review", 4.1, "Rocket tests", "Persistence", "Navigation", reviewer_id=1, org_id="ORG-ACME-CORP")
    add_performance_review("EMP-WAYNE-01", "2025 Review", 5.0, "Enterprise turnaround", "Strategy", "Work-life balance", reviewer_id=1, org_id="ORG-WAYNE-ENT")

    # 1. Directory isolation
    acme_emps = get_employees(org_id="ORG-ACME-CORP")
    wayne_emps = get_employees(org_id="ORG-WAYNE-ENT")

    assert any(e["employee_id"] == "EMP-ACME-01" for e in acme_emps)
    assert not any(e["employee_id"] == "EMP-WAYNE-01" for e in acme_emps)

    assert any(e["employee_id"] == "EMP-WAYNE-01" for e in wayne_emps)
    assert not any(e["employee_id"] == "EMP-ACME-01" for e in wayne_emps)

    # 2. Direct ID lookup isolation
    assert get_employee_by_id("EMP-WAYNE-01", org_id="ORG-ACME-CORP") is None
    assert get_employee_by_id("EMP-ACME-01", org_id="ORG-WAYNE-ENT") is None

    # 3. Modification prevention across org boundaries
    ok_upd, _ = update_employee("EMP-WAYNE-01", name="Tampered", department="Executive", designation="Lead", years_experience=5.0, primary_skills="Leadership", org_id="ORG-ACME-CORP")
    assert ok_upd is False

    ok_del, _ = delete_employee("EMP-ACME-01", org_id="ORG-WAYNE-ENT")
    assert ok_del is False

    # 4. Reviews isolation
    acme_revs = get_performance_reviews(org_id="ORG-ACME-CORP")
    assert all(r["employee_id"] != "EMP-WAYNE-01" for r in acme_revs)

    wayne_revs = get_performance_reviews(org_id="ORG-WAYNE-ENT")
    assert all(r["employee_id"] != "EMP-ACME-01" for r in wayne_revs)

def test_6_employee_cannot_view_another_employee_private_information():
    """Scenario 6: An employee cannot view another employee's private goals, assessments, or reviews."""
    ok1, _ = register("Employee Alice", "alice.private@company.com", "Password123", role="employee", employee_id="EMP-PRIV-A", org_id="ORG-TALENT-01")
    ok2, _ = register("Employee Bob", "bob.private@company.com", "Password123", role="employee", employee_id="EMP-PRIV-B", org_id="ORG-TALENT-01")
    assert ok1 and ok2

    user_alice = login("alice.private@company.com", "Password123")
    user_bob = login("bob.private@company.com", "Password123")

    # Bob creates confidential goals and takes assessment
    add_goal(user_id=user_bob["id"], title="Confidential C-Suite Pivot", description="Strategy", target_date="2027-01-01", progress=25, employee_id="EMP-PRIV-B", org_id="ORG-TALENT-01")
    add_assessment(uid=user_bob["id"], employee_id="EMP-PRIV-B", org_id="ORG-TALENT-01", category="Leadership", skill_name="Leadership", score=90.0, notes="Executive mentorship")

    # Alice queries her goals and assessments
    alice_goals = get_goals(user_id=user_alice["id"], org_id="ORG-TALENT-01")
    assert not any("Confidential C-Suite" in g["title"] for g in alice_goals)

    alice_ass = get_assessments(uid=user_alice["id"], employee_id="EMP-PRIV-A", org_id="ORG-TALENT-01")
    assert len(alice_ass) == 0

    # Alice's dashboard only contains Alice's data
    alice_dash = get_employee_dashboard_data(user_id=user_alice["id"], employee_id="EMP-PRIV-A", org_id="ORG-TALENT-01")
    assert alice_dash["user"]["email"] == "alice.private@company.com"
    assert len(alice_dash["goals"]) == 0
    assert len(alice_dash["assessments"]) == 0

def test_7_hr_dashboard_cards_and_charts_show_only_org_specific_data():
    """Scenario 7: HR dashboard cards and charts show only organization-specific data."""
    create_organization("ORG-METRIC-A", "Metric Corp A")
    create_organization("ORG-METRIC-B", "Metric Corp B")

    # Org A: 2 employees in Engineering and Sales, review score 4.5
    register("A1", "a1@metric.com", "Password123", role="employee", employee_id="MA-01", org_id="ORG-METRIC-A", department="Engineering")
    register("A2", "a2@metric.com", "Password123", role="employee", employee_id="MA-02", org_id="ORG-METRIC-A", department="Sales")
    add_performance_review("MA-01", "2025 Review", 4.5, "Strong release", "Architecture", "None", reviewer_id=1, org_id="ORG-METRIC-A")

    # Org B: 1 employee in Finance, review score 3.0
    register("B1", "b1@metric.com", "Password123", role="employee", employee_id="MB-01", org_id="ORG-METRIC-B", department="Finance")
    add_performance_review("MB-01", "2025 Review", 3.0, "Balance audit", "Accuracy", "Speed", reviewer_id=1, org_id="ORG-METRIC-B")

    stats_a = get_org_dashboard_stats("ORG-METRIC-A")
    assert stats_a["total_employees"] == 2
    assert stats_a["total_departments"] == 2
    assert stats_a["avg_performance"] == 4.5
    assert all(e["employee_id"] != "MB-01" for e in stats_a["recent_joiners"])
    assert "Finance" not in stats_a["dept_counts"]

    stats_b = get_org_dashboard_stats("ORG-METRIC-B")
    assert stats_b["total_employees"] == 1
    assert stats_b["total_departments"] == 1
    assert stats_b["avg_performance"] == 3.0
    assert all(e["employee_id"] != "MA-01" for e in stats_b["recent_joiners"])
    assert "Engineering" not in stats_b["dept_counts"]

def test_8_email_delivery_failures_do_not_corrupt_account_creation(monkeypatch):
    """Scenario 8: Email delivery failures do not corrupt account creation."""
    import smtplib

    def broken_send(*args, **kwargs):
        raise smtplib.SMTPException("Simulated SMTP Server Down")

    monkeypatch.setattr("services.core.send_welcome_email", broken_send)

    ok, msg = register(
        name="Resilient Employee",
        email="resilient.user@company.com",
        password="ValidPassword123",
        role="employee",
        employee_id="EMP-RESILIENT",
        org_id="ORG-TALENT-01"
    )

    # Account creation must succeed even if mail fails
    assert ok is True
    assert "successful" in msg.lower()

    # User can log in without issue
    user = login("resilient.user@company.com", "ValidPassword123")
    assert user is not None
    assert user["name"] == "Resilient Employee"
    assert user["employee_id"] == "EMP-RESILIENT"

def test_9_existing_users_and_data_continue_to_work_after_migrations():
    """Scenario 9: Existing users and data continue to work after database migrations."""
    # Seeded admin user
    admin_user = login("admin@talentgrowth.com", "Admin@12345")
    assert admin_user is not None
    assert admin_user["role"] == "admin"
    assert admin_user["org_id"] == "ORG-TALENT-01"

    # Seeded employee user
    ravi_user = login("ravi@company.com", "Password123")
    assert ravi_user is not None
    assert ravi_user["role"] == "employee"
    assert ravi_user["employee_id"] == "EMP107"

    # Seeded employee skills
    ravi_skills = get_employee_skills("EMP107", org_id="ORG-TALENT-01")
    assert len(ravi_skills) >= 1
    assert any(s["skill_name"] == "Python" for s in ravi_skills)

    # Seeded organizations
    orgs = list_organizations()
    org_ids = [o["org_id"] for o in orgs]
    assert "ORG-TALENT-01" in org_ids
    assert "ORG-TECHCORP-02" in org_ids

def test_10_unauthenticated_and_unauthorized_protections():
    """Scenario 10: Unauthenticated and unauthorized users cannot access or tamper with protected operations."""
    # Invalid password login rejected
    assert login("admin@talentgrowth.com", "WrongPassword") is None

    # Non-existent user login rejected
    assert login("fake_user@company.com", "Password123") is None

    # Password hash verify security
    h, s = hash_password("SecurePassword99")
    assert verify_password("SecurePassword99", h, s) is True
    assert verify_password("WrongGuess", h, s) is False

    # Goal manipulation by unauthorized user is rejected
    ok_goal, _ = add_goal(user_id=1, title="Admin Goal", description="HR target", target_date="2026-12-31", progress=0, org_id="ORG-TALENT-01")
    assert ok_goal is True

    # User 999 attempting to update or delete Admin's goal is rejected
    ok_upd, _ = update_goal(goal_id=1, user_id=999, title="Hacked Title", description="Desc", target_date="2026-12-31", progress=50)
    assert ok_upd is False

    ok_del, _ = delete_goal(goal_id=1, user_id=999)
    assert ok_del is False


# ==============================================================================
# RESUME STUDIO EDITING, PERSISTENCE, VALIDATIONS & PDF EXPORT TESTS
# ==============================================================================

def test_11_resume_studio_initialization_and_load():
    """Scenario 11: Opening Resume Studio loads or initializes structured resume records."""
    res = get_resume(user_id=1, org_id="ORG-TALENT-01")
    assert res is not None
    assert "summary" in res
    assert "skills" in res
    assert "experience" in res
    assert "education" in res
    assert "certifications" in res
    assert "projects" in res
    assert "links" in res
    assert isinstance(res["skills"], list)
    assert isinstance(res["experience"], list)

def test_12_resume_studio_edit_summary_and_persistence():
    """Scenario 12: Editing the professional summary persists to both resumes and profiles tables."""
    res = get_resume(user_id=1, org_id="ORG-TALENT-01")
    assert res is not None

    custom_summary = "Staff Cloud Architect with 10+ years specializing in distributed systems, Kubernetes, and reactive frontend microservices."
    res["summary"] = custom_summary

    ok_save, msg_save = save_resume(user_id=1, resume_data=res, org_id="ORG-TALENT-01")
    assert ok_save is True

    # Reload from database to verify persistence
    reloaded = get_resume(user_id=1, org_id="ORG-TALENT-01")
    assert reloaded is not None
    assert reloaded["summary"] == custom_summary

    # Verify legacy profile synchronization
    prof = get_profile(user_id=1)
    assert prof["summary"] == custom_summary

def test_13_resume_studio_skills_crud_and_deduplication():
    """Scenario 13: Adding, editing, deleting, and deduplicating resume skills."""
    res = get_resume(user_id=1, org_id="ORG-TALENT-01")
    assert res is not None

    res["skills"] = [
        {"name": "Python", "proficiency": "Expert"},
        {"name": "SQL", "proficiency": "Advanced"},
        {"name": "React", "proficiency": "Intermediate"},
        {"name": "python", "proficiency": "Beginner"},  # duplicate lowercase
        {"name": "Docker", "proficiency": "Advanced"}
    ]

    ok_save, _ = save_resume(user_id=1, resume_data=res, org_id="ORG-TALENT-01")
    assert ok_save is True

    reloaded = get_resume(user_id=1, org_id="ORG-TALENT-01")
    skill_names = [s["name"] for s in reloaded["skills"]]
    assert len(skill_names) == 4  # Deduplicated Python
    assert "Python" in skill_names
    assert "SQL" in skill_names
    assert "React" in skill_names
    assert "Docker" in skill_names

    # Delete React
    reloaded["skills"] = [s for s in reloaded["skills"] if s["name"] != "React"]
    ok_save2, _ = save_resume(user_id=1, resume_data=reloaded, org_id="ORG-TALENT-01")
    assert ok_save2 is True

    reloaded2 = get_resume(user_id=1, org_id="ORG-TALENT-01")
    assert "React" not in [s["name"] for s in reloaded2["skills"]]

def test_14_resume_studio_import_from_skills_and_assessment():
    """Scenario 14: Importing verified skills from Skills & Assessment module merges without overwriting."""
    # Add an employee skill for EMP101 (Alex Morgan)
    add_employee_skill(
        employee_id="EMP101",
        skill_name="Apache Kafka",
        proficiency_level="Advanced",
        years_exp=2.5,
        org_id="ORG-TALENT-01"
    )

    current_resume_skills = [
        {"name": "Python", "proficiency": "Advanced"},
        {"name": "SQL", "proficiency": "Advanced"}
    ]

    # Alex user ID is 2
    alex_user = login("alex@company.com", "Password123")
    assert alex_user is not None
    alex_uid = alex_user["id"]

    merged = import_skills_to_resume(user_id=alex_uid, current_skills=current_resume_skills, org_id="ORG-TALENT-01")
    merged_names = [s["name"] for s in merged]
    assert "Python" in merged_names
    assert "SQL" in merged_names
    assert "Apache Kafka" in merged_names

def test_15_resume_studio_experience_crud_and_current_employment():
    """Scenario 15: Adding multiple experience entries, reordering, and current employment flag."""
    res = get_resume(user_id=1, org_id="ORG-TALENT-01")
    assert res is not None

    res["experience"] = [
        {
            "id": "exp_1",
            "job_title": "Lead Software Engineer",
            "company": "CloudScale Systems",
            "employment_type": "Full-time",
            "location": "Bengaluru, India",
            "start_date": "2023-01",
            "end_date": "Present",
            "is_current": True,
            "description": "Architected event-driven microservices processing 5M+ daily requests."
        },
        {
            "id": "exp_2",
            "job_title": "Senior Backend Developer",
            "company": "DataHub Technologies",
            "employment_type": "Full-time",
            "location": "Mumbai, India",
            "start_date": "2020-06",
            "end_date": "2022-12",
            "is_current": False,
            "description": "Optimized PostgreSQL query latency by 45% using materialized views and indexing."
        }
    ]

    ok_save, _ = save_resume(user_id=1, resume_data=res, org_id="ORG-TALENT-01")
    assert ok_save is True

    reloaded = get_resume(user_id=1, org_id="ORG-TALENT-01")
    assert len(reloaded["experience"]) == 2
    assert reloaded["experience"][0]["job_title"] == "Lead Software Engineer"
    assert reloaded["experience"][0]["end_date"] == "Present"
    assert reloaded["experience"][0]["is_current"] is True

    # Reorder entries
    reloaded["experience"][0], reloaded["experience"][1] = reloaded["experience"][1], reloaded["experience"][0]
    ok_save_reorder, _ = save_resume(user_id=1, resume_data=reloaded, org_id="ORG-TALENT-01")
    assert ok_save_reorder is True

    reloaded_order = get_resume(user_id=1, org_id="ORG-TALENT-01")
    assert reloaded_order["experience"][0]["job_title"] == "Senior Backend Developer"

def test_16_resume_studio_education_and_certifications_crud():
    """Scenario 16: Adding education and certification credentials with validation."""
    res = get_resume(user_id=1, org_id="ORG-TALENT-01")
    assert res is not None

    res["education"] = [
        {
            "id": "edu_1",
            "degree": "M.S. in Computer Science",
            "institution": "Stanford University Online",
            "field_of_study": "Distributed Systems",
            "start_date": "2021",
            "end_date": "2023",
            "details": "Specialization in Cloud Infrastructure, GPA: 3.9/4.0"
        }
    ]

    res["certifications"] = [
        {
            "id": "cert_1",
            "name": "AWS Certified Solutions Architect - Professional",
            "issuing_org": "Amazon Web Services",
            "issue_date": "2023-08",
            "expiry_date": "2026-08",
            "no_expiry": False,
            "credential_id": "AWS-892174",
            "credential_url": "https://aws.amazon.com/verify"
        }
    ]

    ok_save, _ = save_resume(user_id=1, resume_data=res, org_id="ORG-TALENT-01")
    assert ok_save is True

    reloaded = get_resume(user_id=1, org_id="ORG-TALENT-01")
    assert len(reloaded["education"]) == 1
    assert reloaded["education"][0]["degree"] == "M.S. in Computer Science"
    assert len(reloaded["certifications"]) == 1
    assert reloaded["certifications"][0]["credential_id"] == "AWS-892174"

def test_17_resume_studio_projects_and_links_crud():
    """Scenario 17: Adding projects and professional links with URL verification."""
    res = get_resume(user_id=1, org_id="ORG-TALENT-01")
    assert res is not None

    res["projects"] = [
        {
            "id": "proj_1",
            "title": "Real-Time Talent Intelligence Platform",
            "role": "Lead Architect",
            "technologies": "Python, Streamlit, PostgreSQL, ReportLab",
            "description": "Enterprise talent assessment engine with ATS scoring and multi-tenant access control.",
            "project_url": "https://talentgrowth.example.com",
            "github_url": "https://github.com/example/talentgrowth"
        }
    ]

    res["links"] = [
        {"id": "link_1", "label": "LinkedIn", "url": "https://linkedin.com/in/lead-engineer"},
        {"id": "link_2", "label": "GitHub", "url": "https://github.com/lead-engineer"},
        {"id": "link_3", "label": "Portfolio", "url": "https://leadengineer.dev"}
    ]

    ok_save, _ = save_resume(user_id=1, resume_data=res, org_id="ORG-TALENT-01")
    assert ok_save is True

    reloaded = get_resume(user_id=1, org_id="ORG-TALENT-01")
    assert len(reloaded["projects"]) == 1
    assert len(reloaded["links"]) == 3
    assert any("linkedin.com" in l["url"] for l in reloaded["links"])

def test_18_resume_studio_validations_invalid_dates_and_urls():
    """Scenario 18: Rejecting invalid date ranges (start > end) and malformed URLs."""
    res = get_resume(user_id=1, org_id="ORG-TALENT-01")
    assert res is not None

    # Invalid date range: start 2024 is after end 2022
    bad_res_dates = dict(res)
    bad_res_dates["experience"] = [
        {
            "id": "exp_bad",
            "job_title": "Software Engineer",
            "company": "Invalid Dates Corp",
            "start_date": "2024-05",
            "end_date": "2022-01",
            "is_current": False,
            "description": "Test"
        }
    ]
    ok_bad_date, err_date = save_resume(user_id=1, resume_data=bad_res_dates, org_id="ORG-TALENT-01")
    assert ok_bad_date is False
    assert "start date" in err_date.lower() or "after" in err_date.lower()

    # Invalid URL format in links
    bad_res_url = dict(res)
    bad_res_url["experience"] = []
    bad_res_url["links"] = [
        {"id": "link_bad", "label": "Website", "url": "not a valid web url @@!!"}
    ]
    ok_bad_url, err_url = save_resume(user_id=1, resume_data=bad_res_url, org_id="ORG-TALENT-01")
    assert ok_bad_url is False
    assert "invalid" in err_url.lower()

def test_19_resume_studio_cross_employee_and_tenant_isolation():
    """Scenario 19: Strict multi-tenant isolation prevents cross-organization resume viewing and modification."""
    # Seed TechCorp user if not present
    tech_user = login("jane@techcorp.com", "Password123")
    if not tech_user:
        ok_reg, _ = register(
            name="Jane Doe",
            email="jane.doe@techcorp.com",
            password="Password123",
            role="employee",
            org_id="ORG-TECHCORP-02",
            department="Engineering",
            job_title="DevOps Engineer"
        )
        assert ok_reg is True
        tech_user = login("jane.doe@techcorp.com", "Password123")
    assert tech_user is not None
    tech_uid = tech_user["id"]

    # HR in Org TALENT attempting to access Org TECHCORP employee resume is blocked
    blocked_resume = get_resume(user_id=tech_uid, org_id="ORG-TALENT-01")
    assert blocked_resume is None

    # Attempting to save resume for TechCorp user under Org TALENT is blocked
    ok_cross_save, err_cross = save_resume(user_id=tech_uid, resume_data={"summary": "Hacked"}, org_id="ORG-TALENT-01")
    assert ok_cross_save is False
    assert "unauthorized" in err_cross.lower()

    # Authorized access within same organization succeeds
    allowed_resume = get_resume(user_id=tech_uid, org_id="ORG-TECHCORP-02")
    assert allowed_resume is not None

def test_20_resume_studio_pdf_generation_valid_output():
    """Scenario 20: Generating high-quality, printable ReportLab PDF without overlaps."""
    res = get_resume(user_id=1, org_id="ORG-TALENT-01")
    assert res is not None

    user_info = {
        "name": "HR Administrator",
        "email": "admin@talentgrowth.com",
        "phone": "+1 (555) 019-2834",
        "location": "San Francisco, CA"
    }

    pdf_bytes = generate_resume_pdf(resume_data=res, user_info=user_info)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-1.")

    # Test with empty optional sections (graceful rendering)
    empty_res = {
        "summary": "Brief summary",
        "skills": [],
        "experience": [],
        "education": [],
        "certifications": [],
        "projects": [],
        "links": []
    }
    empty_pdf = generate_resume_pdf(resume_data=empty_res, user_info={"name": "Minimal User", "email": "min@test.com"})
    assert isinstance(empty_pdf, bytes)
    assert empty_pdf.startswith(b"%PDF-1.")

def test_21_resume_studio_text_formatting_and_ai_audit_integration(monkeypatch):
    """Scenario 21: Formatted text export integrates seamlessly with AI ATS Screening."""
    monkeypatch.setenv("GEMINI_API_KEY", "")
    from services.ai_coach import analyze_resume_with_ai

    res = get_resume(user_id=1, org_id="ORG-TALENT-01")
    assert res is not None

    user_info = {"name": "Alex Morgan", "email": "alex@company.com", "phone": "555-0199", "location": "Bangalore"}
    formatted_text = format_resume_as_text(res, user_info)
    assert "Alex Morgan" in formatted_text
    assert "PROFESSIONAL SUMMARY" in formatted_text
    assert "CORE COMPETENCIES & SKILLS" in formatted_text

    audit = analyze_resume_with_ai(
        resume_text=formatted_text,
        target_role="Senior Software Engineer",
        target_skills=["Python", "SQL", "Docker", "System Design"],
        profile={"job_title": "Software Engineer", "years_experience": 4.0},
        api_key=None
    )
    assert audit is not None
    assert isinstance(audit["ats_score"], int)
    assert audit["ats_score"] > 0
    assert len(audit["bullet_optimizations"]) > 0

def test_22_employee_dashboard_skills_and_assessment_key_resilience():
    """Scenario 22: Dashboard skills and assessment data structures never raise KeyError."""
    from services.core import get_employee_dashboard_data, add_skill, add_employee_skill

    # 1. Existing user dashboard data has required fields
    dash = get_employee_dashboard_data(user_id=1)
    assert "skills" in dash
    assert isinstance(dash["skills"], list)
    for s in dash["skills"]:
        assert "category" in s
        assert "skill_name" in s
        assert "proficiency_level" in s
        # Ensure string interpolation works without KeyError
        formatted = f"**{s['skill_name']}** ({s['proficiency_level']}) - {s['category']}"
        assert len(formatted) > 0

    # 2. Existing employee EMP107 in ORG-TALENT-01 has verified skills
    dash_emp = get_employee_dashboard_data(user_id=2, employee_id="EMP107", org_id="ORG-TALENT-01")
    assert any(s["skill_name"] == "Python" and "category" in s for s in dash_emp["skills"])

    # 3. Verify user with no skills returns empty list safely without exception
    dash_empty = get_employee_dashboard_data(user_id=99999, employee_id="EMP-NONE", org_id="ORG-TALENT-01")
    assert isinstance(dash_empty["skills"], list)
    assert isinstance(dash_empty["assessments"], list)

def test_23_healthcheck_and_database_backup_resilience():
    """Scenario 23: Production healthcheck, WAL mode, and online database snapshots work cleanly."""
    from services.core import get_connection, check_db_health
    from healthcheck import evaluate_health
    from scripts.db_backup import create_backup, list_backups

    # 1. Verify WAL mode and busy timeout
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode")
        mode = cur.fetchone()[0]
        assert mode.lower() == "wal"
    finally:
        conn.close()

    # 2. Verify healthcheck evaluation
    health = evaluate_health()
    assert "status" in health
    assert "database" in health
    assert health["database"]["connected"] is True
    assert health["database"]["integrity"].lower() == "ok"
    # Verify no employee records or sensitive details leaked in healthcheck
    health_str = str(health)
    assert "password" not in health_str.lower()
    assert "salt" not in health_str.lower()

    # 3. Verify online snapshot backup
    backup_file = create_backup(retention_count=5)
    assert backup_file.exists()
    assert backup_file.stat().st_size > 0
    backups = list_backups()
    assert len(backups) >= 1
    assert any(b["filename"] == backup_file.name for b in backups)


# ----------------- Organization Membership & Dynamic Registration Tests -----------------

def test_24_organization_id_generation_and_case_insensitive_lookup():
    """Scenario 24: Unique organization ID generation and case-insensitive name resolution."""
    org_name = "Horizon Dynamics Corp"
    org_id_1 = generate_unique_org_id(org_name)
    assert org_id_1.startswith("ORG-HORIZOND")

    ok, msg = create_organization(org_id=org_id_1, name=org_name)
    assert ok is True

    # Next generation for same base name should generate sequential candidate
    org_id_2 = generate_unique_org_id(org_name)
    assert org_id_2 != org_id_1
    assert "ORG-HORIZOND" in org_id_2

    # Case-insensitive lookups
    assert get_organization_by_name("horizon dynamics corp") is not None
    assert get_organization_by_name("HORIZON DYNAMICS CORP")["org_id"] == org_id_1
    assert get_organization_by_name("  Horizon Dynamics Corp  ")["name"] == org_name
    assert get_organization_by_name("Nonexistent Org") is None


def test_25_register_new_organization_creates_org_and_unique_id():
    """Scenario 25: Registering with a new organization generates unique ID and associates user."""
    new_org = "Starlight Quantum Systems"
    ok, msg = register(
        name="Sarah Connor",
        email="sarah.c@starlight.com",
        password="Password123",
        role="employee",
        is_new_org=True,
        org_name=new_org,
        department="Engineering",
        job_title="Lead Quantum Engineer"
    )
    assert ok is True
    assert "created successfully" in msg.lower() or "please sign in" in msg.lower()

    # 1. Organization record exists in DB
    found_org = get_organization_by_name(new_org)
    assert found_org is not None
    generated_org_id = found_org["org_id"]
    assert generated_org_id.startswith("ORG-")

    # 2. User record is associated with newly created org
    user_data = login("sarah.c@starlight.com", "Password123")
    assert user_data is not None
    assert user_data["org_id"] == generated_org_id
    assert user_data["org_name"] == new_org

    # 3. User profile and get_user_by_id have correct company and org details
    user_by_id = get_user_by_id(user_data["id"])
    assert user_by_id["org_name"] == new_org
    prof = get_profile(user_data["id"])
    assert prof["company"] == new_org


def test_26_register_duplicate_organization_case_insensitive():
    """Scenario 26: Duplicate organization registration is rejected with case-insensitive check."""
    # Attempt duplicate with lowercase
    ok_dup_lower, msg_lower = register(
        name="John Connor",
        email="john.c@starlight.com",
        password="Password123",
        role="employee",
        is_new_org=True,
        org_name="starlight quantum systems"
    )
    assert ok_dup_lower is False
    assert "already exists" in msg_lower.lower()

    # Attempt duplicate with uppercase and whitespace
    ok_dup_upper, msg_upper = register(
        name="Kyle Reese",
        email="kyle.r@starlight.com",
        password="Password123",
        role="employee",
        is_new_org=True,
        org_name="  STARLIGHT QUANTUM SYSTEMS  "
    )
    assert ok_dup_upper is False
    assert "already exists" in msg_upper.lower()


def test_27_register_new_organization_validation_and_atomic_creation():
    """Scenario 27: Organization name is required for new orgs; org not created on invalid forms."""
    # Empty org name
    ok_empty, msg_empty = register(
        name="Marcus Wright",
        email="marcus@future.com",
        password="Password123",
        role="employee",
        is_new_org=True,
        org_name="   "
    )
    assert ok_empty is False
    assert "organization name is required" in msg_empty.lower()

    # Invalid form submission (short password) should not create org
    org_candidate = "Phantom Innovations Lab"
    ok_fail, _ = register(
        name="Marcus Wright",
        email="marcus@future.com",
        password="short",  # Invalid password
        role="employee",
        is_new_org=True,
        org_name=org_candidate
    )
    assert ok_fail is False
    # Verify organization was NOT created
    assert get_organization_by_name(org_candidate) is None


def test_28_register_with_existing_organization_selection():
    """Scenario 28: Registering with existing organization associates user without duplicating org."""
    orgs_before = len(list_organizations())

    ok, msg = register(
        name="Existing Org Employee",
        email="existing_emp@company.com",
        password="Password123",
        role="employee",
        is_new_org=False,
        org_id="ORG-TALENT-01"
    )
    assert ok is True

    orgs_after = len(list_organizations())
    assert orgs_after == orgs_before  # No new organization created

    user_info = login("existing_emp@company.com", "Password123")
    assert user_info["org_id"] == "ORG-TALENT-01"


def test_29_hr_admin_registration_requires_verification_and_approval():
    """Scenario 29: HR administrator registration requires authorization key or approval."""
    # 1. HR admin registered without valid authorization key
    ok_unverified, msg_unverified = register(
        name="Unverified Admin",
        email="unverified_admin@company.com",
        password="AdminPassword123",
        role="admin",
        require_hr_approval=True,
        hr_verification_code="INVALID_CODE"
    )
    assert ok_unverified is True
    assert "pending verification" in msg_unverified.lower()

    unverified_user = login("unverified_admin@company.com", "AdminPassword123")
    assert unverified_user["status"] == "Pending Approval"

    # 2. Activate via verification function
    ok_act, msg_act = verify_and_activate_hr_admin(unverified_user["id"], "HR2026")
    assert ok_act is True
    verified_user = get_user_by_id(unverified_user["id"])
    assert verified_user["status"] == "Active"

    # 3. HR admin registered directly with valid verification key
    ok_verified, msg_verified = register(
        name="Directly Verified Admin",
        email="verified_admin@company.com",
        password="AdminPassword123",
        role="admin",
        require_hr_approval=True,
        hr_verification_code="HR2026"
    )
    assert ok_verified is True
    directly_verified = login("verified_admin@company.com", "AdminPassword123")
    assert directly_verified["status"] == "Active"


# ----------------- Organization-Based Employee Mapping & HR Management Tests (Scenarios 1 - 13) -----------------

def test_scenario_1_and_2_register_organizations_a_and_b():
    """Scenario 1 & 2: Register Organization A and Organization B with official emails, contacts, and unique IDs."""
    ok_a, msg_a = create_organization(
        org_id="ORG-TEST-AAA",
        name="Apex Global Technologies",
        official_email="contact@apextech.com",
        contact_number="+1-555-0101",
        status="Active"
    )
    assert ok_a is True
    org_a = get_organization("ORG-TEST-AAA")
    assert org_a is not None
    assert org_a["org_id"] == "ORG-TEST-AAA"
    assert org_a["name"] == "Apex Global Technologies"
    assert org_a["status"] == "Active"

    ok_b, msg_b = create_organization(
        org_id="ORG-TEST-BBB",
        name="Beacon Enterprises Inc",
        official_email="info@beaconent.com",
        contact_number="+1-555-0202",
        status="Active"
    )
    assert ok_b is True
    org_b = get_organization("ORG-TEST-BBB")
    assert org_b is not None
    assert org_b["org_id"] == "ORG-TEST-BBB"
    assert org_b["name"] == "Beacon Enterprises Inc"

    # Verify duplicate prevention by case-insensitive name
    dup_name_ok, dup_name_err = create_organization(
        name="apex global technologies",
        official_email="another@apextech.com"
    )
    assert dup_name_ok is False
    assert "already exists" in dup_name_err.lower()


def test_scenario_3_and_4_register_hr_for_org_a_and_org_b():
    """Scenario 3 & 4: Register HR for Organization A and HR for Organization B with authorization verification."""
    # HR A
    ok_hra, _ = register(
        name="HR Leader Alpha",
        email="hr.alpha@apextech.com",
        password="SecureHRPassword123",
        role="admin",
        employee_id="HRA-01",
        org_id="ORG-TEST-AAA",
        require_hr_approval=True,
        hr_verification_code="HR2026"
    )
    assert ok_hra is True
    user_hra = login("hr.alpha@apextech.com", "SecureHRPassword123")
    assert user_hra is not None
    assert user_hra["org_id"] == "ORG-TEST-AAA"
    assert user_hra["role"] == "admin"
    assert user_hra["status"] == "Active"

    # HR B
    ok_hrb, _ = register(
        name="HR Leader Beta",
        email="hr.beta@beaconent.com",
        password="SecureHRPassword123",
        role="admin",
        employee_id="HRB-01",
        org_id="ORG-TEST-BBB",
        require_hr_approval=True,
        hr_verification_code="HR2026"
    )
    assert ok_hrb is True
    user_hrb = login("hr.beta@beaconent.com", "SecureHRPassword123")
    assert user_hrb is not None
    assert user_hrb["org_id"] == "ORG-TEST-BBB"
    assert user_hrb["role"] == "admin"

    # Verify that attempting to register HR with an invalid authorization key flags Pending Approval
    ok_unauth, _ = register(
        name="Imposter HR",
        email="imposter@beaconent.com",
        password="SecureHRPassword123",
        role="admin",
        employee_id="HR-FAKE-01",
        org_id="ORG-TEST-BBB",
        require_hr_approval=True,
        hr_verification_code="WRONG_KEY"
    )
    assert ok_unauth is True
    unauth_user = login("imposter@beaconent.com", "SecureHRPassword123")
    assert unauth_user["status"] == "Pending Approval"


def test_scenario_5_hr_a_generates_employee_invitation_code():
    """Scenario 5: HR A generates an employee invitation code."""
    ok_code, code_data = generate_invitation_code(
        org_id="ORG-TEST-AAA",
        created_by="HR Leader Alpha",
        expiry_days=7,
        max_uses=5
    )
    assert ok_code is True
    assert "code" in code_data
    assert code_data["code"].startswith("INV-")
    assert code_data["max_uses"] == 5
    assert code_data["used_count"] == 0
    assert code_data["status"] == "Active"

    # Validate code resolution
    valid, info = validate_invitation_code(code_data["code"])
    assert valid is True
    assert info["org_id"] == "ORG-TEST-AAA"
    assert info["org_name"] == "Apex Global Technologies"


def test_scenario_6_and_7_employee_joins_using_hr_a_invitation_code_and_maps_to_org_a():
    """Scenario 6 & 7: Employee joins using HR A's invitation code; verify employee is mapped strictly to Org A."""
    ok_code, code_data = generate_invitation_code(
        org_id="ORG-TEST-AAA",
        created_by="HR Leader Alpha",
        expiry_days=7,
        max_uses=2
    )
    invite_code = code_data["code"]

    # Even if client maliciously attempts to submit org_id="ORG-TEST-BBB", backend binds strictly to Org A
    ok_reg, msg_reg = register(
        name="Clara Oswald",
        email="clara@apextech.com",
        password="EmployeePassword123",
        role="employee",
        employee_id="EMP-APEX-01",
        org_id="ORG-TEST-BBB",  # Malicious attempt
        department="Engineering",
        job_title="Software Architect",
        invitation_code=invite_code
    )
    assert ok_reg is True

    # Login and verify mapping
    emp_user = login("clara@apextech.com", "EmployeePassword123")
    assert emp_user is not None
    assert emp_user["org_id"] == "ORG-TEST-AAA"  # Overridden and bound to Org A!
    assert emp_user["employee_id"] == "EMP-APEX-01"

    # Check employee record in database
    emp_record = get_employee_by_id("EMP-APEX-01", org_id="ORG-TEST-AAA")
    assert emp_record is not None
    assert emp_record["org_id"] == "ORG-TEST-AAA"
    assert emp_record["name"] == "Clara Oswald"

    # Verify invitation code used_count incremented
    _, updated_info = validate_invitation_code(invite_code)
    assert updated_info["used_count"] == 1


def test_scenario_8_hr_a_can_view_that_employee():
    """Scenario 8: HR A can view that employee in their organization directory."""
    emp_list = get_employees(org_id="ORG-TEST-AAA")
    matching = [e for e in emp_list if e["employee_id"] == "EMP-APEX-01"]
    assert len(matching) == 1
    assert matching[0]["name"] == "Clara Oswald"
    assert matching[0]["org_id"] == "ORG-TEST-AAA"
    assert matching[0]["designation"] == "Software Architect"


def test_scenario_9_hr_b_cannot_view_that_employee():
    """Scenario 9: HR B cannot view that employee belonging to Org A."""
    # HR B queries their own organization
    hr_b_employees = get_employees(org_id="ORG-TEST-BBB")
    assert not any(e["employee_id"] == "EMP-APEX-01" for e in hr_b_employees)
    assert not any(e["email"] == "clara@apextech.com" for e in hr_b_employees)

    # Direct query targeting Clara under Org B must return None
    cross_lookup = get_employee_by_id("EMP-APEX-01", org_id="ORG-TEST-BBB")
    assert cross_lookup is None


def test_scenario_10_hr_b_cannot_update_or_delete_that_employee():
    """Scenario 10: HR B cannot update or delete employees belonging to another organization."""
    # Attempt update by HR B (scoped with org_id="ORG-TEST-BBB")
    ok_upd, msg_upd = update_employee(
        employee_id="EMP-APEX-01",
        name="Malicious Name Overwrite",
        department="Finance",
        designation="Janitor",
        years_experience=0.0,
        primary_skills="None",
        org_id="ORG-TEST-BBB"  # HR B's tenant scope
    )
    assert ok_upd is False
    assert "not found" in msg_upd.lower()

    # Verify Clara was not altered
    clara_intact = get_employee_by_id("EMP-APEX-01", org_id="ORG-TEST-AAA")
    assert clara_intact["name"] == "Clara Oswald"
    assert clara_intact["department"] == "Engineering"

    # Attempt deletion by HR B
    ok_del, msg_del = delete_employee("EMP-APEX-01", org_id="ORG-TEST-BBB")
    assert ok_del is False

    # Attempt deactivation by HR B
    ok_dea, msg_dea = deactivate_employee("EMP-APEX-01", org_id="ORG-TEST-BBB")
    assert ok_dea is False

    # Verify Clara still exists in Org A
    clara_still_there = get_employee_by_id("EMP-APEX-01", org_id="ORG-TEST-AAA")
    assert clara_still_there is not None


def test_scenario_11_employee_cannot_change_their_organization_id():
    """Scenario 11: Employee cannot modify their organizationId directly."""
    emp_user = login("clara@apextech.com", "EmployeePassword123")
    assert emp_user["org_id"] == "ORG-TEST-AAA"

    # Employee tries to update their profile and inject a new org_id
    save_profile(
        user_id=emp_user["id"],
        data={
            "job_title": "Lead Software Engineer",
            "org_id": "ORG-TEST-BBB",  # Tampering attempt
            "summary": "Specialist in distributed microservices."
        }
    )

    # Reload user and employee records
    reloaded_user = get_user_by_id(emp_user["id"])
    assert reloaded_user["org_id"] == "ORG-TEST-AAA"  # Immutable org_id!

    reloaded_emp = get_employee_by_id("EMP-APEX-01", org_id="ORG-TEST-AAA")
    assert reloaded_emp["org_id"] == "ORG-TEST-AAA"  # Intact!

    # Attempting to call update_employee with employee permissions should also never change org_id
    update_employee(
        employee_id="EMP-APEX-01",
        name="Clara Oswald",
        department="Engineering",
        designation="Lead Engineer",
        years_experience=3.5,
        primary_skills="Python, SQL, Cloud",
        org_id="ORG-TEST-AAA"
    )
    clara_check = get_employee_by_id("EMP-APEX-01", org_id="ORG-TEST-AAA")
    assert clara_check["org_id"] == "ORG-TEST-AAA"


def test_scenario_12_expired_and_revoked_invitation_codes_are_rejected():
    """Scenario 12: Expired and revoked invitation codes must be rejected."""
    # 1. Create a revoked code
    ok_gen, code_data = generate_invitation_code(
        org_id="ORG-TEST-AAA",
        created_by="HR Leader Alpha",
        expiry_days=10,
        max_uses=5
    )
    rev_code = code_data["code"]

    # Revoke it
    ok_rev, _ = revoke_invitation_code(code_data["id"], org_id="ORG-TEST-AAA")
    assert ok_rev is True

    # Validate rejected
    val_rev, rev_info = validate_invitation_code(rev_code)
    assert val_rev is False
    assert "revoked" in rev_info.get("error", "").lower()

    # Attempt registration with revoked code
    ok_reg_rev, msg_reg_rev = register(
        name="Rejected Candidate",
        email="rejected.candidate@apextech.com",
        password="Password123",
        role="employee",
        invitation_code=rev_code
    )
    assert ok_reg_rev is False
    assert "revoked" in msg_reg_rev.lower()

    # 2. Simulate expired code (expiry in the past)
    from services.core import get_connection, hash_invitation_code
    conn = get_connection()
    c = conn.cursor()
    exp_code = "INV-EXPIRED-TEST-CODE"
    c.execute("""
        INSERT INTO invitation_codes (org_id, code_hash, code_prefix, expires_at, max_uses, used_count, status, created_by, created_at)
        VALUES (?, ?, ?, datetime('now', '-2 days'), 10, 0, 'Active', 'HR Admin', datetime('now', '-5 days'))
    """, ("ORG-TEST-AAA", hash_invitation_code(exp_code), "INV-EXP...",))
    conn.commit()
    conn.close()

    val_exp, exp_info = validate_invitation_code(exp_code)
    assert val_exp is False
    assert "expired" in exp_info.get("error", "").lower()


def test_scenario_13_invitation_code_cannot_exceed_usage_limit():
    """Scenario 13: An invitation code must not exceed its maximum usage limit."""
    # Create single-use code
    ok_gen, code_data = generate_invitation_code(
        org_id="ORG-TEST-AAA",
        created_by="HR Leader Alpha",
        expiry_days=7,
        max_uses=1
    )
    single_code = code_data["code"]

    # First employee uses it
    ok1, _ = register(
        name="Lucky Joiner 1",
        email="lucky1@apextech.com",
        password="Password123",
        role="employee",
        employee_id="EMP-LUCKY-01",
        invitation_code=single_code
    )
    assert ok1 is True

    # Code should now be Depleted
    val_dep, dep_info = validate_invitation_code(single_code)
    assert val_dep is False
    assert "maximum" in dep_info.get("error", "").lower() or "depleted" in dep_info.get("error", "").lower()

    # Second employee tries to use it
    ok2, msg2 = register(
        name="Unlucky Joiner 2",
        email="unlucky2@apextech.com",
        password="Password123",
        role="employee",
        employee_id="EMP-UNLUCKY-02",
        invitation_code=single_code
    )
    assert ok2 is False
    assert "maximum" in msg2.lower() or "depleted" in msg2.lower()



