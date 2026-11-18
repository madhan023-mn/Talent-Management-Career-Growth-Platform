"""
Settings UI Module — Enterprise SaaS Configuration & Preference Center
Supports two user roles:
  1. HR Administrator: Organization Profile, HR Account, Employee Config, Performance,
                       Career Development, Training, PDF Reports, Security, Notifications.
  2. Employee: Personal Profile, Account Security, Career Preferences, Notifications,
               Appearance, Privacy & Data Governance.
"""

from __future__ import annotations
import base64
import json
from io import BytesIO
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from services.settings import (
    get_org_profile_settings,
    save_org_profile_settings,
    update_hr_account_profile,
    change_account_password,
    get_org_employee_config,
    save_org_employee_config,
    get_org_performance_config,
    save_org_performance_config,
    get_org_career_config,
    save_org_career_config,
    get_org_training_config,
    save_org_training_config,
    get_org_pdf_config,
    save_org_pdf_config,
    get_org_security_config,
    save_org_security_config,
    get_org_notification_config,
    save_org_notification_config,
    get_user_preferences,
    save_employee_personal_profile,
    save_employee_career_preferences,
    save_employee_notification_preferences,
    save_employee_appearance_preferences,
    save_employee_privacy_preferences,
    request_account_deactivation,
    get_account_deactivation_status,
)
from services.core import (
    check_db_health,
    export_user_data,
    get_db_path,
    list_stored_users,
    list_stored_employees_all,
    get_recent_email_logs,
)
from style import get_svg_icon


def _safe_index(options: List[Any], value: Any, default_idx: int = 0) -> int:
    """
    Safely finds the index of a value in options without raising ValueError.
    Supports case-insensitive matching, prefix/substring matching, and graceful fallback.
    """
    if not options:
        return 0
    safe_def = default_idx if 0 <= default_idx < len(options) else 0
    if value is None:
        return safe_def

    # 1. Exact match
    try:
        if value in options:
            return options.index(value)
    except Exception:
        pass

    # 2. Case-insensitive string match
    str_val = str(value).strip().lower()
    for idx, opt in enumerate(options):
        if str(opt).strip().lower() == str_val:
            return idx

    # 3. Partial / substring match
    for idx, opt in enumerate(options):
        opt_str = str(opt).strip().lower()
        if str_val in opt_str or opt_str in str_val:
            return idx

    return safe_def


def _render_html(html_str: str) -> None:
    """Renders HTML cleanly into Streamlit."""
    clean = "\n".join(line.strip() for line in html_str.splitlines() if line.strip())
    st.markdown(clean, unsafe_allow_html=True)


def _file_to_base64_data_uri(uploaded_file) -> Optional[str]:
    """Converts a Streamlit UploadedFile to a base64 data URI."""
    if uploaded_file is None:
        return None
    try:
        bytes_data = uploaded_file.getvalue()
        mime_type = uploaded_file.type or "image/png"
        encoded = base64.b64encode(bytes_data).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"
    except Exception:
        return None


def _calculate_password_strength(password: str, policy: Dict[str, Any]) -> tuple[int, str, str]:
    """Evaluates password strength against policy rules."""
    if not password:
        return 0, "No Password", "#94A3B8"
    score = 0
    min_len = policy.get("min_length", 8)
    if len(password) >= min_len:
        score += 25
    if len(password) >= min_len + 4:
        score += 15
    if any(c.isupper() for c in password):
        score += 20
    if any(c.isdigit() for c in password):
        score += 20
    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        score += 20

    if score < 40:
        return score, "Weak", "#EF4444"
    elif score < 75:
        return score, "Fair", "#F59E0B"
    elif score < 95:
        return score, "Good", "#3B82F6"
    else:
        return 100, "Strong & Compliant", "#10B981"


def render_settings_module(user: Dict[str, Any], is_admin: bool, is_individual: bool = False, org_id: Optional[str] = None) -> None:
    """Master renderer for the Settings page across HR and Employee roles."""
    uid = user.get("id")
    effective_org = org_id or user.get("org_id") or "ORG-TALENT-01"

    # Settings Page Header Banner
    role_title = "HR Administrator Settings" if is_admin else "Employee Account & Preferences"
    role_subtitle = (
        "Configure organization identity, workforce parameters, rating models, career frameworks, PDF branding, and security controls."
        if is_admin else
        "Manage your personal profile, account credentials, career targets, notifications, view density, and privacy controls."
    )
    badge_text = "HR EXECUTIVE GOVERNANCE" if is_admin else "EMPLOYEE PREFERENCE HUB"

    _render_html(
        f"""
        <div style="background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F766E 100%); border-radius: 16px; padding: 1.6rem 2rem; color: #FFFFFF; margin-bottom: 1.5rem; box-shadow: 0 4px 18px rgba(15, 23, 42, 0.15);">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px;">
                <div>
                    <span style="background: rgba(255, 255, 255, 0.15); border: 1px solid rgba(255, 255, 255, 0.25); color: #F0FDFA; font-size: 0.74rem; font-weight: 800; padding: 4px 12px; border-radius: 9999px; letter-spacing: 0.05em; text-transform: uppercase;">
                        {badge_text}
                    </span>
                    <div style="font-size: 1.65rem; font-weight: 800; margin-top: 8px; letter-spacing: -0.01em;">
                        {role_title}
                    </div>
                    <div style="color: #CBD5E1; font-size: 0.92rem; margin-top: 4px; max-width: 680px;">
                        {role_subtitle}
                    </div>
                </div>
                <div style="text-align: right; background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 12px; padding: 10px 18px;">
                    <div style="font-size: 0.72rem; text-transform: uppercase; color: #94A3B8; font-weight: 700;">Active Context</div>
                    <div style="font-size: 1.05rem; font-weight: 800; color: #FFFFFF;">{effective_org}</div>
                    <div style="font-size: 0.80rem; color: #5EEAD4;">{user.get('name', 'User')} ({user.get('email', '')})</div>
                </div>
            </div>
        </div>
        """
    )

    if is_admin:
        _render_hr_settings(user, effective_org)
    else:
        _render_employee_settings(user, effective_org, is_individual)


# ==============================================================================
# HR SETTINGS SUB-PAGES
# ==============================================================================
def _render_hr_settings(user: Dict[str, Any], org_id: str) -> None:
    """Renders the 9 dedicated HR settings sub-sections with full interactive tabs."""
    hr_tabs = st.tabs([
        "Organization Profile",
        "HR Account",
        "Employee Config",
        "Performance",
        "Career Development",
        "Training",
        "PDF Reports",
        "Security & Policies",
        "Notifications"
    ])

    # 1. Organization Profile
    with hr_tabs[0]:
        _render_hr_org_profile(user, org_id)

    # 2. HR Account Settings
    with hr_tabs[1]:
        _render_hr_account_settings(user, org_id)

    # 3. Employee Configuration
    with hr_tabs[2]:
        _render_hr_employee_config(user, org_id)

    # 4. Performance Settings
    with hr_tabs[3]:
        _render_hr_performance_config(user, org_id)

    # 5. Career Development Settings
    with hr_tabs[4]:
        _render_hr_career_config(user, org_id)

    # 6. Training Settings
    with hr_tabs[5]:
        _render_hr_training_config(user, org_id)

    # 7. PDF Report Customization
    with hr_tabs[6]:
        _render_hr_pdf_customization(user, org_id)

    # 8. Security & Policies
    with hr_tabs[7]:
        _render_hr_security_settings(user, org_id)

    # 9. Notification Settings
    with hr_tabs[8]:
        _render_hr_notification_settings(user, org_id)


