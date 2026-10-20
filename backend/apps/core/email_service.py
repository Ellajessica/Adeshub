"""
AdesHub Core Transactional Email Service.

Provides a robust, reusable transactional email sending interface using the official
Resend Python SDK with:
- Configurable sender identity and Reply-To (Info@adeshub.co.uk)
- Strict secret and token protection (no credentials or tokens in logs)
- Email masking for PII-safe diagnostic logging
- Explicit failure reporting (no silent fallbacks to unverified backends in production)
- Clean fallback to Django dev/test mail backends during local development or unit testing
- Retries with backoff for transient network issues
"""

import logging
import sys
import time
from typing import Any, Union
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def mask_email(email: str) -> str:
    """
    Safely mask an email address for diagnostic logs without exposing full customer PII.
    Example: 'customer@adeshub.com' -> 'c******r@adeshub.com'
    """
    if not email or '@' not in email:
        return 'unknown'
    local_part, domain = email.strip().split('@', 1)
    if len(local_part) <= 2:
        masked_local = local_part[0] + '*'
    else:
        masked_local = local_part[0] + '*' * (len(local_part) - 2) + local_part[-1]
    return f"{masked_local}@{domain}"


def get_email_configuration() -> dict[str, str]:
    """
    Retrieve current email configuration values from Django settings / environment.
    Never exposes API secrets in output.
    """
    resend_api_key = getattr(settings, 'RESEND_API_KEY', '').strip()
    email_from = getattr(settings, 'EMAIL_FROM', '').strip() or getattr(settings, 'DEFAULT_FROM_EMAIL', '').strip()
    email_reply_to = getattr(settings, 'EMAIL_REPLY_TO', '').strip() or 'Info@adeshub.co.uk'
    support_email = getattr(settings, 'SUPPORT_EMAIL', '').strip() or 'Info@adeshub.co.uk'
    frontend_url = getattr(settings, 'FRONTEND_URL', 'https://adeshubafricanstore.com').rstrip('/')

    return {
        'is_resend_configured': bool(resend_api_key),
        'email_from': email_from,
        'email_reply_to': email_reply_to,
        'support_email': support_email,
        'frontend_url': frontend_url,
    }


def validate_email_configuration() -> tuple[bool, str | None]:
    """
    Validate that required email sending parameters are configured.
    Returns (is_valid, error_message).
    """
    resend_api_key = getattr(settings, 'RESEND_API_KEY', '').strip()
    email_from = getattr(settings, 'EMAIL_FROM', '').strip() or getattr(settings, 'DEFAULT_FROM_EMAIL', '').strip()

    if not resend_api_key:
        is_dev = getattr(settings, 'DEBUG', False) or 'test' in sys.argv
        if is_dev:
            return True, None
        return False, "RESEND_API_KEY environment variable is not configured."

    if not email_from:
        return False, "EMAIL_FROM sender address is not configured."

    return True, None


