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
os.environ["DATABASE_PATH"] = str(Path(temp_db_dir) / "test_individual.db")

from services.core import (
    init_db, register, register_individual, login, get_user_by_id, get_profile, save_profile,
    list_skills, add_skill, update_skill, delete_skill,
    get_available_assessments, get_assessment_questions, evaluate_assessment, get_skill_assessment_history,
    SKILL_ASSESSMENT_BANK,
    add_goal, get_goals, update_goal, update_goal_progress, delete_goal,
    get_individual_dashboard_stats, join_organization,
    get_employees, get_employee_by_id, get_assessments,
    create_organization, generate_invitation_code, revoke_invitation_code,
    gap_analysis, role_match, ROLE_CATALOG,
    get_membership_requests, approve_membership_request, reject_membership_request,
    get_organization_by_name,
    get_org_dashboard_stats,
    get_recent_email_logs, send_test_email
)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

# ------------------------------------------------------------------------------
# 1. INDIVIDUAL REGISTRATION & ACCOUNT TYPE TESTS
# ------------------------------------------------------------------------------

def test_individual_registration_successful():
    """Verify an individual user can register without organization affiliation."""
    ok, msg = register_individual(
        name="Ananya Sharma",
        email="ananya.sharma@example.com",
        password="SecurePassword@2026",
        phone="+91 98765 43210",
        education="M.Tech in Data Science - IIT Madras",
        interests="Machine Learning, Distributed Systems, Cloud Architecture"
    )
    assert ok is True
    assert "successfully" in msg.lower()

    user = login("ananya.sharma@example.com", "SecurePassword@2026")
    assert user is not None
    assert user["name"] == "Ananya Sharma"
    assert user["email"] == "ananya.sharma@example.com"
    assert user["role"] == "employee"
    assert user["account_type"] == "Individual"
    assert user["org_id"] is None
    assert user["employee_id"] is None

    # Verify profile was seeded with education and interests
    uid = user["id"]
    prof = get_profile(uid)
    assert prof["education"] == "M.Tech in Data Science - IIT Madras"
    assert prof["phone"] == "+91 98765 43210"
    assert "Machine Learning" in prof.get("summary", "") or "Machine Learning" in prof.get("target_role", "")


def test_individual_registration_validation_rules():
    """Verify required fields, email format, password length, and duplicate detection."""
    # Blank name
    ok, msg = register_individual("", "test1@example.com", "Password123")
    assert ok is False
    assert "name is required" in msg.lower()

    # Invalid email
    ok, msg = register_individual("User Name", "invalid-email-format", "Password123")
    assert ok is False
    assert "valid email" in msg.lower()

    # Short password
    ok, msg = register_individual("User Name", "test2@example.com", "123")
    assert ok is False
    assert "at least 6 characters" in msg.lower()

    # Password confirmation mismatch
    ok, msg = register_individual("User Name", "test3@example.com", "Password123", confirm_password="DifferentPassword")
    assert ok is False
    assert "do not match" in msg.lower()

    # Duplicate email
    ok1, _ = register_individual("Original", "duplicate@example.com", "Password123")
    assert ok1 is True
    ok2, msg2 = register_individual("Duplicate", "duplicate@example.com", "AnotherPassword123")
    assert ok2 is False
    assert "already exists" in msg2.lower()


# ------------------------------------------------------------------------------
# 2. INDIVIDUAL LOGIN & USER CONTEXT
# ------------------------------------------------------------------------------

def test_individual_login_context():
    """Verify individual user login returns account_type='Individual' and org_id=None."""
    register_individual("Rohit Verma", "rohit.verma@example.com", "RohitPass2026!")

    user = login("rohit.verma@example.com", "RohitPass2026!")
    assert user is not None
    assert user["name"] == "Rohit Verma"
    assert user["account_type"] == "Individual"
    assert user["org_id"] is None
    assert user["org_name"] is None

    # Invalid password returns None
    assert login("rohit.verma@example.com", "WrongPassword") is None


# ------------------------------------------------------------------------------
# 3. INDIVIDUAL DASHBOARD DATA AGGREGATION
# ------------------------------------------------------------------------------

