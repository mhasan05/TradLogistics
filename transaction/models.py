from django.db import models
from driver.models import Driver
from order.models import Delivery
from accounts.models import TimestampedModel
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from driver.models import Driver

class PaymentMethod(TimestampedModel):
    name = models.CharField(max_length=100)  # bKash, Nagad, Card, Cash, etc.
    image = models.ImageField(upload_to='payment_icons/', null=True, blank=True)

class BankAccount(TimestampedModel):  # renamed from PayoutMethod
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='bank_accounts')
    bank_name = models.CharField(max_length=100)
    branch = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    account_name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=50)

class DriverTransaction(models.Model):
    class Type(models.TextChoices):
        DELIVERY_EARNING = "delivery_earning"
        WITHDRAW = "withdraw"
        ADJUSTMENT = "adjustment"

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name="transactions")
    type = models.CharField(max_length=30, choices=Type.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.driver} - {self.type} - {self.amount}"




class WithdrawRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        APPROVED = "approved"
        REJECTED = "rejected"

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name="withdraw_requests")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    bank_name = models.CharField(max_length=100, blank=True)
    branch = models.CharField(max_length=100, blank=True)
    swift_code = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    account_name = models.CharField(max_length=100, blank=True)
    account_type = models.CharField(max_length=50, blank=True)

    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.driver} - {self.amount} - {self.status}"