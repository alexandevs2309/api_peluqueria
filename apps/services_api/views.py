from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from apps.audit_api.mixins import AuditLoggingMixin
from .models import Service
from .serializers import ServiceSerializer

class ServiceViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = ['price', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price']
    ordering = ['name']

    def get_queryset(self):
        return Service.objects.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)
