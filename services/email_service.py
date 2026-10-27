from __future__ import annotations
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("talent_growth.email")

def get_email_config() -> dict:
    """Loads email settings strictly from environment variables without hardcoded secrets."""
    return {
        "smtp_host": os.getenv("SMTP_HOST", os.getenv("SMTP_SERVER", "")).strip(),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "smtp_user": os.getenv("SMTP_USER", os.getenv("SMTP_USERNAME", "")).strip(),
        "smtp_password": os.getenv("SMTP_PASSWORD", os.getenv("SMTP_PASS", "")).strip(),
        "smtp_from": os.getenv("SMTP_FROM", os.getenv("SMTP_SENDER", "no-reply@talentgrowth.com")).strip(),
        "smtp_use_tls": os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes"),
        "app_url": os.getenv("APP_URL", "https://talent-growth.vercel.app").strip()
    }

def build_welcome_email_content(
    user_name: str,
    role: str,
    org_name: str,
    app_url: str
) -> Tuple[str, str]:
    """Generates plain text and rich HTML email contents with professional Talent Growth branding."""
    role_display = "HR Administrator" if role == "admin" else "Employee"

    # Plain text version (strictly matching prompt guidelines)
    plain_text = f"""Subject: Welcome to Talent Growth!

Dear {user_name},

Thank you for creating an account with Talent Growth.

Your account has been successfully created. You can now sign in and access the features available for your role as {role_display} at {org_name}.

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
                Thank you for creating an account with <strong>Talent Growth</strong>. Your account has been successfully created and configured for your organization.
              </p>

              <!-- Account Summary Card -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #F1F5F9; border-radius: 12px; border: 1px solid #E2E8F0; margin: 0 0 24px 0;">
                <tr>
                  <td style="padding: 18px 22px;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="4">
                      <tr>
                        <td width="35%" style="font-size: 13px; color: #64748B; font-weight: 600;">Organization:</td>
                        <td style="font-size: 14px; color: #0F172A; font-weight: 700;">{org_name}</td>
                      </tr>
                      <tr>
                        <td style="font-size: 13px; color: #64748B; font-weight: 600;">Account Role:</td>
                        <td style="font-size: 14px; color: #2563EB; font-weight: 700;">{role_display}</td>
                      </tr>
                      <tr>
                        <td style="font-size: 13px; color: #64748B; font-weight: 600;">Status:</td>
                        <td style="font-size: 14px; color: #059669; font-weight: 700;">Active & Verified</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <p style="font-size: 15px; line-height: 1.6; color: #334155; margin: 0 0 24px 0;">
                You can now sign in to access your personal competency assessments, skill gap visualizations, career milestones, and executive dashboards.
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
    app_url: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Sends a welcome email to the newly registered user.
    Handles delivery failures gracefully without crashing or rolling back user creation.
    Safe against credential leakage in logs.
    """
    cfg = get_email_config()
    final_app_url = app_url or cfg["app_url"]
    
    plain_text, html_content = build_welcome_email_content(
        user_name=user_name,
        role=role,
        org_name=org_name,
        app_url=final_app_url
    )

    # Check if SMTP host is configured
    if not cfg["smtp_host"]:
        logger.info(
            f"SMTP host not configured. Welcome email for '{to_email}' ({role}) logged locally."
        )
        return True, "Email service not configured; welcome notice logged successfully."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Welcome to Talent Growth!"
        msg["From"] = cfg["smtp_from"]
        msg["To"] = to_email

        # Attach text and HTML parts
        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        server = smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=15)
        if cfg["smtp_use_tls"]:
            server.starttls()
        
        if cfg["smtp_user"] and cfg["smtp_password"]:
            server.login(cfg["smtp_user"], cfg["smtp_password"])

        server.send_message(msg)
        server.quit()
        logger.info(f"Welcome email successfully sent to '{to_email}'.")
        return True, "Welcome email sent successfully."
    except Exception as e:
        # Secure logging without revealing passwords
        logger.warning(f"Failed to deliver welcome email to '{to_email}': {e}")
        return False, f"Email delivery notice: {e}"
