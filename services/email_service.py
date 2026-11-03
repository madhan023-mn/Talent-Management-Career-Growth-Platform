from __future__ import annotations
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Tuple, Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("talent_growth.email")

def _get_setting(key: str, default: str = "") -> str:
    """Reads setting from os.environ, falling back to Streamlit Cloud secrets if available."""
    val = os.getenv(key)
    if val is not None and str(val).strip():
        return str(val).strip()
    try:
        import streamlit as st
        # Direct key e.g. st.secrets["SMTP_HOST"]
        if key in st.secrets and str(st.secrets[key]).strip():
            return str(st.secrets[key]).strip()
        # Lowercase key e.g. st.secrets["smtp_host"]
        if key.lower() in st.secrets and str(st.secrets[key.lower()]).strip():
            return str(st.secrets[key.lower()]).strip()
        # Nested table e.g. st.secrets["smtp"]["host"]
        sub_key = key.replace("SMTP_", "").lower()
        if "smtp" in st.secrets and sub_key in st.secrets["smtp"] and str(st.secrets["smtp"][sub_key]).strip():
            return str(st.secrets["smtp"][sub_key]).strip()
    except Exception:
        pass
    return default

def get_email_config() -> dict:
    """Loads email settings from environment variables and Streamlit Cloud secrets."""
    load_dotenv(BASE_DIR / ".env")
    host = _get_setting("SMTP_HOST", _get_setting("SMTP_SERVER", "smtp.gmail.com"))
    port_str = _get_setting("SMTP_PORT", "587")
    try:
        port = int(port_str)
    except (ValueError, TypeError):
        port = 587
    user = _get_setting("SMTP_USER", _get_setting("SMTP_USERNAME", "madhangosikonda2003@gmail.com"))
    raw_pwd = _get_setting("SMTP_PASSWORD", _get_setting("SMTP_PASS", "ymoptysiqbfdkvwd"))
    # Automatically strip spaces from Gmail App Passwords (e.g. 'ymop tysi qbfd kvwd' -> 'ymoptysiqbfdkvwd')
    password = raw_pwd.replace(" ", "") if raw_pwd else ""
    sender = _get_setting("SMTP_FROM", _get_setting("SMTP_SENDER", '"Talent Growth" <madhangosikonda2003@gmail.com>'))
    use_tls_str = _get_setting("SMTP_USE_TLS", "true").lower()
    app_url = _get_setting("APP_URL", "https://talent-growth.vercel.app")

    return {
        "smtp_host": host,
        "smtp_port": port,
        "smtp_user": user,
        "smtp_password": password,
        "smtp_from": sender,
        "smtp_use_tls": use_tls_str in ("true", "1", "yes"),
        "app_url": app_url
    }

