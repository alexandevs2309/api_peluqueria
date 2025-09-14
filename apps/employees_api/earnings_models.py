from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

class Earning(models.Model):
    """Registro de ganancias por empleado"""
    
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
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    earning_type = models.CharField(max_length=20, choices=EARNING_TYPE_CHOICES, default='service')
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Porcentaje de comisión")
    
    description = models.TextField(blank=True)
    date_earned = models.DateTimeField(default=timezone.now)
    
    # Campos de quincena
    fortnight_year = models.IntegerField()
    fortnight_number = models.IntegerField()  # 1-24 (2 por mes)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-date_earned']
        indexes = [
            models.Index(fields=['employee', 'fortnight_year', 'fortnight_number']),
            models.Index(fields=['date_earned']),
        ]
    
    def save(self, *args, **kwargs):
        # Calcular quincena automáticamente
        if not self.fortnight_year or not self.fortnight_number:
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

class FortnightSummary(models.Model):
    """Resumen de ganancias por quincena"""
    
    employee = models.ForeignKey(
        'employees_api.Employee', 
        on_delete=models.CASCADE, 
        related_name='fortnight_summaries'
    )
    
    fortnight_year = models.IntegerField()
    fortnight_number = models.IntegerField()
    
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_services = models.IntegerField(default=0)
    total_commissions = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_tips = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('employee', 'fortnight_year', 'fortnight_number')
        ordering = ['-fortnight_year', '-fortnight_number']
    
    @property
    def fortnight_display(self):
        month = ((self.fortnight_number - 1) // 2) + 1
        half = "1ra" if (self.fortnight_number % 2) == 1 else "2da"
        months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        return f"{half} quincena {months[month-1]} {self.fortnight_year}"
    
    def __str__(self):
        return f"{self.employee} - {self.fortnight_display} - ${self.total_earnings}"