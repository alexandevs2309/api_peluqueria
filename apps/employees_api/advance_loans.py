from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import date, timedelta
from .models import Employee

class AdvanceLoan(models.Model):
    LOAN_TYPES = [
        ('advance', 'Anticipo de Sueldo'),
        ('personal_loan', 'Préstamo Personal'),
        ('emergency', 'Préstamo de Emergencia')
    ]
    
    STATUS_CHOICES = [
        ('active', 'Activo'),
        ('completed', 'Completado'),
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
        """Sin límites - siempre puede solicitar préstamos"""
        return True

class LoanPayment(models.Model):
    loan = models.ForeignKey(AdvanceLoan, on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_number = models.IntegerField()
    
    # Referencia al pago de nómina
    payroll_payment = models.ForeignKey('FortnightSummary', on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['payment_number']
        unique_together = ['loan', 'payment_number']

def process_loan_deductions(employee, payment_amount, fortnight_summary):
    """Procesa deducciones de préstamos - puede generar saldos negativos"""
    active_loans = AdvanceLoan.objects.filter(
        employee=employee,
        status='active',
        remaining_balance__gt=0
    ).order_by('first_payment_date')
    
    total_deductions = Decimal('0')
    
    for loan in active_loans:
        # Sin límites - deducir todo lo que se pueda
        deduction = min(loan.monthly_payment, loan.remaining_balance)
        
        # Crear pago del préstamo
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
        if loan.remaining_balance <= 0:
            loan.status = 'completed'
        loan.save()
        
        total_deductions += deduction
    
    return total_deductions