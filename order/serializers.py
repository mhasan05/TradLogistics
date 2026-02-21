from rest_framework import serializers
from django.utils import timezone
from .models import Delivery, DeliveryRating, DeliveryTip
from driver.models import *

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