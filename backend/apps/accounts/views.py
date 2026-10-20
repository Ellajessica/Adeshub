import logging
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
from apps.core.email_service import mask_email
from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    LoginSerializer,
    UserProfileUpdateSerializer,
    PasswordResetRequestSerializer,
    PasswordResetTokenValidateSerializer,
    PasswordResetConfirmSerializer,
)
from .permissions import IsAdminOrStaff

logger = logging.getLogger(__name__)
User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    """
    Endpoint for customer user registration.
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)

        user_data = UserSerializer(user, context={'request': request}).data
        return Response({
            'message': 'User registered successfully.',
            'token': token.key,
            'user': user_data
        }, status=status.HTTP_201_CREATED)


class UserLoginView(APIView):
    """
    Endpoint for user authentication login.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)

        user_data = UserSerializer(user, context={'request': request}).data
        return Response({
            'message': 'Login successful.',
            'token': token.key,
            'user': user_data
        }, status=status.HTTP_200_OK)


class UserLogoutView(APIView):
    """
    Endpoint for user logout (deletes auth token).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            request.user.auth_token.delete()
        except (AttributeError, Token.DoesNotExist):
            pass
        return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Endpoint for retrieving and updating the authenticated user's profile.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserProfileUpdateSerializer
        return UserSerializer

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        full_user_data = UserSerializer(request.user, context={'request': request}).data
        return Response({
            'message': 'Profile updated successfully.',
            'user': full_user_data
        }, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    """
    Endpoint for authenticated password change.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        from .serializers import ChangePasswordSerializer
        from django.contrib.auth import update_session_auth_hash

        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data['current_password']):
            return Response({'current_password': ['Current password is incorrect.']}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data['new_password'])
        user.save()

        update_session_auth_hash(request, user)

        return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)


class AddressListCreateView(generics.ListCreateAPIView):
    """
    GET /api/auth/addresses/ - List user's saved addresses.
    POST /api/auth/addresses/ - Add a new delivery address.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        from .serializers import AddressSerializer
        return AddressSerializer

    def get_queryset(self):
        from .models import Address
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/auth/addresses/<id>/ - View address.
    PUT/PATCH /api/auth/addresses/<id>/ - Edit address.
    DELETE /api/auth/addresses/<id>/ - Remove address.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        from .serializers import AddressSerializer
        return AddressSerializer

    def get_queryset(self):
        from .models import Address
        return Address.objects.filter(user=self.request.user)


class UserListView(generics.ListAPIView):
    """
    Protected endpoint to list registered users (Staff/Admin only).
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrStaff]


class PasswordResetRequestView(APIView):
    """
    POST /api/auth/password-reset/
    Request a password reset link for the provided email address.
    For security, returns a generic response regardless of whether
    the account exists to prevent account enumeration.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        import sys
        from django.conf import settings
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from .email_service import send_password_reset_email, send_password_reset_email_async

        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        masked = mask_email(email)

        logger.info("[PasswordReset] Request received for email: %s", masked)

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            logger.info(
                "[PasswordReset] Account lookup succeeded for email: %s (user_id=%s, is_active=%s). Generating reset token.",
                masked,
                user.pk,
                user.is_active,
            )
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            frontend_base = getattr(settings, 'FRONTEND_URL', 'https://adeshubafricanstore.com').rstrip('/')
            reset_url = f"{frontend_base}/reset-password?uid={uid}&token={token}"

            # In test runner environment, send synchronously so test outbox has the email immediately
            if 'test' in sys.argv:
                logger.info("[PasswordReset] Test runner detected: delivering reset email synchronously for user_id=%s", user.pk)
                send_password_reset_email(user, reset_url)
            else:
                logger.info("[PasswordReset] Dispatching async background email job for user_id=%s", user.pk)
                send_password_reset_email_async(user.pk, reset_url)
        else:
            logger.warning(
                "[PasswordReset] Account lookup: no active account found matching email: %s. Email dispatch skipped (returning generic success response to prevent enumeration).",
                masked,
            )

        return Response({
            'message': 'If an account exists with this email address, a password reset link has been sent to your inbox.'
        }, status=status.HTTP_200_OK)


class PasswordResetValidateTokenView(APIView):
    """
    POST /api/auth/password-reset/validate/
    Validate whether a given uid and token combination is active and unexpired.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetTokenValidateSerializer(data=request.data)
        if serializer.is_valid():
            return Response({
                'valid': True,
                'message': 'Password reset token is valid.'
            }, status=status.HTTP_200_OK)
        return Response({
            'valid': False,
            'message': 'This password reset link is invalid or has expired.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """
    POST /api/auth/password-reset/confirm/
    Set a new password for the user associated with the validated uid and token.
    Invalidates the token immediately upon completion and purges existing active auth tokens.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        new_password = serializer.validated_data['new_password']

        # Securely set new hashed password
        user.set_password(new_password)
        user.save()

        # Invalidate existing session/auth tokens for security
        Token.objects.filter(user=user).delete()

        return Response({
            'message': 'Your password has been reset successfully. You can now log in with your new password.'
        }, status=status.HTTP_200_OK)

