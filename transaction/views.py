from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.utils import timezone
from django.db.models.functions import Coalesce
from django.db.models import Sum, Q, Count
from decimal import Decimal
from django.db.models.functions import TruncDate
from django.utils.dateparse import parse_date
from django.db.models import DecimalField, Value
from django.shortcuts import get_object_or_404
from .models import *
from .serializers import *


class DriverWithdrawRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]


    def get(self, request, driver_id = None):

        status_filter = request.GET.get("status")

        # only admin allowed
        if request.user.role == "company" or request.user.role == "customer":
            return Response(
                {"status": "error", "detail": "Only admin and driver can access this API."},
                status=status.HTTP_403_FORBIDDEN
            )
        if not driver_id:
            driver_id = request.user.user_id

        driver = get_object_or_404(Driver, user_id=driver_id)

        withdraw_qs = WithdrawRequest.objects.filter(driver=driver).order_by("-requested_at")

        if status_filter:
            withdraw_qs = withdraw_qs.filter(status=status_filter)

        serializer = WithdrawRequestSerializer(withdraw_qs, many=True)

        return Response(
            {
                "status": "success",
                "driver_id": driver_id,
                "count": withdraw_qs.count(),
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    def post(self, request):
        user = request.user
        
        if user.role != "driver":
            return Response({"status": "error", "detail": "Only driver can request withdraw."}, status=403)

        user = Driver.objects.get(user_id=user.user_id)
        serializer = WithdrawRequestSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            withdraw = serializer.save(driver=user)

            # Deduct balance immediately (recommended approach)
            user.balance -= withdraw.amount
            user.save(update_fields=["balance"])

            DriverTransaction.objects.create(
                driver=user,
                type=DriverTransaction.Type.WITHDRAW,
                amount=-withdraw.amount,
                reference=f"Withdraw #{withdraw.id}"
            )

        return Response({
            "status": "success",
            "message": "Withdraw request submitted successfully.",
            "data": {"withdraw_id": withdraw.id}
        }, status=status.HTTP_201_CREATED)
    



class AdminProcessWithdrawAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, withdraw_id):
        user = request.user

        if user.role != "admin":
            return Response({"status": "error", "detail": "Only admin allowed."}, status=403)

        action = request.data.get("action")  # approve / reject

        try:
            withdraw = WithdrawRequest.objects.select_for_update().get(id=withdraw_id)
        except WithdrawRequest.DoesNotExist:
            return Response({"status": "error", "detail": "Not found."}, status=404)

        if withdraw.status != WithdrawRequest.Status.PENDING:
            return Response({"status": "error", "detail": "Already processed."}, status=400)

        with transaction.atomic():
            if action == "approve":
                withdraw.status = WithdrawRequest.Status.APPROVED
            elif action == "reject":
                withdraw.status = WithdrawRequest.Status.REJECTED

                # Refund balance
                driver = withdraw.driver
                driver.balance += withdraw.amount
                driver.save(update_fields=["balance"])

                DriverTransaction.objects.create(
                    driver=driver,
                    type=DriverTransaction.Type.ADJUSTMENT,
                    amount=withdraw.amount,
                    reference=f"Refund Withdraw #{withdraw.id}"
                )
            else:
                return Response({"status": "error", "detail": "Invalid action."}, status=400)

            withdraw.processed_at = timezone.now()
            withdraw.processed_by = user
            withdraw.save()

        return Response({"status": "success", "message": f"Withdraw {action}ed."})
    


class DriverWalletSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user = Driver.objects.get(user_id=user.user_id)

        if user.role != "driver":
            return Response({"status": "error", "detail": "Only driver allowed."}, status=403)

        # Total earnings from transactions
        total_earnings = DriverTransaction.objects.filter(
            driver=user,
            type=DriverTransaction.Type.DELIVERY_EARNING
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        # Total withdrawn (approved only)
        total_withdrawn = WithdrawRequest.objects.filter(
            driver=user,
            status=WithdrawRequest.Status.APPROVED
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        # Pending withdraw amount
        pending_withdraw = WithdrawRequest.objects.filter(
            driver=user,
            status=WithdrawRequest.Status.PENDING
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        return Response({
            "status": "success",
            "data": {
                "current_balance": user.balance,
                "total_earnings": total_earnings,
                "total_withdrawn": total_withdrawn,
                "pending_withdraw": pending_withdraw,
                "available_to_withdraw": user.balance,
            }
        })
    

class DriverEarningsSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role != "driver":
            return Response(
                {"status": "error", "detail": "Only driver allowed."},
                status=403
            )

        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        deliveries = Delivery.objects.filter(
            driver=user,
            status=Delivery.Status.DELIVERED
        )

        # Apply date filters safely
        if start_date:
            sd = parse_date(start_date)
            if sd:
                deliveries = deliveries.filter(created_at__date__gte=sd)

        if end_date:
            ed = parse_date(end_date)
            if ed:
                deliveries = deliveries.filter(created_at__date__lte=ed)

        total_deliveries = deliveries.count()

        total_earnings = deliveries.aggregate(
            total=Coalesce(
                Sum("price"),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )["total"]

        # Daily breakdown
        daily_qs = (
            deliveries
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(
                total_earnings=Coalesce(
                    Sum("price"),
                    Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                ),
                total_deliveries=Count("id")
            )
            .order_by("-date")
        )

        # Convert queryset to JSON-safe list
        daily_data = [
            {
                "date": row["date"].isoformat() if row["date"] else None,
                "total_earnings": row["total_earnings"],
                "total_deliveries": row["total_deliveries"],
            }
            for row in daily_qs
        ]

        return Response({
            "status": "success",
            "data": {
                "filters": {
                    "start_date": start_date,
                    "end_date": end_date,
                },
                "total_deliveries": total_deliveries,
                "total_earnings": total_earnings,
                "daily_breakdown": daily_data
            }
        })
    




from django.db.models import Sum, DecimalField, Value
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_date

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from order.models import Delivery

DECIMAL_OUT = DecimalField(max_digits=12, decimal_places=2)

def d0():
    return Value(0, output_field=DECIMAL_OUT)


class DriverEarningsDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user = Driver.objects.get(user_id=user.user_id)

        if user.role != "driver":
            return Response({"status": "error", "detail": "Only driver allowed."}, status=403)

        # Filters
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        # Pagination
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        page = max(page, 1)
        page_size = min(max(page_size, 1), 50)

        qs = Delivery.objects.filter(driver=user, status=Delivery.Status.DELIVERED)

        withdraw_qs = WithdrawRequest.objects.filter(driver=user).order_by("-requested_at")

        # Apply date filters (safe)
        if start_date:
            sd = parse_date(start_date)
            if sd:
                qs = qs.filter(created_at__date__gte=sd)

        if end_date:
            ed = parse_date(end_date)
            if ed:
                qs = qs.filter(created_at__date__lte=ed)

        trips_completed = qs.count()

        total_earnings = qs.aggregate(
            total=Coalesce(Sum("price"), d0(), output_field=DECIMAL_OUT)
        )["total"]

        # Online hours (from Driver model)
        online_hours = getattr(user, "total_online_hours", 0)

        # History list (recent deliveries)
        start = (page - 1) * page_size
        end = start + page_size

        history_qs = qs.order_by("-created_at")[start:end].values(
            "id",
            "pickup_address",
            "dropoff_address",
            "created_at",
            "price",
            "service_type",
            "vehicle_type",
        )

        history = [
            {
                "delivery_id": row["id"],
                "pickup_address": row["pickup_address"],
                "dropoff_address": row["dropoff_address"],
                "date": row["created_at"].date().isoformat() if row["created_at"] else None,
                "time": row["created_at"].time().strftime("%H:%M") if row["created_at"] else None,
                "amount": row["price"],
                "service_type": row["service_type"],
                "vehicle_type": row["vehicle_type"],
            }
            for row in history_qs
        ]
        withdraw_history = [
            {
                "withdraw_id": row.id,
                "amount": row.amount,
                "status": row.status,
                "bank_name": row.bank_name,
                "branch": row.branch,
                "swift_code": row.swift_code,
                "account_number": row.account_number,
                "account_name": row.account_name,
                "account_type": row.account_type,
                "requested_at": row.requested_at.date().isoformat() if row.requested_at else None,
                "processed_at": row.processed_at.strftime("%H:%M") if row.processed_at else None,
                "processed_by": row.processed_by.user_id if row.processed_by else None,
            }
            for row in withdraw_qs
        ]

        has_next = qs.count() > end  # simple (fine for small/medium). can optimize later.

        return Response({
            "status": "success",
            "data": {
                "summary": {
                    "current_balance": user.balance,
                    "total_earnings": total_earnings,
                    "trips_completed": trips_completed,
                    "online_hours": online_hours,
                },
                "delivery_history": history,
                "withdraw_history": withdraw_history,
                "paging": {
                    "page": page,
                    "page_size": page_size,
                    "has_next": has_next,
                },
                "filters": {
                    "start_date": start_date,
                    "end_date": end_date,
                }
            }
        })