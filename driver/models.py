from django.db import models
from accounts.models import User

class Driver(User):
    balance = models.FloatField(default=0)
    total_delivery = models.IntegerField(default=0)
    total_online_hours = models.FloatField(default=0)
    address = models.TextField()
    police_record = models.ImageField(upload_to='police_record', null=True, blank=True)
    location_lat = models.FloatField(null=True, blank=True)
    location_long = models.FloatField(null=True, blank=True)
    payment_frequency = models.CharField(max_length=10)
    total_rating = models.FloatField(default=0)
    rating_count = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0)
    is_online = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)



# class Rating(models.Model):
#     driver_id = models.ForeignKey(Driver, on_delete=models.CASCADE)
#     rating = models.FloatField()
#     created_on = models.DateTimeField(auto_now_add=True)
#     updated_on = models.DateTimeField(auto_now=True)