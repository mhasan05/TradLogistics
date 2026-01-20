from django.db import models
from driver.models import Driver
from accounts.models import User
# Create your models here.

class Order(models.Model):
    order_id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    from_address_lat = models.FloatField()
    from_address_long = models.FloatField()
    to_address_lat = models.FloatField()
    to_address_long = models.FloatField()
    vehicle_type = models.CharField(max_length=10)
    weight = models.FloatField()
    price = models.FloatField()
    special_instruction = models.TextField()
    package_description = models.TextField()
    sensitivity_level = models.CharField(max_length=10)
    is_fragile_item = models.BooleanField(default=False)
    delivery_date = models.DateField()
    delivery_time = models.TimeField()
    payment_method = models.CharField(max_length=100)
    driver_id = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True)
    confirmation_pin = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)