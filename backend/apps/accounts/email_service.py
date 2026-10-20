import logging
import sys
import threading
from django.conf import settings
from apps.accounts.models import User
from apps.core.email_service import send_transactional_email, mask_email

logger = logging.getLogger(__name__)


def _mask_email(email: str) -> str:
    """Safely mask an email address for logging without exposing full PII."""
    return mask_email(email)


def build_password_reset_email_content(user: User, reset_url: str) -> tuple[str, str, str]:
    """
    Construct subject, plain text body, and responsive HTML body
    for a password reset email matching AdesHub brand identity.
    """
    subject = "Reset Your AdesHub Password"
    customer_name = user.get_full_name() or user.first_name or "Valued Customer"
    support_email = getattr(settings, 'SUPPORT_EMAIL', 'Info@adeshub.co.uk')
    frontend_url = getattr(settings, 'FRONTEND_URL', 'https://adeshubafricanstore.com').rstrip('/')

    # 1. Plain Text Version (Universal ASCII-compatible)
    text_content = f"""Hello {customer_name},

We received a request to reset the password associated with your AdesHub account ({user.email}).

To create a new password, please visit the following link:
{reset_url}

This password reset link will expire in 24 hours and can only be used once.

If you did not request this password reset, please ignore this email. Your password will remain unchanged and your account is completely safe.

For questions or assistance, contact our customer support team at {support_email}.

Best regards,
The AdesHub Team
{frontend_url}
"""

    # 2. Responsive HTML Version matching AdesHub Emerald Brand Palette
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your AdesHub Password</title>
</head>
<body style="margin:0;padding:0;background-color:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1e293b;line-height:1.5;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#f8fafc;padding:32px 16px;">
        <tr>
            <td align="center">
                <!-- Main Card -->
                <table role="presentation" width="100%" style="max-width:580px;background-color:#ffffff;border-radius:12px;box-shadow:0 4px 6px -1px rgba(0,0,0,0.05),0 2px 4px -2px rgba(0,0,0,0.05);overflow:hidden;border:1px solid #e2e8f0;">
                    
                    <!-- Header Banner -->
                    <tr>
                        <td style="background:linear-gradient(135deg, #065f46 0%, #059669 100%);padding:36px 32px;text-align:center;">
                            <div style="display:inline-block;background-color:#10b981;width:48px;height:48px;border-radius:50%;text-align:center;line-height:48px;margin-bottom:16px;">
                                <span style="color:#ffffff;font-size:24px;font-weight:bold;">&#128274;</span>
                            </div>
                            <h1 style="margin:0 0 6px;color:#ffffff;font-size:24px;font-weight:700;letter-spacing:-0.5px;">AdesHub</h1>
                            <p style="margin:0;color:#d1fae5;font-size:15px;font-weight:500;">African Grocery E-Commerce</p>
                        </td>
                    </tr>

                    <!-- Body Content -->
                    <tr>
                        <td style="padding:32px 32px 28px;">
                            <h2 style="margin:0 0 14px;font-size:18px;color:#0f172a;font-weight:600;">Hello {customer_name},</h2>
                            <p style="margin:0 0 16px;color:#475569;font-size:15px;line-height:1.6;">
                                We received a request to reset the password for your AdesHub account (<strong>{user.email}</strong>).
                            </p>
                            <p style="margin:0 0 24px;color:#475569;font-size:15px;line-height:1.6;">
                                Click the button below to choose a new password:
                            </p>

                            <!-- Primary CTA Button -->
                            <div style="text-align:center;margin-bottom:28px;">
                                <a href="{reset_url}" style="display:inline-block;background-color:#059669;color:#ffffff;text-decoration:none;padding:14px 32px;border-radius:8px;font-weight:600;font-size:15px;box-shadow:0 3px 6px rgba(5,150,105,0.25);letter-spacing:0.2px;">
                                    Reset My Password &rarr;
                                </a>
                            </div>

                            <!-- Expiration Warning Notice -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#fefce8;border:1px solid #fef08a;border-radius:8px;margin-bottom:24px;">
                                <tr>
                                    <td style="padding:14px 18px;">
                                        <p style="margin:0;color:#854d0e;font-size:13px;line-height:1.5;">
                                            &#9201; <strong>Security Notice:</strong> This password reset link is valid for <strong>24 hours</strong> and can only be used once.
                                        </p>
                                    </td>
                                </tr>
                            </table>

                            <!-- Fallback Link Section -->
                            <p style="margin:0 0 8px;color:#64748b;font-size:13px;">
                                If you're having trouble clicking the button, copy and paste this URL into your web browser:
                            </p>
                            <div style="background-color:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:10px 12px;margin-bottom:24px;word-break:break-all;">
                                <a href="{reset_url}" style="color:#059669;font-size:12px;text-decoration:none;font-family:monospace;">{reset_url}</a>
                            </div>

                            <!-- Ignore Advice -->
                            <p style="margin:0;color:#64748b;font-size:13px;line-height:1.5;border-top:1px solid #f1f5f9;padding-top:16px;">
                                If you did not request a password reset, please disregard this email. Your password will remain unchanged and your account is secure.
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color:#f8fafc;padding:24px 32px;border-top:1px solid #e2e8f0;text-align:center;">
                            <p style="margin:0 0 6px;color:#64748b;font-size:13px;">
                                Need help? Contact us at <a href="mailto:{support_email}" style="color:#059669;text-decoration:none;">{support_email}</a>
                            </p>
                            <p style="margin:0;color:#94a3b8;font-size:12px;">
                                &copy; AdesHub African Store. Authentic African Groceries. All rights reserved.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    return subject, text_content, html_content