def test_individual_dashboard_stats_aggregation():
    """Verify aggregated dashboard statistics for an individual user."""
    register_individual("Vikram Das", "vikram.das@example.com", "VikramPass2026!")
    user = login("vikram.das@example.com", "VikramPass2026!")
    uid = user["id"]

    # Initial stats should show base seeded skills and zero assessments
    stats = get_individual_dashboard_stats(uid)
    assert stats["total_skills"] >= 1
    assert stats["completed_assessments"] == 0
    assert stats["average_assessment_score"] == 0.0
    assert stats["avg_assessment_score"] == 0.0
    assert "match_percentage" in stats
    assert "role_readiness" in stats
    assert "goal_avg_progress" in stats
    assert "career_growth_progress" in stats
    assert "role_gaps" in stats
    assert "assessment_history" in stats
    assert isinstance(stats["proficiency_distribution"], dict)
    assert isinstance(stats["recent_activities"], list)
    assert isinstance(stats["skills_missing"], list)


# ------------------------------------------------------------------------------
# 4. PERSONAL SKILLS MANAGEMENT (CRUD & PRACTICAL EXPERIENCE)
# ------------------------------------------------------------------------------

def test_individual_skills_crud():
    """Verify personal skill management: add, edit with notes, and delete."""
    register_individual("Pooja Nair", "pooja.nair@example.com", "PoojaPass2026!")
    user = login("pooja.nair@example.com", "PoojaPass2026!")
    uid = user["id"]

    # 1. Add new skill not in default seed
    ok, msg = add_skill(
        uid=uid,
        name="TypeScript",
        category="Engineering",
        proficiency="Advanced",
        years=3.5,
        description="Developed type-safe frontend microfrontends."
    )
    assert ok is True

    skills = list_skills(uid)
    ts_skill = next((s for s in skills if s["name"] == "TypeScript"), None)
    assert ts_skill is not None
    assert ts_skill["proficiency"] == "Advanced"
    assert ts_skill["years"] == 3.5
    assert ts_skill["description"] == "Developed type-safe frontend microfrontends."

    # 2. Update skill
    ok_up, msg_up = update_skill(
        uid=uid,
        skill_id=ts_skill["id"],
        proficiency="Expert",
        years=5.0,
        category="Frontend Architecture",
        description="Led TypeScript migration across 14 enterprise services."
    )
    assert ok_up is True

    updated_skills = list_skills(uid)
    updated_ts = next((s for s in updated_skills if s["id"] == ts_skill["id"]), None)
    assert updated_ts["proficiency"] == "Expert"
    assert updated_ts["years"] == 5.0
    assert "Led TypeScript migration" in updated_ts["description"]

    # 3. Delete skill
    ok_del = delete_skill(uid=uid, skill_id=ts_skill["id"])
    assert ok_del is True
    assert not any(s["id"] == ts_skill["id"] for s in list_skills(uid))


# ------------------------------------------------------------------------------
# 5. TECHNICAL SKILL ASSESSMENTS & AUTOMATED GRADING
# ------------------------------------------------------------------------------

def test_skill_assessment_evaluation_and_grading():
    """Verify available assessments, technical MCQ question evaluation, and explanations."""
    register_individual("Karthik Rao", "karthik.rao@example.com", "KarthikPass2026!")
    user = login("karthik.rao@example.com", "KarthikPass2026!")
    uid = user["id"]

    available = get_available_assessments()
    assert len(available) >= 8
    assert any(a["skill_name"] == "Python" for a in available)

    questions = get_assessment_questions("Python")
    assert len(questions) >= 5
    for q in questions:
        assert "question" in q
        assert len(q["options"]) == 4

    # Fetch reference bank answers
    bank_questions = SKILL_ASSESSMENT_BANK["Python"]
    user_answers = {
        q["id"]: q["answer"] for q in bank_questions[:-1]
    }
    user_answers[bank_questions[-1]["id"]] = "Intentional Wrong Answer"

    res = evaluate_assessment(uid, "Python", user_answers)
    assert res["total_questions"] == len(bank_questions)
    assert res["correct_answers"] == len(bank_questions) - 1
    assert res["score_percentage"] < 100.0
    assert len(res["breakdown"]) == len(bank_questions)
    assert res["breakdown"][0]["is_correct"] is True
    assert res["breakdown"][-1]["is_correct"] is False
    assert len(res["breakdown"][-1]["explanation"]) > 0

    # Verify assessment is persisted in database
    history = get_skill_assessment_history(uid)
    assert len(history) == 1
    assert history[0]["skill_name"] == "Python"
    assert history[0]["score"] == res["score_percentage"]


