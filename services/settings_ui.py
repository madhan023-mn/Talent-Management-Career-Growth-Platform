"""
Settings UI Module — Enterprise SaaS Configuration & Preference Center
Supports two user roles:
  1. HR Administrator: Organization Profile and HR Account settings.
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
    get_org_security_config,
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
    export_user_data,
)
try:
    from style import get_svg_icon
except Exception:
    try:
        import style
        import importlib
        importlib.reload(style)
        get_svg_icon = getattr(style, "get_svg_icon", lambda name, *a, **k: "")
    except Exception:
        def get_svg_icon(name: str, size: int = 18, color: str = "#4F46E5", extra_style: str = "") -> str:
            return ""


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
        "Manage your organization profile, brand identity, and HR administrator account credentials."
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
    """Renders the HR Settings sub-sections: Organization Profile and HR Account."""
    hr_tabs = st.tabs([
        "Organization Profile",
        "HR Account"
    ])

    # 1. Organization Profile
    with hr_tabs[0]:
        _render_hr_org_profile(user, org_id)

    # 2. HR Account Settings
    with hr_tabs[1]:
        _render_hr_account_settings(user, org_id)


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