def send_transactional_email(
    to_email: Union[str, list[str]],
    subject: str,
    text_content: str,
    html_content: str | None = None,
    reply_to: str | None = None,
    from_email: str | None = None,
    max_retries: int = 1,
) -> dict[str, Any]:
    """
    Send an authoritative transactional email.

    In production:
      Delivers through the official Resend SDK.
      If Resend is configured and fails, logs diagnostics safely and returns a failure status.
      Never silently falls back to an unverified secondary provider in production.

    In local development / unit tests (when RESEND_API_KEY is not set):
      Falls back to Django's standard email backend (console, locmem) for development safety.

    Args:
        to_email: Single recipient email string or list of recipient emails.
        subject: Email subject line.
        text_content: Plain text representation of the email body.
        html_content: Optional rich HTML body.
        reply_to: Optional Reply-To address (defaults to settings.EMAIL_REPLY_TO -> Info@adeshub.co.uk).
        from_email: Optional sender address override (defaults to settings.EMAIL_FROM).
        max_retries: Maximum number of retry attempts on network error (default 1).

    Returns:
        dict: {
            'success': bool,
            'status': 'sent' | 'failed' | 'unconfigured' | 'no_recipient',
            'message_id': str | None,
            'provider': 'resend' | 'django_dev_backend' | 'none',
            'error': str | None,
        }
    """
    # 1. Normalize and validate recipient(s)
    if isinstance(to_email, str):
        recipients = [to_email.strip()] if to_email.strip() else []
    else:
        recipients = [e.strip() for e in to_email if e and e.strip()]

    if not recipients:
        logger.warning("send_transactional_email called with empty recipient list.")
        return {
            'success': False,
            'status': 'no_recipient',
            'message_id': None,
            'provider': 'none',
            'error': 'No recipient email specified',
        }

    masked_recipients = [mask_email(e) for e in recipients]
    recipients_log_str = ", ".join(masked_recipients)

    # 2. Resolve sender and Reply-To
    raw_from = getattr(settings, 'EMAIL_FROM', '').strip() or getattr(settings, 'DEFAULT_FROM_EMAIL', '').strip()
    sender = (
        from_email
        or raw_from.strip('\'"')
        or 'AdesHub <noreply@adeshubafricanstore.com>'
    )
    reply_to_addr = (
        reply_to
        or getattr(settings, 'EMAIL_REPLY_TO', '').strip().strip('\'"')
        or 'Info@adeshub.co.uk'
    )

    resend_api_key = getattr(settings, 'RESEND_API_KEY', '').strip()
    is_testing = 'test' in sys.argv or getattr(settings, 'IS_TESTING', False)

    # 3. Path A: Official Resend SDK
    if resend_api_key:
        try:
            import resend
        except ImportError:
            logger.error("resend package is not installed. Run 'pip install resend'.")
            return {
                'success': False,
                'status': 'failed',
                'message_id': None,
                'provider': 'resend',
                'error': 'resend package is not installed in the environment.',
            }

        resend.api_key = resend_api_key

        params: dict[str, Any] = {
            'from': sender,
            'to': recipients if len(recipients) > 1 else recipients[0],
            'subject': subject,
            'text': text_content,
        }
        if html_content:
            params['html'] = html_content
        if reply_to_addr:
            params['reply_to'] = reply_to_addr

        logger.info(
            "Attempting Resend transactional email delivery: from='%s', to=%s, subject=%r",
            sender,
            recipients_log_str,
            subject,
        )

        attempt = 0
        last_error = None
        while attempt <= max_retries:
            attempt += 1
            try:
                response = resend.Emails.send(params)
                message_id = None
                if isinstance(response, dict):
                    message_id = response.get('id')
                elif hasattr(response, 'id'):
                    message_id = getattr(response, 'id')

                logger.info(
                    "Resend transactional email delivery succeeded for %s: message_id=%s, subject=%r",
                    recipients_log_str,
                    message_id,
                    subject
                )
                return {
                    'success': True,
                    'status': 'sent',
                    'message_id': str(message_id) if message_id else None,
                    'provider': 'resend',
                    'error': None,
                }
            except Exception as err:
                last_error = err
                logger.warning(
                    "Resend transactional email attempt %d/%d failed for %s: %s",
                    attempt,
                    max_retries + 1,
                    recipients_log_str,
                    str(err)
                )
                if attempt <= max_retries:
                    time.sleep(1.0 * attempt)

        # Resend attempts exhausted
        logger.error(
            "Resend transactional email delivery failed all %d attempts for %s: %s",
            max_retries + 1,
            recipients_log_str,
            str(last_error) if last_error else 'Unknown Resend error'
        )
        return {
            'success': False,
            'status': 'failed',
            'message_id': None,
            'provider': 'resend',
            'error': str(last_error) if last_error else 'Resend delivery failed',
        }

    # 4. Path B: Fallback for Development & Testing (when RESEND_API_KEY is not configured)
    is_debug = getattr(settings, 'DEBUG', False)
    if is_debug or is_testing:
        logger.info(
            "RESEND_API_KEY not configured. Using Django development email backend (%s) for %s",
            getattr(settings, 'EMAIL_BACKEND', 'default'),
            recipients_log_str
        )
        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=sender,
                to=recipients,
                reply_to=[reply_to_addr] if reply_to_addr else None,
            )
            if html_content:
                msg.attach_alternative(html_content, "text/html")
            sent_count = msg.send(fail_silently=False)
            if sent_count > 0:
                return {
                    'success': True,
                    'status': 'sent',
                    'message_id': 'django-dev-backend',
                    'provider': 'django_dev_backend',
                    'error': None,
                }
            return {
                'success': False,
                'status': 'failed',
                'message_id': None,
                'provider': 'django_dev_backend',
                'error': 'Django email backend returned 0 messages sent',
            }
        except Exception as dev_err:
            logger.error("Django dev email backend failed for %s: %s", recipients_log_str, dev_err)
            return {
                'success': False,
                'status': 'failed',
                'message_id': None,
                'provider': 'django_dev_backend',
                'error': str(dev_err),
            }

    # 5. Production without RESEND_API_KEY
    logger.critical(
        "RESEND_API_KEY is missing in production environment. Refusing to send transactional email to %s.",
        recipients_log_str
    )
    return {
        'success': False,
        'status': 'unconfigured',
        'message_id': None,
        'provider': 'none',
        'error': 'RESEND_API_KEY is not configured in production environment',
    }