def test_assessment_history_improvement_tracking():
    """Verify tracking improvements across multiple attempts for the same skill."""
    register_individual("Neha Patel", "neha.patel@example.com", "NehaPass2026!")
    user = login("neha.patel@example.com", "NehaPass2026!")
    uid = user["id"]

    bank_questions = SKILL_ASSESSMENT_BANK["SQL"]

    # Attempt 1: 3 out of 6 correct (50%)
    ans_attempt1 = {
        bank_questions[0]["id"]: bank_questions[0]["answer"],
        bank_questions[1]["id"]: bank_questions[1]["answer"],
        bank_questions[2]["id"]: bank_questions[2]["answer"],
        bank_questions[3]["id"]: "Wrong 1",
        bank_questions[4]["id"]: "Wrong 2"
    }
    evaluate_assessment(uid, "SQL", ans_attempt1)

    # Attempt 2: all correct (100%)
    ans_attempt2 = {q["id"]: q["answer"] for q in bank_questions}
    evaluate_assessment(uid, "SQL", ans_attempt2)

    history = get_skill_assessment_history(uid)
    assert len(history) == 2
    # Verify both attempts are recorded with scores
    scores = [h["score"] for h in history]
    assert 50.0 in scores
    assert 100.0 in scores


# ------------------------------------------------------------------------------
# 6. SKILL GAP ANALYSIS
# ------------------------------------------------------------------------------

def test_skill_gap_analysis_for_target_role():
    """Verify comparing acquired skills with target role requirements."""
    register_individual("Siddharth Menon", "sid.menon@example.com", "SidPass2026!")
    user = login("sid.menon@example.com", "SidPass2026!")
    uid = user["id"]

    # Add specific skills
    add_skill(uid, "Git", "Tool", "Intermediate", 2.0)

    user_skills = list_skills(uid)
    target_role = "Junior Python Developer"

    match_pct = role_match(target_role, user_skills, years_experience=2.0)
    assert match_pct > 0

    gaps = gap_analysis(target_role, user_skills)
    assert len(gaps) > 0


# ------------------------------------------------------------------------------
# 7. PERSONAL CAREER GOAL MANAGEMENT
# ------------------------------------------------------------------------------

def test_individual_career_goals_lifecycle():
    """Verify creating, updating progress, and completing personal career goals."""
    register_individual("Aakash Gupta", "aakash.gupta@example.com", "AakashPass2026!")
    user = login("aakash.gupta@example.com", "AakashPass2026!")
    uid = user["id"]

    # 1. Add career goal
    ok, msg = add_goal(
        user_id=uid,
        title="Complete AWS Solutions Architect Associate",
        description="Study official guide and complete 5 mock practice exams.",
        target_date="2026-11-30",
        progress=0
    )
    assert ok is True

    goals = get_goals(user_id=uid)
    assert len(goals) >= 1
    gid = goals[0]["id"]

    # 2. Update progress to 50%
    ok_p, _ = update_goal_progress(goal_id=gid, user_id=uid, progress=50)
    assert ok_p is True

    goal = next(g for g in get_goals(user_id=uid) if g["id"] == gid)
    assert goal["progress"] == 50
    assert goal["status"] == "In Progress"

    # 3. Update progress to 100% -> should auto-complete
    update_goal_progress(goal_id=gid, user_id=uid, progress=100)
    goal_done = next(g for g in get_goals(user_id=uid) if g["id"] == gid)
    assert goal_done["progress"] == 100
    assert goal_done["status"] == "Completed"

    # 4. Delete goal
    ok_del, _ = delete_goal(goal_id=gid, user_id=uid)
    assert ok_del is True
    assert not any(g["id"] == gid for g in get_goals(user_id=uid))


# ------------------------------------------------------------------------------
# 8. SECURITY & MULTI-TENANT ISOLATION
# ------------------------------------------------------------------------------

