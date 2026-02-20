import random
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from accounts.models import User
from driver.models import Driver
from .models import Delivery, DeliveryRating, DeliveryTip
from .serializers import (
    DeliveryCreateSerializer,
    DeliveryListSerializer,
    DeliveryDetailSerializer,
    DeliveryStatusSerializer,
    DeliveryRatingCreateSerializer,
    DeliveryTipCreateSerializer,
)


def _make_pin(length=4):
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def _ensure_role(user, role: str):
    return getattr(user, "role", None) == role


def _get_driver_for_user(user: User) -> Driver:
    """
    Works for:
    1) DriverProfile with OneToOneField(User) named 'user'
    2) Multi-table inheritance Driver(User) where PK matches user_id
    """
    # OneToOne profile case
    try:
        return Driver.objects.get(user=user)
    except Exception:
        pass

    # Inheritance case
    return get_object_or_404(Driver, user_id=user.user_id)


# ---------------------------
# CUSTOMER: Delivery CRUD
# ---------------------------

class DeliveryListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Delivery.objects.filter(customer=request.user).order_by("-id")
        return Response(DeliveryListSerializer(qs, many=True).data, status=200)

    @transaction.atomic
    def post(self, request):
        if not (_ensure_role(request.user, "customer") or _ensure_role(request.user, "business")):
            return Response({"detail": "Only customer/business can create delivery."}, status=403)

        ser = DeliveryCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        delivery = Delivery.objects.create(
            customer=request.user,
            verification_pin=_make_pin(),
            status=Delivery.Status.PENDING,
            price=0,  # set later by pricing engine
            **ser.validated_data
        )

        # TODO: pricing calculation
        delivery.price = 120
        delivery.save(update_fields=["price"])

        return Response(
            {"status": "success", "message": "Delivery created.", "data": DeliveryDetailSerializer(delivery).data},
            status=status.HTTP_201_CREATED
        )


class DeliveryDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        delivery = get_object_or_404(Delivery, pk=pk)

        # customer can see own, driver can see assigned
        driver = None
        if _ensure_role(request.user, "driver"):
            try:
                driver = _get_driver_for_user(request.user)
            except Exception:
                driver = None

        if delivery.customer != request.user and (not driver or delivery.driver_id != driver.id):
            return Response({"detail": "Not allowed."}, status=403)

        return Response(DeliveryDetailSerializer(delivery).data, status=200)

    def patch(self, request, pk):
        delivery = get_object_or_404(Delivery, pk=pk, customer=request.user)

        if delivery.status not in [Delivery.Status.PENDING]:
            return Response({"detail": "You can edit only when status=pending."}, status=400)

        ser = DeliveryCreateSerializer(delivery, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()

        return Response({"status": "success", "message": "Updated.", "data": DeliveryDetailSerializer(delivery).data}, status=200)

    def delete(self, request, pk):
        delivery = get_object_or_404(Delivery, pk=pk, customer=request.user)

        if delivery.status in [Delivery.Status.DELIVERED, Delivery.Status.CANCELLED]:
            return Response({"detail": "Cannot delete now."}, status=400)

        delivery.delete()
        return Response({"status": "success", "message": "Deleted."}, status=200)


# ---------------------------
# CUSTOMER: Start Searching + Cancel
# ---------------------------

class DeliveryStartSearchingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        delivery = get_object_or_404(Delivery, pk=pk, customer=request.user)

        if delivery.status != Delivery.Status.PENDING:
            return Response({"detail": "Can start searching only from pending."}, status=400)

        delivery.status = Delivery.Status.SEARCHING
        delivery.save(update_fields=["status"])

        return Response({"status": "success", "message": "Searching for driver..."}, status=200)


class DeliveryCancelAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        delivery = get_object_or_404(Delivery, pk=pk, customer=request.user)

        if delivery.status in [Delivery.Status.DELIVERED, Delivery.Status.CANCELLED]:
            return Response({"detail": "Cannot cancel now."}, status=400)

        delivery.status = Delivery.Status.CANCELLED
        delivery.save(update_fields=["status"])

        return Response({"status": "success", "message": "Delivery cancelled."}, status=200)


# ---------------------------
# DRIVER: Available Deliveries + Accept + Status Update
# ---------------------------

class DriverAvailableDeliveriesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _ensure_role(request.user, "driver"):
            return Response({"detail": "Only drivers can access."}, status=403)

        # You can later filter by radius/vehicle type
        qs = Delivery.objects.filter(status=Delivery.Status.SEARCHING).order_by("-id")
        return Response(DeliveryListSerializer(qs, many=True).data, status=200)


class DriverAcceptDeliveryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        if not _ensure_role(request.user, "driver"):
            return Response({"detail": "Only drivers can accept."}, status=403)

        driver = _get_driver_for_user(request.user)
        delivery = get_object_or_404(Delivery, pk=pk, status=Delivery.Status.SEARCHING)

        delivery.driver = driver
        delivery.status = Delivery.Status.DRIVER_ASSIGNED
        delivery.save(update_fields=["driver", "status"])

        return Response({"status": "success", "message": "Delivery accepted."}, status=200)


class DriverUpdateDeliveryStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _ensure_role(request.user, "driver"):
            return Response({"detail": "Only drivers can update status."}, status=403)

        driver = _get_driver_for_user(request.user)
        delivery = get_object_or_404(Delivery, pk=pk, driver=driver)

        ser = DeliveryStatusSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        new_status = ser.validated_data["status"]

        allowed = {
            Delivery.Status.DRIVER_ASSIGNED: [Delivery.Status.PICKED_UP, Delivery.Status.CANCELLED],
            Delivery.Status.PICKED_UP: [Delivery.Status.IN_TRANSIT],
            Delivery.Status.IN_TRANSIT: [Delivery.Status.DELIVERED],
        }

        if delivery.status not in allowed or new_status not in allowed[delivery.status]:
            return Response({"detail": f"Invalid transition from {delivery.status} to {new_status}."}, status=400)

        delivery.status = new_status
        delivery.save(update_fields=["status"])
        return Response({"status": "success", "message": "Status updated."}, status=200)


# ---------------------------
# CUSTOMER: Rating + Tip
# ---------------------------

class DeliveryRateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        delivery = get_object_or_404(Delivery, pk=pk, customer=request.user)

        if delivery.status != Delivery.Status.DELIVERED:
            return Response({"detail": "You can rate only after delivered."}, status=400)

        if not delivery.driver:
            return Response({"detail": "No driver assigned."}, status=400)

        if DeliveryRating.objects.filter(delivery=delivery).exists():
            return Response({"detail": "Already rated."}, status=400)

        ser = DeliveryRatingCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        DeliveryRating.objects.create(
            delivery=delivery,
            customer=request.user,
            driver=delivery.driver,
            **ser.validated_data
        )

        return Response({"status": "success", "message": "Rated successfully."}, status=201)


class DeliveryTipAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        delivery = get_object_or_404(Delivery, pk=pk, customer=request.user)

        if delivery.status != Delivery.Status.DELIVERED:
            return Response({"detail": "You can tip only after delivered."}, status=400)

        if not delivery.driver:
            return Response({"detail": "No driver assigned."}, status=400)

        if DeliveryTip.objects.filter(delivery=delivery).exists():
            return Response({"detail": "Tip already sent."}, status=400)

        ser = DeliveryTipCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        DeliveryTip.objects.create(
            delivery=delivery,
            customer=request.user,
            driver=delivery.driver,
            **ser.validated_data
        )

        return Response({"status": "success", "message": "Tip sent successfully."}, status=201)