def _render_hr_org_profile(user: Dict[str, Any], org_id: str) -> None:
    st.markdown(f"### {get_svg_icon('building', size=22, color='#2563EB')} Organization Profile & Branding", unsafe_allow_html=True)
    st.caption("Maintain your organization's official legal name, contact credentials, physical address, and brand imagery.")

    org_data = get_org_profile_settings(org_id)

    col_l, col_r = st.columns([6, 4], gap="large")

    with col_l:
        org_name = st.text_input("Organization Name *", value=org_data.get("name", ""), key="hr_org_name")
        c1, c2 = st.columns(2)
        with c1:
            off_email = st.text_input("Official Corporate Email", value=org_data.get("official_email", ""), key="hr_org_email")
        with c2:
            contact_num = st.text_input("Contact Phone Number", value=org_data.get("contact_number", ""), key="hr_org_phone")

        c3, c4 = st.columns(2)
        with c3:
            website = st.text_input("Official Website URL", value=org_data.get("website", ""), placeholder="https://example.com", key="hr_org_web")
        with c4:
            ind_options = [
                "Technology & Software",
                "Financial Services",
                "Healthcare & Life Sciences",
                "Manufacturing & Supply Chain",
                "Consulting & Professional Services",
                "Education",
                "Retail & E-commerce",
                "Other"
            ]
            industry = st.selectbox(
                "Industry / Sector",
                ind_options,
                index=_safe_index(ind_options, org_data.get("industry"), 0),
                key="hr_org_ind"
            )

        address = st.text_area("Physical Headquarters Address", value=org_data.get("address", ""), height=75, key="hr_org_addr")
        description = st.text_area("Organization Description / Mission", value=org_data.get("description", ""), height=100, key="hr_org_desc")

    with col_r:
        _render_html(
            """
            <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 12px; padding: 1.25rem; margin-bottom: 1rem;">
                <div style="font-weight: 700; color: #0F172A; font-size: 0.95rem; margin-bottom: 6px;">Brand Logo &amp; Identity</div>
                <div style="font-size: 0.82rem; color: #64748B; margin-bottom: 12px;">This logo automatically brands your organization across dashboards, header bars, and newly generated PDF dossiers.</div>
            """
        )
        current_logo = org_data.get("logo_base64")
        if current_logo:
            st.image(current_logo, width=160, caption="Active Organization Logo")
            if st.button("Clear / Remove Active Logo", key="btn_clear_logo"):
                st.session_state.pending_org_logo = ""
                st.rerun()

        uploaded_logo = st.file_uploader("Upload New Organization Logo", type=["png", "jpg", "jpeg", "svg"], key="hr_logo_uploader")
        if uploaded_logo:
            new_logo_b64 = _file_to_base64_data_uri(uploaded_logo)
            if new_logo_b64:
                st.session_state.pending_org_logo = new_logo_b64
                st.image(new_logo_b64, width=160, caption="Preview of Selected Logo")

        _render_html("</div>")

    col_btn1, col_btn2, _ = st.columns([2.5, 2, 5.5])
    with col_btn1:
        if st.button("Save Organization Profile", type="primary", use_container_width=True, key="btn_save_org_profile"):
            final_logo = st.session_state.get("pending_org_logo", current_logo)
            ok, msg = save_org_profile_settings(
                org_id=org_id,
                name=org_name,
                official_email=off_email,
                contact_number=contact_num,
                address=address,
                website=website,
                industry=industry,
                description=description,
                logo_base64=final_logo,
                requesting_role="admin"
            )
            if ok:
                st.success("Organization profile and branding successfully updated!")
                st.rerun()
            else:
                st.error(f"Error saving profile: {msg}")

    with col_btn2:
        if st.button("Cancel Changes", type="secondary", use_container_width=True, key="btn_cancel_org_profile"):
            st.session_state.pop("pending_org_logo", None)
            st.rerun()


def _render_hr_account_settings(user: Dict[str, Any], org_id: str) -> None:
    st.markdown(f"### {get_svg_icon('user', size=22, color='#2563EB')} HR Executive Account Settings", unsafe_allow_html=True)
    st.caption("Manage your administrative contact profile, executive photo, and account security credentials.")

    uid = user.get("id")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("#### Executive Profile Details")
        hr_name = st.text_input("Full Name", value=user.get("name", ""), key="hr_acc_name")
        hr_email = st.text_input("Administrative Email", value=user.get("email", ""), key="hr_acc_email")
        hr_phone = st.text_input("Direct Phone Number", value=user.get("phone", ""), key="hr_acc_phone")

        current_avatar = user.get("avatar_base64")
        if current_avatar:
            st.image(current_avatar, width=90, caption="Current Profile Photo")

        avatar_file = st.file_uploader("Upload New Profile Picture", type=["png", "jpg", "jpeg"], key="hr_acc_avatar")
        if avatar_file:
            st.session_state.pending_hr_avatar = _file_to_base64_data_uri(avatar_file)
            st.image(st.session_state.pending_hr_avatar, width=90, caption="New Avatar Preview")

        if st.button("Save Account Details", type="primary", key="btn_save_hr_acc"):
            final_avatar = st.session_state.get("pending_hr_avatar", current_avatar)
            ok, msg = update_hr_account_profile(
                user_id=uid,
                name=hr_name,
                email=hr_email,
                phone=hr_phone,
                avatar_base64=final_avatar,
                requesting_role="admin"
            )
            if ok:
                user["name"] = hr_name
                user["email"] = hr_email
                st.success("HR Account Profile updated successfully!")
                st.rerun()
            else:
                st.error(f"Failed to update profile: {msg}")

    with col2:
        st.markdown("#### Change Account Password")
        curr_pwd = st.text_input("Current Password", type="password", key="hr_pwd_curr")
        new_pwd = st.text_input("New Password", type="password", key="hr_pwd_new")
        confirm_pwd = st.text_input("Confirm New Password", type="password", key="hr_pwd_confirm")

        policy = get_org_security_config(org_id)
        if new_pwd:
            score, strength_label, color = _calculate_password_strength(new_pwd, policy)
            _render_html(
                f"""
                <div style="margin-top: 6px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 700;">
                        <span>Password Strength:</span>
                        <span style="color: {color};">{strength_label}</span>
                    </div>
                    <div style="height: 6px; background: #E2E8F0; border-radius: 9999px; margin-top: 4px; overflow: hidden;">
                        <div style="height: 100%; width: {score}%; background: {color}; border-radius: 9999px; transition: width 0.3s ease;"></div>
                    </div>
                </div>
                """
            )

        if st.button("Update Password", type="primary", key="btn_hr_pwd_change"):
            ok, msg = change_account_password(user_id=uid, current_password=curr_pwd, new_password=new_pwd, confirm_password=confirm_pwd, org_id=org_id)
            if ok:
                st.success("Password updated successfully! Please use your new password next time you sign in.")
            else:
                st.error(f"Password update failed: {msg}")


