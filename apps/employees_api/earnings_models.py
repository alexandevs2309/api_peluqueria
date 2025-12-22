from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import get_random_string
import uuid
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
        from django.db import transaction
        from django.db.models import Sum, Count
        
        # Validar campos requeridos
        if not self.employee_id:
            raise ValueError("Employee es requerido")
        if not self.amount:
            self.amount = Decimal('0.00')
        if not self.date_earned:
            self.date_earned = timezone.now()
        
        # Calcular quincena automáticamente SIEMPRE
        self.fortnight_year, self.fortnight_number = self.calculate_fortnight(self.date_earned)
        
        with transaction.atomic():
            super().save(*args, **kwargs)
            
            # Actualizar FortnightSummary automáticamente
            summary, created = FortnightSummary.objects.get_or_create(
                employee=self.employee,
                fortnight_year=self.fortnight_year,
                fortnight_number=self.fortnight_number,
                defaults={
                    'total_earnings': Decimal('0.00'),
                    'total_services': 0,
                    'is_paid': False
                }
            )
            
            # Recalcular totales desde la DB
            earnings_data = Earning.objects.filter(
                employee=self.employee,
                fortnight_year=self.fortnight_year,
                fortnight_number=self.fortnight_number
            ).aggregate(
                total_amount=Sum('amount'),
                total_count=Count('id')
            )
            
            summary.total_earnings = earnings_data['total_amount'] or Decimal('0.00')
            summary.total_services = earnings_data['total_count'] or 0
            summary.save()
    
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
    
    # Descuentos legales (República Dominicana)
    afp_deduction = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text="Descuento AFP (2.87%)"
    )
    sfs_deduction = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text="Descuento SFS (3.04%)"
    )
    isr_deduction = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text="Descuento ISR (según escala)"
    )
    total_deductions = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text="Total de descuentos legales"
    )
    net_salary = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text="Salario neto después de descuentos"
    )
    
    payment_reference = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="Referencia bancaria o número de cheque"
    )
    payment_notes = models.TextField(
        null=True, blank=True,
        help_text="Notas adicionales del pago"
    )
    
    # Campo para pagos anticipados
    is_advance_payment = models.BooleanField(
        default=False,
        help_text="Indica si este pago fue realizado antes de la fecha correspondiente"
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
    
    @property
    def period_dates(self):
        """Obtiene fechas de inicio y fin del período"""
        from datetime import datetime, timedelta
        
        if not self.fortnight_number or not self.fortnight_year:
            return None, None
        
        month = ((self.fortnight_number - 1) // 2) + 1
        is_first_half = (self.fortnight_number % 2) == 1
        
        if is_first_half:
            start_date = datetime(self.fortnight_year, month, 1).date()
            end_date = datetime(self.fortnight_year, month, 15).date()
        else:
            start_date = datetime(self.fortnight_year, month, 16).date()
            if month == 12:
                next_month = datetime(self.fortnight_year + 1, 1, 1)
            else:
                next_month = datetime(self.fortnight_year, month + 1, 1)
            end_date = (next_month - timedelta(days=1)).date()
        
        return start_date, end_date
    
    @property
    def payment_status(self):
        """Estado derivado del período de pago"""
        if self.is_paid:
            return 'paid'
        
        start_date, end_date = self.period_dates
        if not end_date:
            return 'unknown'
        
        today = timezone.now().date()
        
        if today <= end_date:
            return 'in_progress'
        elif today > end_date:
            # Considerar atrasado después de 7 días
            days_overdue = (today - end_date).days
            if days_overdue > 7:
                return 'overdue'
            else:
                return 'due'
        
        return 'unknown'
    
    @property
    def payment_status_display(self):
        """Texto amigable para el estado de pago"""
        status = self.payment_status
        start_date, end_date = self.period_dates
        
        if status == 'paid':
            if self.paid_at:
                return f"Pagado el {self.paid_at.strftime('%d/%m/%Y')}"
            return "Pagado"
        elif status == 'in_progress':
            return "Período en curso"
        elif status == 'due':
            if end_date:
                return f"Pago pendiente (desde {end_date.strftime('%d/%m/%Y')})"
            return "Pago pendiente"
        elif status == 'overdue':
            if end_date:
                days_overdue = (timezone.now().date() - end_date).days
                return f"Pago atrasado ({days_overdue} días)"
            return "Pago atrasado"
        
        return "Estado desconocido"
    
    @property
    def period_display(self):
        """Muestra el período trabajado en formato legible"""
        start_date, end_date = self.period_dates
        if start_date and end_date:
            return f"{start_date.strftime('%d')}-{end_date.strftime('%d %b %Y')}"
        return self.fortnight_display
    
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

class PeriodSummary(models.Model):
    """Resumen de ganancias por período (multifrecuencia)"""
    
    FREQUENCY_CHOICES = [
        ('daily', 'Diario'),
        ('weekly', 'Semanal'),
        ('biweekly', 'Quincenal'),
        ('monthly', 'Mensual')
    ]
    
    employee = models.ForeignKey(
        'employees_api.Employee',
        on_delete=models.CASCADE,
        related_name='period_summaries'
    )
    
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    period_start = models.DateField()
    period_end = models.DateField()
    period_year = models.IntegerField()
    period_index = models.IntegerField()  # 1-365 daily, 1-52 weekly, 1-24 biweekly, 1-12 monthly
    
    total_earnings = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_services = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
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
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_reference = models.CharField(max_length=100, null=True, blank=True)
    payment_notes = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('employee', 'frequency', 'period_year', 'period_index')
        ordering = ['-period_year', '-period_index']
        indexes = [
            models.Index(fields=['employee', 'frequency', 'period_year', 'period_index']),
            models.Index(fields=['is_paid']),
        ]
    
    def __str__(self):
        return f"{self.employee} - {self.frequency} {self.period_year}/{self.period_index} - ${self.total_earnings}"

class PayrollBatch(models.Model):
    """Lotes de nómina para procesamiento masivo"""
    
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('approved', 'Aprobado'),
        ('processing', 'Procesando'),
        ('completed', 'Completado'),
        ('failed', 'Fallido')
    ]
    
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE, related_name='payroll_batches')
    batch_number = models.CharField(max_length=50, unique=True)
    period_start = models.DateField()
    period_end = models.DateField()
    frequency = models.CharField(max_length=10, choices=PeriodSummary.FREQUENCY_CHOICES)
    
    total_employees = models.IntegerField(default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Tracking fields
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_payroll_batches'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Task tracking
    task_id = models.CharField(max_length=100, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['batch_number']),
            models.Index(fields=['created_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.batch_number:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            short_uuid = str(uuid.uuid4())[:8]
            self.batch_number = f"{timestamp}-{short_uuid}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Batch {self.batch_number} - {self.status}"

class PayrollBatchItem(models.Model):
    """Items individuales dentro de un lote de nómina"""
    
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('paid', 'Pagado'),
        ('failed', 'Fallido')
    ]
    
    batch = models.ForeignKey(PayrollBatch, on_delete=models.CASCADE, related_name='items')
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE)
    period_summary = models.ForeignKey(PeriodSummary, on_delete=models.CASCADE, null=True, blank=True)
    
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Desglose de descuentos legales
    afp_deduction = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text="AFP (2.87%)"
    )
    sfs_deduction = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text="SFS (3.04%)"
    )
    isr_deduction = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text="ISR (según escala)"
    )
    
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    external_ref = models.CharField(max_length=100, null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['batch', 'employee']
        indexes = [
            models.Index(fields=['batch', 'status']),
            models.Index(fields=['employee']),
        ]
    
    def __str__(self):
        return f"{self.batch.batch_number} - {self.employee.user.full_name} - ${self.net_amount}"