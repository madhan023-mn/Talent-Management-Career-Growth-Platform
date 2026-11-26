"""
Django Views for Talent Growth Platform.
Directly interfaces with MongoDB Atlas via services.core and services.db.
"""
import csv
import json
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages

import services.core as core
from services.reports import create_report

def _require_auth(request):
    """Helper to ensure user is logged in, returns user dict or None."""
    user = request.session.get("user")
    if not user:
        return None
    return user


# ------------------------------------------------------------------------------
# AUTHENTICATION & LANDING VIEWS
# ------------------------------------------------------------------------------
def landing_view(request):
    if request.session.get("user"):
        return redirect('/dashboard/')
    return render(request, 'landing.html')


def login_view(request):
    if request.session.get("user"):
        return redirect('/dashboard/')

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        user = core.login(email, password)
        if user:
            request.session["user"] = user
            messages.success(request, f"Welcome back, {user.get('name')}!")
            return redirect('/dashboard/')
        else:
            messages.error(request, "Invalid email or password. Please verify your credentials.")

    return render(request, 'login.html')


def register_view(request):
    if request.session.get("user"):
        return redirect('/dashboard/')

    if request.method == "POST":
        account_type = request.POST.get("account_type", "Individual")
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'register.html')

        if account_type == "Individual":
            job_title = request.POST.get("job_title", "").strip()
            target_role = request.POST.get("target_role", "").strip()

            success, msg = core.register_individual(
                name=name,
                email=email,
                password=password,
                job_title=job_title,
                target_role=target_role
            )
            if success:
                messages.success(request, msg)
                return redirect('/login/')
            else:
                messages.error(request, msg)
        else:
            org_reg_type = request.POST.get("org_reg_type", "new_org")
            org_name = request.POST.get("org_name", "").strip()
            invitation_code = request.POST.get("invitation_code", "").strip()

            if org_reg_type == "new_org":
                success, msg = core.register(
                    name=name,
                    email=email,
                    password=password,
                    role="admin",
                    org_name=org_name,
                    account_type="Organization"
                )
            else:
                success, msg = core.register(
                    name=name,
                    email=email,
                    password=password,
                    role="employee",
                    invitation_code=invitation_code,
                    account_type="Organization"
                )

            if success:
                messages.success(request, msg)
                return redirect('/login/')
            else:
                messages.error(request, msg)

    return render(request, 'register.html')


def logout_view(request):
    request.session.flush()
    messages.success(request, "You have been signed out.")
    return redirect('/')


# ------------------------------------------------------------------------------
# DASHBOARD VIEWS
# ------------------------------------------------------------------------------
def dashboard_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    role = (user.get("role") or "employee").lower()
    is_admin = (role == "admin")
    is_individual = (user.get("account_type") == "Individual")
    uid = user.get("id")
    org_id = user.get("org_id") or "ORG-TALENT-01"

    if is_admin and not is_individual:
        stats = core.get_org_dashboard_stats(org_id)
        recent_employees = core.get_employees(org_id=org_id)[:5]
        dept_summary = core.get_department_performance_summary(org_id=org_id)

        dept_chart_labels = [d.get("department", "Unit") for d in dept_summary] if dept_summary else ["Engineering", "Product", "Operations", "Sales", "HR"]
        dept_chart_counts = [d.get("employee_count", 1) for d in dept_summary] if dept_summary else [14, 8, 6, 10, 5]

        # Performance score distribution buckets
        perf_data = [35, 50, 15]

        return render(request, 'dashboard_admin.html', {
            "stats": stats,
            "recent_employees": recent_employees,
            "dept_chart_labels": dept_chart_labels,
            "dept_chart_counts": dept_chart_counts,
            "perf_chart_data": perf_data,
        })
    else:
        profile = core.get_profile(uid)
        emp_id = user.get("employee_id")
        emp_dash = core.get_employee_dashboard_data(uid, employee_id=emp_id, org_id=org_id)
        skills = emp_dash.get("skills") or core.list_skills(uid)
        goals = emp_dash.get("goals") or core.get_goals(user_id=uid)

        target_role = profile.get("target_role") or "Senior Full Stack Engineer"
        years_exp = float(profile.get("years_experience") or 2.0)
        score = core.role_match(target_role, skills, years_exp)
        match = {"match_score": score}

        return render(request, 'dashboard_employee.html', {
            "profile": profile,
            "skills": skills,
            "goals": goals,
            "match": match,
            "emp_dash": emp_dash,
        })


