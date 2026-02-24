import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.shortcuts import get_object_or_404
import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.db import transaction
from order.models import Delivery
from utils.geo import haversine_m
from utils.google_maps import get_distance_and_eta_to_dropoff, GoogleMapsError

from .models import *



TRACKABLE_STATUSES = {
    Delivery.Status.ACCEPTED,
    Delivery.Status.DRIVER_ASSIGNED,
    Delivery.Status.PICKED_UP,
    Delivery.Status.IN_TRANSIT,
}

MIN_MOVE_METERS = 30
MIN_UPDATE_SECONDS = 10
GOOGLE_CACHE_SECONDS = 15

DEFAULT_PAGE_SIZE = 30
MAX_PAGE_SIZE = 100

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


from channels.generic.websocket import AsyncJsonWebsocketConsumer
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.db import transaction

from accounts.models import User
from .models import Conversation, Message, ConversationParticipant


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket:
      ws://<host>/ws/chat/<conversation_public_id>/?token=<JWT>

    Client->Server:
      {"type":"fetch_chat","page":1,"page_size":30}
      {"type":"send_message","text":"hello"}

    Server->Client:
      {"type":"chat_details","data":{...}}
      {"type":"new_message","data":{...}}
      {"type":"message_ack","data":{...}}
      {"type":"error","detail":"..."}
    """

    async def connect(self):
        self.conversation_public_id = self.scope["url_route"]["kwargs"]["public_id"]
        self.user = self.scope.get("user")

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        allowed = await self._is_participant(self.conversation_public_id, self.user.user_id)
        if not allowed:
            await self.close(code=4003)
            return

        self.group_name = f"chat_{self.conversation_public_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # optional: send initial page immediately
        payload = await self._build_chat_details(page=1, page_size=DEFAULT_PAGE_SIZE)
        await self.send_json({"type": "chat_details", "data": payload})

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        msg_type = content.get("type")

        if msg_type == "fetch_chat":
            page = int(content.get("page", 1))
            page_size = int(content.get("page_size", DEFAULT_PAGE_SIZE))
            page_size = min(max(page_size, 1), MAX_PAGE_SIZE)

            payload = await self._build_chat_details(page=page, page_size=page_size)
            await self.send_json({"type": "chat_details", "data": payload})
            return

        if msg_type == "send_message":
            text = (content.get("text") or "").strip()
            if not text:
                await self.send_json({"type": "error", "detail": "Message text is required."})
                return

            msg_data = await self._create_message(
                public_id=self.conversation_public_id,
                sender_id=self.user.user_id,
                text=text,
            )

            # ACK sender
            await self.send_json({"type": "message_ack", "data": msg_data})

            # Broadcast to everyone (including sender; frontend can ignore duplicates if needed)
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "broadcast_new_message", "data": msg_data},
            )
            return

        await self.send_json({"type": "error", "detail": "Unknown message type."})

    async def broadcast_new_message(self, event):
        await self.send_json({"type": "new_message", "data": event["data"]})

    # ---------------- DB helpers ----------------

    @sync_to_async
    def _is_participant(self, public_id, user_id) -> bool:
        return ConversationParticipant.objects.filter(
            conversation__public_id=public_id,
            user_id=user_id
        ).exists()

    @sync_to_async
    def _build_chat_details(self, page=1, page_size=DEFAULT_PAGE_SIZE):
        conv = Conversation.objects.get(public_id=self.conversation_public_id)

        participants = list(
            ConversationParticipant.objects.select_related("user")
            .filter(conversation=conv)
            .values("user_id", "user__first_name", "user__last_name", "user__phone")
        )
        participants_data = [
            {
                "user_id": p["user_id"],
                "name": f'{p["user__first_name"]} {p["user__last_name"]}'.strip(),
                "phone": p["user__phone"],
                "role": "driver" if p["user_id"] == self.user.user_id else "customer",
            }
            for p in participants
        ]

        qs = Message.objects.filter(conversation=conv).order_by("-id")
        total = qs.count()

        start = (page - 1) * page_size
        end = start + page_size

        rows = list(qs[start:end].values("id", "sender_id", "text", "created_at", "delivered_at"))
        rows.reverse()  # oldest -> newest for UI

        has_next = end < total

        # Optional conversation metadata
        data = {
            "conversation": {
                "public_id": str(conv.public_id),
                "title": getattr(conv, "title", ""),
                "delivery_id": getattr(conv, "delivery_id", None),
            },
            "participants": participants_data,
            "messages": [
                {
                    "id": r["id"],
                    "sender_id": r["sender_id"],
                    "role": "driver" if r["sender_id"] == self.user.user_id else "customer",
                    "text": r["text"],
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                    "delivered_at": r["delivered_at"].isoformat() if r["delivered_at"] else None,
                }
                for r in rows
            ],
            "paging": {
                "page": page,
                "page_size": page_size,
                "has_next": has_next,
                "total": total,
            }
        }
        return data

    @sync_to_async
    def _create_message(self, public_id, sender_id, text):
        with transaction.atomic():
            conv = Conversation.objects.select_for_update().get(public_id=public_id)

            msg = Message.objects.create(
                conversation=conv,
                sender_id=sender_id,
                text=text,
            )

            # If you want: mark delivered_at immediately for sender
            # msg.delivered_at = timezone.now()
            # msg.save(update_fields=["delivered_at"])

            # Optional: maintain last_message_at
            if hasattr(conv, "last_message_at"):
                conv.last_message_at = timezone.now()
                conv.save(update_fields=["last_message_at"])

        return {
            "id": msg.id,
            "sender_id": msg.sender_id,
            "text": msg.text,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
            "delivered_at": msg.delivered_at.isoformat() if msg.delivered_at else None,
            "conversation_public_id": str(conv.public_id),
        }

class DeliveryTrackingConsumer(AsyncJsonWebsocketConsumer):
    """
    - Driver sends: {"type":"location_update","lat":..., "lng":...}
    - Server broadcasts to group: {"type":"driver_location", ...}
    """

    async def connect(self):
        self.delivery_id = int(self.scope["url_route"]["kwargs"]["delivery_id"])
        self.group_name = f"delivery_track_{self.delivery_id}"

        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        allowed = await self._is_allowed(user.user_id, getattr(user, "role", None))
        if not allowed:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send initial snapshot (optional)
        snapshot = await self._get_snapshot()
        await self.send_json({"type": "snapshot", "data": snapshot})

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        """
        Driver sends location updates here.
        """
        msg_type = content.get("type")
        if msg_type != "location_update":
            await self.send_json({"type": "error", "detail": "Invalid message type."})
            return

        user = self.scope["user"]
        if getattr(user, "role", None) != "driver":
            await self.send_json({"type": "error", "detail": "Only driver can update location."})
            return

        lat = content.get("lat")
        lng = content.get("lng")
        if lat is None or lng is None:
            await self.send_json({"type": "error", "detail": "lat and lng are required."})
            return

        # Main logic (DB + throttle + ETA)
        result = await self._update_location(user.user_id, float(lat), float(lng))

        # ACK to driver
        await self.send_json({"type": "location_ack", "data": result})

        # Broadcast to customer/others if saved
        if result["location_saved"]:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "broadcast_location",
                    "payload": {
                        "type": "driver_location",
                        "delivery_id": self.delivery_id,
                        "location_saved": True,
                        "moved_m": result["moved_m"],
                        "lat": result["lat"],
                        "lng": result["lng"],
                        "updated_at": result["updated_at"],
                        "eta_to_dropoff": result["eta_to_dropoff"],
                    },
                },
            )

    async def broadcast_location(self, event):
        await self.send_json(event["payload"])

    # ----------------- DB / permission helpers -----------------

    @sync_to_async
    def _is_allowed(self, user_id: int, role: str | None) -> bool:
        """
        Customer: must own delivery
        Driver: must be assigned
        """
        try:
            d = Delivery.objects.only("id", "customer_id", "driver_id", "status").get(id=self.delivery_id)
        except Delivery.DoesNotExist:
            return False

        if d.status not in TRACKABLE_STATUSES:
            return False

        if role == "driver":
            return d.driver_id == user_id
        if role == "customer":
            return d.customer_id == user_id

        # allow admin if you want:
        # if role == "admin": return True
        return False

    @sync_to_async
    def _get_snapshot(self):
        d = (
            Delivery.objects.only(
                "id", "driver_last_lat", "driver_last_lng",
                "driver_last_updated_at", "estimate_arrival_time",
                "status"
            ).get(id=self.delivery_id)
        )
        return {
            "delivery_id": d.id,
            "status": d.status,
            "lat": d.driver_last_lat,
            "lng": d.driver_last_lng,
            "updated_at": d.driver_last_updated_at.isoformat() if d.driver_last_updated_at else None,
            "estimate_arrival_time": getattr(d, "estimate_arrival_time", None),
        }

    @sync_to_async
    def _update_location(self, driver_user_id: int, new_lat: float, new_lng: float):
        """
        Your existing logic adapted for WS.
        Runs in sync thread (DB + Google + cache).
        """
        now = timezone.now()

        with transaction.atomic():
            delivery = (
                Delivery.objects.select_for_update()
                .only(
                    "id", "status", "driver_id",
                    "driver_last_lat", "driver_last_lng", "driver_last_updated_at",
                    "dropoff_lat", "dropoff_lng",
                    # if you have this:
                    "estimate_arrival_time",
                )
                .get(id=self.delivery_id)
            )

            if not delivery.driver_id or delivery.driver_id != driver_user_id:
                return {
                    "location_saved": False,
                    "error": "This delivery is not assigned to you.",
                    "lat": new_lat, "lng": new_lng,
                    "moved_m": None,
                    "updated_at": now.isoformat(),
                    "eta_to_dropoff": None,
                }

            if delivery.status not in TRACKABLE_STATUSES:
                return {
                    "location_saved": False,
                    "error": "Tracking not allowed for this status.",
                    "lat": new_lat, "lng": new_lng,
                    "moved_m": None,
                    "updated_at": now.isoformat(),
                    "eta_to_dropoff": None,
                }

            moved_m = None
            should_update = True

            if delivery.driver_last_lat is not None and delivery.driver_last_lng is not None:
                moved_m = haversine_m(delivery.driver_last_lat, delivery.driver_last_lng, new_lat, new_lng)

                if delivery.driver_last_updated_at:
                    elapsed = (now - delivery.driver_last_updated_at).total_seconds()
                    if elapsed < MIN_UPDATE_SECONDS:
                        should_update = False

                if moved_m < MIN_MOVE_METERS:
                    should_update = False

            if should_update:
                delivery.driver_last_lat = new_lat
                delivery.driver_last_lng = new_lng
                delivery.driver_last_updated_at = now
                delivery.save(update_fields=["driver_last_lat", "driver_last_lng", "driver_last_updated_at"])

        # ---- Google ETA outside transaction ----
        eta_payload = None
        if delivery.dropoff_lat is not None and delivery.dropoff_lng is not None:
            cache_key = f"delivery:{delivery.id}:eta:{round(new_lat,5)}:{round(new_lng,5)}"
            eta_payload = cache.get(cache_key)

            if eta_payload is None:
                try:
                    route = get_distance_and_eta_to_dropoff(
                        origin_lat=new_lat,
                        origin_lng=new_lng,
                        dest_lat=delivery.dropoff_lat,
                        dest_lng=delivery.dropoff_lng,
                    )
                    eta_seconds = route.duration_in_traffic_s or route.duration_s
                    eta_payload = {
                        "distance_m": route.distance_m,
                        "eta_seconds": eta_seconds,
                        "eta_minutes": int(eta_seconds // 60),
                        "traffic_used": route.duration_in_traffic_s is not None,
                    }
                    cache.set(cache_key, eta_payload, GOOGLE_CACHE_SECONDS)

                    # if you store it
                    try:
                        delivery.estimate_arrival_time = str(int(eta_seconds // 60))
                        delivery.save(update_fields=["estimate_arrival_time"])
                    except Exception:
                        pass

                except GoogleMapsError as e:
                    eta_payload = {"error": str(e)}

        return {
            "location_saved": bool(should_update),
            "moved_m": moved_m,
            "lat": new_lat,
            "lng": new_lng,
            "updated_at": now.isoformat(),
            "eta_to_dropoff": eta_payload,
        }