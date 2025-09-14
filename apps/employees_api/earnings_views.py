from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count
from django.utils import timezone
from apps.tenants_api.mixins import TenantFilterMixin, TenantPermissionMixin
from .earnings_models import Earning, FortnightSummary
from .earnings_serializers import (
    EarningSerializer, FortnightSummarySerializer, EarningCreateSerializer
)

class EarningViewSet(TenantFilterMixin, TenantPermissionMixin, viewsets.ModelViewSet):
    queryset = Earning.objects.all()
    serializer_class = EarningSerializer
    permission_classes = [IsAuthenticated]
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['employee', 'earning_type', 'fortnight_year', 'fortnight_number']
    ordering_fields = ['date_earned', 'amount']
    ordering = ['-date_earned']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # SuperAdmin ve todo
        if user.roles.filter(name='Super-Admin').exists():
            return queryset
            
        # Client-Staff solo ve sus ganancias
        if user.roles.filter(name='Client-Staff').exists():
            try:
                employee = user.employee_profile
                return queryset.filter(employee=employee)
            except:
                return queryset.none()
                
        # Client-Admin y Manager ven todas las ganancias de su tenant
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            return queryset.filter(employee__tenant=tenant)
            
        return queryset.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return EarningCreateSerializer
        return EarningSerializer
    
    @action(detail=False, methods=['get'])
    def my_earnings(self, request):
        """Ganancias del empleado autenticado"""
        try:
            employee = request.user.employee_profile
            earnings = Earning.objects.filter(employee=employee).order_by('-date_earned')[:20]
            serializer = EarningSerializer(earnings, many=True)
            return Response(serializer.data)
        except:
            return Response({'error': 'Usuario no es empleado'}, status=400)
    
    @action(detail=False, methods=['get'])
    def current_fortnight(self, request):
        """Ganancias de la quincena actual"""
        now = timezone.now()
        year, fortnight = Earning.calculate_fortnight(now)
        
        queryset = self.get_queryset().filter(
            fortnight_year=year,
            fortnight_number=fortnight
        )
        
        serializer = EarningSerializer(queryset, many=True)
        total = queryset.aggregate(total=Sum('amount'))['total'] or 0
        
        return Response({
            'earnings': serializer.data,
            'total': total,
            'fortnight_year': year,
            'fortnight_number': fortnight
        })

class FortnightSummaryViewSet(TenantFilterMixin, TenantPermissionMixin, viewsets.ModelViewSet):
    queryset = FortnightSummary.objects.all()
    serializer_class = FortnightSummarySerializer
    permission_classes = [IsAuthenticated]
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['employee', 'fortnight_year', 'is_paid']
    ordering = ['-fortnight_year', '-fortnight_number']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # SuperAdmin ve todo
        if user.roles.filter(name='Super-Admin').exists():
            return queryset
            
        # Client-Staff solo ve sus resúmenes
        if user.roles.filter(name='Client-Staff').exists():
            try:
                employee = user.employee_profile
                return queryset.filter(employee=employee)
            except:
                return queryset.none()
                
        # Client-Admin y Manager ven todos los resúmenes de su tenant
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            return queryset.filter(employee__tenant=tenant)
            
        return queryset.none()
    
    @action(detail=False, methods=['get'])
    def my_summary(self, request):
        """Resumen de ganancias del empleado autenticado"""
        try:
            employee = request.user.employee_profile
            summaries = FortnightSummary.objects.filter(employee=employee)[:12]
            serializer = FortnightSummarySerializer(summaries, many=True)
            return Response(serializer.data)
        except:
            return Response({'error': 'Usuario no es empleado'}, status=400)
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Marcar quincena como pagada"""
        summary = self.get_object()
        summary.is_paid = True
        summary.paid_at = timezone.now()
        summary.paid_by = request.user
        summary.save()
        
        return Response({'detail': 'Quincena marcada como pagada'})
    
    @action(detail=False, methods=['post'])
    def generate_summaries(self, request):
        """Generar resúmenes de quincena para todos los empleados"""
        from .tasks import generate_fortnight_summaries
        
        year = request.data.get('year', timezone.now().year)
        fortnight = request.data.get('fortnight')
        
        if not fortnight:
            _, fortnight = Earning.calculate_fortnight(timezone.now())
            
        # Ejecutar tarea
        generate_fortnight_summaries.delay(year, fortnight)
        
        return Response({'detail': 'Generando resúmenes de quincena'})