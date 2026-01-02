from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import get_random_string
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime, timedelta
from decimal import Decimal

class Earning(models.Model):
    """Registro de ganancias por empleado - ÚNICO modelo de deuda"""
    
    EARNING_TYPE_CHOICES = [
        ('service', 'Servicio'),
        ('commission', 'Comisión'),
        ('tip', 'Propina'),
        ('bonus', 'Bono'),
        ('adjustment', 'Ajuste'),
    ]
    
    employee = models.ForeignKey(
        'employees_api.Employee', 
        on_delete=models.CASCADE, 
        related_name='earnings'
    )
    sale = models.ForeignKey(
        'pos_api.Sale', 
        on_delete=models.CASCADE, 
        related_name='earnings',
        null=True, blank=True
    )
    appointment = models.ForeignKey(
        'appointments_api.Appointment', 
        on_delete=models.CASCADE, 
        related_name='earnings',
        null=True, blank=True
    )
    
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Monto de la ganancia"
    )
    earning_type = models.CharField(
        max_length=20, 
        choices=EARNING_TYPE_CHOICES, 
        default='service'
    )
    percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Porcentaje de comisión (0-100)"
    )
    
    description = models.TextField(blank=True)
    date_earned = models.DateTimeField(default=timezone.now)
    
    # Campos de quincena
    fortnight_year = models.IntegerField()
    fortnight_number = models.IntegerField()  # 1-24 (2 por mes)
    
    # Campo para idempotencia
    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-date_earned']
        indexes = [
            models.Index(fields=['employee', 'fortnight_year', 'fortnight_number']),
            models.Index(fields=['external_id']),
            models.Index(fields=['date_earned']),
        ]
    
    def save(self, *args, **kwargs):
        # Validar campos requeridos
        if not self.employee_id:
            raise ValueError("Employee es requerido")
        if not self.amount:
            self.amount = Decimal('0.00')
        if not self.date_earned:
            self.date_earned = timezone.now()
        
        # Calcular quincena automáticamente SIEMPRE
        self.fortnight_year, self.fortnight_number = self.calculate_fortnight(self.date_earned)
        
        super().save(*args, **kwargs)
    
    @staticmethod
    def calculate_fortnight(date):
        """Calcula año y número de quincena (1-24)"""
        year = date.year
        month = date.month
        day = date.day
        
        # Quincena 1: días 1-15, Quincena 2: días 16-fin de mes
        fortnight_in_month = 1 if day <= 15 else 2
        fortnight_number = (month - 1) * 2 + fortnight_in_month
        
        return year, fortnight_number
    
    @property
    def fortnight_display(self):
        """Muestra la quincena en formato legible"""
        month = ((self.fortnight_number - 1) // 2) + 1
        half = "1ra" if (self.fortnight_number % 2) == 1 else "2da"
        months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        return f"{half} quincena {months[month-1]} {self.fortnight_year}"
    
    def __str__(self):
        return f"{self.employee} - ${self.amount} ({self.fortnight_display})"

# MODELOS LEGACY ELIMINADOS:
# - FortnightSummary (reemplazado por PayrollSettlement)
# - PeriodSummary (reemplazado por PayrollSettlement)
# - PayrollBatch (reemplazado por PayrollSettlement)
# - PayrollBatchItem (reemplazado por PayrollSettlement)
# - PaymentReceipt (funcionalidad movida a PayrollPayment)