# ------------------------------------------------------------------------------
# EMPLOYEE MANAGEMENT VIEWS
# ------------------------------------------------------------------------------
def employees_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    org_id = user.get("org_id") or "ORG-TALENT-01"
    q = request.GET.get("q", "").strip()
    dept = request.GET.get("department", "").strip()
    status = request.GET.get("status", "").strip()

    all_emps = core.get_employees(org_id=org_id)

    # Filter in memory
    filtered = all_emps
    if q:
        q_lower = q.lower()
        filtered = [
            e for e in filtered
            if q_lower in str(e.get("name", "")).lower()
            or q_lower in str(e.get("email", "")).lower()
            or q_lower in str(e.get("employee_id", "")).lower()
        ]
    if dept:
        filtered = [e for e in filtered if e.get("department") == dept]
    if status:
        filtered = [e for e in filtered if e.get("employment_status") == status]

    departments = core.get_all_departments(org_id=org_id)

    return render(request, 'employees.html', {
        "employees": filtered,
        "departments": departments,
        "query": q,
        "selected_dept": dept,
        "selected_status": status,
    })


def employee_add_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    org_id = user.get("org_id") or "ORG-TALENT-01"

    if request.method == "POST":
        emp_id = request.POST.get("employee_id", "").strip().upper()
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        dept = request.POST.get("department", "").strip()
        desig = request.POST.get("designation", "").strip()
        years = float(request.POST.get("years_experience") or 0)
        status = request.POST.get("employment_status", "Active")
        skills = request.POST.get("primary_skills", "").strip()

        success, msg = core.add_employee(
            employee_id=emp_id,
            name=name,
            email=email,
            phone=phone,
            department=dept,
            designation=desig,
            years_experience=years,
            primary_skills=skills,
            employment_status=status,
            org_id=org_id,
            created_by=user.get("id")
        )
        if success:
            messages.success(request, f"Employee {name} added successfully!")
            return redirect('/employees/')
        else:
            messages.error(request, msg)

    departments = core.get_all_departments(org_id=org_id)
    return render(request, 'employee_form.html', {
        "departments": departments,
        "is_edit": False,
    })


def employee_edit_view(request, emp_id):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    org_id = user.get("org_id") or "ORG-TALENT-01"
    emp = core.get_employee_by_id(emp_id, org_id=org_id)
    if not emp:
        messages.error(request, "Employee not found.")
        return redirect('/employees/')

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        dept = request.POST.get("department", "").strip()
        desig = request.POST.get("designation", "").strip()
        years = float(request.POST.get("years_experience") or 0)
        status = request.POST.get("employment_status", "Active")
        skills = request.POST.get("primary_skills", "").strip()

        success, msg = core.update_employee(
            employee_id=emp_id,
            name=name,
            email=email,
            phone=phone,
            department=dept,
            designation=desig,
            years_experience=years,
            primary_skills=skills,
            employment_status=status,
            org_id=org_id
        )
        if success:
            messages.success(request, f"Employee {name} updated successfully!")
            return redirect('/employees/')
        else:
            messages.error(request, msg)

    departments = core.get_all_departments(org_id=org_id)
    return render(request, 'employee_form.html', {
        "employee": emp,
        "departments": departments,
        "is_edit": True,
    })


def employee_delete_view(request, emp_id):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    org_id = user.get("org_id") or "ORG-TALENT-01"
    success, msg = core.delete_employee(emp_id, org_id=org_id)
    if success:
        messages.success(request, f"Employee {emp_id} removed.")
    else:
        messages.error(request, msg)
    return redirect('/employees/')


def employee_export_csv_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    org_id = user.get("org_id") or "ORG-TALENT-01"
    employees = core.get_employees(org_id=org_id)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="workforce_directory.csv"'

    writer = csv.writer(response)
    writer.writerow(['Employee ID', 'Name', 'Email', 'Department', 'Designation', 'Experience (Years)', 'Status', 'Primary Skills'])
    for e in employees:
        writer.writerow([
            e.get('employee_id'),
            e.get('name'),
            e.get('email'),
            e.get('department'),
            e.get('designation'),
            e.get('years_experience'),
            e.get('employment_status'),
            e.get('primary_skills'),
        ])
    return response


