"""
URL Routing for Talent Growth Platform.
Directly mapped to all original Streamlit pages, tabs, actions, and workflows.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Auth & Public
    path('', views.landing_view, name='landing'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboards
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Workforce & Employee Management
    path('employees/', views.employees_view, name='employees'),
    path('employees/add/', views.employee_add_view, name='employee_add'),
    path('employees/bulk-import/', views.employee_bulk_import_view, name='employee_bulk_import'),
    path('employees/<str:emp_id>/edit/', views.employee_edit_view, name='employee_edit'),
    path('employees/<str:emp_id>/delete/', views.employee_delete_view, name='employee_delete'),
    path('employees/<str:emp_id>/deactivate/', views.employee_deactivate_view, name='employee_deactivate'),
    path('employees/export/', views.employee_export_csv_view, name='employee_export_csv'),
    path('employees/invite-codes/', views.invite_code_generate_view, name='invite_code_generate'),
    path('employees/invite-codes/<int:code_id>/revoke/', views.invite_code_revoke_view, name='invite_code_revoke'),
    path('employees/membership-requests/<int:request_id>/approve/', views.membership_request_approve_view, name='membership_request_approve'),
    path('employees/membership-requests/<int:request_id>/reject/', views.membership_request_reject_view, name='membership_request_reject'),

    # Performance Reviews & Analytics
    path('performance/', views.performance_view, name='performance'),
    path('performance/add/', views.performance_add_view, name='performance_add'),

    # Skills & Assessments
    path('skills/', views.skills_view, name='skills'),
    path('skills/add/', views.skill_add_view, name='skill_add'),
    path('skills/<str:skill_id>/delete/', views.skill_delete_view, name='skill_delete'),
    path('skills/assess/', views.assessment_add_view, name='assessment_add'),
    path('skills/mcq-test/', views.skill_mcq_test_view, name='skill_mcq_test'),
    path('skills/mcq-submit/', views.skill_mcq_submit_view, name='skill_mcq_submit'),
    path('skills/training/add/', views.training_record_add_view, name='training_record_add'),

    # Career Goals & Progress
    path('goals/', views.goals_view, name='goals'),
    path('goals/add/', views.goal_add_view, name='goal_add'),
    path('goals/<int:goal_id>/update/', views.goal_update_view, name='goal_update'),
    path('goals/<int:goal_id>/delete/', views.goal_delete_view, name='goal_delete'),

    # Career Direction & Gaps
    path('role-match/', views.role_match_view, name='role_match'),
    path('career-direction/', views.role_match_view, name='career_direction'),
    path('career-coach/', views.career_coach_view, name='career_coach'),
    path('career-coach/chat/', views.career_coach_chat_api, name='career_coach_chat_api'),

    # Personal Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/save/', views.profile_save_view, name='profile_save'),

    # ATS Resume Studio
    path('resume-studio/', views.resume_studio_view, name='resume_studio'),
    path('resume-studio/export/', views.resume_export_pdf_view, name='resume_export_pdf'),
    path('resume-studio/sync-skills/', views.resume_sync_skills_view, name='resume_sync_skills'),
    path('resume-studio/screen/', views.resume_screen_view, name='resume_screen'),

    # Reports & PDF Dossiers
    path('reports/', views.reports_view, name='reports'),
    path('reports/pdf/', views.report_pdf_download_view, name='report_pdf_download'),
    path('reports/org-pdf/', views.report_org_pdf_download_view, name='report_org_pdf_download'),
    path('reports/export-data/', views.export_my_data_view, name='export_my_data'),

    # Settings & Workspace Administration
    path('settings/', views.settings_view, name='settings'),
    path('settings/profile/', views.settings_profile_update_view, name='settings_profile_update'),
    path('settings/security/', views.settings_security_update_view, name='settings_security_update'),
    path('settings/preferences/', views.settings_preferences_update_view, name='settings_preferences_update'),
    path('settings/deactivate/', views.settings_deactivate_request_view, name='settings_deactivate_request'),
    path('join-organization/', views.join_organization_view, name='join_organization'),
]
