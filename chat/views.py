from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from accounts.models import User
from .models import Conversation, ConversationParticipant, Message
from .serializers import ConversationListSerializer, MessageSerializer


class ConversationListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Conversation.objects.filter(participants__user=request.user).distinct().order_by("-id")
        data = ConversationListSerializer(qs, many=True, context={"request": request}).data
        return Response({"status": "success", "data": data}, status=200)

    @transaction.atomic
    def post(self, request):
        """
        Create or fetch conversation between me and another user.
        Body: { "user_id": 12, "delivery_id": optional }
        """
        other_user_id = request.data.get("user_id")
        delivery_id = request.data.get("delivery_id")

        if not other_user_id:
            return Response({"detail": "user_id is required."}, status=400)

        other = get_object_or_404(User, user_id=other_user_id)

        # Find existing 1-to-1 conversation (optionally tied to delivery)
        qs = Conversation.objects.filter(participants__user=request.user).filter(participants__user=other)

        if delivery_id:
            qs = qs.filter(delivery_id=delivery_id)

        convo = qs.distinct().first()

        if not convo:
            convo = Conversation.objects.create(delivery_id=delivery_id if delivery_id else None)
            ConversationParticipant.objects.create(conversation=convo, user=request.user)
            ConversationParticipant.objects.create(conversation=convo, user=other)

        return Response(
            {"status": "success", "data": ConversationListSerializer(convo, context={"request": request}).data},
            status=201
        )


class ConversationMessagesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, public_id):
        convo = get_object_or_404(Conversation, public_id=public_id, participants__user=request.user)

        # simple pagination
        limit = int(request.query_params.get("limit", 30))
        before_id = request.query_params.get("before_id")  # for infinite scroll

        qs = convo.messages.select_related("sender").order_by("-id")
        if before_id:
            qs = qs.filter(id__lt=int(before_id))

        msgs = list(qs[:limit])
        msgs.reverse()  # oldest -> newest for UI
        return Response({"status": "success", "data": MessageSerializer(msgs, many=True).data}, status=200)


class ConversationMarkReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, public_id):
        convo = get_object_or_404(Conversation, public_id=public_id, participants__user=request.user)
        last_message = convo.messages.order_by("-id").first()

        participant = ConversationParticipant.objects.get(conversation=convo, user=request.user)
        if last_message:
            participant.last_read_message_id = last_message.id
        participant.last_read_at = timezone.now()
        participant.save(update_fields=["last_read_message_id", "last_read_at"])

        return Response({"status": "success", "message": "Marked as read."}, status=200)