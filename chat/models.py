from django.db import models
from accounts.models import User
from driver.models import Driver
# Create your models here.

class ChatRoom(models.Model):
    room_id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    driver_id = models.ForeignKey(Driver, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)



class Message(models.Model):
    room_id = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    sender_id = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    is_seen = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)