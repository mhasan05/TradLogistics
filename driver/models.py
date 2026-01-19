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



class Vehicle(models.Model):
    driver_id = models.ForeignKey(Driver, on_delete=models.CASCADE)
    vehicle_type = models.CharField(max_length=10)
    vehicle_brand = models.CharField(max_length=10)
    vehicle_model = models.CharField(max_length=10)
    vehicle_color = models.CharField(max_length=10)
    registration_number = models.CharField(max_length=10)
    vehicle_image = models.ImageField(upload_to='vehicle_image', null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)



class Document(models.Model):
    driver_id = models.ForeignKey(Driver, on_delete=models.CASCADE)
    driving_licence_front = models.ImageField(upload_to='driving_licence', null=True, blank=True)
    driving_licence_back = models.ImageField(upload_to='driving_licence', null=True, blank=True)
    national_id_front = models.ImageField(upload_to='national_id', null=True, blank=True)
    national_id_back = models.ImageField(upload_to='national_id', null=True, blank=True)
    reg_document = models.ImageField(upload_to='reg_document', null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)


class Rating(models.Model):
    driver_id = models.ForeignKey(Driver, on_delete=models.CASCADE)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    order_id = models.ForeignKey('order.Order', on_delete=models.CASCADE)
    rating = models.FloatField()
    review = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)