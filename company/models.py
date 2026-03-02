import uuid
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from accounts.models import User
from django.db.models import Max


class Company(User):
    class BusinessType(models.TextChoices):
        ECOMMERCE = "ecommerce", _("E-commerce / Shiping Company")
        GAS = "gas_company", _("Gas Company")
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
    


class Zone(models.Model):
    name = models.CharField(max_length=100)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name



class Truck(models.Model):

    class VehicleType(models.TextChoices):
        SmallPickup = "small_pickup", "Small Pickup"
        MediumTruck = "medium_truck", "Medium Truck"
        LargeTruck = "large_truck", "Large Truck"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        MAINTENANCE = "maintenance", "Maintenance"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    truck_id = models.CharField(max_length=50, unique=True)  # e.g TRK-A12
    vehicle_type = models.CharField(
        max_length=20,
        choices=VehicleType.choices,
        null=True,
        blank=True
    )

    operating_zone = models.ForeignKey(
        Zone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    driver = models.ForeignKey(
        "driver.Driver",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_trucks"
    )

    # Inventory
    cylinder_12kg = models.PositiveIntegerField(default=0)
    cylinder_25kg = models.PositiveIntegerField(default=0)

    last_lat = models.FloatField(null=True, blank=True)
    last_lng = models.FloatField(null=True, blank=True)
    last_location_updated_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 🔥 AUTO GENERATE FUNCTION
    def generate_truck_id(self):
        last_truck = Truck.objects.aggregate(max_id=Max("id"))["max_id"]

        if not last_truck:
            next_number = 1
        else:
            next_number = last_truck + 1

        return f"TRK-{str(next_number).zfill(5)}"

    # 🔥 OVERRIDE SAVE
    def save(self, *args, **kwargs):
        if not self.truck_id:
            with transaction.atomic():
                self.truck_id = self.generate_truck_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.truck_id} ({self.vehicle_type})"
