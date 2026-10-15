from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Custom Manager for User model where email is the unique identifier
    for authentication instead of usernames.
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError('The Email field must be set')

        email = self.normalize_email(email).strip().lower()
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', User.UserType.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for AdesHub supporting Customers, Staff, and Administrators.
    """

    class UserType(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        STAFF = 'STAFF', 'Staff'
        ADMIN = 'ADMIN', 'Administrator'

    email = models.EmailField('Email Address', unique=True, db_index=True)
    first_name = models.CharField('First Name', max_length=150, blank=True)
    last_name = models.CharField('Last Name', max_length=150, blank=True)
    phone_number = models.CharField('Phone Number', max_length=20, blank=True)
    user_type = models.CharField(
        'User Type',
        max_length=20,
        choices=UserType.choices,
        default=UserType.CUSTOMER
    )

    is_active = models.BooleanField(
        'Active',
        default=True,
        help_text='Designates whether this user should be treated as active.'
    )
    is_staff = models.BooleanField(
        'Staff Status',
        default=False,
        help_text='Designates whether the user can log into this admin site.'
    )

    date_joined = models.DateTimeField('Date Joined', default=timezone.now)
    updated_at = models.DateTimeField('Updated At', auto_now=True)

    objects: UserManager = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return self.email

    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name

    def get_short_name(self):
        return self.first_name.strip() if self.first_name else ""

    @property
    def display_name(self):
        """
        Customer display name according to AdesHub identity rules:
        1. Actual first and last name when available (e.g., 'Ella Jessica')
        2. First name if last name is missing (e.g., 'Ella')
        3. Username if name fields are empty
        4. 'My Account' fallback if no usable name/username exists
        Never displays email address as the customer's primary display name.
        """
        first = (self.first_name or '').strip()
        last = (self.last_name or '').strip()
        if first and last:
            return f"{first} {last}"
        if first:
            return first
        username = getattr(self, 'username', None)
        if username and str(username).strip() and str(username).strip().lower() != self.email.lower():
            return str(username).strip()
        return "My Account"


class Address(models.Model):
    """
    Address model for customer delivery addresses.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name='User'
    )
    recipient_name = models.CharField('Recipient Name', max_length=255)
    phone_number = models.CharField('Phone Number', max_length=30)
    address_line1 = models.CharField('Address Line 1', max_length=255)
    address_line2 = models.CharField('Address Line 2', max_length=255, blank=True)
    city = models.CharField('City / Town', max_length=100)
    county_region = models.CharField('County / Region', max_length=100, blank=True)
    postal_code = models.CharField('Postal Code', max_length=20)
    country = models.CharField('Country', max_length=100, default='United Kingdom')
    is_default = models.BooleanField('Default Address', default=False)

    created_at = models.DateTimeField('Created At', auto_now_add=True)
    updated_at = models.DateTimeField('Updated At', auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Address'
        verbose_name_plural = 'Addresses'
        ordering = ['-is_default', '-updated_at']

    def __str__(self):
        return f"{self.recipient_name}, {self.address_line1}, {self.city} ({self.postal_code})"

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

