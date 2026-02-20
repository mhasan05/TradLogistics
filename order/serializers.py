from rest_framework import serializers
from django.utils import timezone
from .models import Delivery, DeliveryRating, DeliveryTip


class DeliveryCreateSerializer(serializers.ModelSerializer):
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
        ]

    def validate_scheduled_at(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("scheduled_at cannot be in the past.")
        return value


class DeliveryListSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    driver_name = serializers.SerializerMethodField()

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
            "customer_name",
            "driver_name",
            "created_at",
            "updated_at",
        ]

    def get_customer_name(self, obj):
        return f"{obj.customer.first_name} {obj.customer.last_name}"

    def get_driver_name(self, obj):
        if not obj.driver:
            return None
        # If Driver has user:
        u = getattr(obj.driver, "user", None)
        if u:
            return f"{u.first_name} {u.last_name}"
        # If Driver inherits User:
        return f"{obj.driver.first_name} {obj.driver.last_name}"


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
        }

    def get_driver(self, obj):
        if not obj.driver:
            return None

        u = getattr(obj.driver, "user", None)
        if u:
            return {
                "driver_id": obj.driver.pk,
                "user_id": u.user_id,
                "name": f"{u.first_name} {u.last_name}",
                "phone": u.phone,
            }

        # inheritance Driver(User)
        return {
            "driver_id": obj.driver.pk,
            "user_id": obj.driver.user_id,
            "name": f"{obj.driver.first_name} {obj.driver.last_name}",
            "phone": obj.driver.phone,
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