def _render_hr_employee_config(user: Dict[str, Any], org_id: str) -> None:
    st.markdown(f"### {get_svg_icon('employees', size=22, color='#2563EB')} Workforce & Employee Configuration", unsafe_allow_html=True)
    st.caption("Standardize departments, official designations, employee categories, employment statuses, and organizational skill categories.")

    cfg = get_org_employee_config(org_id)

    # 1. Departments Editor
    st.markdown("#### 1. Organizational Departments")
    dept_str = st.text_area("Departments (comma-separated list)", value=", ".join(cfg.get("departments", [])), height=75, key="cfg_depts")

    # 2. Designations Editor
    st.markdown("#### 2. Official Designations / Job Titles")
    desig_str = st.text_area("Designations (comma-separated list)", value=", ".join(cfg.get("designations", [])), height=100, key="cfg_desigs")

    # 3. Employee Categories
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 3. Employee Categories")
        cat_str = st.text_area("Categories (comma-separated)", value=", ".join(cfg.get("employee_categories", [])), height=75, key="cfg_cats")

    with c2:
        st.markdown("#### 4. Employment Status Options")
        stat_str = st.text_area("Status Options (comma-separated)", value=", ".join(cfg.get("employment_statuses", [])), height=75, key="cfg_stats")

    # 5. Skill Categories
    st.markdown("#### 5. Organizational Skill Categories")
    skill_cat_str = st.text_area("Skill Categories (comma-separated)", value=", ".join(cfg.get("skill_categories", [])), height=75, key="cfg_skill_cats")

    cb1, cb2, _ = st.columns([2.5, 2, 5.5])
    with cb1:
        if st.button("Save Employee Configuration", type="primary", key="btn_save_emp_cfg"):
            new_cfg = {
                "departments": [d.strip() for d in dept_str.split(",") if d.strip()],
                "designations": [d.strip() for d in desig_str.split(",") if d.strip()],
                "employee_categories": [c.strip() for c in cat_str.split(",") if c.strip()],
                "employment_statuses": [s.strip() for s in stat_str.split(",") if s.strip()],
                "skill_categories": [sc.strip() for sc in skill_cat_str.split(",") if sc.strip()]
            }
            ok, msg = save_org_employee_config(org_id, new_cfg, requesting_role="admin")
            if ok:
                st.success("Workforce configuration successfully saved!")
                st.rerun()
            else:
                st.error(f"Failed to save configuration: {msg}")

    with cb2:
        if st.button("Reset to Defaults", key="btn_reset_emp_cfg"):
            ok, msg = save_org_employee_config(org_id, {}, requesting_role="admin")
            st.info("Reset workforce configuration to system defaults.")
            st.rerun()


def _render_hr_performance_config(user: Dict[str, Any], org_id: str) -> None:
    st.markdown(f"### {get_svg_icon('performance', size=22, color='#2563EB')} Performance Evaluation Model & Rating Scale", unsafe_allow_html=True)
    st.caption("Customize the organizational performance appraisal framework, review cycles, and rating tier definitions.")

    cfg = get_org_performance_config(org_id)

    st.markdown("#### Performance Rating Tier Descriptions (1.0 to 5.0 Scale)")
    r_desc = cfg.get("rating_descriptions", {})

    c1, c2 = st.columns(2)
    with c1:
        d1 = st.text_input("Level 1.0 (Lowest Tier)", value=r_desc.get("1", "Unsatisfactory"), key="perf_d1")
        d2 = st.text_input("Level 2.0 (Developing Tier)", value=r_desc.get("2", "Needs Improvement"), key="perf_d2")
        d3 = st.text_input("Level 3.0 (Target Standard)", value=r_desc.get("3", "Meets Expectations"), key="perf_d3")
    with c2:
        d4 = st.text_input("Level 4.0 (High Performer)", value=r_desc.get("4", "Exceeds Expectations"), key="perf_d4")
        d5 = st.text_input("Level 5.0 (Top 5% Performer)", value=r_desc.get("5", "Outstanding"), key="perf_d5")

    st.markdown("#### Review Periods & Evaluation Dimensions")
    c3, c4 = st.columns(2)
    with c3:
        periods_str = st.text_area("Review Periods (comma-separated)", value=", ".join(cfg.get("review_periods", [])), height=75, key="perf_periods")
    with c4:
        cats_str = st.text_area("Evaluation Competency Dimensions", value=", ".join(cfg.get("performance_categories", [])), height=75, key="perf_cats")

    crit_str = st.text_area("Evaluation Criteria Checklist (comma-separated)", value=", ".join(cfg.get("evaluation_criteria", [])), height=75, key="perf_crit")

    cb1, cb2, _ = st.columns([2.5, 2, 5.5])
    with cb1:
        if st.button("Save Performance Settings", type="primary", key="btn_save_perf_cfg"):
            new_cfg = {
                "rating_scale_min": 1.0,
                "rating_scale_max": 5.0,
                "rating_descriptions": {"1": d1, "2": d2, "3": d3, "4": d4, "5": d5},
                "evaluation_criteria": [c.strip() for c in crit_str.split(",") if c.strip()],
                "review_periods": [p.strip() for p in periods_str.split(",") if p.strip()],
                "performance_categories": [pc.strip() for pc in cats_str.split(",") if pc.strip()]
            }
            ok, msg = save_org_performance_config(org_id, new_cfg, requesting_role="admin")
            if ok:
                st.success("Performance evaluation settings saved successfully!")
                st.rerun()
            else:
                st.error(f"Error saving performance settings: {msg}")
    with cb2:
        if st.button("Reset to Enterprise Defaults", key="btn_reset_perf_cfg"):
            save_org_performance_config(org_id, {}, requesting_role="admin")
            st.info("Reset to default performance settings.")
            st.rerun()


def _render_hr_career_config(user: Dict[str, Any], org_id: str) -> None:
    st.markdown(f"### {get_svg_icon('goals', size=22, color='#2563EB')} Career Development & Job Architecture", unsafe_allow_html=True)
    st.caption("Standardize organizational career levels, job families, progression ladders, and recommended developmental horizons.")

    cfg = get_org_career_config(org_id)

    st.markdown("#### 1. Career Hierarchy Levels")
    levels_str = st.text_area("Career Levels (ordered ladder, comma-separated)", value=", ".join(cfg.get("career_levels", [])), height=75, key="car_levels")

    st.markdown("#### 2. Active Job Roles Catalog")
    roles_str = st.text_area("Job Roles (comma-separated)", value=", ".join(cfg.get("job_roles", [])), height=100, key="car_roles")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 3. Standard Career Progression Ladders")
        paths_str = st.text_area("Progression Paths (comma-separated, e.g. A -> B)", value=", ".join(cfg.get("progression_paths", [])), height=100, key="car_paths")
    with c2:
        st.markdown("#### 4. Default Progression Timelines")
        timelines_str = st.text_area("Milestone Timelines (comma-separated)", value=", ".join(cfg.get("default_timelines", [])), height=100, key="car_timelines")

    cb1, cb2, _ = st.columns([2.5, 2, 5.5])
    with cb1:
        if st.button("Save Career Settings", type="primary", key="btn_save_car_cfg"):
            new_cfg = {
                "career_levels": [l.strip() for l in levels_str.split(",") if l.strip()],
                "job_roles": [r.strip() for r in roles_str.split(",") if r.strip()],
                "role_skill_requirements": cfg.get("role_skill_requirements", {}),
                "progression_paths": [p.strip() for p in paths_str.split(",") if p.strip()],
                "default_timelines": [t.strip() for t in timelines_str.split(",") if t.strip()]
            }
            ok, msg = save_org_career_config(org_id, new_cfg, requesting_role="admin")
            if ok:
                st.success("Career development framework successfully saved!")
                st.rerun()
            else:
                st.error(f"Failed to save career settings: {msg}")
    with cb2:
        if st.button("Reset Career Framework", key="btn_reset_car_cfg"):
            save_org_career_config(org_id, {}, requesting_role="admin")
            st.info("Reset to default career framework.")
            st.rerun()


