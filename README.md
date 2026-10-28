# Talent Growth — Talent Management & Career Growth Platform

Talent Growth is a modern, enterprise-ready Python Streamlit application for **Employee Performance Management, Workforce Competency Tracking, Skill Gap Analysis, and Career Goal Development**. Built with a local-first SQLite persistence architecture, it provides role-based access control (RBAC) for both **HR Administrators** and **Employees**.

---

## 🌟 Core Features

### 1. 📊 Executive & Personal Dashboards
- **HR Executive Dashboard**: Workforce distribution by department, organization-wide average performance scores, interactive Plotly charts, review logs, and goal completion rates.
- **Employee Career Dashboard**: Profile readiness score, competency radar, target role alignment percentage, actionable development recommendations, and milestone progress.

### 2. 👥 Employee Management (Day 3 Classroom Task)
- **Two Ingestion Workflows**:
  - **Method 1: Manual Single Employee Form**: Real-time form with validation, clean form reset, and direct SQLite entry.
  - **Method 2: Bulk Dataset Upload (CSV / Excel)**: High-throughput batch ingestion supporting `.csv` and `.xlsx` files, downloadable sample template (`talent_growth_sample_employees.csv`), dataframe preview, row-by-row validation, and duplicate skipping.
- **Enterprise Fields**: Employee ID (Unique), Full Name, Corporate Email, Phone, Department, Designation, Joining Date, Employment Status (Active, On Leave, Terminated), Years of Experience, and Primary Skills.
- **Search & Filtering**: Real-time search across names, IDs, designations, and skills, with department and status filters.
- **Validation & Duplicate Prevention**: Rejects invalid/negative experience, missing required fields, and duplicate employee IDs/emails.
- **Clean Form Reset**: Dedicated "Clear Form" action that resets form state across reruns.
- **Export**: Instant CSV export of the entire filtered employee directory.

### 3. ⭐ Performance Management & Reviews
- **Structured Performance Reviews**: Log review period, performance score (1.0–5.0), achievements, strengths, improvement areas, and manager feedback.
- **Performance History**: Historical review tracking per employee.
- **Department Analytics**: Average rating calculation and visual score distributions.

### 4. 💡 Skills & Competency Matrix
- **Skills Catalog**: Manage technical, domain, and soft skills with proficiency levels (*Beginner*, *Intermediate*, *Advanced*, *Expert*).
- **Deterministic Gap Analysis**: Compare an employee's cataloged skills against benchmark roles (e.g., Software Engineer, Senior Engineer, Data Scientist, ML Engineer, DevOps Architect, Product Manager, etc.).
- **Training Assignments**: Recommend and assign internal/external training programs to close priority skill gaps.

### 5. 🎯 Career Development & Goal Tracking (Weekend Assignment)
- **SMART Career Goals**: Set goal title, target designation, description, target completion date, and discrete progress milestones (**0%**, **25%**, **50%**, **75%**, **100%**).
- **Dynamic Status**: Automatically calculates status: *Not Started* (0%), *In Progress* (25%–75%), *Completed* (100%), or *Overdue* (when deadline has passed).
- **Visual Milestones**: Interactive Plotly progress charts and quick inline progress updaters.
- **User Privacy & Isolation**: Employee goals and private assessments are isolated to their authenticated user account.

### 6. 📄 ATS Resume Studio & AI Bullet Rewriter
- **AI-Powered Resume Auditor**: Deep ATS screening evaluating keywords, impact scores, and passive voice detection.
- **STAR-Format Bullet Rewriting**: Automatically transforms weak experience statements into high-impact Google XYZ / STAR format bullets with quantified metrics.
- **ATS Resume Generator**: Real-time ATS resume preview and one-click PDF generation.
- **Resume Text Import**: Import existing PDF/DOCX resumes and evaluate target role keyword alignment.
- **Publication-Grade Reports**: Multi-page PDF career dossier generated using ReportLab, along with full JSON data export.

### 7. 🤖 Generative AI Career Coach (Google Gemini Integration)
- **Live Executive Strategy Advisor**: Interactive career coaching powered by Google Gemini API (`gemini-2.5-flash` / `gemini-2.0-flash`).
- **Context-Aware Sprints**: Generates customized 30/60/90-day developmental roadmaps, architectural leadership moves, and review cycle preparation based on candidate's real skill matrix and identified benchmark gaps.
- **Dual-Mode Architecture**: Operates live when `GEMINI_API_KEY` is provided, with an intelligent offline deterministic heuristic engine when offline.

