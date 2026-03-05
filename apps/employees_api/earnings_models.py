from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime, timedelta
from decimal import Decimal

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
    
    # Alias para compatibilidad con código existente
    LEGACY_STATUS_MAP = {
        'ready': 'approved',  # ready se mapea a approved
    }
    
    employee = models.ForeignKey(
        'employees_api.Employee',
        on_delete=models.CASCADE,
        related_name='payroll_periods'
    )
    
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPE_CHOICES, default='biweekly')
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Snapshots de compensación (determinismo)
    payment_type_snapshot = models.CharField(max_length=10, null=True, blank=True, help_text='Tipo de pago vigente al crear período')
    fixed_salary_snapshot = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Salario fijo vigente al crear período')
    
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    commission_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    deductions_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Snapshot inmutable del cálculo (se guarda al aprobar)
    calculation_snapshot = models.JSONField(null=True, blank=True, help_text='Snapshot del cálculo al momento de aprobación')
    
    # FASE 3: Flag de finalización (Payroll Determinístico)
    is_finalized = models.BooleanField(
        default=False,
        help_text='Indica si el período está finalizado y no debe recalcularse'
    )
    
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
            models.Index(fields=['employee']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'period_start', 'period_end'],
                name='unique_employee_period'
            )
        ]
    
    def save(self, *args, **kwargs):
        """Override save para proteger períodos aprobados/pagados"""
        from django.core.exceptions import ValidationError
        
        # Permitir creación inicial
        if self.pk is None:
            # Capturar snapshots de compensación al crear
            if not self.payment_type_snapshot:
                self.payment_type_snapshot = self.employee.payment_type
            if not self.fixed_salary_snapshot:
                self.fixed_salary_snapshot = self.employee.fixed_salary
            return super().save(*args, **kwargs)
        
        # Verificar si existe instancia anterior
        try:
            old_instance = PayrollPeriod.objects.get(pk=self.pk)
        except PayrollPeriod.DoesNotExist:
            return super().save(*args, **kwargs)
        
        # FIX 1: SNAPSHOTS INMUTABLES
        if old_instance.payment_type_snapshot != self.payment_type_snapshot:
            raise ValidationError("No se puede modificar payment_type_snapshot")
        if old_instance.fixed_salary_snapshot != self.fixed_salary_snapshot:
            raise ValidationError("No se puede modificar fixed_salary_snapshot")
        # Permitir establecer snapshot por primera vez durante aprobación.
        # Tratar snapshot vacío ({}) como no inicializado.
        old_snapshot = old_instance.calculation_snapshot
        had_real_snapshot = old_snapshot not in (None, {}, [])
        if had_real_snapshot and old_snapshot != self.calculation_snapshot:
            raise ValidationError("No se puede modificar calculation_snapshot")
        
        # FIX 3: is_finalized BLOQUEA TODO
        if old_instance.is_finalized:
            # Solo permitir cambios administrativos mínimos
            allowed_when_finalized = {
                'payment_method',
                'payment_reference',
                'paid_at',
                'paid_by',
                'notification_sent',
                'notification_sent_at',
                'updated_at',
            }
            
            for field in self._meta.fields:
                field_name = field.name
                if field_name in allowed_when_finalized:
                    continue
                
                old_value = getattr(old_instance, field_name)
                new_value = getattr(self, field_name)
                
                if old_value != new_value:
                    raise ValidationError(
                        f"No se puede modificar '{field_name}' en un período finalizado"
                    )
        
        # FIX 2: BLOQUEO TOTAL POST-APPROVED/PAID
        if old_instance.status in ['approved', 'paid']:
            # Campos permitidos para cambiar
            allowed_changes = {
                'status',
                'payment_method',
                'payment_reference',
                'paid_at',
                'paid_by',
                'notification_sent',
                'notification_sent_at',
                'updated_at',
            }
            
            # Validar explícitamente campos financieros
            if old_instance.base_salary != self.base_salary:
                raise ValidationError("No se puede modificar base_salary en período aprobado/pagado")
            if old_instance.commission_earnings != self.commission_earnings:
                raise ValidationError("No se puede modificar commission_earnings en período aprobado/pagado")
            if old_instance.gross_amount != self.gross_amount:
                raise ValidationError("No se puede modificar gross_amount en período aprobado/pagado")
            if old_instance.deductions_total != self.deductions_total:
                raise ValidationError("No se puede modificar deductions_total en período aprobado/pagado")
            if old_instance.net_amount != self.net_amount:
                raise ValidationError("No se puede modificar net_amount en período aprobado/pagado")
            
            # Detectar cambios en campos protegidos
            protected_fields_changed = []
            for field in self._meta.fields:
                field_name = field.name
                if field_name in allowed_changes:
                    continue
                
                old_value = getattr(old_instance, field_name)
                new_value = getattr(self, field_name)
                
                if old_value != new_value:
                    protected_fields_changed.append(field_name)
            
            if protected_fields_changed:
                raise ValidationError(
                    f"No se puede modificar un período con status '{old_instance.status}'. "
                    f"Campos protegidos: {', '.join(protected_fields_changed)}"
                )
            
            # Validar transiciones de estado permitidas
            if old_instance.status != self.status:
                allowed_transitions = {
                    'approved': ['paid'],
                    'paid': [],
                }
                
                if self.status not in allowed_transitions.get(old_instance.status, []):
                    raise ValidationError(
                        f"Transición de estado no permitida: '{old_instance.status}' -> '{self.status}'"
                    )
        
        return super().save(*args, **kwargs)
    
    def calculate_amounts(self):
        """Calcula montos del período usando snapshots (Payroll Determinístico)
        
        IDEMPOTENTE: Puede llamarse múltiples veces sin efectos secundarios.
        Solo actualiza campos de cálculo, no modifica estado.
        """
        
        # PROTECCIÓN: Si está finalizado, NO recalcular
        if hasattr(self, 'is_finalized') and self.is_finalized:
            return
        
        # PROTECCIÓN: Si ya está aprobado/pagado y tiene snapshot, no recalcular
        if self.status in ['approved', 'paid'] and self.calculation_snapshot:
            return
        
        # FIX 3: Bloquear recalcular si está finalizado
        if self.status in ['approved', 'paid']:
            return
        
        # NUEVO: Usar servicio de cálculo desde snapshots
        try:
            from apps.employees_api.payroll_services import PayrollCalculationService
            
            calculation = PayrollCalculationService.calculate_from_snapshots(self)
            
            # Aplicar resultados (IDEMPOTENTE: solo asigna valores)
            self.base_salary = calculation['base_salary']
            self.commission_earnings = calculation['commission_earnings']
            self.gross_amount = calculation['gross_amount']
            
            # Calcular deducciones y neto
            deductions = self.deductions.all()
            self.deductions_total = sum(d.amount for d in deductions)
            self.net_amount = self.gross_amount - self.deductions_total
            
        except ImportError:
            # Fallback a lógica antigua si el servicio no existe aún
            employee = self.employee
            
            # Calcular salario base según tipo de pago y período
            if employee.payment_type in ['fixed', 'mixed']:
                if self.period_type == 'monthly':
                    self.base_salary = employee.fixed_salary
                elif self.period_type == 'biweekly':
                    self.base_salary = employee.fixed_salary / 2
                elif self.period_type == 'weekly':
                    self.base_salary = employee.fixed_salary / 4
            else:
                self.base_salary = Decimal('0.00')
            
            # Calcular comisiones desde las ventas del período
            if employee.payment_type in ['commission', 'mixed']:
                from apps.pos_api.models import Sale
                sales = Sale.objects.filter(
                    employee=employee,
                    date_time__date__gte=self.period_start,
                    date_time__date__lte=self.period_end
                )
                total_sales = sum(sale.total for sale in sales)
                commission_rate = employee.commission_rate / 100
                self.commission_earnings = Decimal(str(total_sales)) * Decimal(str(commission_rate))
            else:
                self.commission_earnings = Decimal('0.00')
            
            # Calcular totales
            self.gross_amount = self.base_salary + self.commission_earnings
            deductions = self.deductions.all()
            self.deductions_total = sum(d.amount for d in deductions)
            self.net_amount = self.gross_amount - self.deductions_total
        
        # Validar si se puede pagar
        if self.status == 'open':
            self.can_pay = False
            self.pay_block_reason = "El período aún está abierto"
        elif self.status == 'pending_approval':
            self.can_pay = False
            self.pay_block_reason = "El período está pendiente de aprobación"
        elif self.net_amount <= 0:
            self.can_pay = False
            self.pay_block_reason = "El monto neto es cero o negativo"
        else:
            self.can_pay = True
            self.pay_block_reason = None
    
    def _create_calculation_snapshot(self):
        """Crea snapshot inmutable del cálculo al aprobar"""
        from apps.pos_api.models import Sale
        
        # Obtener ventas del período
        sales = Sale.objects.filter(
            employee=self.employee,
            date_time__date__gte=self.period_start,
            date_time__date__lte=self.period_end
        ).values('id', 'total', 'date_time')
        
        self.calculation_snapshot = {
            'calculated_at': timezone.now().isoformat(),
            'employee': {
                'id': self.employee.id,
                'payment_type': self.employee.payment_type,
                'fixed_salary': float(self.employee.fixed_salary),
                'commission_rate': float(self.employee.commission_rate)
            },
            'period': {
                'type': self.period_type,
                'start': self.period_start.isoformat(),
                'end': self.period_end.isoformat()
            },
            'calculation': {
                'base_salary': float(self.base_salary),
                'commission_earnings': float(self.commission_earnings),
                'gross_amount': float(self.gross_amount),
                'deductions_total': float(self.deductions_total),
                'net_amount': float(self.net_amount)
            },
            'sales': [
                {
                    'id': sale['id'],
                    'total': float(sale['total']),
                    'date': sale['date_time'].isoformat()
                } for sale in sales
            ],
            'sales_count': len(sales),
            'total_sales': float(sum(sale['total'] for sale in sales))
        }
    
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
        
        # Calcular montos finales antes de aprobar.
        self.calculate_amounts()

        # Regla de negocio: no se permite aprobar períodos con neto <= 0.
        if self.net_amount <= 0 or not self.can_pay:
            raise ValueError(self.pay_block_reason or "No se puede aprobar un período con monto neto cero o negativo")

        # Respetar inmutabilidad: si ya existe snapshot, no reescribirlo.
        if self.calculation_snapshot in (None, {}, []):
            self._create_calculation_snapshot()
        
        self.status = 'approved'
        self.approved_at = timezone.now()
        self.approved_by = approved_by
        self.is_finalized = True  # NUEVO: Finalizar al aprobar
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
        self.is_finalized = True  # NUEVO: Asegurar finalización
        self.save()
    
    @property
    def period_display(self):
        return f"{self.period_start.strftime('%d/%m/%Y')} - {self.period_end.strftime('%d/%m/%Y')}"
    
    def delete(self, *args, **kwargs):
        """FIX 5: Bloquear hard delete de períodos aprobados/pagados"""
        from django.core.exceptions import ValidationError
        
        if self.status in ['approved', 'paid']:
            raise ValidationError(
                f"No se puede eliminar un período con status '{self.status}'. "
                "Use soft delete si es necesario."
            )
        
        super().delete(*args, **kwargs)
    
    def __str__(self):
        return f"{self.employee} - {self.period_display} - {self.status}"