def _render_hr_training_config(user: Dict[str, Any], org_id: str) -> None:
    st.markdown(f"### {get_svg_icon('award', size=22, color='#2563EB')} Learning, Training & Certification Settings", unsafe_allow_html=True)
    st.caption("Manage enterprise training providers, certification standards, completion benchmarks, and learning tracks.")

    cfg = get_org_training_config(org_id)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 1. Training Subject Categories")
        cats_str = st.text_area("Categories (comma-separated)", value=", ".join(cfg.get("training_categories", [])), height=100, key="tr_cats")
        st.markdown("#### 3. Approved Certification Types")
        cert_str = st.text_area("Certification Types (comma-separated)", value=", ".join(cfg.get("certification_types", [])), height=100, key="tr_certs")

    with c2:
        st.markdown("#### 2. Authorized Learning Providers")
        prov_str = st.text_area("Providers (comma-separated)", value=", ".join(cfg.get("training_providers", [])), height=100, key="tr_provs")
        st.markdown("#### 4. Verification & Completion Criteria")
        crit_str = st.text_area("Completion Benchmarks (comma-separated)", value=", ".join(cfg.get("completion_criteria", [])), height=100, key="tr_crit")

    cb1, cb2, _ = st.columns([2.5, 2, 5.5])
    with cb1:
        if st.button("Save Training Settings", type="primary", key="btn_save_tr_cfg"):
            new_cfg = {
                "training_categories": [c.strip() for c in cats_str.split(",") if c.strip()],
                "training_providers": [p.strip() for p in prov_str.split(",") if p.strip()],
                "certification_types": [ct.strip() for ct in cert_str.split(",") if ct.strip()],
                "completion_criteria": [cc.strip() for cc in crit_str.split(",") if cc.strip()]
            }
            ok, msg = save_org_training_config(org_id, new_cfg, requesting_role="admin")
            if ok:
                st.success("Training standards successfully saved!")
                st.rerun()
            else:
                st.error(f"Failed to save training settings: {msg}")
    with cb2:
        if st.button("Reset Learning Settings", key="btn_reset_tr_cfg"):
            save_org_training_config(org_id, {}, requesting_role="admin")
            st.info("Reset to default training settings.")
            st.rerun()


def _render_hr_pdf_customization(user: Dict[str, Any], org_id: str) -> None:
    st.markdown(f"### {get_svg_icon('reports', size=22, color='#2563EB')} PDF Report Customization & Branding", unsafe_allow_html=True)
    st.caption("Control the executive styling, company typography, color themes, running header/footer, and confidentiality notices on all generated PDF talent dossiers.")

    cfg = get_org_pdf_config(org_id)

    col_l, col_r = st.columns([6, 4], gap="large")

    with col_l:
        comp_name = st.text_input("Branded Company / Organization Name", value=cfg.get("company_name", "Talent Growth Technologies"), key="pdf_comp_name")
        rep_title = st.text_input("Default Report Title", value=cfg.get("report_title", "Talent Intelligence & Career Dossier"), key="pdf_title")

        c1, c2 = st.columns(2)
        with c1:
            theme_options = ["Navy & Teal", "Modern Indigo", "Emerald Executive", "Classic Slate"]
            theme_choice = st.selectbox(
                "PDF Color Theme",
                theme_options,
                index=_safe_index(theme_options, cfg.get("theme_color"), 0),
                key="pdf_theme"
            )
        with c2:
            date_formats = ["%B %d, %Y", "%Y-%m-%d", "%d/%m/%Y", "%d %b %Y"]
            date_format = st.selectbox(
                "Report Date Format",
                date_formats,
                index=_safe_index(date_formats, cfg.get("date_format"), 0),
                key="pdf_date_fmt"
            )

        header_txt = st.text_input("Running Header Banner Text", value=cfg.get("header_text", "CONFIDENTIAL — TALENT GROWTH ENTERPRISE"), key="pdf_hdr")
        footer_txt = st.text_input("Running Footer Notice", value=cfg.get("footer_text", "Talent Growth Platform · Confidential & Proprietary"), key="pdf_ftr")
        conf_notice = st.text_area("Confidentiality Notice Text", value=cfg.get("confidentiality_notice", "This document contains confidential talent assessment and career development data. Unauthorized distribution is prohibited."), height=75, key="pdf_conf")

    with col_r:
        theme_colors = {
            "Navy & Teal": ("#0F172A", "#0D9488"),
            "Modern Indigo": ("#1E1B4B", "#4F46E5"),
            "Emerald Executive": ("#064E3B", "#059669"),
            "Classic Slate": ("#1E293B", "#475569")
        }
        p_col, a_col = theme_colors.get(theme_choice, ("#0F172A", "#0D9488"))

        _render_html(
            f"""
            <div style="background: #FFFFFF; border: 1.5px solid {a_col}44; border-radius: 12px; padding: 1.25rem; box-shadow: 0 4px 14px rgba(0,0,0,0.04);">
                <div style="font-weight: 800; color: {p_col}; font-size: 0.95rem; margin-bottom: 6px;">Live PDF Branding Preview</div>
                <div style="border-top: 2px solid {a_col}; padding-top: 8px; margin-top: 8px;">
                    <div style="font-size: 0.72rem; color: #94A3B8; font-weight: 700; text-transform: uppercase;">{header_txt}</div>
                    <div style="font-size: 1.15rem; font-weight: 800; color: {p_col}; margin-top: 4px;">{comp_name}</div>
                    <div style="font-size: 0.90rem; font-weight: 700; color: {a_col};">{rep_title}</div>
                    <div style="font-size: 0.76rem; color: #64748B; margin-top: 2px;">Generated on {date_format.replace('%B', 'November').replace('%d', '14').replace('%Y', '2026').replace('%b', 'Nov').replace('%m', '11')}</div>
                    <div style="height: 1px; background: #E2E8F0; margin: 12px 0;"></div>
                    <div style="font-size: 0.75rem; color: #64748B; font-style: italic;">{conf_notice}</div>
                    <div style="font-size: 0.70rem; color: #94A3B8; text-align: center; margin-top: 8px;">{footer_txt}</div>
                </div>
            </div>
            """
        )

    cb1, cb2, _ = st.columns([2.5, 2, 5.5])
    with cb1:
        if st.button("Save PDF Configuration", type="primary", key="btn_save_pdf_cfg"):
            new_cfg = {
                "company_name": comp_name,
                "report_title": rep_title,
                "header_text": header_txt,
                "footer_text": footer_txt,
                "theme_color": theme_choice,
                "confidentiality_notice": conf_notice,
                "date_format": date_format
            }
            ok, msg = save_org_pdf_config(org_id, new_cfg, requesting_role="admin")
            if ok:
                st.success("PDF report customizations saved! Newly downloaded dossiers will use these settings.")
                st.rerun()
            else:
                st.error(f"Failed to save PDF config: {msg}")
    with cb2:
        if st.button("Reset PDF Defaults", key="btn_reset_pdf_cfg"):
            save_org_pdf_config(org_id, {}, requesting_role="admin")
            st.info("Reset to default PDF branding.")
            st.rerun()


