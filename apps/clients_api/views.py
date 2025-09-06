from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.audit_api.mixins import AuditLoggingMixin
from apps.tenants_api.mixins import TenantFilterMixin, TenantPermissionMixin
from .models import Client
from .serializers import ClientSerializer

class ClientViewSet(TenantFilterMixin, TenantPermissionMixin, AuditLoggingMixin, viewsets.ModelViewSet):
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

    def perform_create(self, serializer):
        print(f"Usuario autenticado en perform_create: {self.request.user}, Autenticado: {self.request.user.is_authenticated}")
        if not self.request.user.is_authenticated:
            raise ValueError("No hay usuario autenticado")
        serializer.save(user=self.request.user, created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        client = self.get_object()
        from apps.appointments_api.models import Appointment
        from apps.pos_api.models import Sale
        
        appointments = Appointment.objects.filter(client=client).order_by('-date_time')[:10]
        sales = Sale.objects.filter(client=client).order_by('-date_time')[:10]
        
        return Response({
            'appointments': [{
                'id': apt.id,
                'date_time': apt.date_time,
                'status': apt.status,
                'service': apt.service.name if apt.service else None,
                'stylist': apt.stylist.full_name if apt.stylist else None
            } for apt in appointments],
            'sales': [{
                'id': sale.id,
                'date_time': sale.date_time,
                'total': sale.total,
                'payment_method': sale.payment_method
            } for sale in sales]
        })

    @action(detail=True, methods=['post'])
    def add_loyalty_points(self, request, pk=None):
        client = self.get_object()
        points = request.data.get('points', 0)
        
        if points > 0:
            client.loyalty_points += points
            client.save()
            return Response({'detail': f'{points} puntos agregados. Total: {client.loyalty_points}'})
        
        return Response({'error': 'Puntos deben ser mayor a 0'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def redeem_points(self, request, pk=None):
        client = self.get_object()
        points = request.data.get('points', 0)
        
        if points > 0 and client.loyalty_points >= points:
            client.loyalty_points -= points
            client.save()
            return Response({'detail': f'{points} puntos canjeados. Restantes: {client.loyalty_points}'})
        
        return Response({'error': 'Puntos insuficientes'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        client = self.get_object()
        from apps.appointments_api.models import Appointment
        from apps.pos_api.models import Sale
        from django.db import models
        
        total_appointments = Appointment.objects.filter(client=client).count()
        completed_appointments = Appointment.objects.filter(client=client, status='completed').count()
        total_spent = Sale.objects.filter(client=client).aggregate(
            total=models.Sum('total')
        )['total'] or 0
        
        return Response({
            'total_appointments': total_appointments,
            'completed_appointments': completed_appointments,
            'total_spent': float(total_spent),
            'loyalty_points': client.loyalty_points,
            'last_visit': client.last_visit
        })

    @action(detail=False, methods=['get'])
    def birthdays_this_month(self, request):
        from django.utils import timezone
        current_month = timezone.now().month
        
        clients = Client.objects.filter(
            birthday__month=current_month,
            is_active=True
        ).order_by('birthday__day')
        
        serializer = ClientSerializer(clients, many=True)
        return Response(serializer.data)