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
    ROLE_CHOICES = [
        ('investor', 'Investor'),
        ('show_room_owner', 'Show Room Owner'),
        ('admin', 'Admin'),
    ]
    
    email = models.EmailField(_("email address"), unique=True)
    normalized_email = models.CharField(max_length=255, unique=True, blank=True, null=True)
    username = models.CharField(max_length=30, null=True, blank=True)
    role = models.CharField(max_length=150, choices=ROLE_CHOICES, default="investor")
    
    # Show room owner specific field
    show_room_owner = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='managed_users',
        help_text="The show room owner who manages this user (for investors)"
    )
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    # Investor profile data
    cnic = models.CharField(max_length=150, null=True, blank=True)
    phone_number = models.CharField(max_length=150, null=True, blank=True)
    address = models.CharField(max_length=150, null=True, blank=True)
    show_room_name = models.CharField(max_length=500, null=True, blank=True)
    image = models.ImageField(
            null=True, blank=True,
            upload_to='show_room_images/',
            help_text="Upload show room or related image"
    )
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
    
    @property
    def is_show_room_owner(self):
        """Check if user is a show room owner"""
        return self.role == 'show_room_owner'
    
    @property
    def is_admin_or_super(self):
        """Check if user is admin or superuser"""
        return self.is_superuser or self.role == 'admin'
    
    @property
    def can_manage_cars(self):
        """Check if user can manage cars"""
        return self.is_superuser or self.role in ['admin', 'show_room_owner']
    
    def get_accessible_users(self):
        """Get users that this user can access based on their role"""
        if self.is_superuser:
            # Super admin can see all users
            return User.objects.all()
        elif self.role == 'show_room_owner':
            # Show room owner can see their own managed users + themselves
            return User.objects.filter(
                models.Q(show_room_owner=self) | models.Q(id=self.id)
            )
        else:
            # Regular users can only see themselves
            return User.objects.filter(id=self.id)