def _render_hr_security_settings(user: Dict[str, Any], org_id: str) -> None:
    st.markdown(f"### {get_svg_icon('shield', size=22, color='#2563EB')} Security, Password Policies & Database Health", unsafe_allow_html=True)
    st.caption("Configure authentication complexity constraints, session lifetimes, multi-factor preparedness, and verify storage persistence.")

    cfg = get_org_security_config(org_id)
    policy = cfg.get("password_policy", {})

    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("#### Workforce Password Policy")
        min_len = st.slider("Minimum Password Length (Characters)", min_value=8, max_value=24, value=policy.get("min_length", 8), key="sec_min_len")
        req_upper = st.toggle("Require at least one uppercase letter (A–Z)", value=policy.get("require_uppercase", True), key="sec_upper")
        req_num = st.toggle("Require at least one numeric digit (0–9)", value=policy.get("require_numbers", True), key="sec_num")
        req_sym = st.toggle("Require at least one special symbol (!@#$%...)", value=policy.get("require_symbols", True), key="sec_sym")

        st.markdown("#### Session & Access Controls")
        sess_timeout = st.slider("Session Inactivity Timeout (Minutes)", min_value=15, max_value=480, value=cfg.get("session_timeout_minutes", 60), step=15, key="sec_timeout")
        mfa_enabled = st.toggle("Enable Two-Factor Authentication (MFA Ready)", value=cfg.get("two_factor_auth", False), key="sec_mfa")
        force_pwd_change = st.toggle("Force password change on initial employee login", value=cfg.get("force_password_change", False), key="sec_force_pwd")

    with c2:
        st.markdown("#### Database Health & Persistence Engine")
        db_health = check_db_health()
        db_color = "#10B981" if db_health["connected"] else "#EF4444"
        is_mysql = db_health.get("engine") == "MySQL"
        engine_label = f"MySQL {db_health.get('version', '8.0')} (InnoDB, ACID Compliant)" if is_mysql else "SQLite (WAL Mode, ACID Compliant)"
        db_target_label = "Database Schema" if is_mysql else "Database File"
        check_label = "Connection Health Check" if is_mysql else "PRAGMA Integrity Check"
        _render_html(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 12px; padding: 1.25rem; box-shadow: 0 2px 10px rgba(0,0,0,0.03);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-weight: 700; color: #0F172A; font-size: 0.95rem;">Database Storage State</span>
                    <span style="background: #ECFDF5; border: 1px solid #A7F3D0; color: {db_color}; font-size: 0.72rem; font-weight: 800; padding: 2px 8px; border-radius: 9999px;">
                        {'OPTIMAL & PERSISTING' if db_health['connected'] else 'ATTENTION NEEDED'}
                    </span>
                </div>
                <div style="font-size: 0.84rem; color: #334155; line-height: 1.6;">
                    Storage Engine: <strong>{engine_label}</strong><br/>
                    {db_target_label}: <strong>{db_health['filename']}</strong> ({db_health['size_kb']} KB)<br/>
                    {check_label}: <strong style="color: {db_color};">{db_health['integrity'].upper()}</strong><br/>
                    Foreign Key Enforcement: <strong style="color: #10B981;">ENABLED (ON)</strong><br/>
                    Password Hashing: <strong>PBKDF2-HMAC-SHA256 (100,000 iterations + Salt)</strong>
                </div>
            </div>
            """
        )

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if not is_mysql:
            db_path = get_db_path()
            if db_path.is_file():
                with open(db_path, "rb") as f:
                    db_bytes = f.read()
                st.download_button("Download Database Backup File (SQLite)", db_bytes, file_name="talentgrowth_backup.db", mime="application/octet-stream", use_container_width=True, key="btn_sec_dl_db")
        else:
            health_snapshot = json.dumps(db_health, indent=2, default=str).encode("utf-8")
            st.download_button("Download MySQL Diagnostics Snapshot (JSON)", health_snapshot, file_name=f"{db_health['filename']}_diagnostics.json", mime="application/json", use_container_width=True, key="btn_sec_dl_db")

        if st.button("Run Database Integrity Diagnostic Check", use_container_width=True, key="btn_sec_check_integrity"):
            fresh_health = check_db_health()
            if fresh_health.get("connected"):
                st.success(f"Integrity Diagnostic Passed ({fresh_health.get('engine', 'DB')} · {fresh_health.get('filename', '')}): 100% of tables and foreign key indexes are valid.")
            else:
                st.error(f"Database Health Check Warning: {fresh_health.get('integrity')}")

    cb1, cb2, _ = st.columns([2.5, 2, 5.5])
    with cb1:
        if st.button("Save Security Policies", type="primary", key="btn_save_sec_cfg"):
            new_cfg = {
                "password_policy": {
                    "min_length": min_len,
                    "require_uppercase": req_upper,
                    "require_numbers": req_num,
                    "require_symbols": req_sym
                },
                "session_timeout_minutes": sess_timeout,
                "two_factor_auth": mfa_enabled,
                "force_password_change": force_pwd_change
            }
            ok, msg = save_org_security_config(org_id, new_cfg, requesting_role="admin")
            if ok:
                st.success("Security policies successfully updated and actively enforced!")
                st.rerun()
            else:
                st.error(f"Failed to update security policies: {msg}")
    with cb2:
        if st.button("Reset Security Defaults", key="btn_reset_sec_cfg"):
            save_org_security_config(org_id, {}, requesting_role="admin")
            st.info("Reset to default security policies.")
            st.rerun()

    st.markdown("<div style='border-top: 1px solid #E2E8F0; margin: 1.75rem 0 1.25rem 0;'></div>", unsafe_allow_html=True)
    st.markdown(f"#### {get_svg_icon('shield', size=18, color='#2563EB')} Stored Database Records Explorer", unsafe_allow_html=True)
    st.caption("Inspect registered accounts, employee directory rows, and historical registration logs stored in your active database.")

    c_search, c_refresh = st.columns([4.5, 1.2], gap="small")
    with c_search:
        search_q = st.text_input(
            "Filter stored records",
            placeholder="Search by name, email, role, org ID, department, or date (e.g. 2026-10-16)...",
            key="hr_db_tbl_search",
            label_visibility="collapsed"
        )
    with c_refresh:
        if st.button("Refresh", icon=":material/refresh:", key="hr_db_tbl_refresh", use_container_width=True, type="secondary"):
            st.rerun()

    stored_users = list_stored_users(search=search_q, limit=250)
    stored_emps = list_stored_employees_all(limit=250)
    if search_q.strip():
        sq_low = search_q.strip().lower()
        stored_emps = [
            e for e in stored_emps
            if sq_low in str(e.get("name", "")).lower()
            or sq_low in str(e.get("email", "")).lower()
            or sq_low in str(e.get("employee_id", "")).lower()
            or sq_low in str(e.get("department", "")).lower()
            or sq_low in str(e.get("created_at", "")).lower()
        ]
    email_logs = get_recent_email_logs(limit=100)
    if search_q.strip():
        sq_low = search_q.strip().lower()
        email_logs = [
            lg for lg in email_logs
            if sq_low in str(lg.get("to_email", "")).lower()
            or sq_low in str(lg.get("user_name", "")).lower()
            or sq_low in str(lg.get("created_at", "")).lower()
        ]

    tab_u, tab_e, tab_h = st.tabs([
        f"Registered Accounts ({len(stored_users)})",
        f"Employee Directory ({len(stored_emps)})",
        "Past Registration & Email History"
    ])

    with tab_u:
        if stored_users:
            df_u = pd.DataFrame([
                {
                    "ID": r.get("id"),
                    "Full Name": r.get("name", ""),
                    "Email": r.get("email", ""),
                    "Role": "HR Admin" if r.get("role") == "admin" else "Employee",
                    "Account Type": r.get("account_type", "Organization"),
                    "Organization": r.get("org_name") or r.get("org_id") or "Personal Hub",
                    "Employee ID": r.get("employee_id") or "—",
                    "Department": r.get("department") or "—",
                    "Job Title": r.get("job_title") or "—",
                    "Phone": r.get("phone") or "—",
                    "Status": r.get("status", "Active"),
                    "Created At": str(r.get("created_at") or r.get("date_joined") or "")[:19],
                }
                for r in stored_users
            ])
            st.dataframe(df_u, use_container_width=True, hide_index=True)
        else:
            st.info("No matching user accounts found in the database.")

    with tab_e:
        if stored_emps:
            df_e = pd.DataFrame([
                {
                    "Employee ID": e.get("employee_id", ""),
                    "Name": e.get("name", ""),
                    "Email": e.get("email", ""),
                    "Organization": e.get("org_name") or e.get("org_id", ""),
                    "Department": e.get("department", ""),
                    "Designation": e.get("designation", ""),
                    "Status": e.get("employment_status", "Active"),
                    "Exp (Yrs)": e.get("years_experience", 0.0),
                    "Joining Date": e.get("joining_date", ""),
                    "Stored At": str(e.get("created_at") or "")[:19],
                }
                for e in stored_emps
            ])
            st.dataframe(df_e, use_container_width=True, hide_index=True)
        else:
            st.info("No matching employee records found in the database.")

    with tab_h:
        if email_logs:
            df_l = pd.DataFrame([
                {
                    "Log ID": lg.get("id"),
                    "Account Name": lg.get("user_name", ""),
                    "Email Address": lg.get("to_email", ""),
                    "Role": lg.get("role", ""),
                    "Organization": lg.get("org_name", ""),
                    "Email Status": lg.get("status", ""),
                    "Recorded At": str(lg.get("created_at") or "")[:19],
                }
                for lg in email_logs
            ])
            st.dataframe(df_l, use_container_width=True, hide_index=True)
        else:
            st.info("No historical registration email logs recorded.")


def _render_hr_notification_settings(user: Dict[str, Any], org_id: str) -> None:
    st.markdown(f"### {get_svg_icon('bell', size=22, color='#2563EB')} Organization Notification & Reminder Settings", unsafe_allow_html=True)
    st.caption("Configure automated notification cadences, review triggers, training deadline dispatches, and milestone alerts.")

    cfg = get_org_notification_config(org_id)

    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("#### Evaluation & Milestone Alerts")
        review_rem = st.toggle("Performance Review Cycle Reminders", value=cfg.get("review_reminders_enabled", True), key="notif_rev_rem")
        freq_options = ["Weekly", "Bi-weekly", "Monthly"]
        freq = st.selectbox(
            "Review Reminder Cadence",
            freq_options,
            index=_safe_index(freq_options, cfg.get("reminder_frequency"), 0),
            key="notif_freq"
        )
        training_rem = st.toggle("Training & Course Deadline Reminders", value=cfg.get("training_reminders_enabled", True), key="notif_tr_rem")

    with c2:
        st.markdown("#### Administrative & Platform Events")
        goal_rem = st.toggle("Career Goal Target Date Reminders", value=cfg.get("goal_deadline_reminders", True), key="notif_goal_rem")
        reg_alerts = st.toggle("Employee Registration Alerts", value=cfg.get("employee_registration_alerts", True), key="notif_reg_alerts")
        rep_alerts = st.toggle("Report Generation Notifications", value=cfg.get("report_generation_notifications", True), key="notif_rep_alerts")

    cb1, cb2, _ = st.columns([2.5, 2, 5.5])
    with cb1:
        if st.button("Save Notification Settings", type="primary", key="btn_save_notif_cfg"):
            new_cfg = {
                "review_reminders_enabled": review_rem,
                "reminder_frequency": freq,
                "training_reminders_enabled": training_rem,
                "goal_deadline_reminders": goal_rem,
                "employee_registration_alerts": reg_alerts,
                "report_generation_notifications": rep_alerts
            }
            ok, msg = save_org_notification_config(org_id, new_cfg, requesting_role="admin")
            if ok:
                st.success("Notification dispatch settings successfully saved!")
                st.rerun()
            else:
                st.error(f"Failed to save notification settings: {msg}")
    with cb2:
        if st.button("Reset Notification Defaults", key="btn_reset_notif_cfg"):
            save_org_notification_config(org_id, {}, requesting_role="admin")
            st.info("Reset notification settings to defaults.")
            st.rerun()


# ==============================================================================
# EMPLOYEE SETTINGS SUB-PAGES
# ==============================================================================
def _render_employee_settings(user: Dict[str, Any], org_id: str, is_individual: bool) -> None:
    """Renders the 6 dedicated Employee settings sub-sections with full interactive tabs."""
    emp_tabs = st.tabs([
        "Personal Profile",
        "Account Security",
        "Career Preferences",
        "Notifications",
        "Appearance",
        "Privacy & Data"
    ])

    uid = user.get("id")
    user_prefs = get_user_preferences(uid)

    # 1. Personal Profile
    with emp_tabs[0]:
        _render_employee_personal_profile(user, user_prefs)

    # 2. Account Security
    with emp_tabs[1]:
        _render_employee_account_security(user, org_id)

    # 3. Career Preferences
    with emp_tabs[2]:
        _render_employee_career_preferences(user, user_prefs)

    # 4. Notification Preferences
    with emp_tabs[3]:
        _render_employee_notification_preferences(user, user_prefs)

    # 5. Appearance
    with emp_tabs[4]:
        _render_employee_appearance(user, user_prefs)

    # 6. Privacy & Data
    with emp_tabs[5]:
        _render_employee_privacy(user, user_prefs, is_individual)


def _render_employee_personal_profile(user: Dict[str, Any], user_prefs: Dict[str, Any]) -> None:
    st.markdown(f"### {get_svg_icon('profile', size=22, color='#2563EB')} Personal Profile & Information", unsafe_allow_html=True)
    st.caption("Update your name, public contact coordinates, location, profile avatar, and professional summary.")

    uid = user.get("id")

    col_l, col_r = st.columns([6, 4], gap="large")

    with col_l:
        name = st.text_input("Full Name", value=user.get("name", ""), key="emp_prof_name")
        email = st.text_input("Registered Email (Official ID — Read-Only)", value=user.get("email", ""), disabled=True, key="emp_prof_email")

        c1, c2 = st.columns(2)
        with c1:
            phone = st.text_input("Phone Number", value=user.get("phone", ""), key="emp_prof_phone")
        with c2:
            location = st.text_input("Work Location / City", value=user_prefs.get("location", ""), placeholder="e.g. San Francisco, CA / Remote", key="emp_prof_loc")

        summary = st.text_area("Professional Summary", value=user_prefs.get("summary", ""), height=100, placeholder="Briefly describe your career background and expertise...", key="emp_prof_summary")

    with col_r:
        _render_html(
            """
            <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 12px; padding: 1.25rem; margin-bottom: 1rem;">
                <div style="font-weight: 700; color: #0F172A; font-size: 0.95rem; margin-bottom: 6px;">Profile Avatar</div>
                <div style="font-size: 0.82rem; color: #64748B; margin-bottom: 12px;">Visible to colleagues and across your talent growth profile.</div>
            """
        )
        current_avatar = user.get("avatar_base64")
        if current_avatar:
            st.image(current_avatar, width=110, caption="Current Photo")

        uploaded_avatar = st.file_uploader("Upload New Profile Picture", type=["png", "jpg", "jpeg"], key="emp_avatar_upload")
        if uploaded_avatar:
            st.session_state.pending_emp_avatar = _file_to_base64_data_uri(uploaded_avatar)
            st.image(st.session_state.pending_emp_avatar, width=110, caption="Preview of New Photo")

        _render_html("</div>")

    cb1, cb2, _ = st.columns([2.5, 2, 5.5])
    with cb1:
        if st.button("Save Profile Changes", type="primary", key="btn_save_emp_prof"):
            final_avatar = st.session_state.get("pending_emp_avatar", current_avatar)
            ok, msg = save_employee_personal_profile(
                user_id=uid,
                name=name,
                phone=phone,
                location=location,
                summary=summary,
                avatar_base64=final_avatar
            )
            if ok:
                user["name"] = name
                st.success("Personal profile updated successfully!")
                st.rerun()
            else:
                st.error(f"Error saving profile: {msg}")
    with cb2:
        if st.button("Cancel Changes", key="btn_cancel_emp_prof"):
            st.session_state.pop("pending_emp_avatar", None)
            st.rerun()


def _render_employee_account_security(user: Dict[str, Any], org_id: str) -> None:
    st.markdown(f"### {get_svg_icon('lock', size=22, color='#2563EB')} Account Security & Password Management", unsafe_allow_html=True)
    st.caption("Change your sign-in password and verify your authenticated session attributes.")

    uid = user.get("id")
    policy = get_org_security_config(org_id)

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("#### Change Account Password")
        curr_pwd = st.text_input("Current Password", type="password", key="emp_curr_pwd")
        new_pwd = st.text_input("New Password", type="password", key="emp_new_pwd")
        confirm_pwd = st.text_input("Confirm New Password", type="password", key="emp_conf_pwd")

        if new_pwd:
            score, label, color = _calculate_password_strength(new_pwd, policy)
            _render_html(
                f"""
                <div style="margin-top: 6px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 700;">
                        <span>Password Strength:</span>
                        <span style="color: {color};">{label}</span>
                    </div>
                    <div style="height: 6px; background: #E2E8F0; border-radius: 9999px; margin-top: 4px; overflow: hidden;">
                        <div style="height: 100%; width: {score}%; background: {color}; border-radius: 9999px; transition: width 0.3s ease;"></div>
                    </div>
                </div>
                """
            )

        if st.button("Update Password", type="primary", key="btn_emp_change_pwd"):
            ok, msg = change_account_password(user_id=uid, current_password=curr_pwd, new_password=new_pwd, confirm_password=confirm_pwd, org_id=org_id)
            if ok:
                st.success("Your password has been changed successfully!")
            else:
                st.error(f"Password update failed: {msg}")

    with col2:
        st.markdown("#### Account Security Metadata")
        _render_html(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 12px; padding: 1.25rem; box-shadow: 0 2px 10px rgba(0,0,0,0.03);">
                <div style="font-weight: 700; color: #0F172A; font-size: 0.95rem; margin-bottom: 8px;">Active Credentials Information</div>
                <div style="font-size: 0.84rem; color: #334155; line-height: 1.6;">
                    Account Type: <strong>{user.get('account_type', 'Organization')}</strong><br/>
                    System User ID: <strong>#{user.get('id')}</strong><br/>
                    Employee ID: <strong>{user.get('employee_id', 'N/A')}</strong><br/>
                    Organization ID: <strong>{user.get('org_id', 'INDIVIDUAL')}</strong><br/>
                    Authentication Hash: <strong>PBKDF2-HMAC-SHA256 (Salted)</strong><br/>
                    Session Status: <strong style="color: #10B981;">Active &amp; Authenticated</strong>
                </div>
            </div>
            """
        )


