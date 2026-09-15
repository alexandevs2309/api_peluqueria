import logging
from decimal import Decimal, DecimalException
from django.db import transaction
from django.core.exceptions import ValidationError
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.audit_api.mixins import AuditLoggingMixin
from apps.tenants_api.base_viewsets import TenantScopedViewSet
from apps.core.tenant_permissions import TenantPermissionByAction
from .models import Service, ServiceCategory
from .serializers import ServiceSerializer, ServiceCategorySerializer

logger = logging.getLogger(__name__)

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

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except Exception as e:
            logger.error("ServiceViewSet.update — error: %s | data keys: %s | FILES: %s | method: %s",
                          e, list(request.data.keys()), bool(request.FILES), request.method)
            raise

    def perform_create(self, serializer):
        service = serializer.save()
        # Auto-asignar el nuevo servicio a los empleados activos del tenant
        try:
            from apps.employees_api.models import Employee
            from .models import ServiceEmployee
            tenant = getattr(self.request, 'tenant', None) or getattr(getattr(self.request, 'user', None), 'tenant', None)
            if tenant:
                employee_ids = Employee.objects.filter(tenant=tenant, is_active=True).values_list('id', flat=True)
                ServiceEmployee.objects.bulk_create(
                    [ServiceEmployee(service=service, employee_id=emp_id) for emp_id in employee_ids],
                    ignore_conflicts=True,
                    batch_size=500
                )
        except Exception as e:
            logger.warning("Error auto-assigning service to employees: %s", e)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            logger.error("ServiceViewSet.create — error: %s | data keys: %s | FILES: %s",
                          e, list(request.data.keys()), bool(request.FILES))
            raise

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
        tenant = getattr(request, 'tenant', None) or getattr(request.user, 'tenant', None)
        qs = ServiceCategory.objects.filter(is_active=True)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return Response(list(qs.values('id', 'name')))

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
        if not isinstance(employee_ids, list):
            return Response({'employee_ids': ['Debe proporcionar una lista de ids de empleados.']}, status=status.HTTP_400_BAD_REQUEST)

        tenant = getattr(request, 'tenant', None) or getattr(request.user, 'tenant', None)
        valid_ids = set()
        for emp_id in employee_ids:
            if isinstance(emp_id, str) and not str(emp_id).isdigit():
                return Response({'employee_ids': [f'El id "{emp_id}" no es válido.']}, status=status.HTTP_400_BAD_REQUEST)
            valid_ids.add(int(emp_id))

        from .models import ServiceEmployee
        from apps.employees_api.models import Employee

        with transaction.atomic():
            ServiceEmployee.objects.filter(service=service).delete()
            empleados = Employee.objects.filter(id__in=valid_ids, tenant=tenant)
            encontrados = set(empleados.values_list('id', flat=True))
            faltantes = valid_ids - encontrados
            if faltantes:
                raise ValidationError({'employee_ids': [f'Los empleados {sorted(faltantes)} no existen o no pertenecen a este negocio.']})
            ServiceEmployee.objects.bulk_create(
                [ServiceEmployee(service=service, employee_id=emp_id) for emp_id in encontrados]
            )

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
            price_value = Decimal(str(price))
        except (TypeError, ValueError, DecimalException):
            return Response({'price': ['El precio debe ser un número válido.']}, status=status.HTTP_400_BAD_REQUEST)
        if price_value < 0:
            return Response({'price': ['El precio no puede ser negativo.']}, status=status.HTTP_400_BAD_REQUEST)

        tenant = getattr(request, 'tenant', None) or getattr(request.user, 'tenant', None)
        try:
            employee = Employee.objects.get(id=employee_id, tenant=tenant)
            service_employee, created = ServiceEmployee.objects.get_or_create(
                service=service,
                employee=employee,
                defaults={'custom_price': price_value}
            )
            if not created:
                service_employee.custom_price = price_value
                service_employee.save(update_fields=['custom_price'])

            return Response({'message': 'Precio actualizado correctamente'})
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=400)
