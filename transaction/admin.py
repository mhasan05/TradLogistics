from django.contrib import admin
from .models import *


admin.site.register(PaymentMethod)
admin.site.register(BankAccount)
admin.site.register(DriverTransaction)
admin.site.register(WithdrawRequest)


