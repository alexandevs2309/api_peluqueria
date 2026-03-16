from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator


class EmployeeCompensationHistory(models.Model):
    """Historial inmutable de condiciones de compensación del empleado"""
    
    employee = models.ForeignKey(
        'employees_api.Employee',
        on_delete=models.CASCADE,
        related_name='compensation_history'
    )
    
    # Snapshot de condiciones
    payment_type = models.CharField(
        max_length=10,
        choices=[
            ('fixed', 'Sueldo Fijo'),
            ('commission', 'Comisión'),
            ('mixed', 'Mixto (Sueldo + Comisión)')
        ]
    )
    fixed_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )
    
    # Vigencia
    effective_date = models.DateField(
        help_text='Fecha desde la cual aplican estas condiciones'
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha hasta la cual aplicaron estas condiciones (null = vigente)'
    )
    
    # Auditoría
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='compensation_changes_created'
    )
    created_at = models.DateTimeField(default=timezone.now)
    change_reason = models.TextField(blank=True)
    
    # Snapshot adicional del empleado
    employee_snapshot = models.JSONField(
        default=dict,
        help_text='Snapshot completo del empleado al momento del cambio'
    )
    
    class Meta:
        ordering = ['-effective_date', '-created_at']
        indexes = [
            models.Index(fields=['employee', 'effective_date']),
            models.Index(fields=['employee', 'end_date']),
            models.Index(fields=['effective_date']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__isnull=True) | models.Q(end_date__gte=models.F('effective_date')),
                name='valid_date_range'
            )
        ]
    
    def __str__(self):
        return f"{self.employee} - {self.payment_type} - {self.effective_date}"
    
    def save(self, *args, **kwargs):
        # Inmutabilidad: solo permitir creación
        if self.pk is not None:
            raise ValueError("EmployeeCompensationHistory es inmutable. No se puede modificar.")
        
        # Crear snapshot del empleado
        if not self.employee_snapshot:
            self.employee_snapshot = {
                'employee_id': self.employee.id,
                'user_email': self.employee.user.email,
                'user_full_name': self.employee.user.full_name,
                'specialty': self.employee.specialty,
                'hire_date': self.employee.hire_date.isoformat() if self.employee.hire_date else None,
                'is_active': self.employee.is_active,
                'tenant_id': self.employee.tenant_id,
                'tenant_name': self.employee.tenant.name if self.employee.tenant else None,
            }
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Prevenir eliminación
        raise ValueError("EmployeeCompensationHistory no se puede eliminar. Es un registro histórico inmutable.")
    
    @classmethod
    def get_active_compensation(cls, employee, date=None):
        """Obtener compensación vigente para una fecha específica"""
        if date is None:
            date = timezone.now().date()
        
        return cls.objects.filter(
            employee=employee,
            effective_date__lte=date
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=date)
        ).first()
    
    @classmethod
    def create_from_employee(cls, employee, effective_date, created_by, change_reason=''):
        """Crear registro de historial desde estado actual del empleado"""
        
        # Cerrar registro anterior si existe
        previous = cls.objects.filter(
            employee=employee,
            end_date__isnull=True
        ).first()
        
        if previous and previous.effective_date < effective_date:
            # No modificar el registro, crear uno nuevo con end_date
            # Esto mantiene inmutabilidad pero requiere lógica especial
            pass
        
        # Crear nuevo registro
        return cls.objects.create(
            employee=employee,
            payment_type=employee.payment_type,
            fixed_salary=employee.fixed_salary,
            commission_rate=employee.commission_rate,
            effective_date=effective_date,
            created_by=created_by,
            change_reason=change_reason
        )
