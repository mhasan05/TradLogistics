from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status
from .serializers import *
from .models import *


def _get_driver(request):
    return get_object_or_404(Driver, user_id=request.user.user_id)


def _ensure_driver_role(request):
    if getattr(request.user, "role", None) != "driver":
        return Response({"detail": "Only drivers can access this endpoint."}, status=status.HTTP_403_FORBIDDEN)
    return None


class VehicleListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        deny = _ensure_driver_role(request)
        if deny:
            return deny

        driver = _get_driver(request)
        qs = Vehicle.objects.filter(driver=driver).order_by("-id")
        return Response({"status": "success","data":VehicleSerializer(qs, many=True).data}, status=status.HTTP_200_OK)

    def post(self, request):
        deny = _ensure_driver_role(request)
        if deny:
            return deny

        driver = _get_driver(request)

        ser = VehicleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vehicle = ser.save(driver=driver)

        return Response(
            {"status": "success", "message": "Vehicle created successfully.", "data": VehicleSerializer(vehicle).data},
            status=status.HTTP_201_CREATED
        )


class VehicleDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, request, pk):
        driver = _get_driver(request)
        return get_object_or_404(Vehicle, pk=pk, driver=driver)

    def get(self, request, pk):
        deny = _ensure_driver_role(request)
        if deny:
            return deny

        vehicle = self.get_object(request, pk)
        return Response({"status": "success","data":VehicleSerializer(vehicle).data}, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        deny = _ensure_driver_role(request)
        if deny:
            return deny

        vehicle = self.get_object(request, pk)
        ser = VehicleSerializer(vehicle, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()

        return Response(
            {"status": "success", "message": "Vehicle updated successfully.", "data": ser.data},
            status=status.HTTP_200_OK
        )

    def put(self, request, pk):
        deny = _ensure_driver_role(request)
        if deny:
            return deny

        vehicle = self.get_object(request, pk)
        ser = VehicleSerializer(vehicle, data=request.data)  # full update
        ser.is_valid(raise_exception=True)
        ser.save()

        return Response(
            {"status": "success", "message": "Vehicle updated successfully.", "data": ser.data},
            status=status.HTTP_200_OK
        )

    def delete(self, request, pk):
        deny = _ensure_driver_role(request)
        if deny:
            return deny

        vehicle = self.get_object(request, pk)
        vehicle.delete()
        return Response({"status": "success", "message": "Vehicle deleted successfully."}, status=status.HTTP_200_OK)











class DriverDocumentAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, request):
        driver = _get_driver(request)
        return Document.objects.filter(driver=driver).first(), driver

    def get(self, request):
        deny = _ensure_driver_role(request)
        if deny:
            return deny

        doc, _driver = self.get_object(request)
        if not doc:
            return Response({"status": "error","message": "Documents not uploaded yet."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"status": "success","data":DocumentSerializer(doc).data}, status=status.HTTP_200_OK)

    def post(self, request):
        deny = _ensure_driver_role(request)
        if deny:
            return deny

        doc, driver = self.get_object(request)
        if doc:
            return Response({"status": "error","message": "Documents already exist. Use PATCH to update."}, status=status.HTTP_400_BAD_REQUEST)

        ser = DocumentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        doc = ser.save(driver=driver)

        return Response(
            {"status": "success", "message": "Documents uploaded successfully.", "data": DocumentSerializer(doc).data},
            status=status.HTTP_201_CREATED
        )

    def patch(self, request):
        deny = _ensure_driver_role(request)
        if deny:
            return deny

        doc, driver = self.get_object(request)
        if not doc:
            return Response({"status": "error","message": "Documents not found. Use POST to create."}, status=status.HTTP_404_NOT_FOUND)

        ser = DocumentSerializer(doc, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()

        return Response(
            {"status": "success", "message": "Documents updated successfully.", "data": ser.data},
            status=status.HTTP_200_OK
        )

    def put(self, request):
        deny = _ensure_driver_role(request)
        if deny:
            return deny

        doc, driver = self.get_object(request)
        if not doc:
            return Response({"status": "error","message": "Documents not found. Use POST to create."}, status=status.HTTP_404_NOT_FOUND)

        ser = DocumentSerializer(doc, data=request.data)  # full update
        ser.is_valid(raise_exception=True)
        ser.save()

        return Response(
            {"status": "success", "message": "Documents updated successfully.", "data": ser.data},
            status=status.HTTP_200_OK
        )

    def delete(self, request):
        deny = _ensure_driver_role(request)
        if deny:
            return deny

        doc, _driver = self.get_object(request)
        if not doc:
            return Response({"status": "error","message": "Documents not found."}, status=status.HTTP_404_NOT_FOUND)

        doc.delete()
        return Response({"status": "success", "message": "Documents deleted successfully."}, status=status.HTTP_200_OK)





from django.db import transaction
class AdminDriverDocumentStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, driver_id):
        if request.user.role != "admin":
            return Response(
                {"status": "error", "detail": "Only admin can access this API."},
                status=status.HTTP_403_FORBIDDEN
            )

        driver = get_object_or_404(Driver, user_id=driver_id)
        document = get_object_or_404(Document, driver=driver)

        serializer = AdminDocumentStatusUpdateSerializer(document, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]

        with transaction.atomic():
            document.status = new_status
            document.save(update_fields=["status", "updated_at"] if hasattr(document, "updated_at") else ["status"])

            # Update driver verification flag
            if new_status == "approved":
                driver.is_verified = True
            else:
                driver.is_verified = False

            driver.save(update_fields=["is_verified", "updated_at"] if hasattr(driver, "updated_at") else ["is_verified"])

        return Response(
            {
                "status": "success",
                "message": "Document status updated successfully.",
                "data": {
                    "driver_id": driver.user_id,
                    "document_status": document.status,
                    "driver_is_verified": driver.is_verified,
                }
            },
            status=status.HTTP_200_OK
        )