def test_individual_user_corporate_isolation():
    """Verify that an individual user is NEVER listed in corporate employee directories."""
    # 1. Register corporate org
    ok_org, _ = create_organization(org_id="ORG-CORP-ISO", name="Global Tech Solutions", official_email="global_tech@corp.com", contact_number="+1-555-0199")
    assert ok_org is True

    # 2. Register individual user
    register_individual("Maya Sen", "maya.sen@example.com", "MayaPass2026!")

    # 3. Query corporate employees
    corp_employees = get_employees(org_id="ORG-CORP-ISO")
    assert not any(e["email"] == "maya.sen@example.com" for e in corp_employees)


def test_cross_individual_user_isolation():
    """Verify strict isolation between two different individual users."""
    register_individual("User One", "user1@example.com", "Password@1")
    user1 = login("user1@example.com", "Password@1")
    user1_uid = user1["id"]

    register_individual("User Two", "user2@example.com", "Password@2")
    user2 = login("user2@example.com", "Password@2")
    user2_uid = user2["id"]

    add_skill(user1_uid, "Rust", "Systems", "Expert", 5.0)
    add_skill(user2_uid, "Go", "Backend", "Intermediate", 2.0)

    skills1 = list_skills(user1_uid)
    skills2 = list_skills(user2_uid)

    assert any(s["name"] == "Rust" for s in skills1)
    assert not any(s["name"] == "Go" for s in skills1)

    assert any(s["name"] == "Go" for s in skills2)
    assert not any(s["name"] == "Rust" for s in skills2)


# ------------------------------------------------------------------------------
# 9. JOIN AN ORGANIZATION LATER (TRANSITION WORKFLOW)
# ------------------------------------------------------------------------------

def test_join_organization_successful_transition():
    """Verify an individual user can transition to an organization via invitation code while retaining all data."""
    # 1. Setup organization and generate invitation code
    ok_org, _ = create_organization(org_id="ORG-NEXUS-01", name="Nexus Dynamics", official_email="contact@nexusdyn.com", contact_number="+1-555-0144")
    assert ok_org is True

    ok_code, code_res = generate_invitation_code("ORG-NEXUS-01", max_uses=5)
    assert ok_code is True
    code = code_res["code"]

    # 2. Register individual user with skills, assessments, and goals
    register_individual("Devendra Singh", "devendra.singh@example.com", "DevPass2026!")
    user = login("devendra.singh@example.com", "DevPass2026!")
    uid = user["id"]

    add_skill(uid, "React.js", "Frontend", "Advanced", 3.0, "Built enterprise SPA")
    
    bank_react = SKILL_ASSESSMENT_BANK["React"]
    evaluate_assessment(uid, "React", {q["id"]: q["answer"] for q in bank_react})
    
    add_goal(uid, "Lead Frontend Architecture", "Spearhead Next.js migration", "2026-12-31", 25)

    # 3. Join Organization via invitation code
    ok_join, msg_join, _ = join_organization(uid, code)
    assert ok_join is True
    assert "successfully joined" in msg_join.lower()

    # 4. Verify user record has transitioned
    updated_user = get_user_by_id(uid)
    assert updated_user["account_type"] == "Organization"
    assert updated_user["org_id"] == "ORG-NEXUS-01"
    assert updated_user["employee_id"] is not None

    # 5. Verify employee directory contains the newly converted user
    employees = get_employees(org_id="ORG-NEXUS-01")
    emp_record = next((e for e in employees if e["email"] == "devendra.singh@example.com"), None)
    assert emp_record is not None

    # 6. Verify personal data is 100% preserved
    retained_skills = list_skills(uid)
    assert any(s["name"] == "React.js" for s in retained_skills)

    retained_assessments = get_assessments(uid=uid)
    assert len(retained_assessments) >= 1
    assert any(a.get("skill_name") == "React" for a in retained_assessments)

    retained_goals = get_goals(user_id=uid)
    assert len(retained_goals) >= 1
    assert any(g["title"] == "Lead Frontend Architecture" for g in retained_goals)


