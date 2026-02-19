import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from accounts.models import User


class Company(User):
    class BusinessType(models.TextChoices):
        ECOMMERCE = "ecommerce", _("E-commerce / Shiping Company")
        RESTAURANT = "gas_company", _("Gas Company")
    business_type = models.CharField(max_length=30,choices=BusinessType.choices,default=BusinessType.ECOMMERCE)
    business_name = models.CharField(max_length=150, db_index=True)
    business_address = models.TextField()
    business_license = models.FileField(upload_to="business_licenses/",null=True,blank=True)
    is_verified = models.BooleanField(default=False, db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        indexes = [
            models.Index(fields=["business_type", "is_verified"]),
            models.Index(fields=["business_name"]),
        ]
    def __str__(self):
        return f"Company: {self.first_name} {self.last_name} ({self.business_name})"