# ------------------------------------------------------------------------------
# PERFORMANCE REVIEWS VIEWS
# ------------------------------------------------------------------------------
def performance_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    org_id = user.get("org_id") or "ORG-TALENT-01"
    role = (user.get("role") or "employee").lower()
    is_admin = (role == "admin")
    emp_id = user.get("employee_id")

    if is_admin:
        reviews = core.get_performance_reviews(org_id=org_id)
    else:
        reviews = core.get_performance_reviews(employee_id=emp_id, org_id=org_id) if emp_id else []

    return render(request, 'performance.html', {
        "reviews": reviews,
    })


def performance_add_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    if request.method == "POST":
        org_id = user.get("org_id") or "ORG-TALENT-01"
        emp_id = request.POST.get("employee_id", "").strip().upper()
        period = request.POST.get("review_period", "").strip()
        score = float(request.POST.get("performance_score") or 4.0)
        achieve = request.POST.get("achievements", "").strip()
        strengths = request.POST.get("strengths", "").strip()
        improvements = request.POST.get("improvements", "").strip()

        success, msg = core.add_performance_review(
            employee_id=emp_id,
            review_period=period,
            performance_score=score,
            achievements=achieve,
            strengths=strengths,
            improvements=improvements,
            org_id=org_id,
            reviewer_id=user.get("id")
        )
        if success:
            messages.success(request, f"Review for {emp_id} recorded successfully!")
        else:
            messages.error(request, msg)

    return redirect('/performance/')


# ------------------------------------------------------------------------------
# SKILLS & ASSESSMENTS VIEWS
# ------------------------------------------------------------------------------
def skills_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    org_id = user.get("org_id") or "ORG-TALENT-01"
    emp_id = user.get("employee_id")

    skills = core.get_employee_skills(emp_id, org_id=org_id) if emp_id else core.list_skills(uid)
    assessments = core.get_assessments(uid=uid, employee_id=emp_id, org_id=org_id)

    return render(request, 'skills.html', {
        "skills": skills,
        "assessments": assessments,
    })


def skill_add_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    if request.method == "POST":
        uid = user.get("id")
        org_id = user.get("org_id") or "ORG-TALENT-01"
        emp_id = user.get("employee_id")
        name = request.POST.get("skill_name", "").strip()
        cat = request.POST.get("category", "Technical").strip()
        prof = request.POST.get("proficiency", "Intermediate").strip()
        years = float(request.POST.get("years") or 1.0)

        if emp_id:
            success, msg = core.add_employee_skill(
                employee_id=emp_id,
                skill_name=name,
                category=cat,
                proficiency_level=prof,
                years_exp=years,
                org_id=org_id,
                user_id=uid
            )
        else:
            success, msg = core.add_skill(
                user_id=uid,
                name=name,
                category=cat,
                proficiency=prof,
                years=years
            )

        if success:
            messages.success(request, f"Skill '{name}' added successfully!")
        else:
            messages.error(request, msg)

    return redirect('/skills/')


def skill_delete_view(request, skill_id):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    emp_id = user.get("employee_id")
    org_id = user.get("org_id") or "ORG-TALENT-01"

    if emp_id:
        core.delete_employee_skill(emp_id, skill_name=skill_id, org_id=org_id)
    else:
        try:
            core.delete_skill(uid, int(skill_id))
        except Exception:
            pass

    messages.success(request, "Skill removed.")
    return redirect('/skills/')


def assessment_add_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    if request.method == "POST":
        uid = user.get("id")
        org_id = user.get("org_id") or "ORG-TALENT-01"
        emp_id = user.get("employee_id") or ""
        cat = request.POST.get("category", "").strip()
        skill = request.POST.get("skill_name", "").strip()
        score = float(request.POST.get("score") or 4.0)
        notes = request.POST.get("notes", "").strip()

        core.add_assessment(
            user_id=uid,
            category=cat,
            score=score,
            notes=notes,
            employee_id=emp_id,
            org_id=org_id,
            skill_name=skill
        )
        messages.success(request, "Assessment submitted successfully!")

    return redirect('/skills/')


# ------------------------------------------------------------------------------
# CAREER GOALS VIEWS
# ------------------------------------------------------------------------------
def goals_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    org_id = user.get("org_id") or "ORG-TALENT-01"
    emp_id = user.get("employee_id")

    goals = core.get_goals(user_id=uid, employee_id=emp_id, org_id=org_id)
    return render(request, 'goals.html', {"goals": goals})


