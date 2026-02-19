from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from .manager import UserManager
import uuid


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class SoftDeletableModel(models.Model):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

class User(AbstractBaseUser, PermissionsMixin, TimestampedModel, SoftDeletableModel):
    class Role(models.TextChoices):
        CUSTOMER = "customer", _("Customer")
        DRIVER = "driver", _("Driver")
        COMPANY = "company", _("Company")
        ADMIN = "admin", _("Admin")

    user_id = models.AutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15, unique=True)  # e.g. +18761234567
    profile_image = models.ImageField(upload_to='profile_images/', default='profile_images/default.jpg')

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)

    phone_verified = models.BooleanField(default=False)
    phone_verified_at = models.DateTimeField(null=True, blank=True)

    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()  # your existing manager

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['role']

    class Meta:
        verbose_name_plural = "Users"
        indexes = [models.Index(fields=['phone', 'email'])]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"


class EmailOTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_otps")
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "OTP"
        indexes = [
            models.Index(fields=["user", "is_used"]),
            models.Index(fields=["expires_at"]),
        ]

    def is_expired(self):
        return timezone.now() >= self.expires_at