from rest_framework import serializers
from django.db.models import Max, Count, Q
from .models import Conversation, ConversationParticipant, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_role = serializers.SerializerMethodField()
    sender_avatar = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "conversation", "sender", "sender_name","sender_role", "sender_avatar", "text", "created_at"]
        read_only_fields = ["id", "created_at", "sender"]

    def get_sender_name(self, obj):
        return f"{obj.sender.first_name} {obj.sender.last_name}".strip()
    
    def get_sender_role(self, obj):
        return f"{obj.sender.role}".strip()

    def get_sender_avatar(self, obj):
        try:
            return obj.sender.profile_image.url if obj.sender.profile_image else None
        except Exception:
            return None


class ConversationListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "public_id", "delivery", "created_at", "other_user", "last_message", "unread_count"]

    def get_other_user(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        me = request.user
        p = obj.participants.select_related("user").exclude(user=me).first()
        if not p:
            return None
        u = p.user
        return {
            "user_id": u.user_id,
            "name": f"{u.first_name} {u.last_name}".strip(),
            "phone": u.phone,
            "role": u.role,
            "profile_image": getattr(u.profile_image, "url", None) if getattr(u, "profile_image", None) else None,
        }

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-id").select_related("sender").first()
        if not msg:
            return None
        return MessageSerializer(msg).data

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request:
            return 0
        me = request.user
        participant = obj.participants.filter(user=me).first()
        if not participant:
            return 0
        last_read_id = participant.last_read_message_id or 0
        return obj.messages.filter(id__gt=last_read_id).exclude(sender=me).count()