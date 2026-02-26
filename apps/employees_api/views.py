from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from apps.audit_api.mixins import AuditLoggingMixin
from apps.tenants_api.mixins import TenantFilterMixin, TenantPermissionMixin
from apps.tenants_api.models import Tenant
from apps.roles_api.permissions import IsActiveAndRolePermission, role_permission_for
from apps.subscriptions_api.utils import get_user_active_subscription
from apps.settings_api.utils import validate_employee_limit
from .models import Employee, EmployeeService, WorkSchedule
from apps.roles_api.models import UserRole
from .serializers import EmployeeSerializer, EmployeeServiceSerializer, WorkScheduleSerializer
from .permissions import IsAdminOrOwnStylist, role_permission_for

class EmployeeViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    queryset = Employee.objects.none()  # Seguro por defecto
    serializer_class = EmployeeSerializer
  
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

   
   
    def get_queryset(self):
        user = self.request.user
        
        # DEBUG
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f'DEBUG get_queryset: user={user.email}, is_superuser={user.is_superuser}')
        logger.info(f'DEBUG get_queryset: hasattr tenant={hasattr(self.request, "tenant")}')
        if hasattr(self.request, 'tenant'):
            logger.info(f'DEBUG get_queryset: request.tenant={self.request.tenant}')
        
        # SuperAdmin: acceso total
        if user.is_superuser:
            return Employee.objects.select_related('user', 'tenant').all()
            
        # Usuario sin tenant: sin acceso
        if not hasattr(self.request, 'tenant') or not self.request.tenant:
            logger.error(f'DEBUG: Usuario sin tenant - retornando none()')
            return Employee.objects.none()
            
        # Filtrar por tenant del request
        logger.info(f'DEBUG: Filtrando por tenant={self.request.tenant.id}')
        return Employee.objects.select_related('user', 'tenant').filter(tenant=self.request.tenant)
    

    def perform_create(self, serializer):
        user = self.request.user
        
        # SuperAdmin: puede crear sin tenant
        if user.is_superuser:
            serializer.save()
            return
        
        # Usuario normal: forzar tenant del request
        if not hasattr(self.request, 'tenant') or not self.request.tenant:
            raise ValidationError("Usuario sin tenant asignado")
        
        tenant = self.request.tenant
            
        # Validar límite de empleados según el plan
        plan_type = getattr(tenant, 'plan_type', 'basic')
        if not validate_employee_limit(tenant, plan_type):
            raise ValidationError({
                'error': 'Límite de empleados alcanzado',
                'message': f'Su plan {plan_type} no permite más empleados. Actualice su plan.'
            })
            
        serializer.save(tenant=tenant)

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
    
    @action(detail=True, methods=['get', 'put'], url_path='payroll_config')
    def payroll_config(self, request, pk=None):
        employee = self.get_object()
        
        if request.method == 'GET':
            return Response({
                'payment_type': employee.payment_type or 'commission',
                'fixed_salary': float(employee.fixed_salary or 0),
                'commission_rate': float(employee.commission_rate or 40)
            })
        
        elif request.method == 'PUT':
            payment_type = request.data.get('payment_type')
            if payment_type and payment_type not in ['fixed', 'commission', 'mixed']:
                return Response({'error': 'payment_type inválido'}, status=400)
            
            # Capturar valores anteriores
            old_payment_type = employee.payment_type
            old_fixed_salary = employee.fixed_salary
            old_commission_rate = employee.commission_rate
            
            # Aplicar cambios
            if payment_type:
                employee.payment_type = payment_type
            if 'fixed_salary' in request.data:
                employee.fixed_salary = request.data['fixed_salary']
            if 'commission_rate' in request.data:
                employee.commission_rate = request.data['commission_rate']
            
            employee.save()
            
            # Crear registro en CompensationHistory si hubo cambios
            if (old_payment_type != employee.payment_type or 
                old_fixed_salary != employee.fixed_salary or 
                old_commission_rate != employee.commission_rate):
                
                from apps.employees_api.compensation_models import EmployeeCompensationHistory
                from django.utils import timezone
                
                EmployeeCompensationHistory.objects.create(
                    employee=employee,
                    payment_type=employee.payment_type,
                    fixed_salary=employee.fixed_salary,
                    commission_rate=employee.commission_rate,
                    effective_date=timezone.now().date(),
                    created_by=request.user,
                    change_reason='Actualización manual de configuración de nómina'
                )
            
            return Response({
                'message': 'Configuración actualizada',
                'payment_type': employee.payment_type,
                'fixed_salary': float(employee.fixed_salary or 0),
                'commission_rate': float(employee.commission_rate or 40)
            })
    
    @action(detail=True, methods=['get'], url_path='payment_history')
    def payment_history(self, request, pk=None):
        """Historial de pagos del empleado"""
        employee = self.get_object()
        from apps.employees_api.earnings_models import PayrollPeriod
        
        periods = PayrollPeriod.objects.filter(
            employee=employee,
            status='paid'
        ).order_by('-period_start')
        
        history = [{
            'id': p.id,
            'period_display': p.period_display,
            'period_start': p.period_start.isoformat(),
            'period_end': p.period_end.isoformat(),
            'gross_amount': float(p.gross_amount),
            'deductions_total': float(p.deductions_total),
            'net_amount': float(p.net_amount),
            'paid_at': p.paid_at.isoformat() if p.paid_at else None,
            'payment_method': p.payment_method,
            'payment_reference': p.payment_reference
        } for p in periods]
        
        return Response({'payments': history, 'count': len(history)})
    
    @action(detail=True, methods=['get'], url_path='payment_stats')
    def payment_stats(self, request, pk=None):
        """Estadísticas de pagos del empleado"""
        employee = self.get_object()
        from apps.employees_api.earnings_models import PayrollPeriod
        from django.db.models import Sum, Avg, Count
        from django.utils import timezone
        from datetime import timedelta
        
        # Todos los pagos
        all_payments = PayrollPeriod.objects.filter(employee=employee, status='paid')
        
        # Últimos 6 meses
        six_months_ago = timezone.now().date() - timedelta(days=180)
        recent_payments = all_payments.filter(period_start__gte=six_months_ago)
        
        stats = {
            'total_payments': all_payments.count(),
            'total_earned': float(all_payments.aggregate(total=Sum('net_amount'))['total'] or 0),
            'average_payment': float(all_payments.aggregate(avg=Avg('net_amount'))['avg'] or 0),
            'last_6_months': {
                'count': recent_payments.count(),
                'total': float(recent_payments.aggregate(total=Sum('net_amount'))['total'] or 0),
                'average': float(recent_payments.aggregate(avg=Avg('net_amount'))['avg'] or 0)
            },
            'last_payment': None
        }
        
        last_payment = all_payments.order_by('-paid_at').first()
        if last_payment:
            stats['last_payment'] = {
                'date': last_payment.paid_at.isoformat() if last_payment.paid_at else None,
                'amount': float(last_payment.net_amount),
                'period': last_payment.period_display
            }
        
        return Response(stats)
    
    @action(detail=True, methods=['get', 'post'], url_path='loans')
    def loans(self, request, pk=None):
        """Gestionar préstamos del empleado"""
        employee = self.get_object()
        from apps.employees_api.earnings_models import PayrollDeduction, PayrollPeriod
        
        if request.method == 'GET':
            # Listar todos los préstamos
            loan_deductions = PayrollDeduction.objects.filter(
                period__employee=employee,
                deduction_type__in=['loan', 'advance', 'emergency_loan']
            ).select_related('period').order_by('-created_at')
            
            type_labels = {
                'advance': 'Anticipo de Sueldo',
                'loan': 'Préstamo Personal',
                'emergency_loan': 'Préstamo de Emergencia'
            }
            
            # Mapeo inverso para el frontend
            type_values = {
                'advance': 'advance',
                'loan': 'personal_loan',
                'emergency_loan': 'emergency'
            }
            
            loans_data = [{
                'id': d.id,
                'request_date': d.created_at.isoformat(),
                'loan_type': type_values.get(d.deduction_type, d.deduction_type),
                'type_display': type_labels.get(d.deduction_type, d.deduction_type),
                'installments': d.installments,
                'monthly_payment': float(d.amount),
                'remaining_balance': float(d.amount) if d.period.status != 'paid' else 0,
                'status': 'Pagado' if d.period.status == 'paid' else 'Pendiente',
                'reason': d.description or 'Sin motivo',
                'amount': float(d.amount),
                'period': d.period.period_display,
                'period_status': d.period.status
            } for d in loan_deductions]
            
            return Response({'loans': loans_data, 'count': len(loans_data)})
        
        elif request.method == 'POST':
            # Crear nuevo préstamo
            amount = request.data.get('amount')
            description = request.data.get('description') or request.data.get('reason', '')
            loan_type = request.data.get('type') or request.data.get('loan_type', 'loan')
            installments = request.data.get('installments', 1)
            
            # Mapear valores del frontend a valores del backend
            type_mapping = {
                'personal_loan': 'loan',
                'emergency': 'emergency_loan',
                'advance': 'advance'
            }
            loan_type = type_mapping.get(loan_type, loan_type)
            
            if not amount:
                return Response({'error': 'amount es requerido'}, status=400)
            
            if loan_type not in ['loan', 'advance', 'emergency_loan']:
                return Response({'error': 'type debe ser loan, advance o emergency_loan'}, status=400)
            
            # Buscar período abierto o pendiente, o crear uno nuevo
            period = PayrollPeriod.objects.filter(
                employee=employee,
                status__in=['open', 'pending_approval']
            ).first()
            
            if not period:
                # Crear período para quincena actual
                from django.utils import timezone
                today = timezone.now().date()
                
                if today.day <= 15:
                    start_date = today.replace(day=1)
                    end_date = today.replace(day=15)
                else:
                    start_date = today.replace(day=16)
                    last_day = (today.replace(month=today.month+1 if today.month < 12 else 1, 
                                             year=today.year if today.month < 12 else today.year+1, day=1) 
                               - timezone.timedelta(days=1)).day
                    end_date = today.replace(day=last_day)
                
                period = PayrollPeriod.objects.create(
                    employee=employee,
                    period_type='biweekly',
                    period_start=start_date,
                    period_end=end_date,
                    status='open'
                )
            
            # Verificar si ya existe un préstamo idéntico reciente (últimos 5 segundos)
            from django.utils import timezone
            from datetime import timedelta
            recent_threshold = timezone.now() - timedelta(seconds=5)
            
            existing = PayrollDeduction.objects.filter(
                period=period,
                deduction_type=loan_type,
                amount=amount,
                description=description,
                created_at__gte=recent_threshold
            ).exists()
            
            if existing:
                return Response({'error': 'Préstamo duplicado detectado'}, status=400)
            
            deduction = PayrollDeduction.objects.create(
                period=period,
                deduction_type=loan_type,
                amount=amount,
                description=description,
                installments=installments,
                created_by=request.user
            )
            
            # Recalcular período
            period.calculate_amounts()
            period.save()
            
            return Response({
                'message': 'Préstamo creado exitosamente',
                'loan': {
                    'id': deduction.id,
                    'type': deduction.deduction_type,
                    'amount': float(deduction.amount),
                    'description': deduction.description,
                    'period': period.period_display
                }
            }, status=201)
    
    @action(detail=True, methods=['get'], url_path='loans_summary')
    def loans_summary(self, request, pk=None):
        """Resumen de préstamos del empleado"""
        employee = self.get_object()
        from apps.employees_api.earnings_models import PayrollDeduction
        from django.db.models import Sum, Count
        
        # Préstamos en períodos no pagados (pendientes)
        pending_loans = PayrollDeduction.objects.filter(
            period__employee=employee,
            period__status__in=['open', 'pending_approval', 'approved'],
            deduction_type__in=['loan', 'advance', 'emergency_loan']
        )
        
        # Préstamos ya pagados
        paid_loans = PayrollDeduction.objects.filter(
            period__employee=employee,
            period__status='paid',
            deduction_type__in=['loan', 'advance', 'emergency_loan']
        )
        
        summary = {
            'pending': {
                'count': pending_loans.count(),
                'total': float(pending_loans.aggregate(total=Sum('amount'))['total'] or 0)
            },
            'paid': {
                'count': paid_loans.count(),
                'total': float(paid_loans.aggregate(total=Sum('amount'))['total'] or 0)
            },
            'total_loans': pending_loans.count() + paid_loans.count(),
            'total_amount': float(
                (pending_loans.aggregate(total=Sum('amount'))['total'] or 0) +
                (paid_loans.aggregate(total=Sum('amount'))['total'] or 0)
            )
        }
        
        return Response(summary)

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