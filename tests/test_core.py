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
    get_org_dashboard_stats, get_employee_dashboard_data,
    hash_password, verify_password
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
