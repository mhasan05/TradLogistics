from rest_framework import serializers
from .models import Address, Package, Order, OrderEvent
from accounts.serializers import UserSerializer
from driver.serializers import DriverSerializer

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'

class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
    packages = PackageSerializer(many=True, read_only=True)
    customer = UserSerializer(read_only=True)
    driver = DriverSerializer(read_only=True)

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ['public_id', 'price', 'status', 'created_at']