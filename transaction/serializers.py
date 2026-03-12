from rest_framework import serializers
from decimal import Decimal
from .models import WithdrawRequest
from driver.models import Driver


class WithdrawRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawRequest
        fields = ["id", "amount", "account_name", "account_number", "bank_name","branch","account_type","swift_code","status","requested_at", "processed_at", "processed_by"]

    def validate_amount(self, value):
        driver = self.context["request"].user
        driver = Driver.objects.get(user_id=driver.user_id)
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")

        if driver.balance < value:
            raise serializers.ValidationError("Insufficient balance.")

        return value