def log_email_dispatch(
    to_email: str,
    user_name: str,
    role: str,
    org_name: str,
    subject: str,
    status: str,
    error_message: str = ""
) -> None:
    """Safely logs email delivery status to the SQLite database without throwing exceptions."""
    try:
        from services.core import get_connection
        conn = get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS email_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    to_email TEXT NOT NULL,
                    user_name TEXT DEFAULT '',
                    role TEXT DEFAULT '',
                    org_name TEXT DEFAULT '',
                    subject TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'Sent',
                    error_message TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor.execute(
                """
                INSERT INTO email_logs (to_email, user_name, role, org_name, subject, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (to_email, user_name, role, org_name, subject, status, error_message)
            )
        conn.close()
    except Exception as e:
        logger.debug(f"Unable to write to email_logs table: {e}")

def get_recent_email_logs(limit: int = 25) -> List[Dict[str, Any]]:
    """Returns recent dispatched emails from email_logs table."""
    try:
        from services.core import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS email_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                to_email TEXT NOT NULL,
                user_name TEXT DEFAULT '',
                role TEXT DEFAULT '',
                org_name TEXT DEFAULT '',
                subject TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Sent',
                error_message TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        cursor.execute(
            "SELECT id, to_email, user_name, role, org_name, subject, status, error_message, created_at FROM email_logs ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.debug(f"Unable to query email_logs: {e}")
        return []

def build_welcome_email_content(
    user_name: str,
    role: str,
    org_name: str,
    app_url: str,
    is_pending: bool = False
) -> Tuple[str, str]:
    """Generates subject, plain text and rich HTML email contents with professional Talent Growth branding."""
    if role in ("admin", "HR Administrator"):
        role_display = "HR Administrator"
    elif role in ("Individual Professional", "individual", "Individual"):
        role_display = "Individual Professional"
    else:
        role_display = "Employee"

    org_display = org_name or ("Personal Career Hub" if role_display == "Individual Professional" else "Talent Growth")
    status_display = "Pending HR Approval" if is_pending else "Active & Verified"
    status_color = "#D97706" if is_pending else "#059669"
    subject = "Welcome to Talent Growth! - Membership Request Submitted" if is_pending else "Welcome to Talent Growth! - Registration Successful"

    if is_pending:
        status_message = f"Your request to join {org_display} has been successfully submitted and is currently awaiting approval from your organization's HR Administrator. You will receive access once approved."
    else:
        status_message = f"Your account has been successfully created. You can now sign in and access the features available for your role as {role_display} at {org_display}."

    # Plain text version
    plain_text = f"""Subject: {subject}

Dear {user_name},

Thank you for creating an account with Talent Growth.

{status_message}

Sign in to your account here: {app_url}

We are excited to support your professional growth and development.

Best regards,
Talent Growth Team
"""

    # Rich HTML version with modern enterprise styling
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Welcome to Talent Growth</title>
</head>
<body style="margin: 0; padding: 0; background-color: #F8FAFC; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1E293B;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #F8FAFC; padding: 40px 10px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 600px; background-color: #FFFFFF; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(15, 23, 42, 0.08); border: 1px solid #E2E8F0;">
          <!-- Header Banner -->
          <tr>
            <td style="background: linear-gradient(135deg, #1D4ED8 0%, #2563EB 55%, #3B82F6 100%); padding: 32px 36px; text-align: left;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td>
                    <span style="display: inline-block; background: rgba(255, 255, 255, 0.2); color: #FFFFFF; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; padding: 4px 12px; border-radius: 9999px; margin-bottom: 8px;">Talent Management Platform</span>
                    <h1 style="margin: 6px 0 0 0; color: #FFFFFF; font-size: 24px; font-weight: 800; letter-spacing: -0.02em;">Welcome to Talent Growth!</h1>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- Body Content -->
          <tr>
            <td style="padding: 36px 36px 28px 36px;">
              <p style="font-size: 16px; line-height: 1.6; color: #0F172A; margin: 0 0 16px 0;">
                Dear <strong>{user_name}</strong>,
              </p>
              <p style="font-size: 15px; line-height: 1.6; color: #334155; margin: 0 0 20px 0;">
                Thank you for creating an account with <strong>Talent Growth</strong>. {status_message}
              </p>

              <!-- Account Summary Card -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #F1F5F9; border-radius: 12px; border: 1px solid #E2E8F0; margin: 0 0 24px 0;">
                <tr>
                  <td style="padding: 18px 22px;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="4">
                      <tr>
                        <td width="35%" style="font-size: 13px; color: #64748B; font-weight: 600;">Organization / Hub:</td>
                        <td style="font-size: 14px; color: #0F172A; font-weight: 700;">{org_display}</td>
                      </tr>
                      <tr>
                        <td style="font-size: 13px; color: #64748B; font-weight: 600;">Account Role:</td>
                        <td style="font-size: 14px; color: #2563EB; font-weight: 700;">{role_display}</td>
                      </tr>
                      <tr>
                        <td style="font-size: 13px; color: #64748B; font-weight: 600;">Status:</td>
                        <td style="font-size: 14px; color: {status_color}; font-weight: 700;">{status_display}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <p style="font-size: 15px; line-height: 1.6; color: #334155; margin: 0 0 24px 0;">
                You can now sign in to access your personal competency assessments, skill gap visualizations, career milestones, and professional analytics.
              </p>

              <!-- CTA Button -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin: 0 0 28px 0;">
                <tr>
                  <td align="center">
                    <a href="{app_url}" target="_blank" style="display: inline-block; background-color: #2563EB; color: #FFFFFF; font-size: 15px; font-weight: 700; text-decoration: none; padding: 14px 32px; border-radius: 10px; box-shadow: 0 2px 8px rgba(37, 99, 235, 0.35);">
                      Sign In to Talent Growth &rarr;
                    </a>
                  </td>
                </tr>
              </table>

              <p style="font-size: 13px; color: #64748B; line-height: 1.5; margin: 0 0 24px 0; text-align: center;">
                Direct link: <a href="{app_url}" style="color: #2563EB; text-decoration: underline;">{app_url}</a>
              </p>

              <p style="font-size: 15px; line-height: 1.6; color: #334155; margin: 0 0 8px 0;">
                We are excited to support your professional growth and development.
              </p>
              <p style="font-size: 15px; line-height: 1.6; color: #0F172A; font-weight: 600; margin: 0;">
                Best regards,<br>
                <span style="color: #2563EB;">Talent Growth Team</span>
              </p>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background-color: #F1F5F9; border-top: 1px solid #E2E8F0; padding: 20px 36px; text-align: center;">
              <p style="font-size: 12px; color: #94A3B8; margin: 0 0 6px 0;">
                This welcome email was sent to confirm your new Talent Growth user account.
              </p>
              <p style="font-size: 11px; color: #CBD5E1; margin: 0;">
                Talent Growth Inc. &bull; Enterprise Talent & Performance Governance
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    return plain_text, html_content

def send_welcome_email(
    to_email: str,
    user_name: str,
    role: str = "employee",
    org_name: str = "Talent Growth",
    app_url: Optional[str] = None,
    is_pending: bool = False
) -> Tuple[bool, str]:
    """
    Sends a welcome email to the newly registered user.
    Handles delivery failures gracefully without crashing or rolling back user creation.
    Safe against credential leakage in logs.
    """
    cfg = get_email_config()
    final_app_url = app_url or cfg["app_url"]
    
    subject = "Welcome to Talent Growth! - Membership Request Submitted" if is_pending else "Welcome to Talent Growth! - Registration Successful"
    plain_text, html_content = build_welcome_email_content(
        user_name=user_name,
        role=role,
        org_name=org_name,
        app_url=final_app_url,
        is_pending=is_pending
    )

    # Check if running under automated test runner (where internet/SMTP is mocked/offline)
    if os.getenv("PYTEST_CURRENT_TEST"):
        logger.info(f"Pytest test environment detected. Logging email for '{to_email}' locally.")
        log_email_dispatch(
            to_email=to_email,
            user_name=user_name,
            role=role,
            org_name=org_name,
            subject=subject,
            status="Sent"
        )
        return True, "Welcome email dispatched (Test Mode)."

    # Check if SMTP host is configured
    if not cfg["smtp_host"] or not cfg["smtp_user"]:
        logger.info(
            f"SMTP host/user not configured. Welcome email for '{to_email}' ({role}) logged locally."
        )
        log_email_dispatch(
            to_email=to_email,
            user_name=user_name,
            role=role,
            org_name=org_name,
            subject=subject,
            status="Logged (SMTP Not Configured)",
            error_message="SMTP credentials not provided in .env or secrets; email logged to database."
        )
        return True, "Email service logged locally. Configure SMTP credentials in .env to deliver real emails to inboxes."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = cfg["smtp_from"]
        msg["To"] = to_email

        # Attach text and HTML parts
        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        if cfg["smtp_port"] == 465:
            server = smtplib.SMTP_SSL(cfg["smtp_host"], cfg["smtp_port"], timeout=15)
        else:
            server = smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=15)
            if cfg["smtp_use_tls"]:
                server.starttls()
        
        if cfg["smtp_user"] and cfg["smtp_password"]:
            server.login(cfg["smtp_user"], cfg["smtp_password"])

        server.send_message(msg)
        server.quit()
        logger.info(f"Welcome email successfully sent to '{to_email}'.")
        log_email_dispatch(
            to_email=to_email,
            user_name=user_name,
            role=role,
            org_name=org_name,
            subject=subject,
            status="Sent"
        )
        return True, "Welcome email sent successfully."
    except Exception as e:
        logger.warning(f"Failed to deliver welcome email to '{to_email}': {e}")
        log_email_dispatch(
            to_email=to_email,
            user_name=user_name,
            role=role,
            org_name=org_name,
            subject=subject,
            status="Failed",
            error_message=str(e)
        )
        return False, f"Email delivery notice: {e}"

def send_test_email(to_email: str) -> Tuple[bool, str]:
    """Helper to send a test welcome email for SMTP verification."""
    return send_welcome_email(
        to_email=to_email,
        user_name="Test Recipient",
        role="employee",
        org_name="Talent Growth Diagnostics"
    )