def test_join_organization_invalid_code_rejected():
    """Verify rejection of invalid or revoked invitation codes."""
    ok_org, _ = create_organization(org_id="ORG-APEX-01", name="Apex Innovations", official_email="hr@apex.com", contact_number="+1-555-0188")
    assert ok_org is True

    ok_code, code_res = generate_invitation_code("ORG-APEX-01", max_uses=1)
    assert ok_code is True
    code = code_res["code"]
    revoke_invitation_code(code_res["id"], org_id="ORG-APEX-01")

    register_individual("Nisha Thomas", "nisha.thomas@example.com", "NishaPass2026!")
    user = login("nisha.thomas@example.com", "NishaPass2026!")
    uid = user["id"]

    # Try revoked code
    ok, msg, _ = join_organization(uid, code)
    assert ok is False
    assert "revoked" in msg.lower()

    # Try completely fake code
    ok_fake, msg_fake, _ = join_organization(uid, "FAKE-NON-EXISTENT-CODE")
    assert ok_fake is False
    assert "invalid" in msg_fake.lower()

    # Account remains unchanged as Individual
    user_check = get_user_by_id(uid)
    assert user_check["account_type"] == "Individual"
    assert user_check["org_id"] is None


# ------------------------------------------------------------------------------
# 5. THREE-OPTION ORGANIZATION MEMBERSHIP REGISTRATION TESTS
# ------------------------------------------------------------------------------

def test_three_option_registration_option1_join_existing_org():
    """Option 1: Join Existing Organization creates pending membership request and approves."""
    # Ensure existing org exists
    org = get_organization_by_name("Talent Growth Technologies")
    assert org is not None
    org_id = org["org_id"]

    # 1. Join with invalid org name fails
    ok_fail, msg_fail = register(
        name="Candidate Nonexistent",
        email="candidate.nonexistent@example.com",
        password="ValidPassword123!",
        registration_type="join_org",
        org_name="Nonexistent Galactic Empire Org"
    )
    assert ok_fail is False
    assert "not found" in msg_fail.lower()

    # 2. Join with valid existing org name succeeds with Pending Approval
    ok, msg = register(
        name="Elena Rostova",
        email="elena.rostova@example.com",
        password="SecurePassword123!",
        registration_type="join_org",
        org_name="Talent Growth Technologies",
        department="Engineering",
        job_title="DevOps Specialist",
        primary_skills="Kubernetes, Terraform, Python"
    )
    assert ok is True
    assert "pending hr administrator approval" in msg.lower() or "submitted" in msg.lower()

    # User record is in Pending Approval status
    user = login("elena.rostova@example.com", "SecurePassword123!")
    assert user is not None
    assert user["status"] == "Pending Approval"
    assert user["role"] == "employee"
    assert user["org_id"] == org_id
    uid = user["id"]

    # 3. Membership request exists and HR Admin can see it
    requests = get_membership_requests(org_id=org_id, status_filter="Pending")
    elena_req = next((r for r in requests if r["user_id"] == uid), None)
    assert elena_req is not None
    assert elena_req["user_name"] == "Elena Rostova"
    assert elena_req["status"] == "Pending"

    # 4. HR Admin approves membership request
    ok_appr, msg_appr = approve_membership_request(elena_req["id"], reviewer_id=1)
    assert ok_appr is True

    # User and employee are now active
    user_active = get_user_by_id(uid)
    assert user_active["status"] == "Active"
    emp = get_employee_by_id(user_active["employee_id"])
    assert emp is not None
    assert emp["account_status"] == "Active"


def test_three_option_registration_option2_register_new_org():
    """Option 2: Register New Organization checks duplicates, creates org, and sets initial HR Admin."""
    org_name = "Solaris Dynamics Corp"

    # 1. Register new organization
    ok, msg = register(
        name="Dr. Chris Kelvin",
        email="kelvin@solaris-dynamics.com",
        password="AdminPassword123!",
        registration_type="new_org",
        org_name=org_name,
        official_email="contact@solaris-dynamics.com",
        contact_number="+1-555-8822",
        department="Executive Leadership",
        job_title="Chief People Officer"
    )
    assert ok is True
    assert "registered successfully" in msg.lower()

    # User is initial HR Admin with status Active
    user = login("kelvin@solaris-dynamics.com", "AdminPassword123!")
    assert user is not None
    assert user["role"] == "admin"
    assert user["status"] == "Active"
    assert user["account_type"] == "Organization"
    new_org_id = user["org_id"]
    assert new_org_id is not None

    # Org record exists
    new_org = get_organization_by_name(org_name)
    assert new_org is not None
    assert new_org["org_id"] == new_org_id
    assert new_org["official_email"] == "contact@solaris-dynamics.com"

    # 2. Check duplicate organization name
    ok_dup, msg_dup = register(
        name="Second Admin",
        email="second.admin@solaris.com",
        password="AdminPassword123!",
        registration_type="new_org",
        org_name=org_name,
        official_email="second@solaris.com"
    )
    assert ok_dup is False
    assert "already exists" in msg_dup.lower()


