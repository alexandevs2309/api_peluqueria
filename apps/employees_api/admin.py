from django.contrib import admin
from .models import Employee, EmployeeService, WorkSchedule
from .earnings_models import Earning, FortnightSummary, PaymentReceipt, PayrollPeriod, PayrollDeduction, PayrollConfiguration

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['user', 'tenant', 'payment_type', 'fixed_salary', 'commission_rate', 'is_active']
    list_filter = ['payment_type', 'is_active', 'tenant']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']

@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = ['employee', 'period_display', 'status', 'gross_amount', 'net_amount', 'paid_at']
    list_filter = ['status', 'period_type', 'period_start']
    search_fields = ['employee__user__email']
    readonly_fields = ['base_salary', 'commission_earnings', 'gross_amount', 'deductions_total', 'net_amount']

@admin.register(PayrollDeduction)
class PayrollDeductionAdmin(admin.ModelAdmin):
    list_display = ['period', 'deduction_type', 'amount', 'is_automatic']
    list_filter = ['deduction_type', 'is_automatic']

@admin.register(PayrollConfiguration)
class PayrollConfigurationAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'default_period_type', 'tax_rate', 'social_security_rate']
    list_filter = ['default_period_type']
