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
MOCK_BREVO_OVERRIDE: Optional[Any] = None


class EmailSendResult:
    """Represents the outcome of an email delivery attempt with backwards-compatible boolean behavior."""

    def __init__(
        self,
        success: bool,
        status_code: Optional[int] = None,
        error_type: Optional[str] = None,
        user_message: str = "",
    ):
        self.success = success
        self.status_code = status_code
        self.error_type = error_type
        self.user_message = user_message

    def __bool__(self) -> bool:
        return self.success

    def __repr__(self) -> str:
        return f"<EmailSendResult success={self.success} status_code={self.status_code} error_type={self.error_type}>"


def set_mock_brevo_response(override: Optional[Any]) -> None:
    """Helper for testing: override Brevo response without network calls."""
    global MOCK_BREVO_OVERRIDE
    MOCK_BREVO_OVERRIDE = override


def is_mock_mode() -> bool:
    if os.getenv("BREVO_FORCE_HTTP", "").lower() in ("true", "1"):
        return False
    if os.getenv("TESTING", "").lower() in ("true", "1") or "PYTEST_CURRENT_TEST" in os.environ:
        return True
    key = os.getenv("BREVO_API_KEY", "").strip()
    return not key or key.startswith("your_") or key.startswith("mock_")


def send_email_via_brevo(
    recipient_email: str,
    recipient_name: str,
    subject: str,
    html_content: str,
) -> EmailSendResult:
    global MOCK_BREVO_OVERRIDE
    if MOCK_BREVO_OVERRIDE is not None:
        if isinstance(MOCK_BREVO_OVERRIDE, Exception):
            exc = MOCK_BREVO_OVERRIDE
            if isinstance(exc, httpx.TimeoutException):
                return EmailSendResult(
                    False,
                    status_code=504,
                    error_type="timeout",
                    user_message="Email service timed out. Please try again later.",
                )
            return EmailSendResult(
                False,
                status_code=503,
                error_type="network_error",
                user_message="Unable to reach email service. Please try again later.",
            )
        if isinstance(MOCK_BREVO_OVERRIDE, EmailSendResult):
            return MOCK_BREVO_OVERRIDE
        if isinstance(MOCK_BREVO_OVERRIDE, dict):
            status = MOCK_BREVO_OVERRIDE.get("status_code", 200)
            if status in (200, 201, 202):
                MOCK_SENT_EMAILS.append({
                    "to": recipient_email,
                    "name": recipient_name,
                    "subject": subject,
                    "html": html_content,
                })
                return EmailSendResult(True, status_code=status, user_message="Verification email request accepted.")
            elif status == 401:
                return EmailSendResult(
                    False,
                    status_code=401,
                    error_type="unauthorized",
                    user_message="Email service authorization failed. Please contact support or try again later.",
                )
            elif status == 429:
                return EmailSendResult(
                    False,
                    status_code=429,
                    error_type="rate_limited",
                    user_message="Email delivery rate limit reached. Please wait a moment before trying again.",
                )
            else:
                return EmailSendResult(
                    False,
                    status_code=status,
                    error_type="provider_error",
                    user_message="Email delivery service error. Please try again later.",
                )

    if is_mock_mode():
        logger.info(f"[MOCK EMAIL] To: {recipient_email} | Subject: {subject}")
        MOCK_SENT_EMAILS.append({
            "to": recipient_email,
            "name": recipient_name,
            "subject": subject,
            "html": html_content,
        })
        return EmailSendResult(True, status_code=201, user_message="Verification email request accepted.")

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
                logger.info(f"Email request accepted by Brevo for {recipient_email}")
                return EmailSendResult(
                    True,
                    status_code=response.status_code,
                    user_message="Verification email request accepted.",
                )
            elif response.status_code == 401:
                logger.error(f"Brevo API 401 Unauthorized for {recipient_email} (check API key or authorized IP whitelist).")
                return EmailSendResult(
                    False,
                    status_code=401,
                    error_type="unauthorized",
                    user_message="Email service authorization failed. Please contact support or try again later.",
                )
            elif response.status_code == 429:
                logger.error(f"Brevo API 429 Rate Limited for {recipient_email}.")
                return EmailSendResult(
                    False,
                    status_code=429,
                    error_type="rate_limited",
                    user_message="Email delivery rate limit reached. Please wait a moment before trying again.",
                )
            else:
                logger.error(f"Brevo API returned error status {response.status_code} for {recipient_email}.")
                return EmailSendResult(
                    False,
                    status_code=response.status_code,
                    error_type="provider_error",
                    user_message="Email delivery service error. Please try again later.",
                )
    except httpx.TimeoutException:
        logger.error(f"Brevo API request timed out for {recipient_email}.")
        return EmailSendResult(
            False,
            status_code=504,
            error_type="timeout",
            user_message="Email service timed out. Please try again later.",
        )
    except Exception as exc:
        logger.error(f"Failed to connect to Brevo API for {recipient_email}: {type(exc).__name__}")
        return EmailSendResult(
            False,
            status_code=503,
            error_type="network_error",
            user_message="Unable to reach email service. Please try again later.",
        )


def send_signup_verification_otp(email: str, username: str, otp: str, expiry_minutes: int = 5) -> EmailSendResult:
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


def send_password_reset_otp(email: str, username: str, otp: str, expiry_minutes: int = 5) -> EmailSendResult:
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
