"""
Django Views for Talent Growth Platform.
Directly interfaces with MongoDB Atlas via services.core, services.settings,
services.reports, and services.ai_coach.
"""
import io
import csv
import json
import pandas as pd
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages

import services.core as core
import services.settings as settings_svc
import services.reports as reports_svc
import services.ai_coach as ai_coach_svc


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
                    account_type="Organization",
                    invitation_code=invitation_code
                )

            if success:
                messages.success(request, msg)
                return redirect('/login/')
            else:
                messages.error(request, msg)

    return render(request, 'register.html')


def logout_view(request):
    request.session.flush()
    messages.info(request, "You have been logged out.")
    return redirect('/')


# ------------------------------------------------------------------------------
# DASHBOARD VIEWS
# ------------------------------------------------------------------------------
def dashboard_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    org_id = user.get("org_id") or "ORG-TALENT-01"
    role = (user.get("role") or "employee").lower()
    is_admin = (role == "admin")
    is_individual = (user.get("account_type") == "Individual")
    emp_id = user.get("employee_id")

    if is_admin:
        stats = core.get_org_dashboard_stats(org_id)
        recent_employees = core.get_employees(org_id=org_id)[:6]
        departments = core.get_all_departments(org_id=org_id)
        dept_summary = core.get_department_performance_summary(org_id=org_id)
        pending_requests = core.get_membership_requests(org_id, status_filter="pending")

        return render(request, 'dashboard_admin.html', {
            "stats": stats,
            "recent_employees": recent_employees,
            "departments": departments,
            "dept_summary": dept_summary,
            "pending_requests_count": len(pending_requests),
        })
    else:
        profile = core.get_profile(uid)
        skills = core.list_skills(uid)
        goals = core.get_goals(user_id=uid)
        emp_dash = core.get_employee_dashboard_data(uid, emp_id, org_id)

        target_role = profile.get("target_role") or "Software Engineer"
        years_exp = float(profile.get("years_experience") or 2.0)
        score = core.role_match(target_role, skills, years_exp)
        gaps = core.gap_analysis(target_role, skills)

        return render(request, 'dashboard_employee.html', {
            "profile": profile,
            "skills": skills,
            "goals": goals,
            "match": {"match_score": score, "target_role": target_role},
            "gaps": gaps,
            "emp_dash": emp_dash,
            "is_individual": is_individual,
        })


