from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from apps.audit_api.mixins import AuditLoggingMixin
from apps.tenants_api.mixins import TenantFilterMixin, TenantPermissionMixin
from apps.tenants_api.models import Tenant
from apps.auth_api.permissions import IsClientAdmin, CanViewFinancialData
from apps.subscriptions_api.utils import get_user_active_subscription
from apps.settings_api.utils import validate_employee_limit
from .models import Employee, EmployeeService, WorkSchedule
from apps.auth_api.models import UserRole
from .serializers import EmployeeSerializer, EmployeeServiceSerializer, WorkScheduleSerializer, EmployeePayrollConfigSerializer
from apps.auth_api.permissions import IsSuperAdmin
from apps.auth_api.permissions import (
    IsClientAdminOrStaff, CanViewFinancialData, IsSuperAdmin
)

class EmployeeViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
  
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsClientAdmin]  # Solo CLIENT_ADMIN puede modificar
        elif self.action in ['stats', 'update_payment_config']:
            permission_classes = [IsAuthenticated, CanViewFinancialData]  # Solo CLIENT_ADMIN ve financiero
        else:
            # Vista básica: CLIENT_ADMIN, STAFF o SUPER_ADMIN (solo lectura)
            permission_classes = [IsAuthenticated]  # Filtrado por tenant en get_queryset
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
        if user.is_superuser or user.roles.filter(name='Super-Admin').exists():
            tenant = user.tenant or Tenant.objects.first()
        else:
            if not user.tenant:
                raise ValidationError("Usuario sin tenant asignado")
            tenant = user.tenant
            
        # Validar límite de empleados según el plan
        plan_type = getattr(tenant, 'plan_type', 'basic')  # Asumir basic si no existe
        if not validate_employee_limit(tenant, plan_type):
            raise ValidationError({
                'error': 'Límite de empleados alcanzado',
                'message': f'Su plan {plan_type} no permite más empleados. Actualice su plan.'
            })
            
        serializer.save(tenant=tenant)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsClientAdmin])
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

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def update_payment_config(self, request, pk=None):
        """Endpoint específico para actualizar configuración de pagos"""
        employee = self.get_object()
        
        # Campos permitidos para configuración de pagos
        allowed_fields = [
            'salary_type', 'commission_percentage', 'contractual_monthly_salary',
            'payment_frequency', 'commission_payment_mode', 'commission_on_demand_since',
            'apply_afp', 'apply_sfs', 'apply_isr'
        ]
        
        # Filtrar solo campos permitidos
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        if not update_data:
            return Response(
                {'error': 'No se proporcionaron campos válidos para actualizar'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Actualizar campos
        for field, value in update_data.items():
            setattr(employee, field, value)
        
        try:
            employee.save()
            return Response({
                'message': 'Configuración de pago actualizada correctamente',
                'updated_fields': list(update_data.keys())
            })
        except Exception as e:
            return Response(
                {'error': f'Error al actualizar: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get', 'post'], permission_classes=[IsAuthenticated, IsClientAdmin])
    def loans(self, request, pk=None):
        """GET/POST /api/employees/{id}/loans/ - Préstamos por empleado"""
        employee = self.get_object()
        
        if request.method == 'GET':
            from .advance_loans import AdvanceLoan
            
            loans = AdvanceLoan.objects.filter(
                employee=employee
            ).order_by('-created_at')
            
            data = []
            for loan in loans:
                data.append({
                    'id': loan.id,
                    'loan_type': loan.get_loan_type_display(),
                    'amount': float(loan.amount),
                    'status': loan.get_status_display(),
                    'installments': loan.installments,
                    'monthly_payment': float(loan.monthly_payment),
                    'remaining_balance': float(loan.remaining_balance),
                    'request_date': loan.request_date,
                    'approval_date': loan.approval_date,
                    'reason': loan.reason
                })
            
            return Response({'loans': data})
        
        elif request.method == 'POST':
            from .advance_loans import AdvanceLoan
            from django.db import transaction
            
            loan_type = request.data.get('loan_type')
            amount = request.data.get('amount')
            reason = request.data.get('reason', '').strip()
            installments = request.data.get('installments', 1)
            
            # Validaciones
            if not amount or amount <= 0:
                return Response({'error': 'Monto debe ser mayor a 0'}, status=400)
            if amount > 100000:
                return Response({'error': 'Monto excede límite máximo (RD$100,000)'}, status=400)
            if installments < 1 or installments > 24:
                return Response({'error': 'Cuotas deben estar entre 1 y 24'}, status=400)
            if not reason or len(reason) > 500:
                return Response({'error': 'Motivo requerido (máx. 500 caracteres)'}, status=400)
            
            try:
                with transaction.atomic():
                    loan = AdvanceLoan.objects.create(
                        employee=employee,
                        loan_type=loan_type,
                        amount=amount,
                        reason=reason,
                        installments=installments
                    )
                    
                    return Response({
                        'message': 'Préstamo creado exitosamente',
                        'loan_id': loan.id,
                        'status': loan.status,
                        'monthly_payment': float(loan.monthly_payment),
                        'total_amount': float(loan.total_amount)
                    }, status=201)
                    
            except Exception as e:
                return Response({'error': f'Error creando préstamo: {str(e)}'}, status=400)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsClientAdmin])
    def loans_summary(self, request, pk=None):
        """GET /api/employees/{id}/loans_summary/ - Resumen de préstamos"""
        employee = self.get_object()
        from .advance_loans import AdvanceLoan
        from django.db.models import Sum, Count
        
        # Estadísticas generales
        loans = AdvanceLoan.objects.filter(employee=employee)
        active_loans = loans.filter(status='active')
        
        total_borrowed = loans.aggregate(total=Sum('amount'))['total'] or 0
        total_remaining = active_loans.aggregate(total=Sum('remaining_balance'))['total'] or 0
        active_count = active_loans.count()
        
        # Próximo pago (si hay préstamos activos)
        next_payment = 0
        if active_loans.exists():
            next_payment = active_loans.aggregate(total=Sum('monthly_payment'))['total'] or 0
        
        return Response({
            'total_borrowed': float(total_borrowed),
            'total_remaining': float(total_remaining),
            'active_loans_count': active_count,
            'next_payment_amount': float(next_payment),
            'can_request_new': True  # Sin límites según reglas de negocio
        })

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsClientAdmin])
    def payment_history(self, request, pk=None):
        """GET /api/employees/{id}/payment_history/ - Historial de pagos (SOLO LECTURA)"""
        employee = self.get_object()
        from apps.employees_api.payroll_models import PayrollPayment
        from apps.payroll_api.models import PayrollSettlement
        
        # Obtener pagos del empleado ordenados por fecha
        payments = PayrollPayment.objects.filter(
            employee=employee
        ).select_related('tenant').order_by('-paid_at')
        
        # Obtener settlements para contexto adicional
        settlements = PayrollSettlement.objects.filter(
            employee=employee,
            status='PAID'
        ).select_related('employee__user')
        
        # Crear diccionario de settlements por período para lookup rápido
        settlements_dict = {}
        for settlement in settlements:
            key = f"{settlement.period_year}-{settlement.period_index}"
            settlements_dict[key] = settlement
        
        data = []
        for payment in payments:
            # Buscar settlement correspondiente
            settlement_key = f"{payment.period_year}-{payment.period_index}"
            settlement = settlements_dict.get(settlement_key)
            
            # Formatear período
            period_display = self._format_payment_period(
                payment.period_year, 
                payment.period_index, 
                payment.period_frequency
            )
            
            data.append({
                'id': str(payment.payment_id),
                'paid_at': payment.paid_at,
                'gross_amount': float(payment.gross_amount),
                'net_amount': float(payment.net_amount),
                'total_deductions': float(payment.total_deductions),
                'payment_method': payment.get_payment_method_display(),
                'payment_reference': payment.payment_reference or '',
                'period_display': period_display,
                'period_start': payment.period_start_date,
                'period_end': payment.period_end_date,
                'payment_type': payment.get_payment_type_display(),
                'status': payment.get_status_display(),
                # Detalles de descuentos
                'afp_deduction': float(payment.afp_deduction),
                'sfs_deduction': float(payment.sfs_deduction),
                'isr_deduction': float(payment.isr_deduction),
                'loan_deductions': float(payment.loan_deductions)
            })
        
        return Response({
            'employee_name': employee.user.full_name or employee.user.email,
            'payments': data,
            'total_payments': len(data)
        })
    
    def _format_payment_period(self, year, period_index, frequency):
        """Formatear período de pago para display"""
        if frequency == 'biweekly':
            month_names = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                          'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
            month = ((period_index - 1) // 2) + 1
            half = "1ra" if (period_index % 2) == 1 else "2da"
            return f"{half} quincena {month_names[month-1]} {year}"
        elif frequency == 'monthly':
            month_names = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                          'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
            return f"{month_names[period_index-1]} {year}"
        elif frequency == 'weekly':
            return f"Semana {period_index} - {year}"
        else:
            return f"Período {period_index} - {year}"

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsClientAdmin])
    def payment_stats(self, request, pk=None):
        """GET /api/employees/{id}/payment_stats/ - Estadísticas de pagos (SOLO LECTURA)"""
        employee = self.get_object()
        from apps.employees_api.payroll_models import PayrollPayment
        from django.db.models import Sum, Count, Avg
        from django.utils import timezone
        from datetime import timedelta
        
        # Todos los pagos del empleado
        all_payments = PayrollPayment.objects.filter(employee=employee, status='COMPLETED')
        
        # Pagos del último año
        last_year = timezone.now() - timedelta(days=365)
        recent_payments = all_payments.filter(paid_at__gte=last_year)
        
        # Estadísticas generales
        total_stats = all_payments.aggregate(
            total_payments=Count('id'),
            total_gross=Sum('gross_amount'),
            total_net=Sum('net_amount'),
            total_deductions=Sum('total_deductions'),
            avg_payment=Avg('net_amount')
        )
        
        # Estadísticas del último año
        recent_stats = recent_payments.aggregate(
            recent_payments=Count('id'),
            recent_gross=Sum('gross_amount'),
            recent_net=Sum('net_amount'),
            recent_deductions=Sum('total_deductions')
        )
        
        # Último pago
        last_payment = all_payments.order_by('-paid_at').first()
        
        return Response({
            'employee_name': employee.user.full_name or employee.user.email,
            'all_time': {
                'total_payments': total_stats['total_payments'] or 0,
                'total_gross': float(total_stats['total_gross'] or 0),
                'total_net': float(total_stats['total_net'] or 0),
                'total_deductions': float(total_stats['total_deductions'] or 0),
                'average_payment': float(total_stats['avg_payment'] or 0)
            },
            'last_year': {
                'payments_count': recent_stats['recent_payments'] or 0,
                'total_gross': float(recent_stats['recent_gross'] or 0),
                'total_net': float(recent_stats['recent_net'] or 0),
                'total_deductions': float(recent_stats['recent_deductions'] or 0)
            },
            'last_payment': {
                'date': last_payment.paid_at if last_payment else None,
                'amount': float(last_payment.net_amount) if last_payment else 0,
                'method': last_payment.get_payment_method_display() if last_payment else None
            } if last_payment else None
        })

    @action(detail=True, methods=['get', 'put'], permission_classes=[IsAuthenticated, IsClientAdmin])
    def payroll_config(self, request, pk=None):
        """GET/PUT /api/employees/{id}/payroll-config/ - Configuración de nómina"""
        employee = self.get_object()
        
        if request.method == 'GET':
            serializer = EmployeePayrollConfigSerializer(employee)
            return Response(serializer.data)
        
        elif request.method == 'PUT':
            serializer = EmployeePayrollConfigSerializer(employee, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'message': 'Configuración de nómina actualizada correctamente',
                    'data': serializer.data
                })
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class WorkScheduleViewSet(viewsets.ModelViewSet):
    queryset = WorkSchedule.objects.all()
    serializer_class = WorkScheduleSerializer
    permission_classes = [IsAuthenticated, IsClientAdmin]

    def get_queryset(self):
        if UserRole.objects.filter(user=self.request.user, role__name='Client-Admin').exists():
            return WorkSchedule.objects.all()
        return WorkSchedule.objects.filter(employee__user=self.request.user)

    def perform_create(self, serializer):
        employee = Employee.objects.get(user=self.request.user)
        serializer.save(employee=employee)