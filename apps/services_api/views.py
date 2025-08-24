from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from apps.audit_api.mixins import AuditLoggingMixin
from .models import Service
from .serializers import ServiceSerializer

class ServiceViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = ['category', 'duration', 'price']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price', 'duration']
    ordering = ['name']
