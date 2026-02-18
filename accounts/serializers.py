from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "role", "password"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        # user inactive until email is verified
        user = User.objects.create_user(password=password, is_active=False, **validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone = attrs.get("phone")
        password = attrs.get("password")
        user = authenticate(phone=phone, password=password)
        if not user:
            raise serializers.ValidationError("Invalid phone or password")
        if not user.is_active:
            raise serializers.ValidationError("Account is not active. Verify your email first.")
        attrs["user"] = user
        return attrs

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField(min_length=8)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)


class SendPhoneOTPSerializer(serializers.Serializer):
    phone = serializers.CharField()  # must be E.164 format, e.g. +8801XXXXXXXXX
    channel = serializers.ChoiceField(choices=["sms", "whatsapp"], default="sms")

class VerifyPhoneOTPSerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField(min_length=4, max_length=10)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['public_id', 'first_name', 'last_name', 'email', 'phone', 'profile_image', 'role']
        read_only_fields = ['public_id']


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ["password","is_deleted","deleted_at","is_superuser", "is_staff", "is_active", "date_joined", "last_login", "public_id", "role", "groups", "user_permissions","phone_verified_at","email_verified_at","phone_verified","email_verified"]
        read_only_fields = [
            "user_id",
            "role",
            "is_active",
            "phone_verified",
            "phone_verified_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = read_only_fields

class SendEmailOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

class VerifyEmailOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=4, max_length=10)