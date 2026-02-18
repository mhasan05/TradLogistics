from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User
from driver.models import Driver
from accounts.models import TimestampedModel, SoftDeletableModel
import uuid

class Address(TimestampedModel):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='saved_addresses')
    label = models.CharField(max_length=50, blank=True)  # "Home", "Office"
    address_text = models.TextField()
    parish = models.CharField(max_length=30, choices=[  # Jamaica parishes
        ('kingston', 'Kingston'), ('st_andrew', 'St. Andrew'), ('st_catherine', 'St. Catherine'),
        ('clarendon', 'Clarendon'), ('manchester', 'Manchester'), ('st_elizabeth', 'St. Elizabeth'),
        ('westmoreland', 'Westmoreland'), ('hanover', 'Hanover'), ('st_james', 'St. James'),
        ('trelawny', 'Trelawny'), ('st_ann', 'St. Ann'), ('st_mary', 'St. Mary'),
        ('portland', 'Portland'), ('st_thomas', 'St. Thomas')
    ])
    lat = models.FloatField()
    long = models.FloatField()
    extra_data = models.JSONField(default=dict, blank=True)

class Package(TimestampedModel):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='packages')
    description = models.TextField()
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2)
    length_cm = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    width_cm = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    is_fragile = models.BooleanField(default=False)
    sensitivity_level = models.CharField(max_length=20, choices=[('normal','Normal'),('sensitive','Sensitive'),('high_value','High Value')])
    barcode = models.CharField(max_length=50, blank=True, unique=True, null=True)
    image = models.ImageField(upload_to='package_images/', null=True, blank=True)

class Order(TimestampedModel, SoftDeletableModel):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        CONFIRMED = "confirmed", _("Confirmed")
        ASSIGNED = "assigned", _("Assigned")
        PICKED_UP = "picked_up", _("Picked Up")
        IN_TRANSIT = "in_transit", _("In Transit")
        DELIVERED = "delivered", _("Delivered")
        CANCELLED = "cancelled", _("Cancelled")
        FAILED = "failed", _("Failed")

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    
    from_address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name='orders_from')
    to_address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name='orders_to')
    
    vehicle_type_required = models.CharField(max_length=20, choices=[('bike','Motorcycle'),('car','Car'),('van','Van'),('truck','Truck')])
    
    special_instructions = models.TextField(blank=True)
    delivery_date = models.DateField()
    delivery_time_window_start = models.TimeField(null=True, blank=True)
    delivery_time_window_end = models.TimeField(null=True, blank=True)
    
    payment_method = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='JMD')
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    confirmation_pin = models.CharField(max_length=10, null=True, blank=True)
    
    extra_data = models.JSONField(default=dict, blank=True)  # e.g. business_order_id, tracking_url

    class Meta:
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['driver', 'status']),
        ]

class OrderEvent(TimestampedModel):  # audit trail
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='events')
    status = models.CharField(max_length=20, choices=Order.Status.choices)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    note = models.TextField(blank=True)