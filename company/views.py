from django.db.models import Count, Sum
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Truck
from .serializers import *
from driver.models import Driver

from django.utils import timezone
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def _ensure_roles(user, roles):
    return getattr(user, "role", None) in roles
def _get_user_company(user):

    return getattr(user, "company", None)

class TruckListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role == "admin":
            qs = Truck.objects.select_related("driver", "owner").order_by("-created_at")

        elif user.role == "company":
            qs = Truck.objects.select_related("driver", "owner").filter(owner=user).order_by("-created_at")

        elif user.role == "driver":
            qs = Truck.objects.select_related("driver", "owner").filter(driver=user).order_by("-created_at")

        else:
            return Response({"status": "error", "detail": "Not allowed."}, status=403)

        return Response({"status": "success", "data": TruckSerializer(qs, many=True).data}, status=200)

    def post(self, request):
        if not _ensure_roles(request.user, ["admin", "company"]):
            return Response({"status": "error", "detail": "Not allowed."}, status=403)
        
        assign_driver = request.data.get("assign_driver", None)
        
        data = request.data.copy()
        data["owner"] = request.user.user_id
        ser = TruckCreateUpdateSerializer(data=data)
        ser.is_valid(raise_exception=True)
        truck = ser.save()
        if assign_driver:
            driver = Driver.objects.get(user_id=assign_driver)
            driver.assign_truck = truck.truck_id
            driver.save(update_fields=["assign_truck", "updated_at"])
            print(driver.assign_truck, truck.truck_id)
        return Response({"status": "success", "data": TruckSerializer(truck).data}, status=201)


class TruckDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, public_id):
        return Truck.objects.select_related("driver", "owner").get(public_id=public_id)

    def get(self, request, public_id):
        if not _ensure_roles(request.user, ["admin", "company"]):
            return Response({"status": "error", "detail": "Not allowed."}, status=403)

        truck = self.get_object(public_id)
        return Response({"status": "success", "data": TruckSerializer(truck).data}, status=200)

    def patch(self, request, public_id):
        if not _ensure_roles(request.user, ["admin", "company"]):
            return Response({"status": "error", "detail": "Not allowed."}, status=403)

        truck = self.get_object(public_id)
        ser = TruckCreateUpdateSerializer(truck, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        truck = ser.save()
        return Response({"status": "success", "data": TruckSerializer(truck).data}, status=200)

    def delete(self, request, public_id):
        if not _ensure_roles(request.user, ["admin", "company"]):
            return Response({"status": "error", "detail": "Not allowed."}, status=403)

        truck = self.get_object(public_id)
        truck.delete()
        return Response({"status": "success", "message": "Truck deleted."}, status=200)


class TruckAssignDriverAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, public_id):
        if not _ensure_roles(request.user, ["admin", "company"]):
            return Response({"status": "error", "detail": "Not allowed."}, status=403)

        truck = Truck.objects.get(public_id=public_id)
        ser = AssignDriverSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        driver = Driver.objects.get(user_id=ser.validated_data["driver_id"])

        truck.driver = driver
        truck.save(update_fields=["driver", "updated_at"])

        truck = Truck.objects.select_related("driver", "owner").get(public_id=public_id)
        return Response({"status": "success", "data": TruckSerializer(truck).data}, status=200)


class TruckUnassignDriverAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, public_id):
        if not _ensure_roles(request.user, ["admin", "company"]):
            return Response({"status": "error", "detail": "Not allowed."}, status=403)

        truck = Truck.objects.get(public_id=public_id)
        truck.driver = None
        truck.save(update_fields=["driver", "updated_at"])

        truck = Truck.objects.select_related("driver", "owner").get(public_id=public_id)
        return Response({"status": "success", "data": TruckSerializer(truck).data}, status=200)


class TruckInventoryUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, public_id):
        if not _ensure_roles(request.user, ["admin", "company"]):
            return Response({"status": "error", "detail": "Not allowed."}, status=403)

        truck = Truck.objects.get(public_id=public_id)
        ser = TruckInventoryUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        mode = ser.validated_data["mode"]
        d12 = ser.validated_data.get("cylinder_12kg")
        d25 = ser.validated_data.get("cylinder_25kg")

        if mode == "replace":
            if d12 is not None:
                truck.cylinder_12kg = d12
            if d25 is not None:
                truck.cylinder_25kg = d25

        elif mode == "add":
            if d12 is not None:
                truck.cylinder_12kg += d12
            if d25 is not None:
                truck.cylinder_25kg += d25

        elif mode == "subtract":
            if d12 is not None:
                truck.cylinder_12kg = max(0, truck.cylinder_12kg - d12)
            if d25 is not None:
                truck.cylinder_25kg = max(0, truck.cylinder_25kg - d25)

        truck.save(update_fields=["cylinder_12kg", "cylinder_25kg", "updated_at"])
        return Response({"status": "success", "data": TruckSerializer(truck).data}, status=200)


class FleetDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _ensure_roles(request.user, ["admin", "company"]):
            return Response({"status": "error", "detail": "Not allowed."}, status=403)

        qs = Truck.objects.all()

        total_trucks = qs.count()
        assigned_trucks = qs.filter(driver__isnull=False).count()
        unassigned_trucks = qs.filter(driver__isnull=True).count()

        by_status = list(qs.values("status").annotate(total=Count("id")).order_by())
        by_vehicle_type = list(qs.values("vehicle_type").annotate(total=Count("id")).order_by())

        inventory = qs.aggregate(
            total_12kg=Sum("cylinder_12kg"),
            total_25kg=Sum("cylinder_25kg"),
        )

        return Response({
            "status": "success",
            "data": {
                "total_trucks": total_trucks,
                "assigned_trucks": assigned_trucks,
                "unassigned_trucks": unassigned_trucks,
                "by_status": by_status,
                "by_vehicle_type": by_vehicle_type,
                "inventory_totals": {
                    "cylinder_12kg": inventory["total_12kg"] or 0,
                    "cylinder_25kg": inventory["total_25kg"] or 0,
                },
            }
        }, status=200)
    



class TruckLocationUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, public_id):
        user = request.user

        # only driver can send tracking
        if user.role != "driver":
            return Response({"status": "error", "detail": "Only driver can update location."}, status=403)

        ser = TruckLocationUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        truck = Truck.objects.get(public_id=public_id)

        # ensure driver owns this truck assignment
        if not truck.driver_id or truck.driver_id != user.user_id:
            return Response({"status": "error", "detail": "This truck is not assigned to you."}, status=403)

        if not truck.is_tracking_enabled:
            return Response({"status": "error", "detail": "Tracking disabled for this truck."}, status=400)

        truck.last_lat = ser.validated_data["lat"]
        truck.last_lng = ser.validated_data["lng"]
        truck.last_location_updated_at = timezone.now()
        truck.save(update_fields=["last_lat", "last_lng", "last_location_updated_at"])

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"truck_{truck.public_id}",
            {
                "type": "truck.location",
                "payload": {
                    "truck_public_id": str(truck.public_id),
                    "truck_id": truck.truck_id,
                    "lat": truck.last_lat,
                    "lng": truck.last_lng,
                    "updated_at": truck.last_location_updated_at.isoformat(),
                },
            },
        )

        return Response({
            "status": "success",
            "message": "Location updated",
            "data": {
                "truck_public_id": str(truck.public_id),
                "lat": truck.last_lat,
                "lng": truck.last_lng,
                "updated_at": truck.last_location_updated_at.isoformat(),
            }
        }, status=200)
    



class ZoneListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _ensure_roles(request.user, ["admin", "company"]):
            return Response({"status": "error", "detail": "Not allowed."}, status=403)

        user_company = _get_user_company(request.user)

        qs = Zone.objects.all().order_by("-id")
        if user_company:
            qs = qs.filter(company=user_company)

        return Response({"status": "success", "data": ZoneSerializer(qs, many=True).data}, status=200)

    def post(self, request):
        if not _ensure_roles(request.user, ["admin", "company"]):
            return Response({"status": "error", "detail": "Not allowed."}, status=403)

        data = request.data.copy()

        user_company = _get_user_company(request.user)
        if user_company:
            data["company"] = user_company

        ser = ZoneSerializer(data=data)
        ser.is_valid(raise_exception=True)
        zone = ser.save()

        return Response({"status": "success", "data": ZoneSerializer(zone).data}, status=201)


class ZoneDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self, request):
        qs = Zone.objects.all()
        user_company = _get_user_company(request.user)
        if user_company:
            qs = qs.filter(company=user_company)
        return qs

    def get(self, request, id):
        if not _ensure_roles(request.user, ["admin", "company"]):
            return Response({"status": "error", "detail": "Not allowed."}, status=403)

        zone = get_object_or_404(self.get_queryset(request), id=id)
        return Response({"status": "success", "data": ZoneSerializer(zone).data}, status=200)

    def patch(self, request, id):
        if not _ensure_roles(request.user, ["admin", "company"]):
            return Response({"status": "error", "detail": "Not allowed."}, status=403)

        zone = get_object_or_404(self.get_queryset(request), id=id)

        data = request.data.copy()
        data.pop("company", None)

        ser = ZoneSerializer(zone, data=data, partial=True)
        ser.is_valid(raise_exception=True)
        zone = ser.save()

        return Response({"status": "success", "data": ZoneSerializer(zone).data}, status=200)

    def delete(self, request, id):
        if not _ensure_roles(request.user, ["admin", "company"]):
            return Response({"status": "error", "detail": "Not allowed."}, status=403)

        zone = get_object_or_404(self.get_queryset(request), id=id)
        zone.delete()
        return Response({"status": "success", "message": "Zone deleted."}, status=200)




from order.models import  Delivery
from driver.models import Driver
from django.db.models.functions import Coalesce
from django.db.models import Sum, Q, Count
from decimal import Decimal
class CompanyDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if getattr(user, "role", None) not in ["company", "admin"]:
            return Response(
                {"status": "error", "detail": "Only company/admin can access this dashboard."},
                status=403,
            )

        company = Company.objects.get(user_id=user.user_id)


        today = timezone.localdate()

        delivery_qs = Delivery.objects.all()
        driver_qs = Driver.objects.all()

        if user.role == "company":
            delivery_qs = delivery_qs.filter(driver__driver_company=company)
            driver_qs = driver_qs.filter(driver_company=company)

        


        in_transit = delivery_qs.filter(status__in=[Delivery.Status.IN_TRANSIT, Delivery.Status.PICKED_UP]).count()


        completed_deliveries = delivery_qs.filter(status__in=[Delivery.Status.DELIVERED]).count()


        online_count = driver_qs.filter(is_online=True).count()


        on_delivery_count = delivery_qs.filter(status__in=[Delivery.Status.IN_TRANSIT, Delivery.Status.PICKED_UP]).values("driver_id").distinct().count()


        offline_count = driver_qs.filter(is_online=False).count()

        today_total_revenue = Delivery.objects.filter(
            driver__driver_company=company,created_at__date=today
        ).aggregate(total=Coalesce(Sum("price"), Decimal("0.00")))["total"]

        today_total_order = Delivery.objects.filter(
            driver__driver_company=company,created_at__date=today
        ).count()


        drivers_map = list(
            driver_qs.only("location_lat", "location_long", "is_online").values(
                "location_lat", "location_long", "is_online"
            )[:200]
        )

        deliveries_map = list(
    delivery_qs.filter(
        status__in=[Delivery.Status.IN_TRANSIT, Delivery.Status.PICKED_UP]
        ).values(
            "status",
            "driver_last_lat",
            "driver_last_lng",
            "driver__first_name",
            "driver__last_name",
            "driver__assigned_trucks__truck_id"
        )[:200]
    )

        data = {
            "today_total_order": today_total_order,
            "in_transit": in_transit,
            "completed_deliveries": completed_deliveries,
            "today_total_revenue": today_total_revenue,
            "drivers": {
                "online": online_count,
                "on_delivery": on_delivery_count,
                "offline": offline_count,
            },
            "map": {
                "deliveries": [
                    {
                        
                        "status": x["status"],
                        "driver_name": x["driver__first_name"] + " " + x["driver__last_name"],
                        "truck_id": x["driver__assigned_trucks__truck_id"],
                        "driver_last_lat": x["driver_last_lat"],
                        "driver_last_lng": x["driver_last_lng"],
                        
                    }
                    for x in deliveries_map
                    if x["driver_last_lat"] is not None and x["driver_last_lng"] is not None
                ],
            },
        }

        return Response({"status": "success", "data": data})