class PayrollDeduction(models.Model):
    """Deducciones de nómina"""
    
    DEDUCTION_TYPE_CHOICES = [
        ('tax', 'Impuesto'),
        ('social_security', 'Seguro Social'),
        ('health_insurance', 'Seguro Médico'),
        ('advance', 'Anticipo de Sueldo'),
        ('loan', 'Préstamo Personal'),
        ('emergency_loan', 'Préstamo de Emergencia'),
        ('other', 'Otro'),
    ]
    
    period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE, related_name='deductions')
    deduction_type = models.CharField(max_length=20, choices=DEDUCTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    description = models.TextField(blank=True)
    installments = models.IntegerField(default=1, validators=[MinValueValidator(1)], help_text='Número de cuotas para el préstamo')
    is_automatic = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['deduction_type']
        indexes = [
            models.Index(fields=['period']),
        ]
    
    def __str__(self):
        return f"{self.get_deduction_type_display()} - ${self.amount}"
    
    def save(self, *args, **kwargs):
        """FIX 4: Hacer PayrollDeduction inmutable después de creación"""
        from django.core.exceptions import ValidationError
        
        if self.pk is not None:
            # Bloquear modificación de campos críticos
            original = PayrollDeduction.objects.get(pk=self.pk)
            
            if original.amount != self.amount:
                raise ValidationError("No se puede modificar el monto de una deducción")
            
            if original.deduction_type != self.deduction_type:
                raise ValidationError("No se puede modificar el tipo de deducción")
            
            # Validar que el período no esté finalizado
            if hasattr(self.period, 'is_finalized') and self.period.is_finalized:
                raise ValidationError("No se puede modificar una deducción de un período finalizado")
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """FIX 4: Bloquear eliminación si período está finalizado"""
        from django.core.exceptions import ValidationError
        
        if hasattr(self.period, 'is_finalized') and self.period.is_finalized:
            raise ValidationError("No se puede eliminar una deducción de un período finalizado")
        
        super().delete(*args, **kwargs)


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
