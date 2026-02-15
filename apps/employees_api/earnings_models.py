from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
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
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-date_earned']
        indexes = [
            models.Index(fields=['employee', 'fortnight_year', 'fortnight_number']),
            models.Index(fields=['date_earned']),
        ]
    
    def save(self, *args, **kwargs):
        # Validar campos requeridos
        if not self.employee_id:
            raise ValueError("Employee es requerido")
        if not self.amount:
            self.amount = Decimal('0.00')
        
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
    
    total_earnings = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total de ganancias de la quincena"
    )
    total_services = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Número de servicios realizados"
    )
    total_commissions = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total de comisiones"
    )
    total_tips = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total de propinas"
    )
    
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)  # Cuando se cierra el período
    
    # Campos de pago detallado
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('cash', 'Efectivo'),
            ('transfer', 'Transferencia'),
            ('check', 'Cheque'),
            ('other', 'Otro')
        ],
        null=True, blank=True
    )
    amount_paid = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Monto real pagado"
    )
    payment_reference = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="Referencia bancaria o número de cheque"
    )
    payment_notes = models.TextField(
        null=True, blank=True,
        help_text="Notas adicionales del pago"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('employee', 'fortnight_year', 'fortnight_number')
        ordering = ['-fortnight_year', '-fortnight_number']
        indexes = [
            models.Index(fields=['employee', 'fortnight_year', 'fortnight_number']),
            models.Index(fields=['is_paid']),
        ]
    
    def save(self, *args, **kwargs):
        # Validar campos requeridos
        if not self.employee_id:
            raise ValueError("Employee es requerido")
        if self.total_earnings is None:
            self.total_earnings = Decimal('0.00')
        if self.total_services is None:
            self.total_services = 0
        if self.total_commissions is None:
            self.total_commissions = Decimal('0.00')
        if self.total_tips is None:
            self.total_tips = Decimal('0.00')
        
        super().save(*args, **kwargs)
    
    @property
    def fortnight_display(self):
        """Muestra la quincena en formato legible"""
        if not self.fortnight_number or not self.fortnight_year:
            return "Quincena no definida"
        
        month = ((self.fortnight_number - 1) // 2) + 1
        half = "1ra" if (self.fortnight_number % 2) == 1 else "2da"
        months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        
        if month < 1 or month > 12:
            return f"Quincena {self.fortnight_number} - {self.fortnight_year}"
        
        return f"{half} quincena {months[month-1]} {self.fortnight_year}"
    
    def __str__(self):
        return f"{self.employee} - {self.fortnight_display} - ${self.total_earnings}"

class PaymentReceipt(models.Model):
    """Recibos de pago de nómina"""
    
    fortnight_summary = models.OneToOneField(
        FortnightSummary,
        on_delete=models.CASCADE,
        related_name='receipt'
    )
    receipt_number = models.CharField(max_length=50, unique=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='payment_receipts/', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Payment Receipt'
        verbose_name_plural = 'Payment Receipts'
        ordering = ['-generated_at']
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f"PR{self.fortnight_summary.employee.id:03d}{self.fortnight_summary.fortnight_year}{self.fortnight_summary.fortnight_number:02d}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Recibo {self.receipt_number} - {self.fortnight_summary.employee}"


# ============================================
# MODELOS DE NÓMINA (PAYROLL)
# ============================================

class PayrollPeriod(models.Model):
    """Período de nómina - soporta sueldo fijo, comisión y mixto"""
    
    PERIOD_TYPE_CHOICES = [
        ('weekly', 'Semanal'),
        ('biweekly', 'Quincenal'),
        ('monthly', 'Mensual'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Abierto'),
        ('pending_approval', 'Pendiente de Aprobación'),
        ('approved', 'Aprobado'),
        ('paid', 'Pagado'),
        ('rejected', 'Rechazado'),
    ]
    
    employee = models.ForeignKey(
        'employees_api.Employee',
        on_delete=models.CASCADE,
        related_name='payroll_periods'
    )
    
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPE_CHOICES, default='biweekly')
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    commission_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    deductions_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    can_pay = models.BooleanField(default=True)
    pay_block_reason = models.TextField(null=True, blank=True)
    
    payment_method = models.CharField(max_length=20, choices=[('cash', 'Efectivo'), ('transfer', 'Transferencia')], null=True, blank=True)
    payment_reference = models.CharField(max_length=100, null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='payroll_payments_made')
    
    # Campos de aprobación
    submitted_for_approval_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='payroll_submissions')
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='payroll_approvals')
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='payroll_rejections')
    rejection_reason = models.TextField(null=True, blank=True)
    
    # Notificaciones
    notification_sent = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-period_start']
        indexes = [
            models.Index(fields=['employee', 'period_start', 'period_end']),
            models.Index(fields=['status']),
        ]
    
    def calculate_amounts(self):
        employee = self.employee
        
        if employee.payment_type in ['fixed', 'mixed']:
            if self.period_type == 'monthly':
                self.base_salary = employee.fixed_salary
            elif self.period_type == 'biweekly':
                self.base_salary = employee.fixed_salary / 2
            elif self.period_type == 'weekly':
                self.base_salary = employee.fixed_salary / 4
        else:
            self.base_salary = Decimal('0.00')
        
        if employee.payment_type in ['commission', 'mixed']:
            earnings = Earning.objects.filter(
                employee=employee,
                date_earned__gte=self.period_start,
                date_earned__lte=self.period_end
            )
            self.commission_earnings = sum(e.amount for e in earnings)
        else:
            self.commission_earnings = Decimal('0.00')
        
        self.gross_amount = self.base_salary + self.commission_earnings
        deductions = self.deductions.all()
        self.deductions_total = sum(d.amount for d in deductions)
        self.net_amount = self.gross_amount - self.deductions_total
        
        if self.status == 'open':
            self.can_pay = False
            self.pay_block_reason = "El período aún está abierto"
        elif self.net_amount <= 0:
            self.can_pay = False
            self.pay_block_reason = "El monto neto es cero o negativo"
        else:
            self.can_pay = True
            self.pay_block_reason = None
    
    def close_period(self):
        """Cierra el período y lo envía para aprobación"""
        self.status = 'pending_approval'
        self.submitted_for_approval_at = timezone.now()
        self.calculate_amounts()
        self.save()
    
    def approve(self, approved_by):
        """Aprueba el período para pago"""
        if self.status != 'pending_approval':
            raise ValueError("Solo se pueden aprobar períodos pendientes")
        self.status = 'approved'
        self.approved_at = timezone.now()
        self.approved_by = approved_by
        self.save()
    
    def reject(self, rejected_by, reason):
        """Rechaza el período"""
        if self.status != 'pending_approval':
            raise ValueError("Solo se pueden rechazar períodos pendientes")
        self.status = 'rejected'
        self.rejected_at = timezone.now()
        self.rejected_by = rejected_by
        self.rejection_reason = reason
        self.save()
    
    def mark_as_paid(self, payment_method, payment_reference, paid_by):
        """Marca el período como pagado"""
        if self.status != 'approved':
            raise ValueError("Solo se pueden pagar períodos aprobados")
        self.status = 'paid'
        self.payment_method = payment_method
        self.payment_reference = payment_reference
        self.paid_at = timezone.now()
        self.paid_by = paid_by
        self.save()
    
    @property
    def period_display(self):
        return f"{self.period_start.strftime('%d/%m/%Y')} - {self.period_end.strftime('%d/%m/%Y')}"
    
    def __str__(self):
        return f"{self.employee} - {self.period_display} - {self.status}"


class PayrollDeduction(models.Model):
    """Deducciones de nómina"""
    
    DEDUCTION_TYPE_CHOICES = [
        ('tax', 'Impuesto'),
        ('social_security', 'Seguro Social'),
        ('health_insurance', 'Seguro Médico'),
        ('advance', 'Adelanto'),
        ('loan', 'Préstamo'),
        ('other', 'Otro'),
    ]
    
    period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE, related_name='deductions')
    deduction_type = models.CharField(max_length=20, choices=DEDUCTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    description = models.TextField(blank=True)
    is_automatic = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['deduction_type']
    
    def __str__(self):
        return f"{self.get_deduction_type_display()} - ${self.amount}"


class PayrollConfiguration(models.Model):
    """Configuración de nómina por tenant"""
    
    tenant = models.OneToOneField('tenants_api.Tenant', on_delete=models.CASCADE, related_name='payroll_config')
    default_period_type = models.CharField(max_length=10, choices=PayrollPeriod.PERIOD_TYPE_CHOICES, default='biweekly')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    social_security_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    health_insurance_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    auto_close_periods = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Payroll Configuration'
        verbose_name_plural = 'Payroll Configurations'
    
    def __str__(self):
        return f"Config Nómina - {self.tenant}"