def goal_add_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    if request.method == "POST":
        uid = user.get("id")
        org_id = user.get("org_id") or "ORG-TALENT-01"
        emp_id = user.get("employee_id") or ""
        title = request.POST.get("title", "").strip()
        desig = request.POST.get("target_designation", "").strip()
        tdate = request.POST.get("target_date", "").strip()
        prog = int(request.POST.get("progress") or 0)
        desc = request.POST.get("description", "").strip()

        success, msg = core.add_goal(
            user_id=uid,
            title=title,
            target_date=tdate,
            description=desc,
            employee_id=emp_id,
            org_id=org_id,
            target_designation=desig,
            progress=prog
        )
        if success:
            messages.success(request, f"Career goal '{title}' created!")
        else:
            messages.error(request, msg)

    return redirect('/goals/')


def goal_update_view(request, goal_id):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    if request.method == "POST":
        uid = user.get("id")
        prog = int(request.POST.get("progress") or 0)
        core.update_goal_progress(int(goal_id), prog, user_id=uid)
        messages.success(request, "Goal progress updated.")

    return redirect('/goals/')


def goal_delete_view(request, goal_id):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    core.delete_goal(int(goal_id), user_id=uid)
    messages.success(request, "Goal removed.")
    return redirect('/goals/')


# ------------------------------------------------------------------------------
# ROLE MATCH & CAREER COACH VIEWS
# ------------------------------------------------------------------------------
def role_match_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    profile = core.get_profile(uid)
    skills = core.list_skills(uid)
    years_exp = float(profile.get("years_experience") or 2.0)

    role_catalog = core.ROLE_CATALOG
    selected_role = request.GET.get("role") or profile.get("target_role") or list(role_catalog.keys())[0]

    score = core.role_match(selected_role, skills, years_exp)
    gaps = core.gap_analysis(selected_role, skills)
    matched_skills = [g.get("skill") for g in gaps if g.get("gap", 0) == 0]
    missing_skills = [g.get("skill") for g in gaps if g.get("gap", 0) > 0]

    return render(request, 'role_match.html', {
        "role_catalog": role_catalog.keys(),
        "selected_role": selected_role,
        "match_score": score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "total_required": len(gaps),
    })


def career_coach_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    profile = core.get_profile(uid)
    skills = core.list_skills(uid)

    recs = core.recommendations(profile, skills)
    tips = [
        {"title": r.get("title", "Growth Milestone"), "description": r.get("description", ""), "category": r.get("category", "Coaching Insight")}
        for r in recs
    ] if recs else [
        {
            "title": "Deepen Distributed System Architecture",
            "description": "Lead cross-functional technical specifications and scale container deployments to demonstrate senior technical mastery.",
            "category": "Architecture"
        },
        {
            "title": "Establish Mentorship Cadence",
            "description": "Pair with junior colleagues and facilitate architecture reviews to satisfy leadership benchmarks.",
            "category": "Leadership"
        }
    ]

    return render(request, 'career_coach.html', {"tips": tips})


# ------------------------------------------------------------------------------
# PROFILE VIEWS
# ------------------------------------------------------------------------------
def profile_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    profile = core.get_profile(uid)
    return render(request, 'profile.html', {"profile": profile})


def profile_save_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    if request.method == "POST":
        uid = user.get("id")
        fields = {
            "phone": request.POST.get("phone", "").strip(),
            "location": request.POST.get("location", "").strip(),
            "job_title": request.POST.get("job_title", "").strip(),
            "target_role": request.POST.get("target_role", "").strip(),
            "target_level": request.POST.get("target_level", "Senior").strip(),
            "years_experience": float(request.POST.get("years_experience") or 0),
            "summary": request.POST.get("summary", "").strip(),
            "linkedin": request.POST.get("linkedin", "").strip(),
            "github": request.POST.get("github", "").strip(),
            "portfolio": request.POST.get("portfolio", "").strip(),
        }
        core.save_profile(uid, fields)
        messages.success(request, "Profile updated successfully!")

    return redirect('/profile/')


