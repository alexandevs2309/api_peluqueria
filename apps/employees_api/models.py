from django.db import models
from django.conf import settings
from apps.services_api.models import Service

# Importar modelos de ganancias
from .earnings_models import Earning, FortnightSummary

class Employee(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('fixed', 'Sueldo Fijo'),
        ('commission', 'Comisión'),
        ('mixed', 'Mixto (Sueldo + Comisión)')
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='employee_profile')
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE, related_name='employees')
    specialty = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Payment configuration fields
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES, default='commission')
    fixed_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text='Sueldo fijo mensual')
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=40.00, help_text='Porcentaje de comisión (ej: 40.00 para 40%)')
    
    # Additional fields from API contracts
    avatar = models.ImageField(upload_to='employees/avatars/', null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    bank_account = models.CharField(max_length=50, blank=True)
    tax_id = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__email']

    def __str__(self):
        return self.user.email

class EmployeeService(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='services')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'service')

class WorkSchedule(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.CharField(max_length=10, choices=[
        ('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday'), ('sunday', 'Sunday')
    ])
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'day_of_week', 'start_time')