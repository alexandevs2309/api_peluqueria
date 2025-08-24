from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from apps.audit_api.mixins import AuditLoggingMixin
from .models import Client
from .serializers import ClientSerializer

class ClientViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = ['gender', 'is_active', 'preferred_stylist']
    search_fields = ['full_name', 'email', 'phone']
    ordering_fields = ['created_at', 'updated_at', 'last_visit']
    ordering = ['-created_at']  # default ordering

    # En clients_api/views.py
    def perform_create(self, serializer):
        print(f"Usuario autenticado en perform_create: {self.request.user}, Autenticado: {self.request.user.is_authenticated}")
        if not self.request.user.is_authenticated:
            raise ValueError("No hay usuario autenticado")
        serializer.save(user=self.request.user, created_by=self.request.user)