# ------------------------------------------------------------------------------
# ATS RESUME STUDIO VIEWS
# ------------------------------------------------------------------------------
def resume_studio_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    profile = core.get_profile(uid)
    resume = core.get_resume(uid)

    if request.method == "POST":
        summary = request.POST.get("summary", "").strip()
        skills_str = request.POST.get("skills_str", "").strip()
        exp_text = request.POST.get("experience_text", "").strip()
        edu_text = request.POST.get("education_text", "").strip()

        skills_list = [s.strip() for s in skills_str.split(",") if s.strip()]
        core.save_resume(
            user_id=uid,
            summary=summary,
            skills=skills_list,
            experience=exp_text,
            education=edu_text
        )
        messages.success(request, "Resume profile saved successfully!")
        resume = core.get_resume(uid)

    raw_skills = resume.get("skills", [])
    if isinstance(raw_skills, list):
        skills_str = ", ".join([
            s if isinstance(s, str) else str(s.get("name") or s.get("skill_name") or "")
            for s in raw_skills
        ])
    else:
        skills_str = str(raw_skills)

    return render(request, 'resume_studio.html', {
        "profile": profile,
        "resume": resume,
        "skills_str": skills_str,
    })


def resume_export_pdf_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    profile = core.get_profile(uid)
    resume = core.get_resume(uid)

    user_info = {
        "name": user.get("name"),
        "email": user.get("email"),
        "phone": profile.get("phone", ""),
        "location": profile.get("location", ""),
        "target_role": profile.get("target_role", "Software Engineer"),
    }

    pdf_bytes = core.generate_resume_pdf(resume, user_info)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    safe_name = user.get("name", "Candidate").replace(" ", "_")
    response['Content-Disposition'] = f'attachment; filename="{safe_name}_Resume.pdf"'
    return response


def resume_sync_skills_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    core.import_skills_to_resume(uid)
    messages.success(request, "Skills successfully imported into resume profile!")
    return redirect('/resume-studio/')


# ------------------------------------------------------------------------------
# REPORTS & PDF VIEWS
# ------------------------------------------------------------------------------
def reports_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    profile = core.get_profile(uid)
    skills = core.list_skills(uid)
    match = core.role_match(profile.get("target_role", "Software Engineer"), skills)

    return render(request, 'reports.html', {
        "profile": profile,
        "match": match,
    })


def report_pdf_download_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    org_id = user.get("org_id") or "ORG-TALENT-01"
    profile = core.get_profile(uid)
    skills = core.list_skills(uid)
    analysis = core.profile_analysis(profile, skills)
    gaps = core.gap_analysis(profile.get("target_role", "Software Engineer"), skills)
    recs = core.recommendations(profile, skills)
    goals = core.get_goals(user_id=uid)
    reviews = core.get_performance_reviews(employee_id=user.get("employee_id"), org_id=org_id) if user.get("employee_id") else []

    pdf_bytes = create_report(
        profile=profile,
        skills=skills,
        analysis=analysis,
        gaps=gaps,
        recommendations=recs,
        goals=goals,
        reviews=reviews,
        org_id=org_id
    )

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    safe_name = user.get("name", "Career").replace(" ", "_")
    response['Content-Disposition'] = f'attachment; filename="{safe_name}_Career_Report.pdf"'
    return response


# ------------------------------------------------------------------------------
# SETTINGS & ORGANIZATION VIEWS
# ------------------------------------------------------------------------------
def settings_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    return render(request, 'settings.html')


def invite_code_generate_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    org_id = user.get("org_id") or "ORG-TALENT-01"
    if request.method == "POST":
        max_uses = int(request.POST.get("max_uses") or 1)
        days = int(request.POST.get("days") or 14)
        success, code, msg = core.generate_invitation_code(
            org_id=org_id,
            created_by=str(user.get("id")),
            expires_days=days,
            max_uses=max_uses
        )
        if success:
            messages.success(request, f"New invitation code generated: {code}")
            return render(request, 'settings.html', {"generated_code": code})
        else:
            messages.error(request, msg)

    return redirect('/settings/')


def join_organization_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        uid = user.get("id")

        valid, org_id, msg = core.validate_invitation_code(code)
        if valid and org_id:
            # Upgrade user to organization member
            conn = core.get_connection()
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET org_id = ?, account_type = 'Organization' WHERE id = ?",
                    (org_id, uid)
                )
            user["org_id"] = org_id
            user["account_type"] = "Organization"
            request.session["user"] = user
            messages.success(request, f"Successfully joined organization {org_id}!")
        else:
            messages.error(request, msg or "Invalid or expired invitation code.")

    return redirect('/settings/')
