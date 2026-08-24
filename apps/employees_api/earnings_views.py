import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from django.core.exceptions import ValidationError
from .earnings_models import PayrollPeriod, PayrollDeduction, PayrollConfiguration
from .earnings_serializers import PayrollPeriodSerializer, PayrollDeductionSerializer, PayrollConfigurationSerializer
from django.db import transaction
from django.db.models import Q
from apps.core.tenant_permissions import TenantPermissionByAction
from apps.auth_api.role_utils import get_effective_role_name
from datetime import date, timedelta
from calendar import monthrange

logger = logging.getLogger(__name__)

class PayrollViewSet(viewsets.ViewSet):
    """ViewSet para gestión de nómina"""
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list_periods': 'employees_api.view_employee_payroll',
        'my_earnings': 'employees_api.view_employee_payroll',
        'my_summary': 'employees_api.view_employee_payroll',
        'get_receipt': 'employees_api.view_employee_payroll',
        'register_payment': 'employees_api.approve_payroll',
        'recalculate_period': 'employees_api.change_employee_payroll',
        'submit_for_approval': 'employees_api.change_employee_payroll',
        'approve_period': 'employees_api.approve_payroll',
        'reject_period': 'employees_api.approve_payroll',
        'history': 'employees_api.view_employee_payroll',
        'config': 'employees_api.view_employee_payroll',
        'ensure_period': 'employees_api.change_employee_payroll',
    }
    
    def _require_admin_role(self, request):
        """Validar que el usuario tenga rol de administrador"""
        tenant = getattr(request, 'tenant', getattr(request.user, 'tenant', None))
        if get_effective_role_name(request.user, tenant=tenant) not in {'SuperAdmin', 'Client-Admin'}:
            raise PermissionDenied("No autorizado para operaciones de nómina.")

    @action(detail=False, methods=['get', 'put'], url_path='config')
    def config(self, request):
        """Obtener o actualizar la configuración de nómina del tenant (ISR/SFS/AFP)"""
        user = request.user
        tenant = getattr(request, 'tenant', getattr(user, 'tenant', None))
        if not tenant:
            return Response({'error': 'No se pudo determinar el tenant'}, status=400)

        config, _ = PayrollConfiguration.objects.get_or_create(tenant=tenant)

        if request.method == 'PUT':
            self._require_admin_role(request)
            serializer = PayrollConfigurationSerializer(config, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        return Response(PayrollConfigurationSerializer(config).data)
    
    def get_queryset(self):
        user = self.request.user
        tenant = getattr(self.request, 'tenant', getattr(user, 'tenant', None))
        if tenant:
            return PayrollPeriod.objects.select_related(
                'employee__user',
                'employee__tenant'
            ).prefetch_related('deductions').filter(employee__tenant=tenant)
        return PayrollPeriod.objects.none()
    
    def _ensure_open_periods(self, tenant):
        """Auto-generar períodos abiertos para empleados activos sin período vigente"""
        from .models import Employee
        today = date.today()
        
        # Determinar período actual
        if today.day <= 15:
            start_date = today.replace(day=1)
            end_date = today.replace(day=15)
        else:
            start_date = today.replace(day=16)
            end_date = today.replace(day=monthrange(today.year, today.month)[1])
        
        active_employees = Employee.objects.filter(
            tenant=tenant,
            is_active=True
        )
        
        created = 0
        for employee in active_employees:
            _, was_created = PayrollPeriod.objects.get_or_create(
                employee=employee,
                period_start=start_date,
                period_end=end_date,
                defaults={
                    'period_type': 'biweekly',
                    'status': 'open',
                }
            )
            if was_created:
                created += 1
                # Calcular montos iniciales
                period = PayrollPeriod.objects.get(
                    employee=employee,
                    period_start=start_date,
                    period_end=end_date
                )
                period.calculate_amounts()
                period.save()
        
        return created

    @action(detail=False, methods=['get'], url_path='client/payroll')
    def list_periods(self, request):
        """Endpoint compatible con frontend: GET /payroll/client/payroll/"""
        from apps.employees_api.models import Employee
        from apps.pos_api.models import Sale
        from calendar import monthrange
        from django.db.models import Count, Sum

        tenant = getattr(request, 'tenant', getattr(request.user, 'tenant', None))
        if not tenant:
            return Response({'periods': []})

        today = timezone.localdate()

        # 1. Garantizar un período abierto para cada empleado activo del tenant
        if today.day <= 15:
            start_date = today.replace(day=1)
            end_date = today.replace(day=15)
        else:
            start_date = today.replace(day=16)
            end_date = today.replace(day=monthrange(today.year, today.month)[1])

        for employee in Employee.objects.filter(tenant=tenant, is_active=True):
            period, created = PayrollPeriod.objects.get_or_create(
                employee=employee,
                period_start=start_date,
                period_end=end_date,
                defaults={'period_type': 'biweekly', 'status': 'open'},
            )
            # Sincronizar snapshots de períodos abiertos con valores
            # actuales del empleado. Esto corrige snapshots corruptos del
            # bug anterior (quincenal guardado como mensual, payment_type
            # incorrecto, etc). Usamos .update() para saltar la validación
            # de inmutabilidad de PayrollPeriod.save().
            if period.status == 'open':
                PayrollPeriod.objects.filter(pk=period.pk).update(
                    fixed_salary_snapshot=employee.fixed_salary,
                    commission_rate_snapshot=employee.commission_rate,
                    payment_type_snapshot=employee.payment_type,
                )
                period.refresh_from_db()
                period.calculate_amounts()
                period.save(update_fields=[
                    'base_salary', 'commission_earnings', 'gross_amount',
                    'deductions_total', 'net_amount', 'can_pay', 'pay_block_reason',
                ])

        # 2. Query de períodos
        periods = self.get_queryset().select_related('employee__user')

        status_filter = request.query_params.get('status')
        if status_filter:
            periods = periods.filter(status=status_filter)

        # Ocultar períodos futuros abiertos
        periods = periods.exclude(status='open', period_start__gt=today)

        # 3. Ventas por empleado por período (una query por período con índices)
        sales_by_period = {}
        for period in periods:
            emp_id = period.employee_id
            agg = Sale.objects.filter(
                tenant=tenant,
                employee_id=emp_id,
                date_time__date__gte=period.period_start,
                date_time__date__lte=period.period_end,
            ).aggregate(services_count=Count('id'), gross_sales=Sum('total'))
            sales_by_period[(emp_id, period.period_start, period.period_end)] = {
                'services_count': agg['services_count'] or 0,
                'gross_sales': float(agg['gross_sales'] or 0),
            }

        # 4. Construir respuesta
        periods_data = []
        for period in periods:
            status = period.status
            if status == 'ready':
                status = 'approved'

            sales_data = sales_by_period.get(
                (period.employee_id, period.period_start, period.period_end),
                {'services_count': 0, 'gross_sales': 0.0}
            )

            emp = period.employee
            user = emp.user
            periods_data.append({
                'id': period.id,
                'employee_id': period.employee_id,
                'employee_name': user.full_name or user.email,
                'period_display': period.period_display,
                'status': status,
                'base_salary': float(period.base_salary),
                'commission_earnings': float(period.commission_earnings),
                'gross_amount': float(period.gross_amount),
                'net_amount': float(period.net_amount),
                'deductions_total': float(period.deductions_total),
                'period_start': period.period_start.isoformat(),
                'period_end': period.period_end.isoformat(),
                'can_pay': period.can_pay,
                'pay_block_reason': period.pay_block_reason,
                'employee_payment_type': emp.payment_type,
                'employee_commission_rate': float(emp.commission_rate or 0),
                'employee_profession': emp.get_profession_display() or emp.profession or '',
                'services_count': sales_data['services_count'],
                'gross_sales': round(sales_data['gross_sales'], 2),
            })

        return Response({'periods': periods_data})

    @action(detail=False, methods=['post'], url_path='client/payroll/ensure-period')
    def ensure_period(self, request):
        """Crea el período de nómina abierto actual para un empleado si no existe.

        Necesario para que "Liquidar" funcione con empleados que aún no tienen período
        (los períodos solo se generaban al emitir un préstamo). Idempotente: si el
        empleado ya tiene un período abierto en el ciclo actual, lo devuelve tal cual.
        """
        from apps.employees_api.models import Employee
        from calendar import monthrange

        self._require_admin_role(request)

        tenant = getattr(request, 'tenant', getattr(request.user, 'tenant', None))
        if not tenant:
            return Response({'error': 'No se pudo determinar el tenant'}, status=400)

        employee_id = request.data.get('employee_id')
        if not employee_id:
            return Response({'error': 'employee_id es requerido'}, status=400)

        try:
            employee = Employee.objects.get(id=employee_id, tenant=tenant, is_active=True)
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=404)

        today = timezone.localdate()
        if today.day <= 15:
            start_date = today.replace(day=1)
            end_date = today.replace(day=15)
        else:
            start_date = today.replace(day=16)
            end_date = today.replace(day=monthrange(today.year, today.month)[1])

        period, created = PayrollPeriod.objects.get_or_create(
            employee=employee,
            period_start=start_date,
            period_end=end_date,
            defaults={'period_type': 'biweekly', 'status': 'open'},
        )

        if created or period.status == 'open':
            period.calculate_amounts()
            period.save(update_fields=[
                'base_salary', 'commission_earnings', 'gross_amount',
                'deductions_total', 'net_amount', 'can_pay', 'pay_block_reason',
            ])

        return Response({
            'id': period.id,
            'employee_id': employee.id,
            'status': period.status,
            'net_amount': float(period.net_amount),
            'gross_amount': float(period.gross_amount),
            'created': created,
        })

    @action(detail=False, methods=['get'], url_path='client/payroll/history')
    def history(self, request):
        """Listar períodos pagados o cerrados (historial) con datos completos"""
        # Filtrar períodos que ya fueron pagados o aprobados (incluye los que fueron cerrados)
        periods = self.get_queryset().filter(status__in=['paid', 'approved', 'closed', 'rejected'])
        periods_data = []
        for p in periods:
            # Mapear estados legacy
            status = p.status
            if status == 'ready':
                status = 'approved'
            periods_data.append({
                'id': p.id,
                'employee_name': p.employee.user.full_name or p.employee.user.email,
                'period_display': p.period_display,
                'status': status,
                'base_salary': float(p.base_salary),
                'commission_earnings': float(p.commission_earnings),
                'gross_amount': float(p.gross_amount),
                'net_amount': float(p.net_amount),
                'deductions_total': float(p.deductions_total),
                'period_start': p.period_start.isoformat(),
                'period_end': p.period_end.isoformat(),
                'can_pay': p.can_pay,
                'pay_block_reason': p.pay_block_reason,
                'paid_at': p.paid_at.isoformat() if p.paid_at else None,
            })
        return Response({'periods': periods_data})

    @action(detail=False, methods=['get'], url_path='client/payroll/my-earnings')
    def my_earnings(self, request):
        """Mis períodos de nómina (filtrado por empleado logueado)"""
        try:
            employee = request.user.employee_profile
        except AttributeError:
            return Response({'error': 'No tienes perfil de empleado'}, status=403)

        periods = PayrollPeriod.objects.filter(
            employee=employee,
            employee__tenant=getattr(request, 'tenant', request.user.tenant)
        ).select_related('employee__user').order_by('-period_start')

        periods_data = []
        for period in periods:
            status = period.status
            if status == 'ready':
                status = 'approved'
            periods_data.append({
                'id': period.id,
                'period_display': period.period_display,
                'status': status,
                'base_salary': float(period.base_salary),
                'commission_earnings': float(period.commission_earnings),
                'gross_amount': float(period.gross_amount),
                'net_amount': float(period.net_amount),
                'deductions_total': float(period.deductions_total),
                'period_start': period.period_start.isoformat(),
                'period_end': period.period_end.isoformat(),
                'can_pay': period.can_pay,
                'pay_block_reason': period.pay_block_reason,
                'payment_method': period.get_payment_method_display() if period.payment_method else None,
                'paid_at': period.paid_at.isoformat() if period.paid_at else None,
            })

        return Response({'periods': periods_data})

    @action(detail=False, methods=['get'], url_path='client/payroll/my-summary')
    def my_summary(self, request):
        """Resumen de ingresos del empleado logueado"""
        try:
            employee = request.user.employee_profile
        except AttributeError:
            return Response({'error': 'No tienes perfil de empleado'}, status=403)

        periods = PayrollPeriod.objects.filter(
            employee=employee,
            employee__tenant=getattr(request, 'tenant', request.user.tenant)
        ).exclude(status='rejected')

        total_gross = sum(float(p.gross_amount) for p in periods)
        total_net = sum(float(p.net_amount) for p in periods)
        total_deductions = sum(float(p.deductions_total) for p in periods)
        paid_periods = periods.filter(status='paid').count()
        pending_periods = periods.filter(status__in=['open', 'pending_approval', 'approved']).count()

        return Response({
            'total_gross': round(total_gross, 2),
            'total_net': round(total_net, 2),
            'total_deductions': round(total_deductions, 2),
            'paid_periods': paid_periods,
            'pending_periods': pending_periods,
            'payment_type': employee.get_payment_type_display(),
            'commission_rate': float(employee.commission_rate),
        })
    
    @action(detail=False, methods=['post'], url_path='client/payroll/register_payment')
    def register_payment(self, request):
        """Endpoint compatible con frontend: POST /payroll/client/payroll/register_payment/"""
        self._require_admin_role(request)
        
        period_id = request.data.get('period_id')
        payment_method = request.data.get('payment_method')
        payment_reference = request.data.get('payment_reference', '')
        
        if not period_id or not payment_method:
            return Response({'error': 'period_id y payment_method son requeridos'}, status=400)
        
        try:
            with transaction.atomic():
                # 🔒 BLOQUEO REAL DE FILA
                period = PayrollPeriod.objects.select_for_update().get(id=period_id)
                
                if period.employee.tenant != getattr(request, 'tenant', request.user.tenant):
                    return Response({'error': 'No tienes permiso'}, status=403)
                
                if period.status == 'paid':
                    return Response({'error': 'Ya fue pagado'}, status=400)
                
                if period.status != 'approved':
                    return Response({'error': 'El período debe estar aprobado antes de pagar'}, status=400)
                
                if not period.can_pay:
                    return Response({'error': period.pay_block_reason}, status=400)
                
                period.mark_as_paid(payment_method, payment_reference, request.user)
                self._send_payment_notification(period)
            
            return Response({
                'payment_id': str(period.id),
                'message': 'Pago registrado exitosamente',
                'amount_paid': float(period.net_amount),
                'paid_at': period.paid_at.isoformat()
            })
        except PayrollPeriod.DoesNotExist:
            return Response({'error': 'Período no encontrado'}, status=404)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
    
    @action(detail=False, methods=['post'], url_path='client/payroll/(?P<period_id>[^/.]+)/recalculate')
    def recalculate_period(self, request, period_id=None):
        """Recalcular período manualmente (solo si está open o pending)"""
        self._require_admin_role(request)
        
        try:
            period = PayrollPeriod.objects.get(id=period_id)
            
            if period.employee.tenant != getattr(request, 'tenant', request.user.tenant):
                return Response({'error': 'No tienes permiso'}, status=403)
            
            if period.status in ['approved', 'paid']:
                return Response({'error': 'No se puede recalcular un período aprobado o pagado'}, status=400)
            
            period.calculate_amounts()
            period.save()
            
            return Response({
                'message': 'Período recalculado exitosamente',
                'gross_amount': float(period.gross_amount),
                'net_amount': float(period.net_amount)
            })
        except PayrollPeriod.DoesNotExist:
            return Response({'error': 'Período no encontrado'}, status=404)
    
    @action(detail=False, methods=['post'], url_path='client/payroll/(?P<period_id>[^/.]+)/submit')
    def submit_for_approval(self, request, period_id=None):
        """Enviar período para aprobación"""
        self._require_admin_role(request)

        try:
            period = PayrollPeriod.objects.get(id=period_id)
            
            if period.employee.tenant != getattr(request, 'tenant', request.user.tenant):
                return Response({'error': 'No tienes permiso'}, status=403)
            
            if period.status != 'open':
                return Response({'error': 'Solo se pueden enviar períodos abiertos'}, status=400)
            
            period.submitted_by = request.user
            period.close_period()
            
            return Response({
                'message': 'Período enviado para aprobación',
                'status': period.status
            })
        except PayrollPeriod.DoesNotExist:
            return Response({'error': 'Período no encontrado'}, status=404)
    
    @action(detail=False, methods=['post'], url_path='client/payroll/(?P<period_id>[^/.]+)/approve')
    def approve_period(self, request, period_id=None):
        """Aprobar período para pago"""
        self._require_admin_role(request)
        
        try:
            period = PayrollPeriod.objects.get(id=period_id)
            
            if period.employee.tenant != getattr(request, 'tenant', request.user.tenant):
                return Response({'error': 'No tienes permiso'}, status=403)
            
            period.approve(request.user)
            self._send_approval_notification(period)
            
            return Response({
                'message': 'Período aprobado exitosamente',
                'status': period.status
            })
        except PayrollPeriod.DoesNotExist:
            return Response({'error': 'Período no encontrado'}, status=404)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)
    
    @action(detail=False, methods=['post'], url_path='client/payroll/(?P<period_id>[^/.]+)/reject')
    def reject_period(self, request, period_id=None):
        """Rechazar período"""
        self._require_admin_role(request)
        
        reason = request.data.get('reason', 'Sin motivo especificado')
        
        try:
            period = PayrollPeriod.objects.get(id=period_id)
            
            if period.employee.tenant != getattr(request, 'tenant', request.user.tenant):
                return Response({'error': 'No tienes permiso'}, status=403)
            
            period.reject(request.user, reason)
            self._send_rejection_notification(period)
            
            return Response({
                'message': 'Período rechazado',
                'status': period.status,
                'reason': reason
            })
        except PayrollPeriod.DoesNotExist:
            return Response({'error': 'Período no encontrado'}, status=404)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
    
    def _send_payment_notification(self, period):
        """Enviar notificación de pago"""
        try:
            from apps.auth_api.tasks import send_email_async
            from apps.emails.service import EmailRenderer

            employee_email = period.employee.user.email
            employee_name = period.employee.user.full_name or employee_email

            tenant = period.employee.tenant
            business_name = tenant.name if tenant else 'Auron Suite'

            subject = f'Pago Procesado - {period.period_display}'
            message = f'''Hola {employee_name},

Tu pago del período {period.period_display} ha sido procesado exitosamente.

Detalles:
- Sueldo Base: ${period.base_salary:,.2f}
- Comisiones de Ventas: ${period.commission_earnings:,.2f}
- Monto Bruto: ${period.gross_amount:,.2f}
- Deducciones: ${period.deductions_total:,.2f}
- Monto Neto: ${period.net_amount:,.2f}
- Método: {period.get_payment_method_display()}
- Referencia: {period.payment_reference or 'N/A'}

Saludos,
Equipo de Nómina'''

            html_body = EmailRenderer.render('payroll_notification.html', {
                'business_name': business_name,
                'title': subject,
                'user_full_name': employee_name,
                'message': f'Tu pago del período <strong>{period.period_display}</strong> ha sido procesado exitosamente.',
                'details': [
                    ('Sueldo Base', f'${period.base_salary:,.2f}'),
                    ('Comisiones de Ventas', f'${period.commission_earnings:,.2f}'),
                    ('Monto Bruto', f'${period.gross_amount:,.2f}'),
                    ('Deducciones', f'${period.deductions_total:,.2f}'),
                    ('Monto Neto', f'${period.net_amount:,.2f}'),
                    ('Método', period.get_payment_method_display()),
                    ('Referencia', period.payment_reference or 'N/A'),
                ],
            })

            send_email_async.delay(
                subject=subject,
                message=message,
                from_email='',
                recipient_list=[employee_email],
                html_message=html_body,
            )

            period.notification_sent = True
            period.notification_sent_at = timezone.now()
            period.save()
        except Exception as e:
            logger.error("Error sending payment notification for period %s: %s", period.id, e)

    def _send_approval_notification(self, period):
        """Enviar notificación de aprobación"""
        try:
            from apps.auth_api.tasks import send_email_async
            from apps.emails.service import EmailRenderer

            employee_email = period.employee.user.email
            employee_name = period.employee.user.full_name or employee_email

            tenant = period.employee.tenant
            business_name = tenant.name if tenant else 'Auron Suite'

            subject = f'Período Aprobado - {period.period_display}'
            message = f'''Hola {employee_name},

Tu período de nómina {period.period_display} ha sido aprobado.

Monto a recibir: ${period.net_amount:,.2f}

El pago será procesado próximamente.

Saludos,
Equipo de Nómina'''

            html_body = EmailRenderer.render('payroll_notification.html', {
                'business_name': business_name,
                'title': subject,
                'user_full_name': employee_name,
                'message': f'Tu período de nómina <strong>{period.period_display}</strong> ha sido aprobado.',
                'details': [
                    ('Monto a recibir', f'${period.net_amount:,.2f}'),
                ],
                'extra_note': 'El pago será procesado próximamente.',
            })

            send_email_async.delay(
                subject=subject,
                message=message,
                from_email='',
                recipient_list=[employee_email],
                html_message=html_body,
            )
        except Exception as e:
            logger.error("Error sending approval notification for period %s: %s", period.id, e)

    def _send_rejection_notification(self, period):
        """Enviar notificación de rechazo"""
        try:
            from apps.auth_api.tasks import send_email_async
            from apps.emails.service import EmailRenderer

            employee_email = period.employee.user.email
            employee_name = period.employee.user.full_name or employee_email

            tenant = period.employee.tenant
            business_name = tenant.name if tenant else 'Auron Suite'

            subject = f'Período Rechazado - {period.period_display}'
            message = f'''Hola {employee_name},

Tu período de nómina {period.period_display} ha sido rechazado.

Motivo: {period.rejection_reason}

Por favor, contacta con el departamento de nómina para más información.

Saludos,
Equipo de Nómina'''

            html_body = EmailRenderer.render('payroll_notification.html', {
                'business_name': business_name,
                'title': subject,
                'user_full_name': employee_name,
                'message': f'Tu período de nómina <strong>{period.period_display}</strong> ha sido rechazado.',
                'details': [
                    ('Motivo', period.rejection_reason),
                ],
                'extra_note': 'Contacta con el departamento de nómina para más información.',
            })

            send_email_async.delay(
                subject=subject,
                message=message,
                from_email='',
                recipient_list=[employee_email],
                html_message=html_body,
            )
        except Exception as e:
            logger.error("Error sending rejection notification for period %s: %s", period.id, e)
    
    @action(detail=False, methods=['get'], url_path='payments/(?P<payment_id>[^/.]+)/receipt')
    def get_receipt(self, request, payment_id=None):
        """Endpoint compatible con frontend: GET /payroll/client/payroll/payments/{id}/receipt/"""
        try:
            period = PayrollPeriod.objects.select_related('employee__user', 'employee__tenant').get(id=payment_id)
            
            if period.employee.tenant != getattr(request, 'tenant', request.user.tenant):
                return Response({'error': 'No tienes permiso'}, status=403)
            
            deductions = [{'type': d.get_deduction_type_display(), 'amount': float(d.amount), 'description': d.description} for d in period.deductions.all()]
            
            return Response({
                'payment_id': str(period.id),
                'company': {'name': period.employee.tenant.name, 'address': getattr(period.employee.tenant, 'address', 'N/A')},
                'employee': {'name': period.employee.user.full_name or period.employee.user.email, 'email': period.employee.user.email, 'payment_type': period.employee.get_payment_type_display()},
                'period': {'display': period.period_display, 'start_date': period.period_start.isoformat(), 'end_date': period.period_end.isoformat(), 'type': period.get_period_type_display()},
                'amounts': {'base_salary': float(period.base_salary), 'commission_earnings': float(period.commission_earnings), 'gross_amount': float(period.gross_amount), 'deductions': {'total': float(period.deductions_total), 'items': deductions}, 'net_amount': float(period.net_amount)},
                'payment_info': {'method': period.get_payment_method_display() if period.payment_method else 'N/A', 'reference': period.payment_reference or 'N/A', 'paid_at': period.paid_at.isoformat() if period.paid_at else None, 'paid_by': period.paid_by.full_name if period.paid_by else 'N/A'}
            })
        except PayrollPeriod.DoesNotExist:
            return Response({'error': 'Recibo no encontrado'}, status=404)


class PayrollConfigurationViewSet(viewsets.GenericViewSet):
    """ViewSet para gestionar configuración global de nómina del tenant"""
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'retrieve': 'employees_api.view_employee_payroll',
        'update': 'employees_api.manage_employee_loans',
        'partial_update': 'employees_api.manage_employee_loans',
    }
    serializer_class = PayrollConfigurationSerializer

    def get_object(self):
        tenant = getattr(self.request, 'tenant', getattr(self.request.user, 'tenant', None))
        obj, _ = PayrollConfiguration.objects.get_or_create(tenant=tenant)
        return obj

    def retrieve(self, request):
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)

    def update(self, request):
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request):
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
