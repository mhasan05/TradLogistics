import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import Conversation, Message, ConversationParticipant


@database_sync_to_async
def user_in_conversation(convo_public_id, user):
    return Conversation.objects.filter(public_id=convo_public_id, participants__user=user).exists()


@database_sync_to_async
def create_message(convo_public_id, user, text):
    convo = Conversation.objects.get(public_id=convo_public_id)
    msg = Message.objects.create(conversation=convo, sender=user, text=text, delivered_at=timezone.now())
    return {
        "id": msg.id,
        "conversation": str(convo.public_id),
        "sender": user.user_id,
        "sender_name": f"{user.first_name} {user.last_name}".strip(),
        "text": msg.text,
        "created_at": msg.created_at.isoformat(),
    }


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.public_id = self.scope["url_route"]["kwargs"]["public_id"]
        self.user = self.scope.get("user")

        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        ok = await user_in_conversation(self.public_id, self.user)
        if not ok:
            await self.close(code=4003)
            return

        self.room_group_name = f"chat_{self.public_id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({"type": "connected"}))

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        """
        Incoming payload examples:
          {"type":"message","text":"Hello"}
          {"type":"typing","is_typing":true}
        """
        data = json.loads(text_data or "{}")
        msg_type = data.get("type")

        if msg_type == "message":
            text = (data.get("text") or "").strip()
            if not text:
                return

            msg = await create_message(self.public_id, self.user, text)

            # broadcast to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "chat.message", "message": msg},
            )

        elif msg_type == "typing":
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "chat.typing", "user_id": self.user.user_id, "is_typing": bool(data.get("is_typing"))},
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({"type": "message", "data": event["message"]}))

    async def chat_typing(self, event):
        await self.send(text_data=json.dumps({"type": "typing", "data": event}))