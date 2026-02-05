from django.db import models
from accounts.models import User
from driver.models import Driver
from accounts.models import TimestampedModel
import uuid

class ChatRoom(TimestampedModel):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_rooms_as_customer')
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='chat_rooms')
    is_active = models.BooleanField(default=True)

class Message(TimestampedModel):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)  # works for both customer & driver.user
    content = models.TextField()
    is_seen = models.BooleanField(default=False)
    image = models.ImageField(upload_to='chat_images/', null=True, blank=True)