from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework.authtoken.models import Token
from apps.accounts.models import User


class UserModelTests(TestCase):
    """
    Automated tests for Custom User model and manager.
    """

    def test_create_user_successful(self):
        """Test creating a standard customer user."""
        email = 'customer@adeshub.com'
        password = 'SecurePassword123!'
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name='Amina',
            last_name='Okafor',
            phone_number='+2348012345678'
        )
        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))
        self.assertEqual(user.first_name, 'Amina')
        self.assertEqual(user.last_name, 'Okafor')
        self.assertEqual(user.user_type, User.UserType.CUSTOMER)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.get_full_name(), 'Amina Okafor')

    def test_email_normalization(self):
        """Test email normalization to lowercase during user creation."""
        email = 'Customer@AdesHub.COM'
        user = User.objects.create_user(email=email, password='Password123')
        self.assertEqual(user.email, 'customer@adeshub.com')

    def test_create_user_without_email_raises_error(self):
        """Test user creation without email fails."""
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='Password123')

    def test_create_superuser_successful(self):
        """Test creating a superuser admin."""
        email = 'admin@adeshub.com'
        password = 'AdminPassword123!'
        admin_user = User.objects.create_superuser(
            email=email,
            password=password,
            first_name='Admin',
            last_name='User'
        )
        self.assertEqual(admin_user.email, 'admin@adeshub.com')
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertEqual(admin_user.user_type, User.UserType.ADMIN)


