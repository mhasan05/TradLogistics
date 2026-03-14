from rest_framework import serializers
from .models import *
from accounts.serializers import UserSerializer
class CompanySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Company
        fields = '__all__'


class CompanyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        exclude = ["password","is_deleted","deleted_at","is_superuser", "is_staff", "is_active", "date_joined", "last_login", "public_id", "role", "groups", "user_permissions","phone_verified_at","email_verified_at","phone_verified","email_verified","created_at","updated_at"]




from rest_framework import serializers
from .models import Truck
from driver.models import Driver


class TruckSerializer(serializers.ModelSerializer):
    driver_name = serializers.SerializerMethodField()
    owner_id = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()
    operating_zone_name = serializers.SerializerMethodField()

    class Meta:
        model = Truck
        fields = [
            "id",
            "public_id",
            "truck_id",
            "vehicle_type",
            "operating_zone",
            "operating_zone_name",
            "owner",
            "owner_id",
            "owner_name",  
            "driver",
            "driver_name",
            "cylinder_12kg",
            "cylinder_25kg",
            "cylinder_12kg_price",
            "cylinder_25kg_price",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["public_id", "created_at", "updated_at"]

    def get_driver_name(self, obj):
        if not obj.driver:
            return None
        return f"{obj.driver.first_name} {obj.driver.last_name}"

    def get_owner_id(self, obj):
        return getattr(obj.owner, "user_id", None)
    
    def get_owner_name(self, obj):
        if not obj.owner:
            return None
        return f"{obj.owner.first_name} {obj.owner.last_name}"
    

    def get_operating_zone_name(self, obj):
        if not obj.operating_zone:
            return None
        return obj.operating_zone.name


class TruckCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Truck
        fields = [
            "vehicle_type",
            "operating_zone",
            "owner",
            "driver",
            "cylinder_12kg",
            "cylinder_25kg",
            "cylinder_12kg_price",
            "cylinder_25kg_price",
            "status",
        ]


class AssignDriverSerializer(serializers.Serializer):
    driver_id = serializers.IntegerField()

    def validate_driver_id(self, value):
        if not Driver.objects.filter(user_id=value, role="driver").exists():
            raise serializers.ValidationError("Invalid driver_id.")
        return value


class TruckInventoryUpdateSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=["replace", "add", "subtract"], default="replace")
    cylinder_12kg = serializers.IntegerField(required=False)
    cylinder_25kg = serializers.IntegerField(required=False)

    def validate(self, attrs):
        if "cylinder_12kg" not in attrs and "cylinder_25kg" not in attrs:
            raise serializers.ValidationError("Provide at least cylinder_12kg or cylinder_25kg.")
        # prevent negative inputs
        for k in ["cylinder_12kg", "cylinder_25kg"]:
            if k in attrs and attrs[k] < 0:
                raise serializers.ValidationError({k: "Must be >= 0"})
        return attrs
    

class TruckLocationUpdateSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()



class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ["id", "name", "company", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]