from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from celery import shared_task
from .models import Employee
from .earnings_models import FortnightSummary
from .advance_loans import AdvanceLoan

class PayrollNotificationService:
    
    @staticmethod
    def send_payment_notification(fortnight_summary):
        """Envía notificación de pago procesado"""
        employee = fortnight_summary.employee
        
        context = {
            'employee_name': employee.user.full_name,
            'payment_date': fortnight_summary.paid_at.date(),
            'gross_amount': fortnight_summary.total_earnings,
            'net_amount': fortnight_summary.net_salary,
            'deductions': {
                'afp': fortnight_summary.afp_deduction,
                'sfs': fortnight_summary.sfs_deduction,
                'isr': fortnight_summary.isr_deduction,
                'loans': getattr(fortnight_summary, 'loan_deductions', 0)
            },
            'company_name': employee.tenant.name
        }
        
        subject = f'Comprobante de Pago - {fortnight_summary.paid_at.date()}'
        message = render_to_string('employees/payment_notification.html', context)
        
        send_mail(
            subject=subject,
            message='',
            html_message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[employee.user.email],
            fail_silently=False
        )
    
    @staticmethod
    def send_loan_approval_notification(advance_loan):
        """Notifica aprobación de préstamo"""
        context = {
            'employee_name': advance_loan.employee.user.full_name,
            'loan_type': advance_loan.get_loan_type_display(),
            'amount': advance_loan.amount,
            'installments': advance_loan.installments,
            'monthly_payment': advance_loan.monthly_payment,
            'approval_date': advance_loan.approval_date,
            'first_payment_date': advance_loan.first_payment_date
        }
        
        subject = f'Préstamo Aprobado - {advance_loan.get_loan_type_display()}'
        message = render_to_string('employees/loan_approval.html', context)
        
        send_mail(
            subject=subject,
            message='',
            html_message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[advance_loan.employee.user.email],
            fail_silently=False
        )
    
    @staticmethod
    def send_payroll_summary_to_admin(tenant, period_start, period_end):
        """Envía resumen de nómina a administradores"""
        payments = FortnightSummary.objects.filter(
            employee__tenant=tenant,
            paid_at__date__range=[period_start, period_end],
            is_paid=True
        )
        
        context = {
            'tenant_name': tenant.name,
            'period_start': period_start,
            'period_end': period_end,
            'total_employees': payments.values('employee').distinct().count(),
            'total_payments': payments.count(),
            'gross_total': sum(p.total_earnings for p in payments),
            'net_total': sum(p.net_salary for p in payments),
            'total_deductions': sum(p.total_deductions for p in payments)
        }
        
        # Obtener emails de administradores
        admin_emails = [
            user.email for user in tenant.users.filter(
                groups__name__in=['admin', 'manager']
            ) if user.email
        ]
        
        if admin_emails:
            subject = f'Resumen de Nómina - {period_start} a {period_end}'
            message = render_to_string('employees/payroll_summary.html', context)
            
            send_mail(
                subject=subject,
                message='',
                html_message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
                fail_silently=False
            )

@shared_task
def send_payment_reminders():
    """Tarea programada para recordatorios de pago"""
    # Buscar empleados con pagos pendientes hace más de 3 días
    cutoff_date = timezone.now().date() - timedelta(days=3)
    
    pending_payments = FortnightSummary.objects.filter(
        is_paid=False,
        created_at__date__lte=cutoff_date
    ).select_related('employee', 'employee__user', 'employee__tenant')
    
    for payment in pending_payments:
        # Notificar al empleado
        context = {
            'employee_name': getattr(payment.employee.user, 'full_name', None) or payment.employee.user.email,
            'payment_date': payment.created_at.date(),
            'amount': payment.net_salary,
            'days_overdue': (timezone.now().date() - payment.created_at.date()).days
        }
        
        subject = f'Recordatorio de Pago Pendiente'
        message = render_to_string('employees/payment_reminder.html', context)
        
        send_mail(
            subject=subject,
            message='',
            html_message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[payment.employee.user.email],
            fail_silently=True
        )

@shared_task
def send_monthly_tax_report():
    """Envía reporte mensual de impuestos"""
    from .payroll_reports import PayrollReportGenerator
    
    # Obtener mes anterior
    today = timezone.now().date()
    if today.month == 1:
        year, month = today.year - 1, 12
    else:
        year, month = today.year, today.month - 1
    
    # Generar reportes para cada tenant
    from apps.tenants_api.models import Tenant
    
    for tenant in Tenant.objects.all():
        try:
            report = PayrollReportGenerator.tax_compliance_report(year, month, tenant)
            
            # Obtener emails de administradores
            admin_emails = [
                user.email for user in tenant.users.filter(
                    groups__name__in=['admin', 'manager']
                ) if user.email
            ]
            
            if admin_emails and report['gross_payroll'] > 0:
                context = {
                    'tenant_name': tenant.name,
                    'report': report
                }
                
                subject = f'Reporte Fiscal Mensual - {report["period"]}'
                message = render_to_string('employees/tax_report.html', context)
                
                send_mail(
                    subject=subject,
                    message='',
                    html_message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    fail_silently=True
                )
        except Exception as e:
            print(f"Error enviando reporte fiscal para {tenant.name}: {e}")

@shared_task
def send_loan_payment_reminders():
    """Recordatorios de pagos de préstamos próximos"""
    # Préstamos con pagos en los próximos 7 días
    upcoming_date = timezone.now().date() + timedelta(days=7)
    
    active_loans = AdvanceLoan.objects.filter(
        status='active',
        remaining_balance__gt=0
    ).select_related('employee', 'employee__user')
    
    for loan in active_loans:
        # Calcular próxima fecha de pago (simplificado)
        next_payment_date = loan.first_payment_date
        if next_payment_date and next_payment_date <= upcoming_date:
            context = {
                'employee_name': getattr(loan.employee.user, 'full_name', None) or loan.employee.user.email,
                'loan_type': loan.get_loan_type_display(),
                'payment_amount': loan.monthly_payment,
                'next_payment_date': next_payment_date,
                'remaining_balance': loan.remaining_balance
            }
            
            subject = f'Recordatorio de Pago de Préstamo'
            message = render_to_string('employees/loan_payment_reminder.html', context)
            
            send_mail(
                subject=subject,
                message='',
                html_message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[loan.employee.user.email],
                fail_silently=True
            )