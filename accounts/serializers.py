from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['public_id', 'first_name', 'last_name', 'email', 'phone', 'profile_image', 'role']
        read_only_fields = ['public_id']