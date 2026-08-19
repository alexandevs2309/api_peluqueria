from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Case, When, IntegerField
from django.utils import timezone
from .models import AuditLog
from .serializers import AuditLogSerializer, AuditLogCreateSerializer
from .utils import get_client_ip
from apps.core.tenant_permissions import TenantPermissionByAction
from apps.core.permissions import IsSuperAdmin


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para acceder a todos los logs de auditoria unificados
    """
    queryset = AuditLog.objects.all().select_related('user', 'content_type').only(
        'id', 'user__id', 'user__email', 'user__full_name',
        'action', 'description', 'content_type__id', 'content_type__model',
        'object_id', 'ip_address', 'user_agent', 'extra_data', 'timestamp', 'source', 'tenant_id'
    )
    serializer_class = AuditLogSerializer
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'audit_api.view_auditlog',
        'retrieve': 'audit_api.view_auditlog',
        'summary': 'audit_api.view_auditlog',
        'actions': 'audit_api.view_auditlog',
        'sources': 'audit_api.view_auditlog',
    }
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['action', 'source', 'user', 'content_type']
    search_fields = ['description', 'user__email', 'user__full_name']
    ordering_fields = ['timestamp', 'action', 'source']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        """Permite filtrar por rango de fechas y otros parametros"""
        queryset = super().get_queryset()

        if not self.request.user.is_superuser:
            if not hasattr(self.request, 'tenant') or not self.request.tenant:
                return AuditLog.objects.none()
            queryset = queryset.filter(user__tenant=self.request.tenant)

        # Permite scope explicito por tenant (especialmente util para SuperAdmin).
        tenant_id = self.request.query_params.get('tenant')
        if tenant_id:
            queryset = queryset.filter(user__tenant_id=tenant_id)
        
        # Filtrar por fecha desde
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)
        
        # Filtrar por fecha hasta
        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)
        
        # Filtrar por acciones especificas
        actions = self.request.query_params.getlist('action')
        if actions:
            queryset = queryset.filter(action__in=actions)
        
        # Filtrar por fuente
        sources = self.request.query_params.getlist('source')
        if sources:
            queryset = queryset.filter(source__in=sources)
        
        # Filtrar por usuario especifico
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Retorna un resumen de actividad reciente — optimizado a 3 queries"""
        queryset = self.get_queryset()
        now = timezone.now()
        last_24h = now - timezone.timedelta(hours=24)

        # Query 1: counts (total, errors, warnings, last_24h) en una sola query
        stats = queryset.aggregate(
            total_logs=Count('id'),
            error_logs=Count('id', filter=Q(action__icontains='ERROR')),
            warning_logs=Count('id', filter=Q(action='PERFORMANCE_ALERT')),
            last_24h=Count('id', filter=Q(timestamp__gte=last_24h)),
        )

        # Query 2: actions breakdown
        actions_breakdown = list(
            queryset.values('action')
            .annotate(count=Count('id'))
            .order_by('-count', 'action')[:8]
        )

        # Query 3: sources breakdown
        sources_breakdown = list(
            queryset.values('source')
            .annotate(count=Count('id'))
            .order_by('-count', 'source')[:8]
        )

        # Recent logs: only 5 (not 10) to reduce payload
        recent_logs = queryset[:5]
        serializer = self.get_serializer(recent_logs, many=True)

        return Response({
            'recent_activity': serializer.data,
            'total_logs': stats['total_logs'],
            'error_logs': stats['error_logs'],
            'warning_logs': stats['warning_logs'],
            'last_24h': stats['last_24h'],
            'actions_breakdown': actions_breakdown,
            'sources_breakdown': sources_breakdown
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
    def log_integration_error(service, error_message, request=None, user=None):
        """Metodo estatico para registrar errores de integracion"""
        action_map = {
            'stripe': 'STRIPE_ERROR',
            'paypal': 'PAYPAL_ERROR', 
            'twilio': 'TWILIO_ERROR',
            'sendgrid': 'SENDGRID_ERROR',
        }

        resolved_user = user or getattr(request, 'user', None)
        if resolved_user is not None and not getattr(resolved_user, 'is_authenticated', False):
            resolved_user = None

        ip_address = None
        user_agent = ''
        if request is not None:
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        AuditLog.objects.create(
            user=resolved_user,
            action=action_map.get(service.lower(), 'INTEGRATION_ERROR'),
            description=f"Error en {service}: {error_message}",
            ip_address=ip_address,
            user_agent=user_agent,
            source='INTEGRATIONS'
        )


# Vista auxiliar para crear logs (util para migracion)
class AuditLogCreateView(viewsets.ViewSet):
    """
    Vista para crear nuevos registros de auditoria
    (Principalmente para uso interno durante la migracion)
    """
    
    permission_classes = [IsSuperAdmin]

    def create(self, request):
        serializer = AuditLogCreateSerializer(data=request.data)
        if serializer.is_valid():
            audit_log = serializer.save()
            return Response(AuditLogSerializer(audit_log).data)
        return Response(serializer.errors, status=400)
