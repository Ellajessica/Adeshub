from rest_framework import serializers
from django.contrib.auth import authenticate

from .models import Address, User


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model output.
    """
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    display_name = serializers.CharField(read_only=True)
    username = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'full_name',
            'display_name',
            'phone_number',
            'user_type',
            'is_active',
            'is_staff',
            'is_superuser',
            'date_joined',
            'updated_at',
        )
        read_only_fields = ('id', 'is_active', 'is_staff', 'is_superuser', 'date_joined', 'updated_at')

    def get_username(self, obj):
        return getattr(obj, 'username', None)


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = (
            'email',
            'password',
            'password_confirm',
            'first_name',
            'last_name',
            'phone_number',
        )

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('A user with this email address already exists.')
        return email

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for email/password authentication.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email', '').strip().lower()
        password = attrs.get('password', '')

        if not email or not password:
            raise serializers.ValidationError('Must include both email and password.')

        user = authenticate(
            request=self.context.get('request'),
            username=email,
            password=password
        )

        if not user:
            raise serializers.ValidationError('Invalid email or password credentials.')

        if not user.is_active:
            raise serializers.ValidationError('User account is disabled.')

        attrs['user'] = user
        return attrs


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating logged-in user profile.
    """
    email = serializers.EmailField(required=False)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone_number', 'email')

    def validate_email(self, value):
        email = value.strip().lower()
        if not email:
            raise serializers.ValidationError('Email address cannot be empty.')
        user = self.context.get('request').user if self.context.get('request') else None
        if user and User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            raise serializers.ValidationError('A user with this email address already exists.')
        return email

    def update(self, instance, validated_data):
        if 'email' in validated_data:
            validated_data['email'] = validated_data['email'].strip().lower()
        return super().update(instance, validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change.
    Accepts current_password (or old_password as fallback).
    """
    current_password = serializers.CharField(write_only=True, required=False)
    old_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, min_length=8, required=True)
    new_password_confirm = serializers.CharField(write_only=True, min_length=8, required=True)

    def validate(self, attrs):
        current_pwd = attrs.get('current_password') or attrs.get('old_password')
        if not current_pwd:
            raise serializers.ValidationError({'current_password': ['This field is required.']})
        attrs['current_password'] = current_pwd

        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': ['New passwords do not match.']})

        user = self.context.get('request').user if self.context.get('request') else None
        try:
            from django.contrib.auth.password_validation import validate_password
            validate_password(attrs['new_password'], user=user)
        except Exception as e:
            from django.core.exceptions import ValidationError as DjangoValidationError
            if isinstance(e, DjangoValidationError):
                raise serializers.ValidationError({'new_password': list(e.messages)})
            raise

        return attrs


class AddressSerializer(serializers.ModelSerializer):
    """
    Serializer for customer delivery addresses.
    """
    class Meta:
        model = Address
        fields = (
            'id',
            'recipient_name',
            'phone_number',
            'address_line1',
            'address_line2',
            'city',
            'county_region',
            'postal_code',
            'country',
            'is_default',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for password reset request (submitting email address).
    """
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetTokenValidateSerializer(serializers.Serializer):
    """
    Serializer for validating password reset token and uid.
    """
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str

        uid = attrs.get('uid')
        token = attrs.get('token')

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({'token': ['Invalid or expired password reset link.']})

        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError({'token': ['Invalid or expired password reset link.']})

        attrs['user'] = user
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for setting a new password using a validated reset token.
    """
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError

        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': ['Passwords do not match.']})

        uid = attrs.get('uid')
        token = attrs.get('token')

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({'token': ['Invalid or expired password reset link.']})

        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError({'token': ['Invalid or expired password reset link.']})

        try:
            validate_password(attrs['new_password'], user=user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})

        attrs['user'] = user
        return attrs

