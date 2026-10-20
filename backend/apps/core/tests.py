from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase


class CoreSystemTests(APITestCase):
    """
    Core system baseline automated tests.
    """

    client: APIClient

    def setUp(self):
        self.client = APIClient()

    def test_api_root_endpoint(self):
        """Test root /api/ endpoint responds correctly."""
        url = reverse('core:api-root')
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE])
        self.assertEqual(response.data['app_name'], 'AdesHub Backend API')
        self.assertIn('endpoints', response.data)

    def test_health_check_endpoint(self):
        """Test /api/health/ health check endpoint."""
        url = reverse('core:health-check')
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE])
        self.assertIn('status', response.data)
        self.assertIn('database_connected', response.data)

    def test_admin_url_resolves(self):
        """Test admin login URL loads correctly."""
        response = self.client.get('/admin/login/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CoreEmailServiceTests(APITestCase):
    """
    Automated tests for AdesHub Resend Transactional Email Service.
    Mocks Resend API to ensure no real emails are sent during automated testing.
    """

    def test_mask_email(self):
        """Test safe PII email masking for logs."""
        from apps.core.email_service import mask_email

        self.assertEqual(mask_email("customer@adeshub.com"), "c******r@adeshub.com")
        self.assertEqual(mask_email("ab@domain.com"), "a*@domain.com")
        self.assertEqual(mask_email("a@b.com"), "a*@b.com")
        self.assertEqual(mask_email(""), "unknown")
        self.assertEqual(mask_email("invalid"), "unknown")

    def test_validate_email_configuration(self):
        """Test validation of required email settings."""
        from django.test import override_settings
        from apps.core.email_service import validate_email_configuration

        # When RESEND_API_KEY and EMAIL_FROM are configured
        with override_settings(RESEND_API_KEY="re_test_key_123", EMAIL_FROM="AdesHub <noreply@adeshubafricanstore.com>", DEBUG=False):
            is_valid, err = validate_email_configuration()
            self.assertTrue(is_valid)
            self.assertIsNone(err)

        # When EMAIL_FROM is empty
        with override_settings(RESEND_API_KEY="re_test_key_123", EMAIL_FROM="", DEFAULT_FROM_EMAIL="", DEBUG=False):
            is_valid, err = validate_email_configuration()
            self.assertFalse(is_valid)
            self.assertIn("EMAIL_FROM", err)

    def test_send_transactional_email_empty_recipient(self):
        """Test calling send_transactional_email with empty recipient returns failure."""
        from apps.core.email_service import send_transactional_email

        result = send_transactional_email(to_email="", subject="Hello", text_content="World")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "no_recipient")

    @patch("resend.Emails.send")
    def test_send_transactional_email_via_resend_sdk_success(self, mock_resend_send):
        """Test successful email dispatch using official Resend SDK."""
        from django.test import override_settings
        from apps.core.email_service import send_transactional_email

        mock_resend_send.return_value = {"id": "msg_resend_test_12345"}

        with override_settings(
            RESEND_API_KEY="re_mock_test_key",
            EMAIL_FROM="AdesHub <noreply@adeshubafricanstore.com>",
            EMAIL_REPLY_TO="Info@adeshub.co.uk",
        ):
            result = send_transactional_email(
                to_email="customer@example.com",
                subject="Your Order Confirmation",
                text_content="Thank you for your order.",
                html_content="<p>Thank you for your order.</p>",
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["provider"], "resend")
        self.assertEqual(result["message_id"], "msg_resend_test_12345")

        # Verify SDK parameters passed
        mock_resend_send.assert_called_once()
        call_args = mock_resend_send.call_args[0][0]
        self.assertEqual(call_args["from"], "AdesHub <noreply@adeshubafricanstore.com>")
        self.assertEqual(call_args["to"], "customer@example.com")
        self.assertEqual(call_args["subject"], "Your Order Confirmation")
        self.assertEqual(call_args["text"], "Thank you for your order.")
        self.assertEqual(call_args["html"], "<p>Thank you for your order.</p>")
        self.assertEqual(call_args["reply_to"], "Info@adeshub.co.uk")

    @patch("resend.Emails.send")
    def test_send_transactional_email_default_sender_fallback(self, mock_resend_send):
        """Test that send_transactional_email defaults to verified noreply@adeshubafricanstore.com if EMAIL_FROM is unset."""
        from django.test import override_settings
        from apps.core.email_service import send_transactional_email

        mock_resend_send.return_value = {"id": "msg_resend_test_fallback"}

        with override_settings(
            RESEND_API_KEY="re_mock_test_key",
            EMAIL_FROM="",
            DEFAULT_FROM_EMAIL="",
        ):
            result = send_transactional_email(
                to_email="customer@example.com",
                subject="Default Sender Test",
                text_content="Hello fallback",
            )

        self.assertTrue(result["success"])
        mock_resend_send.assert_called_once()
        call_args = mock_resend_send.call_args[0][0]
        self.assertEqual(call_args["from"], "AdesHub <noreply@adeshubafricanstore.com>")

    @patch("resend.Emails.send")
    def test_send_transactional_email_via_resend_failure_and_retry(self, mock_resend_send):
        """Test Resend API error handling and retries on failure."""
        from django.test import override_settings
        from apps.core.email_service import send_transactional_email

        mock_resend_send.side_effect = Exception("API connection timed out")

        with override_settings(
            RESEND_API_KEY="re_mock_test_key",
            EMAIL_FROM="AdesHub <noreply@adeshubafricanstore.com>",
        ):
            result = send_transactional_email(
                to_email="customer@example.com",
                subject="Order Update",
                text_content="Your order is being packed.",
                max_retries=1,
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["provider"], "resend")
        self.assertIn("API connection timed out", result["error"])
        # Initial attempt + 1 retry = 2 calls
        self.assertEqual(mock_resend_send.call_count, 2)

    @patch("resend.Emails.send")
    def test_production_no_silent_fallback_when_resend_fails(self, mock_resend_send):
        """Test requirement: do NOT silently fall back to another email provider in production when Resend fails."""
        from django.test import override_settings
        from django.core import mail
        from apps.core.email_service import send_transactional_email

        mail.outbox.clear()
        mock_resend_send.side_effect = Exception("Resend service unavailable 503")

        with override_settings(
            RESEND_API_KEY="re_mock_test_key",
            EMAIL_FROM="AdesHub <noreply@adeshubafricanstore.com>",
            DEBUG=False,
        ):
            result = send_transactional_email(
                to_email="customer@example.com",
                subject="Urgent Notice",
                text_content="Service update.",
                max_retries=0,
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["provider"], "resend")
        # Ensure Django mail outbox has 0 emails (no silent fallback!)
        self.assertEqual(len(mail.outbox), 0)

    def test_missing_api_key_in_production_returns_unconfigured(self):
        """Test that missing RESEND_API_KEY in production returns unconfigured status and refuses to send."""
        from django.test import override_settings
        from django.core import mail
        from apps.core.email_service import send_transactional_email

        mail.outbox.clear()
        with override_settings(RESEND_API_KEY="", DEBUG=False, IS_TESTING=False):
            # Temporarily simulate production non-test environment
            import sys
            saved_argv = sys.argv
            sys.argv = ['manage.py', 'runserver']
            try:
                result = send_transactional_email(
                    to_email="customer@example.com",
                    subject="Test Subject",
                    text_content="Body text",
                )
            finally:
                sys.argv = saved_argv

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "unconfigured")
        self.assertEqual(len(mail.outbox), 0)
