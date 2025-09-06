from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from apps.audit_api.mixins import AuditLoggingMixin
from apps.tenants_api.mixins import TenantFilterMixin, TenantPermissionMixin
from apps.roles_api.permissions import IsActiveAndRolePermission, role_permission_for
from apps.subscriptions_api.utils import get_user_active_subscription
from .models import Employee, EmployeeService, WorkSchedule
from apps.auth_api.models import UserRole
from .serializers import EmployeeSerializer, EmployeeServiceSerializer, WorkScheduleSerializer
from .permissions import IsAdminOrOwnStylist, role_permission_for

class EmployeeViewSet(TenantFilterMixin, TenantPermissionMixin, viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
  
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

   
   
    def get_queryset(self):
        user = self.request.user
        
        # SuperAdmin puede ver todo
        if user.is_superuser:
            return Employee.objects.all()
            
        # Usuario debe tener tenant
        if not user.tenant:
            return Employee.objects.none()
            
        # Filtrar por tenant del usuario
        return Employee.objects.filter(tenant=user.tenant)
    

    def perform_create(self, serializer):
        user = self.request.user
        
        # SuperAdmin puede crear para cualquier tenant
        if user.is_superuser:
            return super().perform_create(serializer)
            
        # Usuario normal solo puede crear para su tenant
        if not user.tenant:
            raise ValidationError("Usuario sin tenant asignado")
            
        # Obtener suscripción activa del tenant
        sub = get_user_active_subscription(user)
        max_employees = sub.plan.max_employees if sub and sub.plan else 0

        # Contar empleados del tenant
        current_employees = Employee.objects.filter(tenant=user.tenant).count()

        # Validar límite
        if current_employees >= max_employees:
            raise ValidationError(
                f"Has alcanzado el límite de empleados permitidos en tu plan actual ({max_employees}).")

        serializer.save(tenant=user.tenant)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, role_permission_for(['Admin'])])
    def assign_service(self, request, pk=None):
        employee = self.get_object()
        serializer = EmployeeServiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(employee=employee)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def assign_services(self, request, pk=None):
        employee = self.get_object()
        service_ids = request.data.get('service_ids', [])
        
        # Limpiar servicios existentes
        EmployeeService.objects.filter(employee=employee).delete()
        
        # Asignar nuevos servicios
        for service_id in service_ids:
            try:
                from apps.services_api.models import Service
                service = Service.objects.get(id=service_id, is_active=True)
                EmployeeService.objects.create(employee=employee, service=service)
            except Service.DoesNotExist:
                continue
                
        return Response({'detail': 'Servicios asignados correctamente'})

    @action(detail=True, methods=['get'])
    def services(self, request, pk=None):
        employee = self.get_object()
        employee_services = EmployeeService.objects.filter(employee=employee).select_related('service')
        serializer = EmployeeServiceSerializer(employee_services, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def schedule(self, request, pk=None):
        employee = self.get_object()
        schedules = WorkSchedule.objects.filter(employee=employee)
        serializer = WorkScheduleSerializer(schedules, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def set_schedule(self, request, pk=None):
        employee = self.get_object()
        schedules_data = request.data.get('schedules', [])
        
        # Limpiar horarios existentes
        WorkSchedule.objects.filter(employee=employee).delete()
        
        # Crear nuevos horarios
        for schedule_data in schedules_data:
            schedule_data['employee'] = employee.id
            serializer = WorkScheduleSerializer(data=schedule_data)
            if serializer.is_valid():
                serializer.save()
                
        return Response({'detail': 'Horarios actualizados correctamente'})

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        employee = self.get_object()
        from apps.appointments_api.models import Appointment
        from apps.pos_api.models import Sale
        from django.utils import timezone
        from datetime import timedelta
        
        # Estadísticas del último mes
        last_month = timezone.now() - timedelta(days=30)
        
        appointments_count = Appointment.objects.filter(
            stylist=employee.user,
            date_time__gte=last_month
        ).count()
        
        sales_count = Sale.objects.filter(
            user=employee.user,
            date_time__gte=last_month
        ).count()
        
        return Response({
            'appointments_last_month': appointments_count,
            'sales_last_month': sales_count,
            'services_count': EmployeeService.objects.filter(employee=employee).count()
        })

class WorkScheduleViewSet(viewsets.ModelViewSet):
    queryset = WorkSchedule.objects.all()
    serializer_class = WorkScheduleSerializer
    permission_classes = [IsAdminOrOwnStylist]

    def get_queryset(self):
        if UserRole.objects.filter(user=self.request.user, role__name='Admin').exists():
            return WorkSchedule.objects.all()
        return WorkSchedule.objects.filter(employee__user=self.request.user)

    def perform_create(self, serializer):
        employee = Employee.objects.get(user=self.request.user)
        serializer.save(employee=employee)