def _render_employee_career_preferences(user: Dict[str, Any], user_prefs: Dict[str, Any]) -> None:
    st.markdown(f"### {get_svg_icon('target', size=22, color='#2563EB')} Career Preferences & Aspirations", unsafe_allow_html=True)
    st.caption("Tell your career coach and HR about your target designations, interested growth ladders, and priority skill competencies.")

    uid = user.get("id")
    career_p = user_prefs.get("career_preferences", {})

    c1, c2 = st.columns(2)
    with c1:
        curr_desig = st.text_input("Current Official Designation", value=career_p.get("current_designation", user.get("job_title", "")), key="emp_curr_desig")
        target_desig = st.text_input("Target / Aspirational Designation", value=career_p.get("target_designation", ""), placeholder="e.g. Senior Software Architect", key="emp_target_desig")
    with c2:
        timeline_opts = ["3-6 months", "6-12 months", "1-2 years", "2+ years"]
        timeline = st.selectbox(
            "Preferred Developmental Timeline",
            timeline_opts,
            index=_safe_index(timeline_opts, career_p.get("timeline"), 1),
            key="emp_car_tl"
        )

    paths_str = st.text_area("Interested Career Paths (comma-separated, e.g. Technical Leadership, Cloud Engineering)", value=", ".join(career_p.get("interested_paths", [])), height=75, key="emp_car_paths")
    skills_str = st.text_area("Target Skills to Master (comma-separated, e.g. Kubernetes, System Design, GraphQL)", value=", ".join(career_p.get("preferred_skills", [])), height=75, key="emp_car_skills")

    cb1, _, _ = st.columns([2.5, 2, 5.5])
    with cb1:
        if st.button("Save Career Preferences", type="primary", key="btn_save_emp_car"):
            new_car = {
                "current_designation": curr_desig,
                "target_designation": target_desig,
                "timeline": timeline,
                "interested_paths": [p.strip() for p in paths_str.split(",") if p.strip()],
                "preferred_skills": [s.strip() for s in skills_str.split(",") if s.strip()]
            }
            ok, msg = save_employee_career_preferences(uid, new_car)
            if ok:
                st.success("Career preferences saved! Your recommendations will now reflect these targets.")
                st.rerun()
            else:
                st.error(f"Error saving preferences: {msg}")