class AccountAPITests(APITestCase):
    """
    Automated tests for User Authentication and Account REST API Endpoints.
    """

    client: APIClient

    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('accounts:register')
        self.login_url = reverse('accounts:login')
        self.logout_url = reverse('accounts:logout')
        self.profile_url = reverse('accounts:profile')
        self.change_password_url = reverse('accounts:change-password')
        self.user_list_url = reverse('accounts:user-list')
        self.address_list_url = reverse('accounts:address-list-create')

        self.user_data = {
            'email': 'testuser@adeshub.com',
            'password': 'TestPassword123!',
            'password_confirm': 'TestPassword123!',
            'first_name': 'Kwame',
            'last_name': 'Mensah',
            'phone_number': '+233201234567'
        }

    def test_user_registration_api_successful(self):
        """Test registering a new user via API endpoint with matching password confirmation."""
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['user']['email'], self.user_data['email'])

    def test_registration_failure_when_password_confirm_missing(self):
        """Test registration fails with 400 when password_confirm is omitted."""
        invalid_data = self.user_data.copy()
        del invalid_data['password_confirm']
        response = self.client.post(self.register_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_confirm', response.data)

    def test_registration_failure_when_passwords_do_not_match(self):
        """Test registration fails with 400 when password and password_confirm do not match."""
        mismatched_data = self.user_data.copy()
        mismatched_data['password_confirm'] = 'DifferentPassword123!'
        response = self.client.post(self.register_url, mismatched_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_confirm', response.data)

    def test_duplicate_user_registration_fails(self):
        """Test registering with an existing email returns 400 error."""
        self.client.post(self.register_url, self.user_data, format='json')
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login_api_successful(self):
        """Test user login with valid credentials."""
        User.objects.create_user(
            email='loginuser@adeshub.com',
            password='ValidPassword123!'
        )
        payload = {
            'email': 'loginuser@adeshub.com',
            'password': 'ValidPassword123!'
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_user_login_case_insensitive_email(self):
        """Test user login works with mixed-case email inputs."""
        User.objects.create_user(
            email='CaseUser@AdesHub.com',
            password='ValidPassword123!'
        )
        payload = {
            'email': 'caseuser@adeshub.com',
            'password': 'ValidPassword123!'
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_user_login_invalid_password_fails(self):
        """Test login fails with incorrect password."""
        User.objects.create_user(
            email='loginuser@adeshub.com',
            password='ValidPassword123!'
        )
        payload = {
            'email': 'loginuser@adeshub.com',
            'password': 'WrongPassword!'
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_django_admin_created_user(self):
        """Test valid user account created through Django Admin can log in via login API."""
        admin_created_user = User.objects.create_superuser(
            email='AdminAccount@adeshub.com',
            password='AdminPassword123!',
            first_name='Admin',
            last_name='User'
        )
        payload = {
            'email': 'adminaccount@adeshub.com',
            'password': 'AdminPassword123!'
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['user']['email'], 'adminaccount@adeshub.com')

    def test_unauthenticated_profile_access_denied(self):
        """Test unauthenticated request to /api/auth/me/ is rejected (401)."""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_address_access_denied(self):
        """Test unauthenticated request to /api/auth/addresses/ is rejected (401)."""
        response = self.client.get(self.address_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_profile_access_successful(self):
        """Test authenticated user can retrieve their profile."""
        user = User.objects.create_user(
            email='profile@adeshub.com',
            password='Password123!',
            first_name='Kofi'
        )
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'profile@adeshub.com')
        self.assertEqual(response.data['first_name'], 'Kofi')

    def test_user_list_endpoint_permission_denied_for_customer(self):
        """Test normal customers are forbidden from viewing user list (403)."""
        customer = User.objects.create_user(
            email='normalcust@adeshub.com',
            password='Password123!'
        )
        token, _ = Token.objects.get_or_create(user=customer)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.get(self.user_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_list_endpoint_allowed_for_staff(self):
        """Test staff users can view user list (200)."""
        staff_user = User.objects.create_superuser(
            email='staffadmin@adeshub.com',
            password='Password123!'
        )
        token, _ = Token.objects.get_or_create(user=staff_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.get(self.user_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_profile_update_successful_and_persisted(self):
        """Test authenticated customer can update first name, last name, phone number, and email address."""
        user = User.objects.create_user(
            email='initial@adeshub.com',
            password='Password123!',
            first_name='InitialFirst',
            last_name='InitialLast',
            phone_number='07123456789'
        )
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        update_payload = {
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'phone_number': '07987654321',
            'email': 'updated.email@adeshub.com'
        }
        response = self.client.patch(self.profile_url, update_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['first_name'], 'UpdatedFirst')
        self.assertEqual(response.data['user']['last_name'], 'UpdatedLast')
        self.assertEqual(response.data['user']['email'], 'updated.email@adeshub.com')
        self.assertEqual(response.data['user']['phone_number'], '07987654321')

        # Verify persisted in database
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'UpdatedFirst')
        self.assertEqual(user.last_name, 'UpdatedLast')
        self.assertEqual(user.email, 'updated.email@adeshub.com')
        self.assertEqual(user.phone_number, '07987654321')

        # Verify GET /api/auth/me/ reflects changes
        get_response = self.client.get(self.profile_url)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.data['email'], 'updated.email@adeshub.com')
        self.assertEqual(get_response.data['first_name'], 'UpdatedFirst')

    def test_profile_update_unauthenticated_rejected(self):
        """Test unauthenticated user cannot update profile (401)."""
        response = self.client.patch(self.profile_url, {'first_name': 'Hacker'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_update_duplicate_email_rejected(self):
        """Test updating email to an already registered email is rejected with 400."""
        User.objects.create_user(email='existing@adeshub.com', password='Password123!')
        user = User.objects.create_user(email='myprofile@adeshub.com', password='Password123!')
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Case-insensitive duplicate check
        response = self.client.patch(self.profile_url, {'email': 'Existing@AdesHub.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_password_change_reproduces_missing_current_password_error(self):
        """Regression test reproducing 'current_password: This field is required' error when omitted."""
        user = User.objects.create_user(email='pwtest@adeshub.com', password='CurrentPassword123!')
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Payload without current_password
        payload = {
            'new_password': 'BrandNewPassword123!',
            'new_password_confirm': 'BrandNewPassword123!'
        }
        response = self.client.post(self.change_password_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('current_password', response.data)

    def test_password_change_incorrect_current_password_rejected(self):
        """Test submitting an incorrect current password returns 400 error."""
        user = User.objects.create_user(email='pwtest2@adeshub.com', password='CorrectPassword123!')
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        payload = {
            'current_password': 'WrongPassword123!',
            'new_password': 'BrandNewPassword123!',
            'new_password_confirm': 'BrandNewPassword123!'
        }
        response = self.client.post(self.change_password_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('current_password', response.data)

    def test_password_change_mismatched_new_passwords_rejected(self):
        """Test submitting mismatched new password and confirmation returns 400 error."""
        user = User.objects.create_user(email='pwtest3@adeshub.com', password='CorrectPassword123!')
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        payload = {
            'current_password': 'CorrectPassword123!',
            'new_password': 'BrandNewPassword123!',
            'new_password_confirm': 'NonMatchingPassword123!'
        }
        response = self.client.post(self.change_password_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password_confirm', response.data)

    def test_password_change_weak_new_password_rejected(self):
        """Test submitting a weak new password (e.g. too short or entirely numeric) returns 400."""
        user = User.objects.create_user(email='pwtest4@adeshub.com', password='CorrectPassword123!')
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        payload = {
            'current_password': 'CorrectPassword123!',
            'new_password': 'short',
            'new_password_confirm': 'short'
        }
        response = self.client.post(self.change_password_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password', response.data)

    def test_password_change_successful_and_subsequent_login(self):
        """Test valid password change succeeds and customer can log in with new password while old fails."""
        user = User.objects.create_user(email='pwtest5@adeshub.com', password='OldPassword123!')
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        payload = {
            'current_password': 'OldPassword123!',
            'new_password': 'SuperNewPassword2026!',
            'new_password_confirm': 'SuperNewPassword2026!'
        }
        response = self.client.post(self.change_password_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)

        # Clear credentials
        self.client.credentials()

        # Login with old password must fail
        old_login_resp = self.client.post(
            self.login_url,
            {'email': 'pwtest5@adeshub.com', 'password': 'OldPassword123!'},
            format='json'
        )
        self.assertEqual(old_login_resp.status_code, status.HTTP_400_BAD_REQUEST)

        # Login with new password must succeed
        new_login_resp = self.client.post(
            self.login_url,
            {'email': 'pwtest5@adeshub.com', 'password': 'SuperNewPassword2026!'},
            format='json'
        )
        self.assertEqual(new_login_resp.status_code, status.HTTP_200_OK)
        self.assertIn('token', new_login_resp.data)


class PasswordResetAPITests(APITestCase):
    """
    Automated tests for Password Reset flow (Request, Validate, Confirm, Security).
    """

    client: APIClient

    def setUp(self):
        from django.core import mail
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        self.client = APIClient()
        self.reset_request_url = reverse('accounts:password-reset-request')
        self.reset_validate_url = reverse('accounts:password-reset-validate')
        self.reset_confirm_url = reverse('accounts:password-reset-confirm')
        self.login_url = reverse('accounts:login')

        mail.outbox.clear()

        self.user = User.objects.create_user(
            email='customer.reset@adeshub.com',
            password='OriginalPassword123!',
            first_name='Chioma',
            last_name='Eze'
        )
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = default_token_generator.make_token(self.user)

    def test_password_reset_request_valid_email_generates_email(self):
        """Test requesting password reset sends email with valid reset link."""
        from django.core import mail

        response = self.client.post(self.reset_request_url, {'email': 'customer.reset@adeshub.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)

        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertIn('customer.reset@adeshub.com', sent_email.to)
        self.assertIn('Reset Your AdesHub Password', sent_email.subject)
        self.assertIn('reset-password?uid=', sent_email.body)
        self.assertIn('Chioma Eze', sent_email.body)

    def test_password_reset_request_case_insensitive_email(self):
        """Test requesting password reset with mixed-case email sends email successfully."""
        from django.core import mail

        response = self.client.post(self.reset_request_url, {'email': 'Customer.Reset@AdesHub.COM'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

    def test_password_reset_request_nonexistent_email_generic_success(self):
        """Test non-existent email returns generic success without sending email (prevents enumeration)."""
        from django.core import mail

        response = self.client.post(self.reset_request_url, {'email': 'nonexistent@adeshub.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_request_inactive_user_generic_success(self):
        """Test inactive user returns generic success without sending email."""
        from django.core import mail

        inactive_user = User.objects.create_user(
            email='inactive@adeshub.com',
            password='Password123!',
            is_active=False
        )
        response = self.client.post(self.reset_request_url, {'email': 'inactive@adeshub.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_validate_token_valid(self):
        """Test validating an active token returns valid: True."""
        response = self.client.post(self.reset_validate_url, {
            'uid': self.uid,
            'token': self.token
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('valid'))

    def test_password_reset_validate_token_invalid(self):
        """Test validating an invalid token returns valid: False and 400."""
        response = self.client.post(self.reset_validate_url, {
            'uid': self.uid,
            'token': 'bogus-invalid-token'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get('valid'))

    def test_password_reset_validate_token_invalid_uid(self):
        """Test validating an invalid uid returns valid: False and 400."""
        response = self.client.post(self.reset_validate_url, {
            'uid': 'invalid-base64',
            'token': self.token
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get('valid'))

    def test_password_reset_confirm_successful(self):
        """Test completing password reset updates password, revokes old session, and enables login."""
        # Create an existing auth token to test revocation
        existing_token, _ = Token.objects.get_or_create(user=self.user)

        payload = {
            'uid': self.uid,
            'token': self.token,
            'new_password': 'NewSecurePassword2026!',
            'new_password_confirm': 'NewSecurePassword2026!'
        }
        response = self.client.post(self.reset_confirm_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)

        # Verify old token was revoked/deleted
        self.assertFalse(Token.objects.filter(key=existing_token.key).exists())

        # Verify old password no longer works
        old_login = self.client.post(self.login_url, {
            'email': self.user.email,
            'password': 'OriginalPassword123!'
        }, format='json')
        self.assertEqual(old_login.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify new password works
        new_login = self.client.post(self.login_url, {
            'email': self.user.email,
            'password': 'NewSecurePassword2026!'
        }, format='json')
        self.assertEqual(new_login.status_code, status.HTTP_200_OK)
        self.assertIn('token', new_login.data)

    def test_password_reset_confirm_token_cannot_be_reused(self):
        """Test reset token is invalidated immediately upon password change and cannot be reused."""
        payload = {
            'uid': self.uid,
            'token': self.token,
            'new_password': 'FirstChangePassword2026!',
            'new_password_confirm': 'FirstChangePassword2026!'
        }
        first_resp = self.client.post(self.reset_confirm_url, payload, format='json')
        self.assertEqual(first_resp.status_code, status.HTTP_200_OK)

        # Attempt to reuse the exact same token
        reuse_payload = {
            'uid': self.uid,
            'token': self.token,
            'new_password': 'SecondAttemptPassword2026!',
            'new_password_confirm': 'SecondAttemptPassword2026!'
        }
        second_resp = self.client.post(self.reset_confirm_url, reuse_payload, format='json')
        self.assertEqual(second_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('token', second_resp.data)

    def test_password_reset_confirm_mismatched_passwords_rejected(self):
        """Test mismatched password and confirmation is rejected with 400."""
        payload = {
            'uid': self.uid,
            'token': self.token,
            'new_password': 'PasswordOne123!',
            'new_password_confirm': 'PasswordTwo123!'
        }
        response = self.client.post(self.reset_confirm_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password_confirm', response.data)

    def test_password_reset_confirm_weak_password_rejected(self):
        """Test weak or too short password is rejected by password validators."""
        payload = {
            'uid': self.uid,
            'token': self.token,
            'new_password': 'short',
            'new_password_confirm': 'short'
        }
        response = self.client.post(self.reset_confirm_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password', response.data)

    @patch("resend.Emails.send")
    def test_password_reset_request_via_resend_sdk(self, mock_resend_send):
        """Test password reset request sends email via Resend SDK when RESEND_API_KEY is configured."""
        from django.test import override_settings

        mock_resend_send.return_value = {"id": "msg_pwd_reset_123"}

        with override_settings(
            RESEND_API_KEY="re_mock_reset_key",
            EMAIL_FROM="AdesHub <noreply@adeshubafricanstore.com>",
            EMAIL_REPLY_TO="Info@adeshub.co.uk",
            FRONTEND_URL="https://adeshubafricanstore.com",
        ):
            response = self.client.post(
                self.reset_request_url,
                {'email': 'customer.reset@adeshub.com'},
                format='json'
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)

        # Verify Resend SDK was called
        mock_resend_send.assert_called_once()
        call_params = mock_resend_send.call_args[0][0]
        self.assertEqual(call_params["from"], "AdesHub <noreply@adeshubafricanstore.com>")
        self.assertEqual(call_params["to"], "customer.reset@adeshub.com")
        self.assertEqual(call_params["subject"], "Reset Your AdesHub Password")
        self.assertEqual(call_params["reply_to"], "Info@adeshub.co.uk")
        self.assertIn("https://adeshubafricanstore.com/reset-password?uid=", call_params["text"])
        self.assertIn("https://adeshubafricanstore.com/reset-password?uid=", call_params["html"])

    @patch("resend.Emails.send")
    def test_password_reset_request_default_sender_fallback_uses_noreply(self, mock_resend_send):
        """Test that password reset defaults to AdesHub <noreply@adeshubafricanstore.com> when EMAIL_FROM is unset."""
        from django.test import override_settings

        mock_resend_send.return_value = {"id": "msg_pwd_reset_fallback_456"}

        with override_settings(
            RESEND_API_KEY="re_mock_reset_key",
            EMAIL_FROM="",
            DEFAULT_FROM_EMAIL="",
            EMAIL_REPLY_TO="Info@adeshub.co.uk",
            FRONTEND_URL="https://adeshubafricanstore.com",
        ):
            response = self.client.post(
                self.reset_request_url,
                {'email': 'customer.reset@adeshub.com'},
                format='json'
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_resend_send.assert_called_once()
        call_params = mock_resend_send.call_args[0][0]
        self.assertEqual(call_params["from"], "AdesHub <noreply@adeshubafricanstore.com>")

    @patch("resend.Emails.send")
    def test_password_reset_request_nonexistent_user_does_not_call_resend(self, mock_resend_send):
        """Test that requesting reset for unknown email returns generic 200 without invoking Resend."""
        from django.test import override_settings

        with override_settings(
            RESEND_API_KEY="re_mock_reset_key",
            EMAIL_FROM="AdesHub <noreply@adeshubafricanstore.com>",
        ):
            response = self.client.post(
                self.reset_request_url,
                {'email': 'unknown.user.999@adeshub.com'},
                format='json'
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        # Resend must NOT be called for non-existent account
        mock_resend_send.assert_not_called()

    def test_password_reset_request_logging_emitted(self):
        """Test that password reset request and lookup results are logged safely without leaking tokens."""
        with self.assertLogs('apps.accounts', level='INFO') as log_context:
            self.client.post(
                self.reset_request_url,
                {'email': 'customer.reset@adeshub.com'},
                format='json'
            )
            # Verify request received and account lookup logs
            logs_str = " ".join(log_context.output)
            self.assertIn("[PasswordReset] Request received for email", logs_str)
            self.assertIn("[PasswordReset] Account lookup succeeded", logs_str)
            # Ensure sensitive user details or tokens are not leaked in log output
            self.assertNotIn(self.token, logs_str)

    @patch("resend.Emails.send")
    def test_password_reset_request_resend_failure_does_not_crash(self, mock_resend_send):
        """Test password reset request handles Resend API failure gracefully and returns standard 200 OK."""
        from django.test import override_settings

        mock_resend_send.side_effect = Exception("Resend API rate limit exceeded")

        with override_settings(
            RESEND_API_KEY="re_mock_reset_key",
            EMAIL_FROM="AdesHub <noreply@adeshubafricanstore.com>",
        ):
            response = self.client.post(
                self.reset_request_url,
                {'email': 'customer.reset@adeshub.com'},
                format='json'
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        # Ensure error details and tokens are not leaked
        self.assertNotIn("rate limit", str(response.data))
        self.assertNotIn("token", str(response.data))