# ------------------------------------------------------------------------------
# EMPLOYEE MANAGEMENT VIEWS (6 FULL TABS)
# ------------------------------------------------------------------------------
def employees_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    org_id = user.get("org_id") or "ORG-TALENT-01"
    q = request.GET.get("q", "").strip()
    dept = request.GET.get("department", "").strip()
    status = request.GET.get("status", "").strip()
    active_tab = request.GET.get("tab", "tab_dir")

    all_emps = core.get_employees(org_id=org_id)

    # Filter directory
    filtered = all_emps
    if q:
        q_lower = q.lower()
        filtered = [
            e for e in filtered
            if q_lower in str(e.get("name", "")).lower()
            or q_lower in str(e.get("email", "")).lower()
            or q_lower in str(e.get("employee_id", "")).lower()
            or q_lower in str(e.get("primary_skills", "")).lower()
        ]
    if dept:
        filtered = [e for e in filtered if e.get("department") == dept]
    if status:
        filtered = [e for e in filtered if e.get("employment_status") == status]

    departments = core.get_all_departments(org_id=org_id)
    designations = core.get_all_designations(org_id=org_id)
    invitation_codes = core.list_invitation_codes(org_id)
    membership_requests = core.get_membership_requests(org_id)
    sample_csv = core.get_sample_employee_csv()

    return render(request, 'employees.html', {
        "employees": filtered,
        "all_employees": all_emps,
        "departments": departments,
        "designations": designations,
        "invitation_codes": invitation_codes,
        "membership_requests": membership_requests,
        "sample_csv": sample_csv,
        "query": q,
        "selected_dept": dept,
        "selected_status": status,
        "active_tab": active_tab,
        "total_count": len(all_emps),
        "active_count": sum(1 for e in all_emps if e.get("employment_status") == "Active"),
        "on_leave_count": sum(1 for e in all_emps if e.get("employment_status") == "On Leave"),
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
        salary = float(request.POST.get("salary") or 75000.0)
        years = float(request.POST.get("years_experience") or 0.0)
        status = request.POST.get("employment_status", "Active")
        skills = request.POST.get("primary_skills", "").strip()
        join_date = request.POST.get("join_date", "").strip() or datetime.now().strftime("%Y-%m-%d")

        success, msg = core.add_employee(
            employee_id=emp_id,
            name=name,
            email=email,
            phone=phone,
            department=dept,
            designation=desig,
            years_experience=years,
            salary=salary,
            join_date=join_date,
            primary_skills=skills,
            employment_status=status,
            org_id=org_id,
            created_by=user.get("id")
        )
        if success:
            messages.success(request, f"Employee {name} ({emp_id}) added successfully!")
            return redirect('/employees/?tab=tab_dir')
        else:
            messages.error(request, msg)
            return redirect('/employees/?tab=tab_add')

    return redirect('/employees/?tab=tab_add')


def employee_bulk_import_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    org_id = user.get("org_id") or "ORG-TALENT-01"
    if request.method == "POST" and request.FILES.get("csv_file"):
        csv_file = request.FILES["csv_file"]
        try:
            df = pd.read_csv(csv_file)
            result = core.bulk_import_employees_df(df, created_by=user.get("id"), org_id=org_id)
            if result.get("success"):
                messages.success(request, f"Successfully imported {result.get('imported', 0)} employees! (Skipped: {result.get('skipped', 0)})")
            else:
                messages.error(request, f"Import completed with errors: {result.get('error', 'Validation failed')}")
        except Exception as e:
            messages.error(request, f"Failed to parse CSV file: {str(e)}")

    return redirect('/employees/?tab=tab_bulk')


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
        salary = float(request.POST.get("salary") or emp.get("salary", 75000.0))
        years = float(request.POST.get("years_experience") or 0.0)
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
            salary=salary,
            primary_skills=skills,
            employment_status=status,
            org_id=org_id
        )
        if success:
            messages.success(request, f"Employee {name} updated successfully!")
            return redirect('/employees/?tab=tab_dir')
        else:
            messages.error(request, msg)

    departments = core.get_all_departments(org_id=org_id)
    designations = core.get_all_designations(org_id=org_id)
    return render(request, 'employee_form.html', {
        "employee": emp,
        "departments": departments,
        "designations": designations,
        "is_edit": True,
    })


def employee_deactivate_view(request, emp_id):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    org_id = user.get("org_id") or "ORG-TALENT-01"
    success, msg = core.deactivate_employee(emp_id, org_id=org_id)
    if success:
        messages.success(request, f"Employee {emp_id} deactivated successfully.")
    else:
        messages.error(request, msg)
    return redirect('/employees/?tab=tab_edit')


def employee_delete_view(request, emp_id):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    org_id = user.get("org_id") or "ORG-TALENT-01"
    success, msg = core.delete_employee(emp_id, org_id=org_id)
    if success:
        messages.success(request, f"Employee {emp_id} permanently removed.")
    else:
        messages.error(request, msg)
    return redirect('/employees/?tab=tab_dir')


def employee_export_csv_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    org_id = user.get("org_id") or "ORG-TALENT-01"
    employees = core.get_employees(org_id=org_id)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="workforce_directory.csv"'

    writer = csv.writer(response)
    writer.writerow(['Employee ID', 'Name', 'Email', 'Phone', 'Department', 'Designation', 'Salary', 'Experience (Years)', 'Status', 'Primary Skills'])
    for e in employees:
        writer.writerow([
            e.get('employee_id'),
            e.get('name'),
            e.get('email'),
            e.get('phone', ''),
            e.get('department'),
            e.get('designation'),
            e.get('salary', ''),
            e.get('years_experience'),
            e.get('employment_status'),
            e.get('primary_skills'),
        ])
    return response


# ------------------------------------------------------------------------------
# INVITATION CODES & MEMBERSHIP REQUESTS
# ------------------------------------------------------------------------------
def invite_code_generate_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    org_id = user.get("org_id") or "ORG-TALENT-01"
    if request.method == "POST":
        max_uses = int(request.POST.get("max_uses") or 1)
        days = int(request.POST.get("days") or 14)

        success, res = core.generate_invitation_code(
            org_id=org_id,
            created_by=user.get("id"),
            expiry_days=days,
            max_uses=max_uses
        )
        if success:
            code = res.get("code") if isinstance(res, dict) else str(res)
            messages.success(request, f"Generated invitation code: {code}")
        else:
            messages.error(request, "Failed to generate invitation code.")

    return redirect('/employees/?tab=tab_invite')


def invite_code_revoke_view(request, code_id):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    org_id = user.get("org_id") or "ORG-TALENT-01"
    success, msg = core.revoke_invitation_code(code_id, org_id)
    if success:
        messages.success(request, "Invitation code revoked.")
    else:
        messages.error(request, msg)
    return redirect('/employees/?tab=tab_invite')


def membership_request_approve_view(request, request_id):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    success, msg = core.approve_membership_request(request_id, reviewer_id=user.get("id"))
    if success:
        messages.success(request, "Membership request approved!")
    else:
        messages.error(request, msg)
    return redirect('/employees/?tab=tab_requests')


def membership_request_reject_view(request, request_id):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    success, msg = core.reject_membership_request(request_id, reviewer_id=user.get("id"))
    if success:
        messages.info(request, "Membership request rejected.")
    else:
        messages.error(request, msg)
    return redirect('/employees/?tab=tab_requests')


# ------------------------------------------------------------------------------
# PERFORMANCE REVIEWS & ANALYTICS VIEWS
# ------------------------------------------------------------------------------
def performance_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    org_id = user.get("org_id") or "ORG-TALENT-01"
    role = (user.get("role") or "employee").lower()
    is_admin = (role == "admin")
    emp_id = user.get("employee_id")
    active_tab = request.GET.get("tab", "tab_rev_list")

    if is_admin:
        reviews = core.get_performance_reviews(org_id=org_id)
        all_emps = core.get_employees(org_id=org_id)
        dept_summary = core.get_department_performance_summary(org_id=org_id)
    else:
        reviews = core.get_performance_reviews(employee_id=emp_id, org_id=org_id) if emp_id else []
        all_emps = []
        dept_summary = []

    return render(request, 'performance.html', {
        "reviews": reviews,
        "employees": all_emps,
        "dept_summary": dept_summary,
        "is_admin": is_admin,
        "active_tab": active_tab,
        "avg_score": round(sum(float(r.get("performance_score") or 0) for r in reviews) / max(len(reviews), 1), 2),
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

    return redirect('/performance/?tab=tab_rev_list')


# ------------------------------------------------------------------------------
# SKILLS, ASSESSMENTS & TRAINING VIEWS
# ------------------------------------------------------------------------------
def skills_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    org_id = user.get("org_id") or "ORG-TALENT-01"
    role = (user.get("role") or "employee").lower()
    is_admin = (role == "admin")
    emp_id = user.get("employee_id")
    active_tab = request.GET.get("tab", "tab_sk_matrix" if is_admin else "tab_emp_skills")

    if is_admin:
        all_skills = core.get_employee_skills(org_id=org_id)
        assessments = core.get_assessments(org_id=org_id)
        employees = core.get_employees(org_id=org_id)
        trainings = core.get_training_records(org_id=org_id)
        all_mcq_available = []
        mcq_history = []
    else:
        all_skills = core.get_employee_skills(emp_id, org_id=org_id) if emp_id else core.list_skills(uid)
        assessments = core.get_assessments(uid=uid, employee_id=emp_id, org_id=org_id)
        employees = []
        trainings = core.get_training_records(employee_id=emp_id, org_id=org_id) if emp_id else []
        all_mcq_available = core.get_available_assessments()
        mcq_history = core.get_skill_assessment_history(uid)

    return render(request, 'skills.html', {
        "skills": all_skills,
        "assessments": assessments,
        "employees": employees,
        "trainings": trainings,
        "is_admin": is_admin,
        "all_mcq_available": all_mcq_available,
        "mcq_history": mcq_history,
        "active_tab": active_tab,
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

        target_emp = request.POST.get("target_employee_id") or emp_id
        if target_emp:
            success, msg = core.add_employee_skill(
                employee_id=target_emp,
                skill_name=name,
                category=cat,
                proficiency_level=prof,
                years_exp=years,
                org_id=org_id,
                user_id=uid
            )
        else:
            success, msg = core.add_skill(
                uid=uid,
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
        core.delete_employee_skill(skill_id, employee_id=emp_id, org_id=org_id)
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
        emp_id = request.POST.get("employee_id") or user.get("employee_id") or ""
        cat = request.POST.get("category", "Technical").strip()
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
        messages.success(request, f"Assessment for '{skill}' recorded!")

    return redirect('/skills/?tab=tab_sk_assessments')


def skill_mcq_test_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    skill_name = request.GET.get("skill", "Python")
    questions = core.get_assessment_questions(skill_name)
    return JsonResponse({"skill": skill_name, "questions": questions})


def skill_mcq_submit_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    if request.method == "POST":
        uid = user.get("id")
        skill_name = request.POST.get("skill_name", "Python")
        answers = {}
        for k, v in request.POST.items():
            if k.startswith("q_"):
                try:
                    q_idx = int(k.replace("q_", ""))
                    answers[q_idx] = int(v)
                except Exception:
                    pass

        result = core.evaluate_assessment(uid, skill_name, answers)
        pct = result.get("score_percent", 0)
        if result.get("passed"):
            messages.success(request, f"🎉 Congratulations! You scored {pct}% on the {skill_name} Assessment. Verification recorded!")
        else:
            messages.warning(request, f"You scored {pct}% on the {skill_name} Assessment. Review recommended areas and re-test.")

    return redirect('/skills/?tab=tab_emp_mcq')


def training_record_add_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    org_id = user.get("org_id") or "ORG-TALENT-01"
    if request.method == "POST":
        emp_id = request.POST.get("employee_id", "").strip().upper()
        title = request.POST.get("training_title", "").strip()
        provider = request.POST.get("provider", "").strip()
        comp_date = request.POST.get("completion_date", "").strip() or datetime.now().strftime("%Y-%m-%d")
        status = request.POST.get("status", "Completed")

        success, msg = core.add_training_record(
            employee_id=emp_id,
            training_title=title,
            provider=provider,
            completion_date=comp_date,
            status=status,
            org_id=org_id
        )
        if success:
            messages.success(request, f"Training record '{title}' added for {emp_id}!")
        else:
            messages.error(request, msg)

    return redirect('/skills/?tab=tab_sk_train')


# ------------------------------------------------------------------------------
# CAREER GOALS VIEWS (3 TABS)
# ------------------------------------------------------------------------------
def goals_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    org_id = user.get("org_id") or "ORG-TALENT-01"
    emp_id = user.get("employee_id")
    active_tab = request.GET.get("tab", "tab_g_view")

    goals = core.get_goals(user_id=uid, employee_id=emp_id, org_id=org_id)
    designations = core.get_all_designations(org_id=org_id)

    return render(request, 'goals.html', {
        "goals": goals,
        "designations": designations,
        "active_tab": active_tab,
        "total_goals": len(goals),
        "completed_goals": sum(1 for g in goals if (g.get("progress") or 0) >= 100),
    })


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

    return redirect('/goals/?tab=tab_g_view')


def goal_update_view(request, goal_id):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    if request.method == "POST":
        uid = user.get("id")
        prog = int(request.POST.get("progress") or 0)
        core.update_goal_progress(int(goal_id), uid, prog)
        messages.success(request, "Goal progress updated.")

    return redirect('/goals/?tab=tab_g_view')


def goal_delete_view(request, goal_id):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    core.delete_goal(int(goal_id), user_id=uid)
    messages.success(request, "Goal removed.")
    return redirect('/goals/?tab=tab_g_edit')


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
    benchmark_criteria = role_catalog.get(selected_role, {}).get("criteria", "Strong domain mastery and architectural execution.")

    return render(request, 'role_match.html', {
        "role_catalog": role_catalog.keys(),
        "selected_role": selected_role,
        "match_score": score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "gaps": gaps,
        "benchmark_criteria": benchmark_criteria,
    })


def career_coach_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    profile = core.get_profile(uid)
    skills = core.list_skills(uid)
    recs = core.recommendations(profile, skills)
    starter_prompts = [
        "What specific competencies should I focus on to achieve Senior Engineer?",
        "How can I build evidence for technical leadership and system architecture?",
        "Generate a 90-day action plan for my target career goal.",
        "What are the highest impact project milestones I can initiate?"
    ]

    return render(request, 'career_coach.html', {
        "profile": profile,
        "tips": recs,
        "starter_prompts": starter_prompts,
    })


def career_coach_chat_api(request):
    user = _require_auth(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    if request.method == "POST":
        uid = user.get("id")
        user_msg = request.POST.get("message", "").strip()
        profile = core.get_profile(uid)
        skills = core.list_skills(uid)
        goals = core.get_goals(user_id=uid)

        # Build a prompt that includes user message
        coaching_prompt = f"User question: {user_msg}"
        try:
            response_text = ai_coach_svc.generate_ai_coaching_guidance(
                profile=profile,
                skills=skills,
                goals=goals
            )
            # If a user message was provided, prepend it as context via raw API
            if user_msg:
                raw_resp = ai_coach_svc.call_gemini_api(
                    f"You are an AI career coach. The user asked: {user_msg}\n\nUser profile: {profile}\nSkills: {skills}\nGoals: {goals}\n\nProvide a concise, helpful career coaching response."
                )
                if raw_resp and len(raw_resp) > 20:
                    response_text = raw_resp
        except Exception:
            response_text = (
                f"Based on your profile, here are some career development recommendations:\n\n"
                f"Focus on building skills aligned with your target role. "
                f"Set clear SMART goals and track progress consistently. "
                f"Seek mentorship and continuous learning opportunities."
            )
        return JsonResponse({"reply": response_text})

    return JsonResponse({"error": "Method not allowed"}, status=405)


# ------------------------------------------------------------------------------
# PROFILE VIEWS
# ------------------------------------------------------------------------------
def profile_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    profile = core.get_profile(uid)
    skills = core.list_skills(uid)
    pct, missing = core.profile_completion(profile, skills)

    return render(request, 'profile.html', {
        "profile": profile,
        "completion_pct": pct,
        "missing_fields": missing,
        "role_catalog": core.ROLE_CATALOG.keys(),
    })


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
            "years_experience": float(request.POST.get("years_experience") or 0.0),
            "summary": request.POST.get("summary", "").strip(),
            "linkedin": request.POST.get("linkedin", "").strip(),
            "github": request.POST.get("github", "").strip(),
            "portfolio": request.POST.get("portfolio", "").strip(),
        }
        core.save_profile(uid, fields)
        messages.success(request, "Personal profile updated successfully!")

    return redirect('/profile/')


# ------------------------------------------------------------------------------
# ATS RESUME STUDIO VIEWS (3 TABS)
# ------------------------------------------------------------------------------
def resume_studio_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    profile = core.get_profile(uid)
    _raw_resume = core.get_resume(uid)
    # Normalize resume: ensure it's a dict with expected resume keys
    # (the SQLite fallback may return a profile dict or None)
    if isinstance(_raw_resume, dict) and "summary" in _raw_resume:
        resume = _raw_resume
    else:
        resume = {
            "summary": "",
            "skills": [],
            "experience": "",
            "education": "",
        }
    active_tab = request.GET.get("tab", "tab_editor")

    if request.method == "POST":
        summary = request.POST.get("summary", "").strip()
        skills_str = request.POST.get("skills_str", "").strip()
        exp_text = request.POST.get("experience_text", "").strip()
        edu_text = request.POST.get("education_text", "").strip()

        skills_list = [s.strip() for s in skills_str.split(",") if s.strip()]
        core.save_resume(
            user_id=uid,
            resume_data={
                "summary": summary,
                "skills": skills_list,
                "experience": exp_text,
                "education": edu_text
            }
        )
        messages.success(request, "Resume profile saved successfully!")
        resume = core.get_resume(uid) or {}

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
        "active_tab": active_tab,
    })


def resume_export_pdf_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    profile = core.get_profile(uid)
    resume = core.get_resume(uid) or {}

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
    current_skills = core.list_skills(uid)
    core.import_skills_to_resume(uid, current_skills)
    messages.success(request, "Skills successfully imported into resume profile!")
    return redirect('/resume-studio/?tab=tab_editor')


def resume_screen_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    if request.method == "POST":
        uid = user.get("id")
        jd_text = request.POST.get("job_description", "").strip()
        resume = core.get_resume(uid) or {}

        # Heuristic ATS keyword matching
        resume_text = core.format_resume_as_text(resume, user)
        jd_words = set(w.lower() for w in jd_text.replace(",", " ").replace(".", " ").split() if len(w) > 3)
        res_words = set(w.lower() for w in resume_text.replace(",", " ").replace(".", " ").split() if len(w) > 3)

        matched = list(jd_words.intersection(res_words))
        missing = list(jd_words - res_words)[:12]
        score = int(round(len(matched) / max(len(jd_words), 1) * 100))

        return JsonResponse({
            "score": score,
            "matched_keywords": matched[:15],
            "missing_keywords": missing,
            "bullet_advice": "Quantify outcomes with STAR structure (Situation, Task, Action, Result) and integrate missing domain keywords."
        })

    return redirect('/resume-studio/?tab=tab_screener')


# ------------------------------------------------------------------------------
# REPORTS & PDF VIEWS (2 TABS)
# ------------------------------------------------------------------------------
def reports_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    org_id = user.get("org_id") or "ORG-TALENT-01"
    role = (user.get("role") or "employee").lower()
    is_admin = (role == "admin")
    profile = core.get_profile(uid)
    skills = core.list_skills(uid)
    match = core.role_match(profile.get("target_role", "Software Engineer"), skills)
    dept_summary = core.get_department_performance_summary(org_id=org_id) if is_admin else []

    return render(request, 'reports.html', {
        "profile": profile,
        "match": match,
        "is_admin": is_admin,
        "dept_summary": dept_summary,
    })


def report_pdf_download_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    org_id = user.get("org_id") or "ORG-TALENT-01"
    profile = core.get_profile(uid)
    profile["name"] = user.get("name")
    skills = core.list_skills(uid)
    analysis = core.profile_analysis(profile, skills)
    gaps = core.gap_analysis(profile.get("target_role", "Software Engineer"), skills)
    recs = core.recommendations(profile, skills)
    goals = core.get_goals(user_id=uid)
    reviews = core.get_performance_reviews(employee_id=user.get("employee_id"), org_id=org_id) if user.get("employee_id") else []

    pdf_bytes = reports_svc.create_report(
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


def report_org_pdf_download_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    org_id = user.get("org_id") or "ORG-TALENT-01"
    # Build org analytics PDF using the individual report function with org-level data
    try:
        if hasattr(reports_svc, 'generate_org_analytics_pdf_report'):
            pdf_bytes = reports_svc.generate_org_analytics_pdf_report(org_id=org_id)
        else:
            # Fallback: generate a simple org analytics PDF using existing create_report
            employees = core.list_employees(org_id) if hasattr(core, 'list_employees') else []
            profile_data = {
                "name": "Organization Analytics Report",
                "job_title": "HR Analytics Dossier",
                "department": "All Departments",
                "target_role": "Executive Summary",
                "years_experience": 0,
            }
            pdf_bytes = reports_svc.create_report(
                profile=profile_data,
                skills=[],
                goals=[],
                reviews=[],
                org_id=org_id
            )
    except Exception:
        # Last resort: return a minimal valid PDF
        from reportlab.pdfgen import canvas as pdf_canvas
        from io import BytesIO as _BytesIO
        buf = _BytesIO()
        c = pdf_canvas.Canvas(buf)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, 720, "Organization Analytics Dossier")
        c.setFont("Helvetica", 12)
        c.drawString(72, 690, f"Organization: {org_id}")
        c.drawString(72, 670, "Full analytics available in the web dashboard.")
        c.save()
        pdf_bytes = buf.getvalue()
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{org_id}_Analytics_Dossier.pdf"'
    return response


def export_my_data_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    data = core.export_user_data(uid)
    response = HttpResponse(json.dumps(data, indent=2, default=str), content_type='application/json')
    safe_name = user.get("name", "User").replace(" ", "_")
    response['Content-Disposition'] = f'attachment; filename="{safe_name}_TalentGrowth_Export.json"'
    return response


# ------------------------------------------------------------------------------
# SETTINGS & WORKSPACE ADMINISTRATION (FULL MULTI-TAB)
# ------------------------------------------------------------------------------
def settings_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    org_id = user.get("org_id") or "ORG-TALENT-01"
    role = (user.get("role") or "employee").lower()
    is_admin = (role == "admin")
    is_individual = (user.get("account_type") == "Individual")
    active_tab = request.GET.get("tab", "tab_org_profile" if is_admin else "tab_personal_profile")

    if is_admin:
        org_profile = settings_svc.get_org_profile_settings(org_id)
        emp_config = settings_svc.get_org_employee_config(org_id)
        perf_config = settings_svc.get_org_performance_config(org_id)
        sec_config = settings_svc.get_org_security_config(org_id)
        notif_config = settings_svc.get_org_notification_config(org_id)
        user_prefs = {}
        deact_status = None
    else:
        org_profile = {}
        emp_config = {}
        perf_config = {}
        sec_config = {}
        notif_config = {}
        user_prefs = settings_svc.get_user_preferences(uid)
        deact_status = settings_svc.get_account_deactivation_status(uid)

    return render(request, 'settings.html', {
        "is_admin": is_admin,
        "is_individual": is_individual,
        "org_profile": org_profile,
        "emp_config": emp_config,
        "perf_config": perf_config,
        "sec_config": sec_config,
        "notif_config": notif_config,
        "user_prefs": user_prefs,
        "deact_status": deact_status,
        "active_tab": active_tab,
    })


def settings_profile_update_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    org_id = user.get("org_id") or "ORG-TALENT-01"
    role = (user.get("role") or "employee").lower()

    if request.method == "POST":
        if role == "admin":
            name = request.POST.get("name", "").strip()
            domain = request.POST.get("domain", "").strip()
            industry = request.POST.get("industry", "").strip()
            size = request.POST.get("company_size", "").strip()
            mission = request.POST.get("mission_statement", "").strip()

            settings_svc.save_org_profile_settings(
                org_id=org_id,
                name=name,
                domain=domain,
                industry=industry,
                company_size=size,
                mission_statement=mission
            )
            messages.success(request, "Organization profile updated!")
        else:
            uid = user.get("id")
            phone = request.POST.get("phone", "").strip()
            desig = request.POST.get("designation", "").strip()
            loc = request.POST.get("location", "").strip()
            bio = request.POST.get("bio", "").strip()

            settings_svc.save_employee_personal_profile(
                user_id=uid,
                phone=phone,
                designation=desig,
                location=loc,
                bio=bio
            )
            messages.success(request, "Personal profile settings saved!")

    return redirect('/settings/')


def settings_security_update_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    if request.method == "POST":
        uid = user.get("id")
        current_pwd = request.POST.get("current_password", "")
        new_pwd = request.POST.get("new_password", "")
        confirm_pwd = request.POST.get("confirm_password", "")

        if new_pwd != confirm_pwd:
            messages.error(request, "New passwords do not match.")
            return redirect('/settings/?tab=tab_account_security')

        success, msg = settings_svc.change_account_password(uid, current_pwd, new_pwd)
        if success:
            messages.success(request, "Password changed successfully!")
        else:
            messages.error(request, msg)

    return redirect('/settings/?tab=tab_account_security')


def settings_preferences_update_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    if request.method == "POST":
        pref_type = request.POST.get("pref_type", "career")
        if pref_type == "career":
            roles = request.POST.get("desired_roles", "").strip()
            work_mode = request.POST.get("work_mode", "Hybrid").strip()
            settings_svc.save_employee_career_preferences(uid, desired_roles=roles, work_mode=work_mode)
            messages.success(request, "Career preferences saved!")
        elif pref_type == "notification":
            email_alerts = bool(request.POST.get("email_alerts"))
            goal_reminders = bool(request.POST.get("goal_reminders"))
            settings_svc.save_employee_notification_preferences(uid, email_alerts=email_alerts, goal_reminders=goal_reminders)
            messages.success(request, "Notification preferences saved!")
        elif pref_type == "appearance":
            theme = request.POST.get("theme", "Light").strip()
            settings_svc.save_employee_appearance_preferences(uid, theme=theme)
            messages.success(request, "Appearance preferences saved!")
        elif pref_type == "privacy":
            visible = bool(request.POST.get("profile_visible"))
            settings_svc.save_employee_privacy_preferences(uid, profile_visible=visible)
            messages.success(request, "Privacy preferences saved!")

    return redirect('/settings/')


def settings_deactivate_request_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        success, msg = settings_svc.request_account_deactivation(uid, reason)
        if success:
            messages.warning(request, "Account deactivation request submitted.")
        else:
            messages.error(request, msg)

    return redirect('/settings/?tab=tab_deactivate')


# ------------------------------------------------------------------------------
# JOIN AN ORGANIZATION VIEW
# ------------------------------------------------------------------------------
def join_organization_view(request):
    user = _require_auth(request)
    if not user:
        return redirect('/login/')

    uid = user.get("id")
    all_orgs = core.list_organizations()
    pending_request = core.get_user_membership_request(uid)

    if request.method == "POST":
        action = request.POST.get("action", "code")
        if action == "code":
            code = request.POST.get("invitation_code", "").strip()
            success, msg, org_info = core.join_organization(uid, code)
            if success:
                user["org_id"] = org_info.get("org_id")
                user["account_type"] = "Organization"
                request.session["user"] = user
                messages.success(request, f"Joined {org_info.get('name')} successfully!")
                return redirect('/dashboard/')
            else:
                messages.error(request, msg)
        elif action == "request":
            target_org = request.POST.get("org_id", "").strip()
            message = request.POST.get("message", "").strip()
            success, msg = core.create_membership_request(
                user_id=uid,
                org_id=target_org,
                applicant_name=user.get("name"),
                applicant_email=user.get("email"),
                message=message
            )
            if success:
                messages.success(request, "Membership request submitted for HR review!")
            else:
                messages.error(request, msg)

    return render(request, 'join_organization.html', {
        "organizations": all_orgs,
        "pending_request": pending_request,
    })
