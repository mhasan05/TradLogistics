from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
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
        BUSINESS = "business", _("Business")
        ADMIN = "admin", _("Admin")

    user_id = models.AutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, unique=True)  # e.g. +18761234567
    profile_image = models.ImageField(upload_to='profile_images/', default='profile_images/default.jpg')

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)

    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_expires_at = models.DateTimeField(blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()  # your existing manager

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'email', 'role']

    class Meta:
        verbose_name_plural = "Users"
        indexes = [models.Index(fields=['phone', 'email'])]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"