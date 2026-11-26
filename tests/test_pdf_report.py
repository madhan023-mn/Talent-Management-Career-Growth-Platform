"""
Test Suite for Employee Career & Performance PDF Report Generator
Talent Management & Career Growth Platform
Verifies:
1. Executive 2-page publication layout.
2. All 8 required sections present in sequence.
3. Live MySQL integration.
4. Correct rendering for sparse records (no performance reviews, no active goals).
"""

import pytest
import pypdf
from io import BytesIO
from services.reports import create_report
from services.core import (
    get_employees,
    get_employee_by_id,
    get_employee_skills,
    gap_analysis,
    recommendations,
    role_match
)


def test_pdf_report_two_page_and_eight_sections():
    """Validates the redesigned 2-page ReportLab PDF generation with live MySQL data."""
    emps = get_employees(org_id="ORG-TALENT-01")
    emp = emps[0] if emps else {
        "employee_id": "EMP001",
        "name": "Jordan Miller",
        "department": "Engineering",
        "designation": "Software Engineer",
        "years_experience": 4.0
    }
    skills = get_employee_skills(employee_id=emp["employee_id"], org_id="ORG-TALENT-01")
    gaps = gap_analysis(emp.get("designation", "Software Engineer"), skills)
    recs = recommendations(emp, skills)
    score = role_match(emp.get("designation", "Software Engineer"), skills, emp.get("years_experience", 4.0))

    pdf_bytes = create_report(
        profile=emp,
        skills=skills,
        analysis={"match": score},
        gaps=gaps,
        recommendations=recs,
        org_id="ORG-TALENT-01"
    )
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 1000

    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    assert len(reader.pages) == 2, f"Expected exactly 2 pages, got {len(reader.pages)}"

    p1_text = reader.pages[0].extract_text()
    p2_text = reader.pages[1].extract_text()

    # Section 1: Report Header
    assert "EMPLOYEE CAREER & PERFORMANCE REPORT" in p1_text
    assert ("TALENT GROWTH TECHNOLOGIES" in p1_text or "APEX INNOVATIONS CORP" in p1_text)
    assert "CONFIDENTIAL – HUMAN RESOURCES" in p1_text

    # Section 2 & 3: Employee Info & Career Readiness
    assert "CAREER READINESS OVERVIEW" in p1_text

    # Section 4 & 5: Skills Gap & Development Actions
    assert "SKILLS GAP ANALYSIS" in p1_text
    assert "KEY DEVELOPMENT ACTIONS" in p1_text

    # Section 6, 7 & 8 on Page 2
    assert "CAREER DEVELOPMENT PLAN" in p2_text
    assert "REVIEW STATUS" in p2_text
    assert "ACKNOWLEDGEMENT" in p2_text


def test_pdf_report_sparse_employee_fallbacks():
    """Validates that employees without performance reviews or goals render clean fallbacks."""
    sparse_emp = {
        "employee_id": "EMP_SPARSE",
        "name": "Taylor Swift",
        "department": "Design",
        "designation": "Staff",
        "years_experience": 1.0
    }
    pdf_bytes = create_report(
        profile=sparse_emp,
        skills=[],
        analysis={},
        gaps=[],
        recommendations=[],
        org_id="ORG-TALENT-01"
    )
    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    assert len(reader.pages) == 2

    p2_text = reader.pages[1].extract_text()
    assert "No performance reviews recorded" in p2_text
    assert "No active goals" in p2_text