### 8. 🔒 Role-Based Access Control (RBAC)
- **HR Administrator**: Full management access to employee directory, reviews, training assignments, system metrics, and CSV exports.
- **Employee**: Private profile management, personal goal tracking, skill updates, and performance history access.
- **Password Security**: Salted PBKDF2 SHA-256 password hashing.

---

## 🏗️ Architecture and Folder Structure

```text
infosys_project/
├── app.py                  # Streamlit presentation layer (Admin & Employee portals)
├── style.py                # Styling loader module imported in app.py
├── style.css               # Global custom CSS stylesheet
├── assets/                 # Brand assets and styling
│   ├── style.css           # Modern corporate CSS design system tokens
│   └── *.png               # Brand icons and logos
├── requirements.txt        # Application dependencies
├── pytest.ini              # Pytest configuration
├── README.md               # Documentation & setup guide
├── .env.example            # Environment template (DATABASE_PATH override)
├── services/
│   ├── __init__.py         # Services package initialization
│   ├── core.py             # Database engine, Auth/RBAC, Employee CRUD, Reviews, Goals, Gaps
│   └── reports.py          # ReportLab PDF report generation
├── tests/
│   ├── __init__.py
│   └── test_core.py        # Automated test suite (11 test suites)
└── data/                   # SQLite database (talentgrowth.db created automatically)
```

---

## 🚀 Setup and Run on Windows (Visual Studio Code)

### 1. Prerequisites
- Python 3.10+ installed and added to `PATH`.
- Visual Studio Code or preferred terminal.

### 2. Create Virtual Environment and Install Dependencies
Open PowerShell in the project directory:

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment in PowerShell
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install dependencies
pip install -r requirements.txt
```

### 3. Run the Application
```powershell
streamlit run app.py
```

The application will launch in your browser at `http://localhost:8501`.

---

## 🔑 Default Demo Accounts

Upon initial startup, the database is seeded with realistic demo records and accounts:

| Role | Email | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **HR Administrator** | `admin@talentgrowth.com` | `Admin@12345` | Full system access (Directory, Reviews, Analytics, Training) |
| **Employee (Alex Morgan)** | `alex@company.com` | `Password123` | Personal profile, goals, skills, review history |
| **Employee (Ravi Kumar)** | `ravi@company.com` | `Password123` | Jr Python Dev showcase (SQL/Communication upskilling to Sr Dev) |

*You can also create new admin or employee accounts using the "Create Account" tab on the login screen.*

---

## 🧪 Automated Testing

Run the comprehensive pytest suite:

```powershell
pytest -v
```

All 13 automated test suites verify:
- Registration, password hashing, and role assignment.
- Employee CRUD operations, validation, and duplicate prevention.
- Bulk employee dataset ingestion (CSV/Excel) and duplicate skipping.
- Performance review lifecycle and score bounds.
- Skill matrix, role gap analysis, and training assignments.
- Career goal creation, discrete progress updates, and overdue status calculation.
- Ravi Kumar showcase development journey (Junior to Senior Python Developer).
- Multi-user privacy isolation.
- ReportLab PDF dossier generation.

---

## 💾 Database Schema (SQLite)

- `users` (id, name, email, password_hash, salt, role, employee_id, created_at)
- `employees` (id, employee_id, name, email, phone, department, designation, joining_date, employment_status, years_experience, primary_skills, created_by, created_at, updated_at)
- `performance_reviews` (id, employee_id, review_period, performance_score, achievements, strengths, improvements, manager_feedback, reviewer_id, created_at)
- `employee_skills` (id, employee_id, skill_name, category, proficiency_level, years_exp, last_updated)
- `career_goals` (id, user_id, employee_id, title, target_designation, description, target_date, progress, status, created_at, updated_at)
- `training_records` (id, employee_id, course_name, provider, target_skill, target_completion_date, status, score, created_at)
- `profiles`, `skills`, `assessments`, `progress`, `goals` (backward compatibility)

---

## 🚀 24/7 Production Deployment & Hosting

Talent Growth is configured for **24/7 continuous uptime** without inactivity sleep or data loss:

- **Deployment Guide**: Full platform comparison, pricing, and step-by-step runbooks for Render, Railway, Fly.io, and Linux VPS are available in [`docs/DEPLOYMENT_AND_24_7_HOSTING.md`](docs/DEPLOYMENT_AND_24_7_HOSTING.md).
- **Docker Compose**:
  ```bash
  docker compose up -d --build
  ```
- **Health Check & Diagnostics**:
  ```bash
  python healthcheck.py
  ```
- **Online Database Backups**:
  ```bash
  python scripts/db_backup.py --backup
  python scripts/db_backup.py --list
  ```

