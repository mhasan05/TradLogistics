from django.db import models
from driver.models import Driver
from order.models import Order
from accounts.models import TimestampedModel
from django.utils.translation import gettext_lazy as _

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

class Transaction(TimestampedModel):
    class Type(models.TextChoices):
        ORDER_PAYMENT = "order_payment", _("Order Payment")
        DRIVER_PAYOUT = "driver_payout", _("Driver Payout")
        REFUND = "refund", _("Refund")

    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=Type.choices)
    status = models.CharField(max_length=20, choices=[('pending','Pending'),('completed','Completed'),('failed','Failed')])
    reference = models.CharField(max_length=100, blank=True)  # gateway trx id