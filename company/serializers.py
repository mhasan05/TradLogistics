from rest_framework import serializers
from .models import Company
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