def send_password_reset_email(user: User, reset_url: str, max_retries: int = 1) -> bool:
    """
    Deliver the password reset email to the user using configured transactional email service.
    Tokens are never logged.
    """
    if not user.email:
        logger.warning("[PasswordReset] User pk=%s has no email address. Skipping password reset email.", user.pk)
        return False

    masked = mask_email(user.email)
    subject, text_content, html_content = build_password_reset_email_content(user, reset_url)
    reply_to = getattr(settings, 'EMAIL_REPLY_TO', 'Info@adeshub.co.uk')

    logger.info("[PasswordReset] Dispatching transactional reset email for user pk=%s (%s)", user.pk, masked)

    result = send_transactional_email(
        to_email=user.email,
        subject=subject,
        text_content=text_content,
        html_content=html_content,
        reply_to=reply_to,
        max_retries=max_retries,
    )

    if result.get('success'):
        logger.info(
            "[PasswordReset] Password reset email successfully sent to %s via %s (message_id=%s)",
            masked,
            result.get('provider'),
            result.get('message_id')
        )
        return True
    else:
        logger.error(
            "[PasswordReset] Failed sending password reset email for user %s (%s): provider=%s status=%s error=%s",
            user.pk,
            masked,
            result.get('provider'),
            result.get('status'),
            result.get('error', 'Unknown error')
        )
        return False


def send_password_reset_email_async(user_id: int, reset_url: str):
    """
    Dispatch password reset email in a background daemon thread.
    Does not block the HTTP request. Closes DB connections to avoid thread leaks.
    In testing environment, runs synchronously for deterministic test execution.
    """
    if 'test' in sys.argv:
        user = User.objects.filter(pk=user_id).first()
        if user:
            send_password_reset_email(user, reset_url)
        return

    def _run():
        from django.db import connections
        connections.close_all()
        logger.info("[PasswordReset] Background email thread started execution for user_id=%s", user_id)
        try:
            user = User.objects.filter(pk=user_id).first()
            if user:
                logger.info("[PasswordReset] Background thread retrieved user_id=%s from DB. Delivering reset email.", user_id)
                success = send_password_reset_email(user, reset_url)
                if success:
                    logger.info("[PasswordReset] Background email thread successfully finished for user_id=%s", user_id)
                else:
                    logger.error("[PasswordReset] Background email thread failed to deliver reset email for user_id=%s", user_id)
            else:
                logger.error("[PasswordReset] Background thread could not find active user for user_id=%s in DB.", user_id)
        except Exception as err:
            logger.exception(
                "[PasswordReset] Unhandled exception occurred in async password reset email thread for user_id=%s: %s",
                user_id,
                str(err)
            )
        finally:
            connections.close_all()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    logger.info("[PasswordReset] Background daemon thread spawned for user_id=%s (thread_name=%s)", user_id, thread.name)
