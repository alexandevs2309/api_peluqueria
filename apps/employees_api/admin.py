from django.contrib import admin
from apps.tenants_api.base_admin import BaseTenantAdmin
from .models import Employee, EmployeeService, WorkSchedule, AttendanceRecord
from .earnings_models import PayrollPeriod, PayrollDeduction, PayrollConfiguration

@admin.register(Employee)
class EmployeeAdmin(BaseTenantAdmin):
    list_display = ['user', 'tenant', 'payment_type', 'fixed_salary', 'commission_rate', 'is_active']
    list_filter = ['payment_type', 'is_active', 'tenant']
    search_fields = ['user__email', 'user__full_name']

@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(BaseTenantAdmin):
    list_display = ['employee', 'period_display', 'status', 'gross_amount', 'net_amount', 'paid_at']
    list_filter = ['status', 'period_type', 'period_start']
    search_fields = ['employee__user__email']
    readonly_fields = ['base_salary', 'commission_earnings', 'gross_amount', 'deductions_total', 'net_amount']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'tenant') and request.user.tenant:
            return qs.filter(employee__tenant=request.user.tenant)
        return qs.none()

@admin.register(PayrollDeduction)
class PayrollDeductionAdmin(BaseTenantAdmin):
    list_display = ['period', 'deduction_type', 'amount', 'is_automatic']
    list_filter = ['deduction_type', 'is_automatic']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'tenant') and request.user.tenant:
            return qs.filter(period__employee__tenant=request.user.tenant)
        return qs.none()

@admin.register(PayrollConfiguration)
class PayrollConfigurationAdmin(BaseTenantAdmin):
    list_display = ['tenant', 'default_period_type', 'tax_rate', 'social_security_rate']
    list_filter = ['default_period_type']


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(BaseTenantAdmin):
    list_display = ['employee', 'work_date', 'check_in_at', 'check_out_at', 'status']
    list_filter = ['status', 'work_date']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'tenant') and request.user.tenant:
            return qs.filter(employee__tenant=request.user.tenant)
        return qs.none()
