from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
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
    filterset_fields = ['price', 'is_active', 'category']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price']
    ordering = ['name']

    def get_queryset(self):
        return Service.objects.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Obtener todas las categorías de servicios del tenant"""
        categories = Service.objects.filter(
            tenant=request.user.tenant,
            category__isnull=False
        ).values_list('category', flat=True).distinct().order_by('category')
        
        return Response(list(categories))
    
    @action(detail=True, methods=['get'])
    def employees(self, request, pk=None):
        """Obtener empleados asignados a un servicio"""
        service = self.get_object()
        from .models import ServiceEmployee
        service_employees = ServiceEmployee.objects.filter(service=service).select_related('employee__user')
        
        data = []
        for se in service_employees:
            data.append({
                'id': se.id,
                'service': se.service.id,
                'employee': se.employee.id,
                'employee_name': se.employee.user.email,
                'custom_price': se.custom_price,
                'commission_percentage': se.commission_percentage
            })
        
        return Response(data)
    
    @action(detail=True, methods=['post'])
    def assign_employees(self, request, pk=None):
        """Asignar empleados a un servicio"""
        service = self.get_object()
        employee_ids = request.data.get('employee_ids', [])
        
        from .models import ServiceEmployee
        from apps.employees_api.models import Employee
        
        # Limpiar asignaciones existentes
        ServiceEmployee.objects.filter(service=service).delete()
        
        # Crear nuevas asignaciones
        for employee_id in employee_ids:
            try:
                employee = Employee.objects.get(id=employee_id, tenant=request.user.tenant)
                ServiceEmployee.objects.create(service=service, employee=employee)
            except Employee.DoesNotExist:
                continue
                
        return Response({'message': 'Empleados asignados correctamente'})
    
    @action(detail=True, methods=['post'])
    def set_employee_price(self, request, pk=None):
        """Establecer precio personalizado para un empleado en un servicio"""
        service = self.get_object()
        employee_id = request.data.get('employee_id')
        price = request.data.get('price')
        
        from .models import ServiceEmployee
        from apps.employees_api.models import Employee
        
        try:
            employee = Employee.objects.get(id=employee_id, tenant=request.user.tenant)
            service_employee, created = ServiceEmployee.objects.get_or_create(
                service=service, 
                employee=employee,
                defaults={'custom_price': price}
            )
            if not created:
                service_employee.custom_price = price
                service_employee.save()
                
            return Response({'message': 'Precio actualizado correctamente'})
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=400)
