"""
Global context processors for Talent Growth templates.
Injects current user, role indicators, and navigation lists into every template.
"""
from typing import Dict, Any

def global_context(request) -> Dict[str, Any]:
    user = request.session.get("user")
    if not user:
        return {
            "current_user": None,
            "is_authenticated": False,
            "is_admin": False,
            "is_individual": False,
            "role_label": "Guest",
        }

    role = (user.get("role") or "employee").lower()
    account_type = user.get("account_type") or "Organization"
    is_individual = (account_type == "Individual")
    is_admin = (role == "admin")

    role_label = "INDIVIDUAL" if is_individual else role.upper()

    # Active pages matching Streamlit app.py navigation
    if is_individual:
        active_pages = [
            {"name": "Dashboard", "url": "/dashboard/", "icon": "dashboard"},
            {"name": "My Profile", "url": "/profile/", "icon": "user"},
            {"name": "Resume Studio", "url": "/resume-studio/", "icon": "reports"},
            {"name": "Skills & Assessment", "url": "/skills/", "icon": "skills"},
            {"name": "Career Direction", "url": "/career-direction/", "icon": "target"},
            {"name": "Role Match & Gaps", "url": "/role-match/", "icon": "award"},
            {"name": "Career Coach", "url": "/career-coach/", "icon": "shield"},
            {"name": "Growth Progress", "url": "/goals/", "icon": "goals"},
            {"name": "Career Report", "url": "/reports/", "icon": "reports"},
            {"name": "Settings", "url": "/settings/", "icon": "settings"},
            {"name": "Join an Organization", "url": "/join-organization/", "icon": "building"},
        ]
    elif is_admin:
        active_pages = [
            {"name": "Dashboard", "url": "/dashboard/", "icon": "dashboard"},
            {"name": "Employees", "url": "/employees/", "icon": "employees"},
            {"name": "Performance", "url": "/performance/", "icon": "performance"},
            {"name": "Skills & Assessment", "url": "/skills/", "icon": "skills"},
            {"name": "Career Goals", "url": "/goals/", "icon": "goals"},
            {"name": "Reports", "url": "/reports/", "icon": "reports"},
            {"name": "Resume Studio", "url": "/resume-studio/", "icon": "reports"},
            {"name": "Settings", "url": "/settings/", "icon": "settings"},
        ]
    else:  # Organization Employee
        active_pages = [
            {"name": "Dashboard", "url": "/dashboard/", "icon": "dashboard"},
            {"name": "My Profile", "url": "/profile/", "icon": "user"},
            {"name": "Resume Studio", "url": "/resume-studio/", "icon": "reports"},
            {"name": "Skills & Assessment", "url": "/skills/", "icon": "skills"},
            {"name": "Career Direction", "url": "/career-direction/", "icon": "target"},
            {"name": "Role Match & Gaps", "url": "/role-match/", "icon": "award"},
            {"name": "Career Coach", "url": "/career-coach/", "icon": "shield"},
            {"name": "Growth Progress", "url": "/goals/", "icon": "goals"},
            {"name": "Career Report", "url": "/reports/", "icon": "reports"},
            {"name": "Settings", "url": "/settings/", "icon": "settings"},
        ]

    return {
        "current_user": user,
        "is_authenticated": True,
        "is_admin": is_admin,
        "is_individual": is_individual,
        "role_label": role_label,
        "active_pages": active_pages,
        "org_name": user.get("org_name") or "Talent Growth Technologies",
        "app_title": "Talent Growth",
    }