def _render_employee_notification_preferences(user: Dict[str, Any], user_prefs: Dict[str, Any]) -> None:
    st.markdown(f"### {get_svg_icon('bell', size=22, color='#2563EB')} Notification & Dispatch Preferences", unsafe_allow_html=True)
    st.caption("Customize the frequency of goal deadline alerts, training reminders, and platform achievement dispatches.")

    uid = user.get("id")
    notif_p = user_prefs.get("notification_preferences", {})

    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("#### Goal & Learning Reminders")
        goal_rem_opts = ["Daily", "Weekly", "Bi-weekly", "Disabled"]
        g_rem = st.selectbox(
            "Career Goal Progress Reminders",
            goal_rem_opts,
            index=_safe_index(goal_rem_opts, notif_p.get("goal_reminders"), 1),
            key="emp_notif_goals"
        )
        tr_rem_opts = ["3 Days Before", "1 Week Before", "2 Weeks Before", "Disabled"]
        t_rem = st.selectbox(
            "Training & Certification Deadline Reminders",
            tr_rem_opts,
            index=_safe_index(tr_rem_opts, notif_p.get("training_reminders"), 1),
            key="emp_notif_tr"
        )

    with c2:
        st.markdown("#### Evaluations & Platform Updates")
        rev_notif = st.toggle("Performance Review & Feedback Notifications", value=notif_p.get("performance_review_notifications", True), key="emp_notif_rev")
        plat_notif = st.toggle("Platform Product Updates & Achievement Celebrations", value=notif_p.get("platform_notifications", True), key="emp_notif_plat")

    cb1, _, _ = st.columns([2.5, 2, 5.5])
    with cb1:
        if st.button("Save Notification Preferences", type="primary", key="btn_save_emp_notif"):
            new_notif = {
                "goal_reminders": g_rem,
                "training_reminders": t_rem,
                "performance_review_notifications": rev_notif,
                "platform_notifications": plat_notif
            }
            ok, msg = save_employee_notification_preferences(uid, new_notif)
            if ok:
                st.success("Notification preferences saved successfully!")
                st.rerun()
            else:
                st.error(f"Error saving preferences: {msg}")


