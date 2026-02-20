from django.db import models
from accounts.models import User
from accounts.models import TimestampedModel

class Notification(TimestampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    type = models.CharField(max_length=50, choices=[('order','Order Update'),('chat','New Message'),('promo','Promotion')])
    related_order = models.ForeignKey('order.Delivery', null=True, blank=True, on_delete=models.SET_NULL)