import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class Conversation(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # optional: link to delivery/order
    delivery = models.ForeignKey(
        "order.Delivery",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
    )

    def __str__(self):
        return str(self.public_id)


class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_participations")

    # unread tracking
    last_read_message_id = models.BigIntegerField(null=True, blank=True)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("conversation", "user")


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages_sent")

    text = models.TextField(blank=True)
    # optional attachments later:
    # attachment = models.FileField(upload_to="chat/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    delivered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Msg({self.id}) in {self.conversation_id}"