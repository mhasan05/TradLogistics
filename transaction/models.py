from django.db import models
from driver.models import Driver

# Create your models here.
class PaymentMethod(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='payment_method', null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)


class PayoutMethod(models.Model):
    driver_id = models.ForeignKey(Driver, on_delete=models.CASCADE)
    bank_name = models.CharField(max_length=100)
    branch = models.CharField(max_length=100)
    swift_code = models.CharField(max_length=100)
    account_number = models.CharField(max_length=100)
    account_name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)




class Withdrawal(models.Model):
    trx_id = models.CharField(max_length=100)
    driver_id = models.ForeignKey(Driver, on_delete=models.CASCADE)
    amount = models.FloatField()
    bank_name = models.CharField(max_length=100)
    branch = models.CharField(max_length=100)
    swift_code = models.CharField(max_length=100)
    account_number = models.CharField(max_length=100)
    account_name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)