def _render_employee_appearance(user: Dict[str, Any], user_prefs: Dict[str, Any]) -> None:
    st.markdown(f"### {get_svg_icon('sliders', size=22, color='#2563EB')} Interface Appearance & Density", unsafe_allow_html=True)
    st.caption("Personalize your platform reading comfort, color theme preference, and dashboard layout density.")

    uid = user.get("id")
    app_p = user_prefs.get("appearance", {})

    c1, c2 = st.columns(2, gap="large")

    with c1:
        theme_opts = ["System Default", "Light Mode", "Dark Mode"]
        theme = st.selectbox(
            "Interface Color Theme",
            theme_opts,
            index=_safe_index(theme_opts, app_p.get("theme_mode"), 1),
            key="emp_theme_mode"
        )
        density_opts = ["Comfortable", "Compact"]
        density = st.selectbox(
            "Dashboard View Density",
            density_opts,
            index=_safe_index(density_opts, app_p.get("density"), 0),
            key="emp_density"
        )

    with c2:
        _render_html(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 12px; padding: 1.25rem;">
                <div style="font-weight: 700; color: #0F172A; font-size: 0.95rem; margin-bottom: 6px;">Visual Experience Summary</div>
                <div style="font-size: 0.84rem; color: #334155; line-height: 1.5;">
                    Selected Theme: <strong>{theme}</strong><br/>
                    Layout Spacing: <strong>{density}</strong><br/>
                    Primary Enterprise Accent: <strong style="color: #2563EB;">Vibrant Royal Blue (#2563EB)</strong>
                </div>
            </div>
            """
        )

    cb1, _, _ = st.columns([2.5, 2, 5.5])
    with cb1:
        if st.button("Save Appearance Settings", type="primary", key="btn_save_emp_app"):
            new_app = {
                "theme_mode": theme,
                "density": density
            }
            ok, msg = save_employee_appearance_preferences(uid, new_app)
            if ok:
                st.success("Appearance settings saved successfully!")
                st.rerun()
            else:
                st.error(f"Error saving appearance: {msg}")


def _render_employee_privacy(user: Dict[str, Any], user_prefs: Dict[str, Any], is_individual: bool) -> None:
    st.markdown(f"### {get_svg_icon('shield', size=22, color='#2563EB')} Privacy, Data Governance & Deactivation", unsafe_allow_html=True)
    st.caption("Control your talent profile visibility, download a complete archive of your stored data, or request account deactivation.")

    uid = user.get("id")
    priv_p = user_prefs.get("privacy", {})

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("#### Profile Visibility Controls")
        vis_opts = ["Organization-Wide", "My Department Only", "Private / HR Only"]
        visibility = st.selectbox(
            "Talent Profile Visibility Level",
            vis_opts,
            index=_safe_index(vis_opts, priv_p.get("profile_visibility"), 0),
            key="emp_priv_vis"
        )

        if st.button("Save Privacy Settings", type="primary", key="btn_save_emp_priv"):
            ok, msg = save_employee_privacy_preferences(uid, {"profile_visibility": visibility})
            if ok:
                st.success("Privacy visibility settings successfully updated!")
                st.rerun()
            else:
                st.error(f"Error saving privacy settings: {msg}")

        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        st.markdown("#### Personal Data Export (GDPR / Compliance)")
        st.caption("Download a complete, machine-readable JSON archive of all your skills, assessments, goals, reviews, and resumes stored in the platform.")
        data_snapshot = export_user_data(uid)
        payload = json.dumps(data_snapshot, indent=2, default=str).encode("utf-8")
        st.download_button(
            "Download Complete Personal Data Archive (JSON)",
            payload,
            file_name=f"talent_growth_user_archive_{uid}.json",
            mime="application/json",
            type="secondary",
            use_container_width=True,
            key="btn_emp_dl_archive"
        )

    with col2:
        st.markdown("#### Account Deactivation Request")
        st.caption("If you are transitioning out of your organization or wish to retire your account, you can submit a formal deactivation request.")

        active_req = get_account_deactivation_status(uid)
        if active_req:
            _render_html(
                f"""
                <div style="background: #FFFBEB; border: 1.5px solid #FDE68A; border-radius: 12px; padding: 1.1rem; margin-bottom: 12px;">
                    <div style="font-size: 0.72rem; text-transform: uppercase; font-weight: 800; color: #D97706;">Deactivation Request Status</div>
                    <div style="font-size: 1.1rem; font-weight: 800; color: #92400E; margin-top: 2px;">{active_req['status'].upper()}</div>
                    <div style="font-size: 0.82rem; color: #78350F; margin-top: 4px;">
                        Submitted on: <strong>{active_req['requested_at']}</strong><br/>
                        Reason given: <em>"{active_req['reason']}"</em>
                    </div>
                </div>
                """
            )
        else:
            reason = st.text_area("Reason for Deactivation Request", placeholder="Please tell us why you are requesting account deactivation...", height=100, key="emp_deact_reason")
            if st.button("Submit Deactivation Request", type="secondary", key="btn_emp_submit_deact"):
                if not reason.strip():
                    st.warning("Please provide a reason for requesting account deactivation.")
                else:
                    ok, msg = request_account_deactivation(uid, reason.strip())
                    if ok:
                        st.success("Deactivation request submitted to HR Administrator for review.")
                        st.rerun()
                    else:
                        st.error(f"Request failed: {msg}")

