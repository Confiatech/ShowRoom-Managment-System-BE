from django.db import models
from django.utils.translation import gettext_lazy as _

from django.contrib.auth.models import (
    AbstractUser,
    BaseUserManager,
)
# Create your models here.


# Create your models here.
class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("username", email)
        extra_fields.setdefault("role", "admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model for Loom Centric Project.
    """
    email = models.EmailField(_("email address"), unique=True)
    normalized_email = models.CharField(max_length=255, unique=True, blank=True, null=True)
    username = models.CharField(max_length=30, null=True, blank=True)
    role = models.CharField(max_length=150, default="investor")
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    # Investor profile data
    cnic = models.CharField(max_length=150, null=True, blank=True)
    phone_number = models.CharField(max_length=150, null=True, blank=True)
    address = models.CharField(max_length=150, null=True, blank=True)
    first_name = models.CharField(max_length=150, null=True, blank=True)
    last_name = models.CharField(max_length=150, null=True, blank=True)

    objects = UserManager()

    class Meta:
        ordering = ['-id']

    @staticmethod
    def get_normalized_email(email):
        if not email:
            return ''
        local_part, domain_part = email.lower().split('@')
        return f"{local_part.replace('.', '')}@{domain_part}"

    def save(self, *args, **kwargs):
        # Set normalized_email based on the current email
        if self.email and self.normalized_email is None:
            self.normalized_email = self.get_normalized_email(self.email)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email