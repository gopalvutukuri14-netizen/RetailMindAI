import os
import logging
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "noreply@smartpick.ai")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "SmartPick")

MOCK_SENT_EMAILS: List[Dict[str, Any]] = []


def is_mock_mode() -> bool:
    if os.getenv("TESTING", "").lower() in ("true", "1") or "PYTEST_CURRENT_TEST" in os.environ:
        return True
    key = os.getenv("BREVO_API_KEY", "").strip()
    return not key or key.startswith("your_") or key.startswith("mock_")


def send_email_via_brevo(
    recipient_email: str,
    recipient_name: str,
    subject: str,
    html_content: str,
) -> bool:
    if is_mock_mode():
        logger.info(f"[MOCK EMAIL] To: {recipient_email} | Subject: {subject}")
        MOCK_SENT_EMAILS.append({
            "to": recipient_email,
            "name": recipient_name,
            "subject": subject,
            "html": html_content,
        })
        return True

    headers = {
        "accept": "application/json",
        "api-key": os.getenv("BREVO_API_KEY", BREVO_API_KEY),
        "content-type": "application/json",
    }

    payload = {
        "sender": {
            "name": os.getenv("BREVO_SENDER_NAME", BREVO_SENDER_NAME),
            "email": os.getenv("BREVO_SENDER_EMAIL", BREVO_SENDER_EMAIL),
        },
        "to": [
            {
                "email": recipient_email,
                "name": recipient_name,
            }
        ],
        "subject": subject,
        "htmlContent": html_content,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(BREVO_API_URL, headers=headers, json=payload)
            if response.status_code in (200, 201, 202):
                logger.info(f"Email successfully delivered to {recipient_email} via Brevo")
                return True
            else:
                logger.error(f"Brevo API error: {response.status_code} - {response.text}")
                return False
    except Exception as exc:
        logger.error(f"Failed to connect to Brevo API: {exc}")
        return False


def send_signup_verification_otp(email: str, username: str, otp: str, expiry_minutes: int = 5) -> bool:
    subject = "Verify your SmartPick account"
    html_content = f"""<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; background: #f8fafc; padding: 20px;">
  <div style="max-width: 500px; margin: auto; background: #fff; padding: 24px; border-radius: 8px;">
    <h2>SmartPick Verification</h2>
    <p>Hello {username}, enter the following verification code to activate your account:</p>
    <div style="font-size: 28px; font-weight: bold; color: #0f766e; letter-spacing: 4px; padding: 12px; background: #f0fdfa; text-align: center;">
      <div class="otp-code">{otp}</div>
    </div>
    <p>This code expires in {expiry_minutes} minutes.</p>
  </div>
</body>
</html>"""
    return send_email_via_brevo(email, username, subject, html_content)


def send_password_reset_otp(email: str, username: str, otp: str, expiry_minutes: int = 5) -> bool:
    subject = "Reset your SmartPick password"
    html_content = f"""<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; background: #f8fafc; padding: 20px;">
  <div style="max-width: 500px; margin: auto; background: #fff; padding: 24px; border-radius: 8px;">
    <h2>SmartPick Password Reset</h2>
    <p>Hello {username}, enter the following verification code to reset your password:</p>
    <div style="font-size: 28px; font-weight: bold; color: #dc2626; letter-spacing: 4px; padding: 12px; background: #fef2f2; text-align: center;">
      <div class="otp-code">{otp}</div>
    </div>
    <p>This code expires in {expiry_minutes} minutes.</p>
  </div>
</body>
</html>"""
    return send_email_via_brevo(email, username, subject, html_content)
