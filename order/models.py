from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User
from driver.models import Driver
from accounts.models import TimestampedModel, SoftDeletableModel
import uuid



class Delivery(TimestampedModel, SoftDeletableModel):

    class Status(models.TextChoices):
        PENDING = "pending"
        SEARCHING = "searching"
        ACCEPTED = "accepted"
        DRIVER_ASSIGNED = "driver_assigned"
        PICKED_UP = "picked_up"
        IN_TRANSIT = "in_transit"
        DELIVERED = "delivered"
        CANCELLED = "cancelled"

    class ServiceType(models.TextChoices):
        PICKUP = "pickup_delivery"
        WRECKER = "wrecker"
        REMOVAL = "removal_truck"
        GAS = "cooking_gas"

    class VehicleType(models.TextChoices):
        CAR = "car"
        BIKE = "bike"
        VAN = "van"
        WRECKER = "wrecker"
        TRUCK = "removal_truck"

    class PaymentMethod(models.TextChoices):
        CASH = "cash"
        STRIPE = "stripe"
        LYNK = "lynk"
        JN_MONEY = "jn_money"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True)

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="deliveries")
    driver = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_deliveries")

    service_type = models.CharField(max_length=30, choices=ServiceType.choices)
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices,null=True, blank=True)

    pickup_address = models.CharField(max_length=255,null=True, blank=True)
    pickup_lat = models.FloatField(null=True, blank=True)
    pickup_lng = models.FloatField(null=True, blank=True)

    dropoff_address = models.CharField(max_length=255,null=True, blank=True)
    dropoff_lat = models.FloatField(null=True, blank=True)
    dropoff_lng = models.FloatField(null=True, blank=True)

    weight = models.FloatField(null=True, blank=True)
    description = models.TextField(blank=True)
    special_instruction = models.TextField(blank=True)
    sensitivity_level = models.CharField(max_length=50, blank=True)
    fragile = models.BooleanField(default=False)

    scheduled_at = models.DateTimeField(null=True, blank=True)

    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)

    price = models.DecimalField(max_digits=10, decimal_places=2)

    service_data = models.JSONField(default=dict, blank=True)
    price_breakdown = models.JSONField(default=dict, blank=True)

    verification_pin = models.CharField(max_length=6, blank=True)

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)



class DeliveryRating(TimestampedModel):
    delivery = models.OneToOneField(Delivery, on_delete=models.CASCADE)
    customer = models.ForeignKey(User, on_delete=models.CASCADE,related_name="ratings_as_customer")
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE,related_name="ratings_as_driver")
    rating = models.PositiveIntegerField()  # 1-5
    review = models.TextField(blank=True)



class DeliveryTip(TimestampedModel):
    delivery = models.OneToOneField(Delivery, on_delete=models.CASCADE)
    customer = models.ForeignKey(User, on_delete=models.CASCADE,related_name="tips_as_customer")
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE,related_name="tips_as_driver")

    amount = models.DecimalField(max_digits=8, decimal_places=2)
