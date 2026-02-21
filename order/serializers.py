from rest_framework import serializers
from django.utils import timezone
from .models import Delivery, DeliveryRating, DeliveryTip
from driver.models import *


def _abs_file_url(field_file):
    """
    Safe file URL getter for ImageField/FileField
    """
    try:
        return field_file.url if field_file else None
    except Exception:
        return None

class DeliveryCreateSerializer(serializers.ModelSerializer):
    service_data = serializers.JSONField(required=False, default=dict)

    class Meta:
        model = Delivery
        fields = [
            "service_type",
            "vehicle_type",
            "pickup_address", "pickup_lat", "pickup_lng",
            "dropoff_address", "dropoff_lat", "dropoff_lng",
            "weight",
            "description",
            "special_instruction",
            "sensitivity_level",
            "fragile",
            "scheduled_at",
            "payment_method",
            "service_data",
        ]

    def validate_scheduled_at(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("scheduled_at cannot be in the past.")
        return value

    def validate(self, attrs):
        service_type = attrs.get("service_type")
        service_data = attrs.get("service_data") or {}

        # -------------------------
        # pickup_delivery rules
        # -------------------------
        if service_type == Delivery.ServiceType.PICKUP:
            required = ["vehicle_type", "dropoff_address", "dropoff_lat", "dropoff_lng"]
            missing = [f for f in required if not attrs.get(f)]
            if missing:
                raise serializers.ValidationError({f: "This field is required for pickup_delivery." for f in missing})

        # -------------------------
        # cooking_gas rules
        # -------------------------
        elif service_type == Delivery.ServiceType.GAS:
            # Gas usually needs only delivery address (pickup fields act as delivery address)
            gas = service_data.get("gas", {})

            required = ["cylinder_size", "brand", "transaction_type", "delivery_speed"]
            missing = [k for k in required if not gas.get(k)]
            if missing:
                raise serializers.ValidationError(
                    {"service_data": {"gas": f"Missing fields: {', '.join(missing)}"}}
                )

            # Gas doesn't need these base fields
            attrs["vehicle_type"] = attrs.get("vehicle_type") or ""
            attrs["dropoff_address"] = attrs.get("dropoff_address") or ""
            attrs["dropoff_lat"] = attrs.get("dropoff_lat")
            attrs["dropoff_lng"] = attrs.get("dropoff_lng")

        # -------------------------
        # wrecker rules
        # -------------------------
        elif service_type == Delivery.ServiceType.WRECKER:
            # wrecker needs pickup + dropoff + vehicle_type maybe fixed = wrecker
            required = ["dropoff_address", "dropoff_lat", "dropoff_lng"]
            missing = [f for f in required if not attrs.get(f)]
            if missing:
                raise serializers.ValidationError({f: "This field is required for wrecker." for f in missing})

            # if you want to force vehicle_type = wrecker:
            attrs["vehicle_type"] = Delivery.VehicleType.WRECKER

        # -------------------------
        # removal_truck rules
        # -------------------------
        elif service_type == Delivery.ServiceType.REMOVAL:
            required = ["dropoff_address", "dropoff_lat", "dropoff_lng"]
            missing = [f for f in required if not attrs.get(f)]
            if missing:
                raise serializers.ValidationError({f: "This field is required for removal_truck." for f in missing})

            # if you want to force:
            attrs["vehicle_type"] = Delivery.VehicleType.TRUCK

        return attrs


class DeliveryListSerializer(serializers.ModelSerializer):
    customer = serializers.SerializerMethodField()
    driver = serializers.SerializerMethodField()

    class Meta:
        model = Delivery
        fields = [
            "id",
            "public_id",
            "status",
            "service_type",
            "vehicle_type",
            "pickup_address",
            "dropoff_address",
            "scheduled_at",
            "payment_method",
            "price",
            "customer",
            "driver",
            "price_breakdown",
            "service_data",
            "created_at",
            "updated_at",
        ]

    def get_customer(self, obj):
        return {
            "user_id": obj.customer.user_id,
            "name": f"{obj.customer.first_name} {obj.customer.last_name}",
            "phone": obj.customer.phone,
            "profile_image": obj.customer.profile_image.url,
            

        }

    def get_driver(self, obj):
        vehicle = Vehicle.objects.filter(driver=obj.driver).first()
        if not obj.driver:
            return None

        u = getattr(obj.driver, "user", None)
        if u:
            return {
                "user_id": u.user_id,
                "name": f"{u.first_name} {u.last_name}",
                "phone": u.phone,
                "profile_image": obj.customer.profile_image.url,
                
            }

        # inheritance Driver(User)
        return {
            "user_id": obj.driver.user_id,
            "name": f"{obj.driver.first_name} {obj.driver.last_name}",
            "phone": obj.driver.phone,
            "rating_count": obj.driver.rating_count,
            "average_rating": obj.driver.average_rating,
            "vehicle_type": vehicle.vehicle_type if vehicle else None,
            "brand": vehicle.brand if vehicle else None,
            "model": vehicle.model if vehicle else None,
            "color": vehicle.color if vehicle else None,
            "registration_number": vehicle.registration_number if vehicle else None,
        }


class DeliveryDetailSerializer(serializers.ModelSerializer):
    customer = serializers.SerializerMethodField()
    driver = serializers.SerializerMethodField()

    class Meta:
        model = Delivery
        fields = "__all__"

    def get_customer(self, obj):
        return {
            "user_id": obj.customer.user_id,
            "name": f"{obj.customer.first_name} {obj.customer.last_name}",
            "phone": obj.customer.phone,
            "profile_image": obj.customer.profile_image.url,
            

        }

    def get_driver(self, obj):
        vehicle = Vehicle.objects.filter(driver=obj.driver).first()
        if not obj.driver:
            return None

        u = getattr(obj.driver, "user", None)
        if u:
            return {
                "user_id": u.user_id,
                "name": f"{u.first_name} {u.last_name}",
                "phone": u.phone,
                "profile_image": obj.customer.profile_image.url,
                
            }

        # inheritance Driver(User)
        return {
            "user_id": obj.driver.user_id,
            "name": f"{obj.driver.first_name} {obj.driver.last_name}",
            "phone": obj.driver.phone,
            "rating_count": obj.driver.rating_count,
            "average_rating": obj.driver.average_rating,
            "vehicle_type": vehicle.vehicle_type if vehicle else None,
            "brand": vehicle.brand if vehicle else None,
            "model": vehicle.model if vehicle else None,
            "color": vehicle.color if vehicle else None,
            "registration_number": vehicle.registration_number if vehicle else None,
        }


class DeliveryStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Delivery.Status.choices)


class DeliveryRatingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryRating
        fields = ["rating", "review"]

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value


class DeliveryTipCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryTip
        fields = ["amount"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value