def test_three_option_registration_option3_individual():
    """Option 3: Individual Registration stores org_id as None and gives immediate access."""
    ok, msg = register(
        name="Rohan Mukherjee",
        email="rohan.mukherjee@freelance.dev",
        password="SecurePass2026!",
        registration_type="individual",
        contact_number="+91 99887 76655",
        education="B.Sc Computer Science",
        interests="Frontend Architecture, Next.js",
        primary_skills="JavaScript, TypeScript, React, CSS"
    )
    assert ok is True
    assert "welcome" in msg.lower() or "successfully" in msg.lower()

    # Login and verify account attributes
    user = login("rohan.mukherjee@freelance.dev", "SecurePass2026!")
    assert user is not None
    assert user["account_type"] == "Individual"
    assert user["org_id"] is None
    assert user["status"] == "Active"

    # Verify skills and profile are immediately available without HR approval
    uid = user["id"]
    skills = list_skills(uid)
    assert len(skills) >= 4
    assert any(s["name"] == "JavaScript" for s in skills)

    profile = get_profile(uid)
    assert profile["education"] == "B.Sc Computer Science"
    assert profile["target_role"] == "Frontend Architecture, Next.js"



def test_employee_joins_org_immediately_in_hr_dashboard():
    """Verifies that when an employee registers under an existing organization,
    they are automatically added into that organization's HR dashboard and workforce directory."""
    org_id = "ORG-TALENT-01"
    org_name = "Talent Growth Technologies"

    # Pre-check stats
    initial_stats = get_org_dashboard_stats(org_id)
    initial_emp_count = initial_stats["total_employees"]

    emp_email = "direct.hire@talentgrowth.com"
    ok, msg = register(
        name="Direct Onboard Employee",
        email=emp_email,
        password="SecurePass2026!",
        role="employee",
        org_id=org_id,
        org_name=org_name,
        department="Engineering",
        job_title="Cloud Engineer",
        primary_skills="Python, GCP, Kubernetes",
        years_experience=2.5,
        require_hr_approval=False
    )
    assert ok is True
    assert "successfully" in msg.lower()

    # Verify user account
    user = login(emp_email, "SecurePass2026!")
    assert user is not None
    assert user["status"] == "Active"
    assert user["org_id"] == org_id
    assert user["role"] == "employee"

    # Verify HR can immediately see the employee in workforce directory
    employees = get_employees(org_id=org_id)
    found_emp = next((e for e in employees if e["email"] == emp_email), None)
    assert found_emp is not None
    assert found_emp["account_status"] == "Active"
    assert found_emp["employment_status"] == "Active"
    assert found_emp["department"] == "Engineering"

    # Verify HR dashboard stats immediately reflect the newly joined employee
    updated_stats = get_org_dashboard_stats(org_id)
    assert updated_stats["total_employees"] == initial_emp_count + 1
    assert updated_stats["active_employees"] >= 1


def test_welcome_email_dispatch_and_logging_on_registration():
    """Verifies that creating an account dispatches and logs a welcome email."""
    test_email = "mail.recipient@example.com"
    ok, msg = register(
        name="Email Test User",
        email=test_email,
        password="TestPassword123!",
        role="employee",
        org_id="ORG-TALENT-01",
        org_name="Talent Growth Technologies"
    )
    assert ok is True
    assert "welcome email" in msg.lower() or "confirmation email" in msg.lower()

    # Verify log entry in email_logs table
    logs = get_recent_email_logs(limit=10)
    matched = next((l for l in logs if l["to_email"] == test_email), None)
    assert matched is not None
    assert matched["user_name"] == "Email Test User"
    assert "welcome" in matched["subject"].lower()

    # Test send_test_email helper
    ok_test, msg_test = send_test_email("tester@company.com")
    assert ok_test is True
