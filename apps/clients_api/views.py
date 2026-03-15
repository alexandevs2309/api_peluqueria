from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from apps.audit_api.mixins import AuditLoggingMixin
from apps.tenants_api.base_viewsets import TenantScopedViewSet
from apps.tenants_api.models import Tenant
from apps.core.tenant_permissions import TenantPermissionByAction
from apps.subscriptions_api.permissions import requires_feature
from .models import Client
from .serializers import ClientSerializer

class ClientViewSet(AuditLoggingMixin, TenantScopedViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'clients_api.view_client',
        'retrieve': 'clients_api.view_client',
        'create': 'clients_api.add_client',
        'update': 'clients_api.change_client',
        'partial_update': 'clients_api.change_client',
        'destroy': 'clients_api.delete_client',
        'history': 'clients_api.view_client',
        'add_loyalty_points': 'clients_api.change_client',
        'redeem_points': 'clients_api.change_client',
        'stats': 'clients_api.view_client',
        'birthdays_this_month': 'clients_api.view_client',
        'birthdays_today': 'clients_api.view_client',
        'upcoming_birthdays': 'clients_api.view_client',
    }

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = ['gender', 'is_active', 'preferred_stylist']
    search_fields = ['full_name', 'email', 'phone']
    ordering_fields = ['created_at', 'updated_at', 'last_visit']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'tenant', None)
        if not tenant and not self.request.user.is_superuser:
            raise ValidationError('Usuario sin tenant asignado')

        instance = serializer.save(
            tenant=tenant,
            user=self.request.user,
            created_by=self.request.user
        )
        self.log_action('create', instance, self.request.user, self.request)
        return instance

    @action(detail=True, methods=['get'])
    @requires_feature('client_history')
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
        
        clients = self.get_queryset().filter(
            birthday__month=current_month,
            is_active=True
        ).order_by('birthday__day')
        
        serializer = ClientSerializer(clients, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def birthdays_today(self, request):
        from django.utils import timezone
        today = timezone.now().date()
        
        clients = self.get_queryset().filter(
            birthday__month=today.month,
            birthday__day=today.day,
            is_active=True
        )
        
        serializer = ClientSerializer(clients, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming_birthdays(self, request):
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        next_week = today + timedelta(days=7)
        
        # Clientes con cumpleaños en los próximos 7 días
        clients = self.get_queryset().filter(
            birthday__month__in=[today.month, next_week.month],
            is_active=True
        ).extra(
            select={
                'days_until_birthday': """
                    CASE 
                        WHEN EXTRACT(month FROM birthday) = %s AND EXTRACT(day FROM birthday) >= %s THEN 
                            EXTRACT(day FROM birthday) - %s
                        WHEN EXTRACT(month FROM birthday) = %s THEN 
                            EXTRACT(day FROM birthday) + (31 - %s)
                        ELSE 999
                    END
                """
            },
            select_params=[today.month, today.day, today.day, next_week.month, today.day]
        ).extra(
            where=["days_until_birthday <= 7"]
        ).order_by('days_until_birthday')
        
        serializer = ClientSerializer(clients, many=True)
        return Response(serializer.data)
