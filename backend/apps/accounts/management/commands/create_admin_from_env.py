import os
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounts.models import User


class Command(BaseCommand):
    help = (
        "Safely and idempotently creates a Django superuser from environment variables "
        "(DJANGO_SUPERUSER_EMAIL / DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD) "
        "without requiring shell access. If the user already exists, this command skips creation "
        "without modifying existing data."
    )

    def handle(self, *args, **options):
        raw_email = (
            os.getenv('DJANGO_SUPERUSER_EMAIL')
            or os.getenv('ADMIN_EMAIL')
            or os.getenv('DJANGO_SUPERUSER_USERNAME')
            or os.getenv('ADMIN_USERNAME')
            or ''
        ).strip().strip('\'"')

        raw_password = (
            os.getenv('DJANGO_SUPERUSER_PASSWORD')
            or os.getenv('ADMIN_PASSWORD')
            or ''
        ).strip().strip('\'"')

        first_name = (
            os.getenv('DJANGO_SUPERUSER_FIRST_NAME')
            or os.getenv('ADMIN_FIRST_NAME')
            or 'Admin'
        ).strip().strip('\'"')

        last_name = (
            os.getenv('DJANGO_SUPERUSER_LAST_NAME')
            or os.getenv('ADMIN_LAST_NAME')
            or 'User'
        ).strip().strip('\'"')

        # 1. Verify required environment variables are provided
        if not raw_email or not raw_password:
            self.stdout.write(
                self.style.WARNING(
                    "create_admin_from_env: DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD "
                    "are not configured. Skipping superuser provisioning."
                )
            )
            return

        normalized_email = raw_email.lower().strip()

        # 2. Validate email structure
        if '@' not in normalized_email:
            self.stderr.write(
                self.style.ERROR(
                    f"create_admin_from_env: '{normalized_email}' is not a valid email address. "
                    "AdesHub user accounts require a valid email address as the username."
                )
            )
            return

        # 3. Validate minimum password length
        if len(raw_password) < 8:
            self.stderr.write(
                self.style.ERROR(
                    "create_admin_from_env: Superuser password must be at least 8 characters long."
                )
            )
            return

        # 4. Check if an account already exists with this email address
        existing_user = User.objects.filter(email__iexact=normalized_email).first()
        if existing_user:
            self.stdout.write(
                self.style.NOTICE(
                    f"create_admin_from_env: Account with email '{normalized_email}' already exists "
                    f"(is_staff={existing_user.is_staff}, is_superuser={existing_user.is_superuser}). "
                    "Skipping creation to prevent modifying existing account data."
                )
            )
            return

        # 5. Create superuser within an atomic database transaction
        try:
            with transaction.atomic():
                user = User.objects.create_superuser(
                    email=normalized_email,
                    password=raw_password,
                    first_name=first_name,
                    last_name=last_name,
                )
            self.stdout.write(
                self.style.SUCCESS(
                    f"create_admin_from_env: Superuser account successfully created for '{normalized_email}' "
                    f"(user_id={user.pk}, is_staff=True, is_superuser=True, user_type={user.user_type})."
                )
            )
        except Exception as err:
            self.stderr.write(
                self.style.ERROR(
                    f"create_admin_from_env: Failed to create superuser for '{normalized_email}': {err}"
                )
            )
            raise
