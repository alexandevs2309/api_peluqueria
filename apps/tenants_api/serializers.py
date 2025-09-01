from rest_framework import serializers
from .models import Tenant

class TenantSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Tenant
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "owner")
