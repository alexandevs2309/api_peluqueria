from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import calendar
from .models import Employee
# ARCHIVO LEGACY - FortnightSummary eliminado
# Usar payroll_api.PayrollSettlement en su lugar
from .advance_loans import AdvanceLoan

class PayrollReportGenerator:
    
    @staticmethod
    def monthly_payroll_summary(year, month, tenant):
        """Genera resumen mensual de nómina"""
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, calendar.monthrange(year, month)[1]).date()
        
        payments = FortnightSummary.objects.filter(
            employee__tenant=tenant,
            paid_at__date__range=[start_date, end_date],
            is_paid=True
        )
        
        summary = {
            'period': f"{calendar.month_name[month]} {year}",
            'total_employees': payments.values('employee').distinct().count(),
            'total_payments': payments.count(),
            'gross_total': payments.aggregate(Sum('total_earnings'))['total_earnings__sum'] or 0,
            'deductions_total': payments.aggregate(Sum('total_deductions'))['total_deductions__sum'] or 0,
            'net_total': payments.aggregate(Sum('net_salary'))['net_salary__sum'] or 0,
            'avg_payment': payments.aggregate(Avg('net_salary'))['net_salary__avg'] or 0,
            'by_type': {}
        }
        
        # Desglose por tipo de empleado
        for salary_type in ['fixed', 'commission', 'mixed']:
            type_payments = payments.filter(employee__salary_type=salary_type)
            summary['by_type'][salary_type] = {
                'count': type_payments.count(),
                'total': type_payments.aggregate(Sum('net_salary'))['net_salary__sum'] or 0
            }
        
        return summary
    
    @staticmethod
    def employee_annual_report(employee_id, year):
        """Reporte anual de un empleado"""
        employee = Employee.objects.get(id=employee_id)
        start_date = datetime(year, 1, 1).date()
        end_date = datetime(year, 12, 31).date()
        
        payments = FortnightSummary.objects.filter(
            employee=employee,
            paid_at__date__range=[start_date, end_date],
            is_paid=True
        ).order_by('paid_at')
        
        loans = AdvanceLoan.objects.filter(
            employee=employee,
            request_date__range=[start_date, end_date]
        )
        
        monthly_data = []
        for month in range(1, 13):
            month_start = datetime(year, month, 1).date()
            month_end = datetime(year, month, calendar.monthrange(year, month)[1]).date()
            
            month_payments = payments.filter(paid_at__date__range=[month_start, month_end])
            
            monthly_data.append({
                'month': calendar.month_name[month],
                'payments_count': month_payments.count(),
                'gross_total': month_payments.aggregate(Sum('total_earnings'))['total_earnings__sum'] or 0,
                'net_total': month_payments.aggregate(Sum('net_salary'))['net_salary__sum'] or 0,
                'deductions': month_payments.aggregate(Sum('total_deductions'))['total_deductions__sum'] or 0
            })
        
        return {
            'employee': {
                'name': getattr(employee.user, 'full_name', None) or employee.user.email,
                'salary_type': employee.salary_type,
                'monthly_salary': employee.contractual_monthly_salary
            },
            'year': year,
            'summary': {
                'total_payments': payments.count(),
                'gross_annual': payments.aggregate(Sum('total_earnings'))['total_earnings__sum'] or 0,
                'net_annual': payments.aggregate(Sum('net_salary'))['net_salary__sum'] or 0,
                'total_deductions': payments.aggregate(Sum('total_deductions'))['total_deductions__sum'] or 0,
                'loans_requested': loans.count(),
                'loans_amount': loans.aggregate(Sum('amount'))['amount__sum'] or 0
            },
            'monthly_breakdown': monthly_data,
            'payments': list(payments.values(
                'paid_at', 'total_earnings', 'net_salary', 'total_deductions',
                'afp_deduction', 'sfs_deduction', 'isr_deduction'
            ))
        }
    
    @staticmethod
    def tax_compliance_report(year, month, tenant):
        """Reporte de cumplimiento fiscal"""
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, calendar.monthrange(year, month)[1]).date()
        
        payments = FortnightSummary.objects.filter(
            employee__tenant=tenant,
            paid_at__date__range=[start_date, end_date],
            is_paid=True
        )
        
        return {
            'period': f"{calendar.month_name[month]} {year}",
            'total_employees': payments.values('employee').distinct().count(),
            'afp_total': payments.aggregate(Sum('afp_deduction'))['afp_deduction__sum'] or 0,
            'sfs_total': payments.aggregate(Sum('sfs_deduction'))['sfs_deduction__sum'] or 0,
            'isr_total': payments.aggregate(Sum('isr_deduction'))['isr_deduction__sum'] or 0,
            'gross_payroll': payments.aggregate(Sum('total_earnings'))['total_earnings__sum'] or 0,
            'net_payroll': payments.aggregate(Sum('net_salary'))['net_salary__sum'] or 0,
            'employer_contributions': {
                'afp_employer': (payments.aggregate(Sum('afp_deduction'))['afp_deduction__sum'] or 0) * Decimal('0.71'),  # 7.10% empleador
                'sfs_employer': (payments.aggregate(Sum('sfs_deduction'))['sfs_deduction__sum'] or 0) * Decimal('2.37'),  # 7.09% empleador
                'srl_employer': (payments.aggregate(Sum('total_earnings'))['total_earnings__sum'] or 0) * Decimal('0.012')  # 1.2% SRL
            }
        }
    
    @staticmethod
    def loans_report(tenant, status=None):
        """Reporte de préstamos y anticipos"""
        loans = AdvanceLoan.objects.filter(employee__tenant=tenant)
        
        if status:
            loans = loans.filter(status=status)
        
        summary = {
            'total_loans': loans.count(),
            'total_amount': loans.aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_outstanding': loans.filter(status='active').aggregate(Sum('remaining_balance'))['remaining_balance__sum'] or 0,
            'by_type': {},
            'by_status': {}
        }
        
        # Por tipo
        for loan_type, label in AdvanceLoan.LOAN_TYPES:
            type_loans = loans.filter(loan_type=loan_type)
            summary['by_type'][loan_type] = {
                'label': label,
                'count': type_loans.count(),
                'amount': type_loans.aggregate(Sum('amount'))['amount__sum'] or 0
            }
        
        # Por estado
        for status_code, label in AdvanceLoan.STATUS_CHOICES:
            status_loans = loans.filter(status=status_code)
            summary['by_status'][status_code] = {
                'label': label,
                'count': status_loans.count(),
                'amount': status_loans.aggregate(Sum('amount'))['amount__sum'] or 0
            }
        
        return summary
    
    @staticmethod
    def cost_center_analysis(tenant, year, month):
        """Análisis por centro de costos (departamento)"""
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, calendar.monthrange(year, month)[1]).date()
        
        payments = FortnightSummary.objects.filter(
            employee__tenant=tenant,
            paid_at__date__range=[start_date, end_date],
            is_paid=True
        )
        
        # Agrupar por tipo de salario como proxy de departamento
        departments = {}
        for salary_type in ['fixed', 'commission', 'mixed']:
            dept_payments = payments.filter(employee__salary_type=salary_type)
            departments[salary_type] = {
                'name': {'fixed': 'Administración', 'commission': 'Ventas', 'mixed': 'Supervisión'}[salary_type],
                'employee_count': dept_payments.values('employee').distinct().count(),
                'total_cost': dept_payments.aggregate(Sum('net_salary'))['net_salary__sum'] or 0,
                'avg_salary': dept_payments.aggregate(Avg('net_salary'))['net_salary__avg'] or 0,
                'total_hours': dept_payments.count() * 80,  # Asumiendo 80 horas por quincena
                'cost_per_hour': (dept_payments.aggregate(Sum('net_salary'))['net_salary__sum'] or 0) / (dept_payments.count() * 80) if dept_payments.count() > 0 else 0
            }
        
        return {
            'period': f"{calendar.month_name[month]} {year}",
            'departments': departments,
            'total_payroll_cost': payments.aggregate(Sum('net_salary'))['net_salary__sum'] or 0
        }