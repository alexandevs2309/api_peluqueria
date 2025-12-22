from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import transaction
from decimal import Decimal
from datetime import date, timedelta
from .models import Employee
from .payroll_models import PayrollPayment
import logging

logger = logging.getLogger(__name__)

class AdvanceLoan(models.Model):
    LOAN_TYPES = [
        ('advance', 'Anticipo de Sueldo'),
        ('personal_loan', 'Préstamo Personal'),
        ('emergency', 'Préstamo de Emergencia')
    ]
    
    STATUS_CHOICES = [
        ('active', 'Activo'),
        ('completed', 'Completado'),
        ('pending_cancellation', 'Cancelación Pendiente'),
        ('cancelled', 'Cancelado')
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='advance_loans')
    loan_type = models.CharField(max_length=20, choices=LOAN_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Términos del préstamo
    installments = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # % anual
    
    # Fechas
    request_date = models.DateField(auto_now_add=True)
    approval_date = models.DateField(null=True, blank=True)
    first_payment_date = models.DateField(null=True, blank=True)
    
    # Aprobación
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    approval_notes = models.TextField(blank=True)
    
    # Cancelación
    cancellation_requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='requested_cancellations')
    cancellation_reason = models.TextField(blank=True)
    cancellation_requested_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_loans')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Cálculos
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monthly_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remaining_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if self.status == 'active' and not self.total_amount:
            self.calculate_loan_terms()
        super().save(*args, **kwargs)
    
    def calculate_loan_terms(self):
        """Calcula términos del préstamo"""
        if self.interest_rate > 0:
            monthly_rate = self.interest_rate / 100 / 12
            if monthly_rate > 0:
                # Fórmula de cuota fija con interés
                factor = (monthly_rate * (1 + monthly_rate) ** self.installments) / ((1 + monthly_rate) ** self.installments - 1)
                self.monthly_payment = self.amount * factor
                self.total_amount = self.monthly_payment * self.installments
            else:
                self.monthly_payment = self.amount / self.installments
                self.total_amount = self.amount
        else:
            self.monthly_payment = self.amount / self.installments
            self.total_amount = self.amount
        
        self.remaining_balance = self.total_amount
    
    def can_request_new_loan(self):
        """Sin límites - siempre puede solicitar préstamos
        
        REGLA DE NEGOCIO ACTUAL: No hay restricciones de límites.
        Esta política está definida por el negocio y NO debe cambiarse aquí.
        """
        return True
    
    def validate_balance_consistency(self):
        """Validar consistencia entre remaining_balance y suma de pagos
        
        NO MODIFICA DATOS - Solo valida consistencia interna.
        Útil para detectar corrupción de datos.
        """
        total_paid = sum(payment.amount for payment in self.payments.all())
        expected_balance = self.total_amount - total_paid
        
        # Tolerancia de 0.01 por redondeos decimales
        if abs(self.remaining_balance - expected_balance) > Decimal('0.01'):
            logger.warning(
                f"Inconsistencia detectada en préstamo {self.id}: "
                f"remaining_balance={self.remaining_balance}, "
                f"esperado={expected_balance}"
            )
            return False
        return True

class LoanPayment(models.Model):
    """Registro de pago individual de un préstamo
    
    INVARIANTES:
    - payment_number debe ser secuencial por préstamo
    - amount debe ser > 0
    - payment_date no puede ser futuro
    """
    loan = models.ForeignKey(AdvanceLoan, on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    payment_number = models.IntegerField(validators=[MinValueValidator(1)])
    
    # Referencia al pago de nómina (mantener compatibilidad)
    payroll_payment = models.ForeignKey('FortnightSummary', on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['payment_number']
        unique_together = ['loan', 'payment_number']

class LoanDeduction(models.Model):
    """Registro de deducción real de préstamo en un pago
    
    Este modelo registra las deducciones REALES aplicadas en pagos.
    Separado de LoanPayment para mayor claridad y trazabilidad.
    """
    
    # Referencia al pago de nómina
    payroll_payment = models.ForeignKey(
        'PayrollPayment',
        on_delete=models.CASCADE,
        related_name='deducted_loans'
    )
    
    # Referencia al préstamo
    loan = models.ForeignKey(
        AdvanceLoan,
        on_delete=models.CASCADE,
        related_name='deductions'
    )
    
    # Monto deducido
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Balance del préstamo después de la deducción
    loan_balance_after = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payroll_payment']),
            models.Index(fields=['loan']),
        ]
    
    def __str__(self):
        return f"Deducción ${self.amount} - Préstamo {self.loan.id} - Pago {self.payroll_payment.payment_id}"

@transaction.atomic
def process_loan_deductions(employee, payment_amount, fortnight_summary):
    """Procesa deducciones de préstamos
    
    REGLAS DE NEGOCIO ACTUALES (NO MODIFICAR):
    - Orden: FIFO por first_payment_date (préstamos más antiguos primero)
    - Límite: Sin límites - descuenta monthly_payment o remaining_balance
    - Política: Automático cuando se llama esta función
    
    GARANTÍAS:
    - Operación atómica (rollback completo en caso de error)
    - Consistencia de remaining_balance
    - Secuencia correcta de payment_number
    
    Args:
        employee: Empleado con préstamos activos
        payment_amount: Monto del pago (NO USADO actualmente, mantener por compatibilidad)
        fortnight_summary: Referencia al pago de nómina
    
    Returns:
        Decimal: Total deducido de todos los préstamos
    """
    # REGLA EXPLÍCITA: Orden FIFO por fecha de primer pago
    active_loans = AdvanceLoan.objects.select_for_update().filter(
        employee=employee,
        status='active',
        remaining_balance__gt=0
    ).order_by('first_payment_date')
    
    total_deductions = Decimal('0')
    
    for loan in active_loans:
        # REGLA EXPLÍCITA: Descuento = min(cuota mensual, saldo restante)
        # "Sin límites" significa que NO hay límite de porcentaje del salario
        deduction = min(loan.monthly_payment, loan.remaining_balance)
        
        # Validación interna: deduction debe ser positivo
        assert deduction > 0, f"Deducción inválida para préstamo {loan.id}"
        
        # Crear pago del préstamo con número secuencial
        payment_number = loan.payments.count() + 1
        LoanPayment.objects.create(
            loan=loan,
            payment_date=date.today(),
            amount=deduction,
            payment_number=payment_number,
            payroll_payment=fortnight_summary
        )
        
        # Actualizar balance
        loan.remaining_balance -= deduction
        
        # REGLA EXPLÍCITA: Préstamo se marca 'completed' cuando saldo <= 0
        if loan.remaining_balance <= 0:
            loan.status = 'completed'
        
        loan.save()
        
        # Validación post-operación (NO cambia comportamiento)
        if loan.remaining_balance < 0:
            logger.warning(
                f"Préstamo {loan.id} tiene saldo negativo: {loan.remaining_balance}. "
                "Esto puede indicar un problema de redondeo."
            )
        
        total_deductions += deduction
    
    return total_deductions