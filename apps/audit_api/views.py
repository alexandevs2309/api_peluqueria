from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone
from .models import AuditLog
from .serializers import AuditLogSerializer, AuditLogCreateSerializer

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para acceder a todos los logs de auditoría unificados
    """
    queryset = AuditLog.objects.all().select_related('user', 'content_type')
    serializer_class = AuditLogSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['action', 'source', 'user', 'content_type']
    search_fields = ['description', 'user__email', 'user__first_name', 'user__last_name']
    ordering_fields = ['timestamp', 'action', 'source']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        """Permite filtrar por rango de fechas y otros parámetros"""
        queryset = super().get_queryset()
        
        # Filtrar por fecha desde
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)
        
        # Filtrar por fecha hasta
        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)
        
        # Filtrar por acciones específicas
        actions = self.request.query_params.getlist('action')
        if actions:
            queryset = queryset.filter(action__in=actions)
        
        # Filtrar por fuente
        sources = self.request.query_params.getlist('source')
        if sources:
            queryset = queryset.filter(source__in=sources)
        
        # Filtrar por usuario específico
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Retorna un resumen de actividad reciente"""
        recent_logs = self.get_queryset()[:10]
        serializer = self.get_serializer(recent_logs, many=True)
        
        return Response({
            'recent_activity': serializer.data,
            'total_logs': self.get_queryset().count(),
            'actions_breakdown': []
        })
    
    @action(detail=False, methods=['get'])
    def actions(self, request):
        """Retorna la lista de acciones disponibles"""
        actions = AuditLog.ACTION_CHOICES
        return Response([{'value': action[0], 'label': action[1]} for action in actions])
    
    @action(detail=False, methods=['get'])
    def sources(self, request):
        """Retorna la lista de fuentes disponibles"""
        sources = AuditLog._meta.get_field('source').choices
        return Response([{'value': source[0], 'label': source[1]} for source in sources])
    
    @staticmethod
    def log_integration_error(service, error_message):
        """Método estático para registrar errores de integración"""
        action_map = {
            'stripe': 'STRIPE_ERROR',
            'paypal': 'PAYPAL_ERROR', 
            'twilio': 'TWILIO_ERROR',
            'sendgrid': 'SENDGRID_ERROR',
        }
        
        AuditLog.objects.create(
            action=action_map.get(service.lower(), 'INTEGRATION_ERROR'),
            description=f"Error en {service}: {error_message}",
            source='INTEGRATIONS'
        )

# Vista auxiliar para crear logs (útil para migración)
class AuditLogCreateView(viewsets.ViewSet):
    """
    Vista para crear nuevos registros de auditoría
    (Principalmente para uso interno durante la migración)
    """
    
    def create(self, request):
        serializer = AuditLogCreateSerializer(data=request.data)
        if serializer.is_valid():
            audit_log = serializer.save()
            return Response(AuditLogSerializer(audit_log).data)
        return Response(serializer.errors, status=400)
