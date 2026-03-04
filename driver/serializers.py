from rest_framework import serializers
from .models import Driver, Vehicle, Document, Rating
from accounts.serializers import UserSerializer
from company.serializers import TruckSerializer
class DriverSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    truck_id = serializers.SerializerMethodField()
    class Meta:
        model = Driver
        fields = '__all__'

    def get_truck_id(self, obj):
        if hasattr(obj, "assign_truck"):
            return obj.assign_truck.truck_id
        return None


class DriverUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        exclude = ["password","is_deleted","deleted_at","is_superuser", "is_staff", "is_active", "date_joined", "last_login", "public_id", "role", "groups", "user_permissions","phone_verified_at","email_verified_at","phone_verified","email_verified","created_at","updated_at"]


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = [
            "id",
            "driver",
            "vehicle_type",
            "brand",
            "model",
            "color",
            "registration_number",
            "image",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "driver", "created_at", "updated_at"]

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            "id",
            "driving_license_front",
            "driving_license_back",
            "national_id_front",
            "national_id_back",
            "vehicle_registration",
            "created_at",
            "updated_at",
            "status",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]