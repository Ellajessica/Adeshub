from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailBackend(ModelBackend):
    """
    Custom authentication backend to authenticate users using case-insensitive email address.
    Ensures users created via Registration API or Django Admin can log in reliably regardless of case sensitivity.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username_field = getattr(User, 'USERNAME_FIELD', 'email')
            username = kwargs.get('email') or kwargs.get(username_field)

        if not username or not password:
            return None

        clean_email = username.strip().lower()
        try:
            user = User.objects.get(email__iexact=clean_email)
        except User.DoesNotExist:
            # Perform dummy password hash comparison to prevent timing attacks
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            user = User.objects.filter(email__iexact=clean_email).first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
