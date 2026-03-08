from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from django.core.exceptions import ValidationError
from .earnings_models import PayrollPeriod, PayrollDeduction, PayrollConfiguration
from .earnings_serializers import PayrollPeriodSerializer, PayrollDeductionSerializer, PayrollConfigurationSerializer
from django.db import transaction
from apps.core.tenant_permissions import TenantPermissionByAction

class PayrollViewSet(viewsets.ViewSet):
    """ViewSet para gestión de nómina"""
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list_periods': 'employees_api.view_employee_payroll',
        'register_payment': 'employees_api.view_employee_payroll',
        'recalculate_period': 'employees_api.view_employee_payroll',
        'submit_for_approval': 'employees_api.view_employee_payroll',
        'approve_period': 'employees_api.view_employee_payroll',
        'reject_period': 'employees_api.view_employee_payroll',
        'get_receipt': 'employees_api.view_employee_payroll',
    }
    
    def _require_admin_role(self, request):
        """Validar que el usuario tenga rol de administrador"""
        if not request.user.roles.filter(name__in=['Super-Admin', 'Client-Admin']).exists():
            raise PermissionDenied("No autorizado para operaciones de nómina.")
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'tenant'):
            return PayrollPeriod.objects.select_related(
                'employee__user',
                'employee__tenant'
            ).prefetch_related('deductions').filter(employee__tenant=user.tenant)
        return PayrollPeriod.objects.none()
    
    @action(detail=False, methods=['get'], url_path='client/payroll')
    def list_periods(self, request):
        """Endpoint compatible con frontend: GET /payroll/client/payroll/"""
        periods = self.get_queryset().select_related('employee__user')
        
        # ELIMINADO: No recalcular automáticamente en GET
        # El cálculo solo se hace al cerrar/aprobar o por acción explícita
        
        periods_data = []
        for period in periods:
            # Mapear estados legacy
            status = period.status
            if status == 'ready':
                status = 'approved'
            
            periods_data.append({
                'id': period.id,
                'employee_name': period.employee.user.full_name or period.employee.user.email,
                'period_display': period.period_display,
                'status': status,
                'gross_amount': float(period.gross_amount),
                'net_amount': float(period.net_amount),
                'deductions_total': float(period.deductions_total),
                'period_start': period.period_start.isoformat(),
                'period_end': period.period_end.isoformat(),
                'can_pay': period.can_pay,
                'pay_block_reason': period.pay_block_reason
            })
        
        return Response({'periods': periods_data})
    
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
                
                if period.employee.tenant != request.user.tenant:
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
            
            if period.employee.tenant != request.user.tenant:
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
            
            if period.employee.tenant != request.user.tenant:
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
            
            if period.employee.tenant != request.user.tenant:
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
            
            if period.employee.tenant != request.user.tenant:
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
        """Enviar notificación de pago al empleado"""
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            employee_email = period.employee.user.email
            employee_name = period.employee.user.full_name or employee_email
            
            subject = f'Pago Procesado - {period.period_display}'
            message = f'''Hola {employee_name},

Tu pago del período {period.period_display} ha sido procesado exitosamente.

Detalles:
- Monto Bruto: ${period.gross_amount:,.2f}
- Deducciones: ${period.deductions_total:,.2f}
- Monto Neto: ${period.net_amount:,.2f}
- Método: {period.get_payment_method_display()}
- Referencia: {period.payment_reference or 'N/A'}

Saludos,
Equipo de Nómina'''
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[employee_email],
                fail_silently=True
            )
            
            period.notification_sent = True
            period.notification_sent_at = timezone.now()
            period.save()
        except Exception:
            pass
    
    def _send_approval_notification(self, period):
        """Enviar notificación de aprobación"""
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            employee_email = period.employee.user.email
            employee_name = period.employee.user.full_name or employee_email
            
            subject = f'Período Aprobado - {period.period_display}'
            message = f'''Hola {employee_name},

Tu período de nómina {period.period_display} ha sido aprobado.

Monto a recibir: ${period.net_amount:,.2f}

El pago será procesado próximamente.

Saludos,
Equipo de Nómina'''
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[employee_email],
                fail_silently=True
            )
        except Exception:
            pass
    
    def _send_rejection_notification(self, period):
        """Enviar notificación de rechazo"""
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            employee_email = period.employee.user.email
            employee_name = period.employee.user.full_name or employee_email
            
            subject = f'Período Rechazado - {period.period_display}'
            message = f'''Hola {employee_name},

Tu período de nómina {period.period_display} ha sido rechazado.

Motivo: {period.rejection_reason}

Por favor, contacta con el departamento de nómina para más información.

Saludos,
Equipo de Nómina'''
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[employee_email],
                fail_silently=True
            )
        except Exception:
            pass
    
    @action(detail=False, methods=['get'], url_path='payments/(?P<payment_id>[^/.]+)/receipt')
    def get_receipt(self, request, payment_id=None):
        """Endpoint compatible con frontend: GET /payroll/client/payroll/payments/{id}/receipt/"""
        try:
            period = PayrollPeriod.objects.select_related('employee__user', 'employee__tenant').get(id=payment_id)
            
            if period.employee.tenant != request.user.tenant:
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
