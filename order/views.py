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
from .serializers import *
from django.utils import timezone
from django.db.models import Count, Sum, DecimalField, Value
from django.db.models.functions import TruncMonth, Coalesce


def _make_pin(length=4):
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def _ensure_role(user, role: str):
    return getattr(user, "role", None) == role


def _get_driver(user: User) -> Driver:
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
        user = request.user
        if not (_ensure_role(user, "customer") or _ensure_role(user, "company")):
            qs = Delivery.objects.filter(customer=request.user).order_by("-id")
            return Response({"status": "success", "data": DeliveryListSerializer(qs, many=True).data}, status=200)
        elif _ensure_role(user, "admin"):
            qs = Delivery.objects.all().order_by("-id")
            return Response({"status": "success", "data": DeliveryListSerializer(qs, many=True).data}, status=200)

    @transaction.atomic
    def post(self, request):
        if not (_ensure_role(request.user, "customer") or _ensure_role(request.user, "company")):
            return Response({"detail": "Only customer/company can create delivery."}, status=403)

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


class OngoingDeliveryListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == "customer":
            qs = Delivery.objects.filter(customer=request.user).exclude(
                status__in=[Delivery.Status.DELIVERED, Delivery.Status.CANCELLED]
            ).order_by("-id")
        elif user.role == "driver":
            driver = _get_driver(user)
            qs = Delivery.objects.filter(driver=driver).exclude(
                status__in=[Delivery.Status.DELIVERED, Delivery.Status.CANCELLED]
            ).order_by("-id")
        else:
            return Response({"detail": "Invalid role."}, status=403)
        return Response({"status": "success", "data": DeliveryListSerializer(qs, many=True).data}, status=200)
    
class PastDeliveryListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == "customer":
            qs = Delivery.objects.filter(customer=request.user,status=Delivery.Status.DELIVERED).order_by("-id")
        elif user.role == "driver":
            driver = _get_driver(user)
            qs = Delivery.objects.filter(driver=driver,status=Delivery.Status.DELIVERED).order_by("-id")
        else:
            return Response({"detail": "Invalid role."}, status=403)
        return Response({"status": "success", "data": DeliveryListSerializer(qs, many=True).data}, status=200)

class DeliveryDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        delivery = get_object_or_404(Delivery, pk=pk)

        # customer can see own, driver can see assigned
        driver = None
        if _ensure_role(request.user, "driver"):
            try:
                driver = _get_driver(request.user)
            except Exception:
                driver = None

        # if delivery.customer != request.user and (not driver or delivery.driver != driver.user_id):
        #     return Response({"detail": "Not allowed."}, status=403)

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

        driver = _get_driver(request.user)
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

        driver = _get_driver(request.user)
        delivery = get_object_or_404(Delivery, pk=pk, driver=driver)
        pin = request.data.get("pin")
        req_status = request.data.get("status")
        if req_status == Delivery.Status.DELIVERED and not pin:
            return Response({"detail": "Invalid pin."}, status=400)
        if req_status == Delivery.Status.DELIVERED and pin and delivery.pin != pin:
            return Response({"detail": "Invalid pin."}, status=400)

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

        driver = delivery.driver
        driver.average_rating = (driver.average_rating * driver.rating_count + ser.validated_data["rating"]) / (driver.rating_count + 1)
        driver.rating_count += 1
        driver.save(update_fields=["average_rating", "rating_count"])

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
    


TRACKABLE_STATUSES = {
    Delivery.Status.ACCEPTED,
    Delivery.Status.DRIVER_ASSIGNED,
    Delivery.Status.PICKED_UP,
    Delivery.Status.IN_TRANSIT,
}

from utils.google_maps import get_distance_and_eta_to_dropoff, GoogleMapsError
from utils.geo import haversine_m
from django.core.cache import cache

MIN_MOVE_METERS = 30
MIN_UPDATE_SECONDS = 10
GOOGLE_CACHE_SECONDS = 15


class DeliveryDriverLocationAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, id):
        user = request.user

        if user.role != "driver":
            return Response({"status": "error", "detail": "Only driver can update location."}, status=403)

        ser = DriverLocationUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        new_lat = ser.validated_data["lat"]
        new_lng = ser.validated_data["lng"]

        now = timezone.now()

        with transaction.atomic():
            delivery = (
                Delivery.objects.select_for_update()
                .only(
                    "id", "status", "driver_id",
                    "driver_last_lat", "driver_last_lng", "driver_last_updated_at",
                    "dropoff_lat", "dropoff_lng",
                )
                .get(id=id)
            )

            if not delivery.driver_id or delivery.driver_id != user.user_id:
                return Response({"status": "error", "detail": "This delivery is not assigned to you."}, status=403)

            if delivery.status not in TRACKABLE_STATUSES:
                return Response({"status": "error", "detail": "Tracking not allowed for this status."}, status=400)

            moved_m = None
            should_update = True

            if delivery.driver_last_lat is not None and delivery.driver_last_lng is not None:
                moved_m = haversine_m(delivery.driver_last_lat, delivery.driver_last_lng, new_lat, new_lng)

                # time throttle
                if delivery.driver_last_updated_at:
                    elapsed = (now - delivery.driver_last_updated_at).total_seconds()
                    if elapsed < MIN_UPDATE_SECONDS:
                        should_update = False

                # distance throttle (your "nearest distance then don't update" rule)
                if moved_m < MIN_MOVE_METERS:
                    should_update = False

            if should_update:
                delivery.driver_last_lat = new_lat
                delivery.driver_last_lng = new_lng
                delivery.driver_last_updated_at = now
                delivery.save(update_fields=["driver_last_lat", "driver_last_lng", "driver_last_updated_at"])

        # ---- Google ETA outside transaction (avoid holding DB lock) ----
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

                    delivery.estimate_arrival_time = str(int(eta_seconds // 60))
                    delivery.save(update_fields=["estimate_arrival_time"])

                except GoogleMapsError as e:
                    # Don’t fail location update if Google fails
                    eta_payload = {"error": str(e)}
        
        
        return Response(
            {
                "status": "success",
                "message": "Location updated" if should_update else "Ignored (too close / too frequent)",
                "data": {
                    "delivery_id": delivery.id,
                    "location_saved": should_update,
                    "moved_m": moved_m,
                    "lat": new_lat,
                    "lng": new_lng,
                    "updated_at": now,
                    "eta_to_dropoff": eta_payload,
                },
            },
            status=status.HTTP_200_OK,
        )




DECIMAL_OUT = DecimalField(max_digits=12, decimal_places=2)
MONTH_LABELS = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}

class CompanyDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (_ensure_role(request.user, "customer") or _ensure_role(request.user, "company")):
            return Response({"detail": "Only customer and company can access."}, status=403)

        qs = Delivery.objects.filter(customer=request.user).order_by("-id")

        total_deliveries = qs.count()
        total_pending = qs.filter(status=Delivery.Status.PENDING).count()
        total_searching = qs.filter(status=Delivery.Status.SEARCHING).count()
        total_driver_assigned = qs.filter(status=Delivery.Status.DRIVER_ASSIGNED).count()
        total_picked_up = qs.filter(status=Delivery.Status.PICKED_UP).count()
        total_in_transit = qs.filter(status=Delivery.Status.IN_TRANSIT).count()
        total_delivered = qs.filter(status=Delivery.Status.DELIVERED).count()
        total_cancelled = qs.filter(status=Delivery.Status.CANCELLED).count()
        total_spend = qs.filter(status=Delivery.Status.DELIVERED).aggregate(
            total=Coalesce(Sum("price"), Value(0), output_field=DECIMAL_OUT)
        )["total"]

        year = request.GET.get("year")
        metric = request.GET.get("metric", "count")

        now = timezone.now()
        year = int(year) if year and year.isdigit() else now.year

        chart_qs = qs.filter(created_at__year=year)
        chart_qs = chart_qs.filter(status=Delivery.Status.DELIVERED)

        grouped = (
            chart_qs
            .annotate(m=TruncMonth("created_at"))
            .values("m")
            .annotate(
                total_count=Count("id"),
                total_amount=Coalesce(Sum("price"), Value(0), output_field=DECIMAL_OUT),
            )
            .order_by("m")
        )

        month_map = {}
        for row in grouped:
            month_num = row["m"].month
            month_map[month_num] = {
                "count": row["total_count"],
                "amount": row["total_amount"],
            }

        series = []
        for m in range(1, 13):
            value = month_map.get(m, {"count": 0, "amount": 0})
            series.append({
                "month": m,
                "label": MONTH_LABELS[m],
                "value": value["amount"] if metric == "amount" else value["count"],
                "count": value["count"],
                "amount": value["amount"],
            })

        data = {
            "total_deliveries": total_deliveries,
            "total_pending": total_pending,
            "total_searching": total_searching,
            "total_driver_assigned": total_driver_assigned,
            "total_picked_up": total_picked_up,
            "total_in_transit": total_in_transit,
            "total_delivered": total_delivered,
            "total_cancelled": total_cancelled,
            "total_spend": total_spend,

            "delivery_overview": {
                "year": year,
                "data": series
            }
        }

        return Response({"status": "success", "data": data}, status=200)