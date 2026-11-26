"""
End-to-End Migration Test Suite for Talent Growth Django Platform.
Tests all routes, views, authentication, MongoDB Atlas operations, and PDF generation.
"""
import os
import django
from django.test import TestCase, Client
from django.urls import reverse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'talent_growth_project.settings')
django.setup()

import services.core as core
import services.db as db

class DjangoMigrationEndToEndTests(TestCase):

    def setUp(self):
        self.client = Client()

    def test_01_public_landing_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Build Exceptional Teams")
        self.assertContains(response, "Talent Growth")

    def test_02_login_and_register_pages(self):
        login_resp = self.client.get('/login/')
        self.assertEqual(login_resp.status_code, 200)
        self.assertContains(login_resp, "Welcome Back")

        reg_resp = self.client.get('/register/')
        self.assertEqual(reg_resp.status_code, 200)
        self.assertContains(reg_resp, "Create Your Account")

    def test_03_admin_login_and_dashboard(self):
        # Authenticate as HR Admin
        login_post = self.client.post('/login/', {
            'email': 'admin@talentgrowth.com',
            'password': 'Admin@12345'
        })
        self.assertEqual(login_post.status_code, 302)  # Redirects to /dashboard/

        dash_resp = self.client.get('/dashboard/')
        self.assertEqual(dash_resp.status_code, 200)
        self.assertContains(dash_resp, "Executive Workforce Dashboard")

    def test_04_employee_login_and_dashboard(self):
        # Authenticate as Employee
        login_post = self.client.post('/login/', {
            'email': 'alex@company.com',
            'password': 'Password123'
        })
        self.assertEqual(login_post.status_code, 302)

        dash_resp = self.client.get('/dashboard/')
        self.assertEqual(dash_resp.status_code, 200)
        self.assertContains(dash_resp, "Personal Career Intelligence")

    def test_05_workforce_directory(self):
        # Login as Admin
        self.client.post('/login/', {'email': 'admin@talentgrowth.com', 'password': 'Admin@12345'})
        
        resp = self.client.get('/employees/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Workforce Directory")

        # Test CSV Export
        csv_resp = self.client.get('/employees/export/')
        self.assertEqual(csv_resp.status_code, 200)
        self.assertEqual(csv_resp['Content-Type'], 'text/csv')

    def test_06_performance_reviews(self):
        self.client.post('/login/', {'email': 'admin@talentgrowth.com', 'password': 'Admin@12345'})
        resp = self.client.get('/performance/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Performance Reviews")

    def test_07_skills_and_assessments(self):
        self.client.post('/login/', {'email': 'alex@company.com', 'password': 'Password123'})
        resp = self.client.get('/skills/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Skills & Competency Matrix")

    def test_08_career_goals(self):
        self.client.post('/login/', {'email': 'alex@company.com', 'password': 'Password123'})
        resp = self.client.get('/goals/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Career Goals & Growth Milestones")

    def test_09_role_match_and_coach(self):
        self.client.post('/login/', {'email': 'alex@company.com', 'password': 'Password123'})
        
        rm_resp = self.client.get('/role-match/')
        self.assertEqual(rm_resp.status_code, 200)
        self.assertContains(rm_resp, "Role Match & Competency Gap Analysis")

        coach_resp = self.client.get('/career-coach/')
        self.assertEqual(coach_resp.status_code, 200)
        self.assertContains(coach_resp, "AI Career Coach")

    def test_10_resume_studio_and_pdf_export(self):
        self.client.post('/login/', {'email': 'alex@company.com', 'password': 'Password123'})
        
        rs_resp = self.client.get('/resume-studio/')
        self.assertEqual(rs_resp.status_code, 200)
        self.assertContains(rs_resp, "ATS Resume Studio")

        # PDF Download test
        pdf_resp = self.client.get('/resume-studio/export/')
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertEqual(pdf_resp['Content-Type'], 'application/pdf')
        self.assertTrue(len(pdf_resp.content) > 1000)

    def test_11_reports_and_pdf_download(self):
        self.client.post('/login/', {'email': 'alex@company.com', 'password': 'Password123'})
        
        rep_resp = self.client.get('/reports/')
        self.assertEqual(rep_resp.status_code, 200)
        self.assertContains(rep_resp, "Intelligence Reports")

        # PDF Download test
        pdf_resp = self.client.get('/reports/pdf/')
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertEqual(pdf_resp['Content-Type'], 'application/pdf')
        self.assertTrue(len(pdf_resp.content) > 1000)

    def test_12_settings_and_mongodb_telemetry(self):
        self.client.post('/login/', {'email': 'admin@talentgrowth.com', 'password': 'Admin@12345'})
        resp = self.client.get('/settings/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "MongoDB Atlas")
        self.assertContains(resp, "talent_management")
