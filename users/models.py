from django.db import models
from config.utils import CustomShortUUIDField
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        user = self.model(
            email=self.normalize_email(email).lower(),
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        user = self.create_user(
            email,
            password=password,
            **extra_fields
        )
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class Profession(models.Model):
    id = CustomShortUUIDField(primary_key=True, prefix='prof_')
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = 'professions'

    def __str__(self):
        return self.name

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('professional', 'Professional'),
        ('provider', 'Provider'),
    ]
    
    id = CustomShortUUIDField(primary_key=True, prefix='user_')
    email = models.EmailField(unique=True, max_length=255, db_index=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='professional')

    # Professional-specific fields
    profession = models.ForeignKey(Profession, on_delete=models.SET_NULL, blank=True, null=True, related_name='professionals')
    license_number = models.CharField(max_length=100, blank=True, null=True)

    # Organization-specific fields
    organization_name = models.CharField(max_length=255, blank=True, null=True)
    organization_contact_email = models.EmailField(max_length=255, blank=True, null=True)
    organization_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    organization_address = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_onboarded = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = CustomUserManager()

    REQUIRED_FIELDS = ['first_name', 'last_name']
    USERNAME_FIELD = 'email'

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email
    
    def get_short_name(self):
        return self.first_name
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def clean(self):
        super().clean()
        if self.role == 'provider':
            self.profession = None
            self.license_number = None
        elif self.role == 'professional':
            self.organization_name = None
            self.organization_contact_email = None
            self.organization_contact_phone = None
            self.organization_address = None
        elif self.role == 'admin':
            self.profession = None
            self.license_number = None
            self.organization_name = None
            self.organization_contact_email = None
            self.organization_contact_phone = None
            self.organization_address = None

