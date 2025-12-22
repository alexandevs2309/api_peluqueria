from django.db import models
from django.conf import settings
from apps.services_api.models import Service

# Importar modelos de ganancias
from .earnings_models import Earning, FortnightSummary
from .payroll_models import PayrollPayment, PayrollPaymentSale

class Employee(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('fixed', 'Sueldo Fijo'),
        ('commission', 'Comisión'),
        ('mixed', 'Mixto (Sueldo + Comisión)')
    ]
    
    PAYMENT_FREQUENCY_CHOICES = [
        ('daily', 'Diario'),
        ('weekly', 'Semanal'), 
        ('biweekly', 'Quincenal'),
        ('monthly', 'Mensual')
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='employee_profile')
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE, related_name='employees')
    specialty = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Payment configuration fields - usando nombres correctos del flujo de negocio
    salary_type = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES, default='commission', help_text='Tipo de pago: fixed, commission, mixed')
    
    # NUEVO: Salario contractual mensual (fuente de verdad)
    contractual_monthly_salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text='Salario mensual contractual (fuente de verdad para cálculos de nómina)'
    )
    
    # DEPRECATED: Mantener solo para backward compatibility
    # NO USAR en nueva lógica - usar contractual_monthly_salary + payment_frequency
    salary_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00, 
        help_text='[DEPRECATED] Usar contractual_monthly_salary. Anteriormente: sueldo quincenal'
    )
    
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=40.00, help_text='Porcentaje de comisión (ej: 40.00 para 40%)')
    payment_frequency = models.CharField(max_length=10, choices=PAYMENT_FREQUENCY_CHOICES, default='biweekly', help_text='Frecuencia de pago')
    
    # Modo de pago de comisiones (SOLO para salary_type='commission')
    COMMISSION_PAYMENT_MODE_CHOICES = [
        ('PER_PERIOD', 'Por Período'),
        ('ON_DEMAND', 'Retiro Libre')
    ]
    commission_payment_mode = models.CharField(
        max_length=12, 
        choices=COMMISSION_PAYMENT_MODE_CHOICES, 
        default='PER_PERIOD',
        help_text='Modo de pago de comisiones: PER_PERIOD (por períodos) u ON_DEMAND (retiro libre)'
    )
    commission_on_demand_since = models.DateField(
        null=True, blank=True,
        help_text='Fecha desde la cual las comisiones se manejan ON_DEMAND (previene doble pago)'
    )
    
    # Descuentos legales (opcionales)
    apply_afp = models.BooleanField(default=False, help_text='Aplicar descuento AFP (2.87%)')
    apply_sfs = models.BooleanField(default=False, help_text='Aplicar descuento SFS (3.04%)')
    apply_isr = models.BooleanField(default=False, help_text='Aplicar descuento ISR')
    
    # Campos de compatibilidad (mantener para no romper código existente)
    @property
    def payment_type(self):
        return self.salary_type
    
    @payment_type.setter
    def payment_type(self, value):
        self.salary_type = value
    
    @property
    def fixed_salary(self):
        return self.salary_amount
    
    @fixed_salary.setter
    def fixed_salary(self, value):
        self.salary_amount = value
    
    @property
    def commission_rate(self):
        return self.commission_percentage
    
    @commission_rate.setter
    def commission_rate(self, value):
        self.commission_percentage = value
    
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