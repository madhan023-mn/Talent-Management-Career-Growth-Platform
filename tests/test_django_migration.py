"""
Comprehensive End-to-End Test Suite for Talent Growth Django Platform.
Tests all pages, segmented tabs, forms, actions, MongoDB Atlas operations,
interactive MCQ testing, AI coach chat, and PDF/CSV downloads.
"""
import os
import django
from django.test import TestCase, Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'talent_growth_project.settings')
django.setup()

import services.core as core


class ComprehensiveMigrationRecoveryTests(TestCase):

    def setUp(self):
        self.client = Client()

    def test_01_public_landing_and_auth_routes(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Build Exceptional Teams")

        login_resp = self.client.get('/login/')
        self.assertEqual(login_resp.status_code, 200)
        self.assertContains(login_resp, "Sign In")

        reg_resp = self.client.get('/register/')
        self.assertEqual(reg_resp.status_code, 200)
        self.assertContains(reg_resp, "Create Account")

    def test_02_admin_dashboard_and_metrics(self):
        self.client.post('/login/', {'email': 'admin@talentgrowth.com', 'password': 'Admin@12345'})
        resp = self.client.get('/dashboard/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Executive Workforce Dashboard")
        self.assertContains(resp, "Total Workforce")
        self.assertContains(resp, "Active Departments")

    def test_03_employee_dashboard(self):
        self.client.post('/login/', {'email': 'alex@company.com', 'password': 'Password123'})
        resp = self.client.get('/dashboard/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Welcome")
        self.assertContains(resp, "Target Competency Readiness")

    def test_04_employees_all_six_tabs(self):
        self.client.post('/login/', {'email': 'admin@talentgrowth.com', 'password': 'Admin@12345'})
        
        # Directory Tab
        resp = self.client.get('/employees/?tab=tab_dir')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Workforce Directory")
        self.assertContains(resp, "Add New Employee")
        self.assertContains(resp, "Bulk Dataset Upload")
        self.assertContains(resp, "Manage Records")
        self.assertContains(resp, "Invitation Codes")
        self.assertContains(resp, "Membership Requests")

        # Export CSV
        csv_resp = self.client.get('/employees/export/')
        self.assertEqual(csv_resp.status_code, 200)
        self.assertEqual(csv_resp['Content-Type'], 'text/csv')

        # Generate Invite Code
        gen_resp = self.client.post('/employees/invite-codes/', {
            'role': 'employee',
            'department': 'Engineering',
            'max_uses': 3,
            'days': 7
        })
        self.assertEqual(gen_resp.status_code, 302)

    def test_05_skills_and_interactive_mcq_assessment(self):
        self.client.post('/login/', {'email': 'alex@company.com', 'password': 'Password123'})
        resp = self.client.get('/skills/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Skills, Assessments")
        self.assertContains(resp, "Interactive MCQ Skill Assessment Test")

        # Test AJAX fetch of MCQ questions
        mcq_json = self.client.get('/skills/mcq-test/?skill=Python')
        self.assertEqual(mcq_json.status_code, 200)
        data = mcq_json.json()
        self.assertEqual(data.get('skill'), 'Python')
        self.assertTrue(len(data.get('questions', [])) > 0)

        # Test MCQ submission and instant evaluation
        submit_resp = self.client.post('/skills/mcq-submit/', {
            'skill_name': 'Python',
            'q_0': 1,
            'q_1': 1,
            'q_2': 1,
            'q_3': 1,
            'q_4': 1
        })
        self.assertEqual(submit_resp.status_code, 302)

    def test_06_performance_reviews_and_analytics(self):
        self.client.post('/login/', {'email': 'admin@talentgrowth.com', 'password': 'Admin@12345'})
        resp = self.client.get('/performance/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Performance Reviews")
        self.assertContains(resp, "Evaluation Records")
        self.assertContains(resp, "Distribution Analytics")

    def test_07_career_goals_and_milestones(self):
        self.client.post('/login/', {'email': 'alex@company.com', 'password': 'Password123'})
        resp = self.client.get('/goals/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Career Development & SMART Goals")
        self.assertContains(resp, "Create SMART Career Goal")

    def test_08_role_match_and_competency_gaps(self):
        self.client.post('/login/', {'email': 'alex@company.com', 'password': 'Password123'})
        resp = self.client.get('/role-match/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Role Match")
        self.assertContains(resp, "Matched Competencies")

    def test_09_career_coach_and_chat_api(self):
        self.client.post('/login/', {'email': 'alex@company.com', 'password': 'Password123'})
        resp = self.client.get('/career-coach/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "AI Executive Career Coach")

        # Test instant AI Chat AJAX endpoint
        chat_resp = self.client.post('/career-coach/chat/', {
            'message': 'How can I become a Principal Architect?'
        })
        self.assertEqual(chat_resp.status_code, 200)
        self.assertIn('reply', chat_resp.json())

    def test_10_resume_studio_and_pdf(self):
        self.client.post('/login/', {'email': 'alex@company.com', 'password': 'Password123'})
        resp = self.client.get('/resume-studio/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ATS Resume Studio")
        self.assertContains(resp, "Interactive Resume Editor")
        self.assertContains(resp, "AI ATS Screener")

        # Test Resume PDF download
        pdf_resp = self.client.get('/resume-studio/export/')
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertEqual(pdf_resp['Content-Type'], 'application/pdf')
        self.assertTrue(len(pdf_resp.content) > 500)

    def test_11_reports_and_dossiers(self):
        self.client.post('/login/', {'email': 'admin@talentgrowth.com', 'password': 'Admin@12345'})
        resp = self.client.get('/reports/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Reports & Analytics Dossiers")

        # Test Career PDF download
        pdf_resp = self.client.get('/reports/pdf/')
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertEqual(pdf_resp['Content-Type'], 'application/pdf')

        # Test Org PDF download
        org_pdf_resp = self.client.get('/reports/org-pdf/')
        self.assertEqual(org_pdf_resp.status_code, 200)
        self.assertEqual(org_pdf_resp['Content-Type'], 'application/pdf')

        # Test JSON Data Export
        json_resp = self.client.get('/reports/export-data/')
        self.assertEqual(json_resp.status_code, 200)
        self.assertEqual(json_resp['Content-Type'], 'application/json')

    def test_12_settings_and_join_organization(self):
        self.client.post('/login/', {'email': 'admin@talentgrowth.com', 'password': 'Admin@12345'})
        resp = self.client.get('/settings/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Settings & Workspace Administration")
        self.assertContains(resp, "Organization Profile")

        # Test Join Organization page
        join_resp = self.client.get('/join-organization/')
        self.assertEqual(join_resp.status_code, 200)
        self.assertContains(join_resp, "Join an Organization")
