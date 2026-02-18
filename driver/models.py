from django.db import models
from accounts.models import TimestampedModel, SoftDeletableModel, User
from django.conf import settings

class Driver(TimestampedModel, SoftDeletableModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driver_profile"
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deliveries = models.PositiveIntegerField(default=0)
    total_online_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    address_text = models.TextField(blank=True)
    police_record = models.ImageField(upload_to='police_records/', null=True, blank=True)
    proof_of_address = models.ImageField(upload_to='address_records/', null=True, blank=True)
    
    location_lat = models.FloatField(null=True, blank=True)
    location_long = models.FloatField(null=True, blank=True)
    
    payment_frequency = models.CharField(max_length=20, choices=[('weekly','Weekly'),('biweekly','Bi-weekly'),('monthly','Monthly')], default='monthly')
    
    total_rating = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    is_online = models.BooleanField(default=False, db_index=True)
    is_verified = models.BooleanField(default=False, db_index=True)
    
    extra_data = models.JSONField(default=dict, blank=True)  # future: preferred areas, etc.

    def __str__(self):
        return f"Driver: {self.user}"

class Vehicle(TimestampedModel):
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='vehicles')
    vehicle_type = models.CharField(max_length=20, choices=[('bike','Bike'),('car','Car'),('van','Van'),('wrecker','Wrecker'),('removal_truck','Removal Truck')])
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    color = models.CharField(max_length=30)
    registration_number = models.CharField(max_length=20, unique=True)
    image = models.ImageField(upload_to='vehicle_images/', null=True, blank=True)

class Document(TimestampedModel):
    driver = models.OneToOneField(Driver, on_delete=models.CASCADE, related_name='documents')
    driving_license_front = models.ImageField(upload_to='licenses/')
    driving_license_back = models.ImageField(upload_to='licenses/')
    national_id_front = models.ImageField(upload_to='national_ids/',null=True, blank=True)
    national_id_back = models.ImageField(upload_to='national_ids/',null=True, blank=True)
    vehicle_registration = models.ImageField(upload_to='reg_documents/', null=True, blank=True)

# Rating stays in driver/models.py (or move to order if you prefer)
class Rating(TimestampedModel):
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey('order.Order', on_delete=models.CASCADE)
    rating = models.DecimalField(max_digits=3, decimal_places=2)
    review = models.TextField(blank=True)