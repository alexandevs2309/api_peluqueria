from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.audit_api.mixins import AuditLoggingMixin
from apps.tenants_api.base_viewsets import TenantScopedViewSet
from apps.core.tenant_permissions import TenantPermissionByAction
from .models import Service, ServiceCategory
from .serializers import ServiceSerializer, ServiceCategorySerializer

class ServiceCategoryViewSet(TenantScopedViewSet):
    queryset = ServiceCategory.objects.filter(is_active=True)
    serializer_class = ServiceCategorySerializer
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        # Reusar permisos base de servicios para mantener compatibilidad
        # con roles existentes (Client-Admin) que no incluyen codenames
        # default de ServiceCategory.
        'list': 'services_api.view_service',
        'retrieve': 'services_api.view_service',
        'create': 'services_api.add_service',
        'update': 'services_api.change_service',
        'partial_update': 'services_api.change_service',
        'destroy': 'services_api.delete_service',
    }

class ServiceViewSet(AuditLoggingMixin, TenantScopedViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'services_api.view_service',
        'retrieve': 'services_api.view_service',
        'create': 'services_api.add_service',
        'update': 'services_api.change_service',
        'partial_update': 'services_api.change_service',
        'destroy': 'services_api.delete_service',
        'categories': 'services_api.view_service',
        'employees': 'services_api.view_service',
        'assign_employees': 'services_api.assign_employees',
        'set_employee_price': 'services_api.set_employee_price',
    }

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = ['price', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price']
    ordering = ['name']
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Obtener todas las categorías de servicios del tenant"""
        categories = Service.objects.filter(
            tenant=self.request.tenant if hasattr(self.request, 'tenant') else None,
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
                employee = Employee.objects.get(id=employee_id, tenant=self.request.tenant if hasattr(self.request, 'tenant') else None)
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
            employee = Employee.objects.get(id=employee_id, tenant=self.request.tenant if hasattr(self.request, 'tenant') else None)
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
