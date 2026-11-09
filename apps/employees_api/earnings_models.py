from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime, timedelta
from decimal import Decimal

# ============================================
# TABLAS FISCALES VERSIONADAS (ISR)
# ============================================

class FiscalTable(models.Model):
    """Tabla fiscal versionada por ejercicio y fecha de vigencia."""
    fiscal_year = models.IntegerField(help_text='Año fiscal')
    effective_date = models.DateField(help_text='Fecha de vigencia')
    exemption_annual = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    exemption_monthly = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    source = models.CharField(max_length=255, default='DGII')
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fiscal_year', '-effective_date', '-version']
        unique_together = ('fiscal_year', 'version')

    def calculate_isr(self, annual_income):
        """Calcula ISR anual según la escala de esta tabla."""
        annual_income = Decimal(str(annual_income or 0))
        if annual_income <= self.exemption_annual:
            return Decimal('0.00')
        tax = Decimal('0.00')
        for bracket in self.brackets.order_by('order'):
            if bracket.max_amount is None or annual_income <= bracket.max_amount:
                taxable = annual_income - bracket.min_amount
                tax = bracket.base_amount + (taxable * bracket.rate / 100)
                break
            # if annual_income exceeds this bracket, continue
        return tax.quantize(Decimal('0.01'))

    @classmethod
    def get_for_year(cls, fiscal_year):
        obj = cls.objects.filter(fiscal_year=fiscal_year).order_by('-version').first()
        if obj is None:
            obj = cls.objects.filter(fiscal_year__lte=fiscal_year).order_by('-fiscal_year', '-version').first()
        if obj is None:
            # Seed defaults if no fiscal table exists (e.g., test env without migrations)
            import datetime
            from decimal import Decimal
            obj = cls.objects.create(
                fiscal_year=fiscal_year,
                effective_date=datetime.date(fiscal_year, 1, 1),
                exemption_annual=Decimal('416220.00') if fiscal_year <= 2026 else Decimal('480000.00'),
                exemption_monthly=Decimal('34685.00') if fiscal_year <= 2026 else Decimal('40000.00'),
                source='DGII',
                version=1,
            )
            if fiscal_year <= 2026:
                FiscalBracket.objects.create(fiscal_table=obj, min_amount=Decimal('0.00'), max_amount=Decimal('416220.00'), rate=Decimal('0.00'), base_amount=Decimal('0.00'), order=0)
                FiscalBracket.objects.create(fiscal_table=obj, min_amount=Decimal('416220.01'), max_amount=Decimal('624329.00'), rate=Decimal('15.00'), base_amount=Decimal('0.00'), order=1)
                FiscalBracket.objects.create(fiscal_table=obj, min_amount=Decimal('624329.01'), max_amount=Decimal('867123.00'), rate=Decimal('20.00'), base_amount=Decimal('31216.00'), order=2)
                FiscalBracket.objects.create(fiscal_table=obj, min_amount=Decimal('867123.01'), max_amount=None, rate=Decimal('25.00'), base_amount=Decimal('79776.00'), order=3)
            else:
                FiscalBracket.objects.create(fiscal_table=obj, min_amount=Decimal('0.00'), max_amount=Decimal('480000.00'), rate=Decimal('0.00'), base_amount=Decimal('0.00'), order=0)
                FiscalBracket.objects.create(fiscal_table=obj, min_amount=Decimal('480000.01'), max_amount=Decimal('624329.00'), rate=Decimal('15.00'), base_amount=Decimal('0.00'), order=1)
                FiscalBracket.objects.create(fiscal_table=obj, min_amount=Decimal('624329.01'), max_amount=Decimal('867123.00'), rate=Decimal('20.00'), base_amount=Decimal('31216.00'), order=2)
                FiscalBracket.objects.create(fiscal_table=obj, min_amount=Decimal('867123.01'), max_amount=None, rate=Decimal('27.00'), base_amount=Decimal('79776.00'), order=3)
        return obj


class FiscalBracket(models.Model):
    """Tramo de una tabla fiscal."""
    fiscal_table = models.ForeignKey(FiscalTable, on_delete=models.CASCADE, related_name='brackets')
    min_amount = models.DecimalField(max_digits=12, decimal_places=2)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    rate = models.DecimalField(max_digits=5, decimal_places=2, help_text='Porcentaje')
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'min_amount']

    def __str__(self):
        return f"{self.min_amount} - {self.max_amount or chr(8734)} @ {self.rate}%"


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
    commission_rate_snapshot = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Porcentaje de comisión vigente al crear período'
    )
    
    christmas_bonus = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text='Bono navideño (importe manual o calculado)'
    )

    # Aportes patronales (costo laboral, no deducción del empleado)
    employer_sfs = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    employer_afp = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    employer_srl = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    employer_infotep = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    employer_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

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
            if not self.commission_rate_snapshot:
                self.commission_rate_snapshot = self.employee.commission_rate
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
        if old_instance.commission_rate_snapshot != self.commission_rate_snapshot:
            raise ValidationError("No se puede modificar commission_rate_snapshot")
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
                'status',  # Permitir transición approved -> paid
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
                'employer_sfs',
                'employer_afp',
                'employer_srl',
                'employer_infotep',
                'employer_total',
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
            if old_instance.christmas_bonus != self.christmas_bonus:
                raise ValidationError("No se puede modificar christmas_bonus en período aprobado/pagado")
            if old_instance.employer_total != self.employer_total:
                raise ValidationError("No se puede modificar employer_total en período aprobado/pagado")
            
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

        # 1. Eliminar deducciones automáticas anteriores para este periodo
        # para que al recalcular no se dupliquen (identificadas por source)
        self.deductions.filter(is_automatic=True, source='auto_attendance').delete()
        
        # 2. Calcular deducciones automáticas por asistencia tardía / inasistencia
        employee = self.employee
        if employee.payment_type in ['fixed', 'mixed']:
            from .models import AttendanceRecord
            attendances = AttendanceRecord.objects.filter(
                employee=employee,
                work_date__gte=self.period_start,
                work_date__lte=self.period_end,
                is_justified=False
            )
            
            minutes_late = 0
            days_absent = 0
            for att in attendances:
                if att.status == 'late':
                    if att.late_minutes > 0:
                        minutes_late += att.late_minutes
                    elif att.notes and "Retraso de" in att.notes:
                        # Legacy fallback: read from notes for old records without late_minutes
                        try:
                            minutes_late += int(att.notes.split("Retraso de ")[1].split(" minutos")[0])
                        except Exception:
                            minutes_late += 30
                    else:
                        minutes_late += 30
                elif att.status == 'absent':
                    days_absent += 1
            
            fixed_salary = employee.fixed_salary
            if fixed_salary > 0:
                salary_daily = Decimal(str(fixed_salary)) / Decimal('23.83')
                value_minute = salary_daily / Decimal('480.0') # 8h * 60m
                
                if minutes_late > 0:
                    amount_late = (Decimal(minutes_late) * value_minute).quantize(Decimal('0.01'))
                    if amount_late > 0:
                        PayrollDeduction.objects.create(
                            period=self,
                            deduction_type='other',
                            amount=amount_late,
                            description=f"[Asistencia] Deducción por tardanza acumulada ({minutes_late} minutos)",
                            is_automatic=True,
                            source='auto_attendance',
                        )
                
                if days_absent > 0:
                    amount_absent = (Decimal(days_absent) * salary_daily).quantize(Decimal('0.01'))
                    if amount_absent > 0:
                        PayrollDeduction.objects.create(
                            period=self,
                            deduction_type='other',
                            amount=amount_absent,
                            description=f"[Asistencia] Deducción por inasistencia ({days_absent} días)",
                            is_automatic=True,
                            source='auto_attendance',
                        )

        # Auto-deduct active loan installments (Bug 3)
        self.deductions.filter(
            is_automatic=True,
            source='auto_loan',
        ).delete()

        from apps.employees_api.models import Loan
        active_loans = Loan.objects.filter(
            employee=employee,
            status='active',
            remaining_balance__gt=Decimal('0.00')
        )

        for loan in active_loans:
            if loan.installments > 0 and loan.amount > 0:
                installment_amount = (loan.amount / loan.installments).quantize(
                    Decimal('0.01')
                )
                installment_amount = min(installment_amount, loan.remaining_balance)

                if installment_amount > 0:
                    PayrollDeduction.objects.create(
                        period=self,
                        deduction_type='loan',
                        amount=installment_amount,
                        description=f"[Préstamo] Cuota automática — {loan.description or 'Préstamo #' + str(loan.id)}",
                        is_automatic=True,
                        source='auto_loan',
                        loan=loan,
                    )
        
        try:
            from apps.employees_api.payroll_services import PayrollCalculationService

            calculation = PayrollCalculationService.calculate_from_snapshots(self)

            # Aplicar resultados (IDEMPOTENTE: solo asigna valores)
            self.base_salary = calculation['base_salary']
            self.commission_earnings = calculation['commission_earnings']
            self.gross_amount = calculation['gross_amount'] + (self.christmas_bonus or Decimal('0.00'))

        except ImportError as exc:
            import logging
            logging.getLogger(__name__).exception(
                "PayrollCalculationService no disponible; no se puede calcular la nómina del período %s",
                getattr(self, 'pk', None),
            )
            raise RuntimeError(
                "Servicio de cálculo de nómina no disponible"
            ) from exc

        # Auto-apply configured rates from PayrollConfiguration / FiscalTable
        self.deductions.filter(
            is_automatic=True,
            source='auto_config',
        ).delete()

        try:
            payroll_config = employee.tenant.payroll_config
        except Exception:
            payroll_config = None

        if self.gross_amount > 0:
            # SFS empleado (tope RD$232,230)
            if payroll_config is not None:
                sfs_rate = payroll_config.health_insurance_rate or Decimal('0.00')
            else:
                sfs_rate = Decimal('3.04')
            sfs_base = min(self.gross_amount, Decimal('232230.00'))
            sfs_amount = Decimal('0.00')
            if sfs_rate and sfs_rate > 0:
                sfs_amount = (sfs_base * sfs_rate / 100).quantize(Decimal('0.01'))
                if sfs_amount > 0:
                    PayrollDeduction.objects.create(
                        period=self,
                        deduction_type='health_insurance',
                        amount=sfs_amount,
                        description=f"[Config] SFS ({sfs_rate}%)",
                        is_automatic=True,
                        source='auto_config',
                    )

            # AFP empleado (tope RD$464,460)
            if payroll_config is not None:
                afp_rate = payroll_config.social_security_rate or Decimal('0.00')
            else:
                afp_rate = Decimal('2.87')
            afp_base = min(self.gross_amount, Decimal('464460.00'))
            afp_amount = Decimal('0.00')
            if afp_rate and afp_rate > 0:
                afp_amount = (afp_base * afp_rate / 100).quantize(Decimal('0.01'))
                if afp_amount > 0:
                    PayrollDeduction.objects.create(
                        period=self,
                        deduction_type='social_security',
                        amount=afp_amount,
                        description=f"[Config] AFP ({afp_rate}%)",
                        is_automatic=True,
                        source='auto_config',
                    )

            # ISR progresivo (FiscalTable) o tasa plana si configurada
            taxable_base = self.gross_amount - sfs_amount - afp_amount
            if taxable_base < 0:
                taxable_base = Decimal('0.00')

            if payroll_config is not None and payroll_config.tax_rate and payroll_config.tax_rate > 0:
                tax_amount = (self.gross_amount * payroll_config.tax_rate / 100).quantize(Decimal('0.01'))
                if tax_amount > 0:
                    PayrollDeduction.objects.create(
                        period=self,
                        deduction_type='tax',
                        amount=tax_amount,
                        description=f"[Config] ISR ({payroll_config.tax_rate}%)",
                        is_automatic=True,
                        source='auto_config',
                    )
            else:
                try:
                    from apps.employees_api.earnings_models import FiscalTable
                    ft = FiscalTable.get_for_year(self.period_start.year)
                    if ft:
                        monthly_isr = (ft.calculate_isr(taxable_base * 12) / 12).quantize(Decimal('0.01'))
                        if monthly_isr > 0:
                            PayrollDeduction.objects.create(
                                period=self,
                                deduction_type='tax',
                                amount=monthly_isr,
                                description=f"[Config] ISR (tabla {ft.fiscal_year})",
                                is_automatic=True,
                                source='auto_config',
                            )
                except Exception:
                    import logging
                    logging.getLogger(__name__).exception(
                        "Error al calcular ISR para período %s", getattr(self, 'pk', None)
                    )

        # APORTES PATRONALES (no reducen el neto del empleado)
        try:
            payroll_config = self.employee.tenant.payroll_config
        except Exception:
            payroll_config = None
        srl_rate = Decimal('1.20')
        if payroll_config and getattr(payroll_config, 'srl_rate', None) and payroll_config.srl_rate > 0:
            srl_rate = payroll_config.srl_rate
        sfs_employer_base = min(self.gross_amount, Decimal('232230.00'))
        afp_employer_base = min(self.gross_amount, Decimal('464460.00'))
        srl_base = min(self.gross_amount, Decimal('92892.00'))
        self.employer_sfs = (sfs_employer_base * Decimal('7.09') / 100).quantize(Decimal('0.01'))
        self.employer_afp = (afp_employer_base * Decimal('7.10') / 100).quantize(Decimal('0.01'))
        self.employer_srl = (srl_base * srl_rate / 100).quantize(Decimal('0.01'))
        self.employer_infotep = (self.gross_amount * Decimal('1.00') / 100).quantize(Decimal('0.01'))
        self.employer_total = self.employer_sfs + self.employer_afp + self.employer_srl + self.employer_infotep

        # Calcular deducciones y neto finales (solo deducciones del empleado)
        deductions = self.deductions.all()
        self.deductions_total = sum(d.amount for d in deductions)
        self.net_amount = self.gross_amount - self.deductions_total
        
        # Assertions de consistencia de nómina (Task 6)
        if self.gross_amount < 0:
            raise ValueError(f"El monto bruto no puede ser negativo. Encontrado: {self.gross_amount}")
        if self.net_amount != self.gross_amount - self.deductions_total:
            raise ValueError(
                f"El monto neto no coincide con la fórmula (Bruto - Deducciones). "
                f"Esperado: {self.gross_amount - self.deductions_total}, Encontrado: {self.net_amount}"
            )
        expected_gross = self.base_salary + self.commission_earnings + (self.christmas_bonus or Decimal('0.00'))
        if self.gross_amount != expected_gross:
            raise ValueError(
                f"El monto bruto no coincide con la suma de salario base y comisiones. "
                f"Esperado: {expected_gross}, Encontrado: {self.gross_amount}"
            )
        
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
        import datetime
        from zoneinfo import ZoneInfo
        from django.utils.timezone import make_aware
        try:
            tenant_tz = ZoneInfo(
                getattr(self.employee.tenant, 'timezone', None) or 'America/Santo_Domingo'
            )
        except Exception:
            tenant_tz = ZoneInfo('America/Santo_Domingo')
        
        start_dt = make_aware(
            datetime.datetime.combine(self.period_start, datetime.time.min),
            timezone=tenant_tz
        )
        end_dt = make_aware(
            datetime.datetime.combine(self.period_end, datetime.time.max),
            timezone=tenant_tz
        )
        
        # Obtener ventas del período
        sales = Sale.objects.filter(
            tenant=self.employee.tenant,
            employee=self.employee,
            date_time__gte=start_dt,
            date_time__lte=end_dt
        ).values('id', 'total', 'date_time')
        
        self.calculation_snapshot = {
            'calculated_at': timezone.now().isoformat(),
            'employee': {
                'id': self.employee.id,
                'payment_type': self.employee.payment_type,
                'fixed_salary': float(self.fixed_salary_snapshot or self.employee.fixed_salary),
                'commission_rate': float(self.commission_rate_snapshot or self.employee.commission_rate)
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
        # Nota: can_pay se usa para habilitar el pago (no la aprobación) y en
        # pending_approval será False por diseño.
        if self.net_amount <= 0:
            raise ValueError("No se puede aprobar un período con monto neto cero o negativo")

        # Respetar inmutabilidad: si ya existe snapshot, no reescribirlo.
        if self.calculation_snapshot in (None, {}, []):
            self._create_calculation_snapshot()
        
        # Al aprobar, este flag debe reflejar "listo para pagar".
        self.can_pay = True
        self.pay_block_reason = None
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

        # Update loan remaining balances for auto-deducted installments.
        # Se usa la referencia explícita `loan` para evitar matching por monto.
        loan_deductions = self.deductions.filter(
            is_automatic=True,
            deduction_type='loan',
            loan__isnull=False,
        )
        for deduction in loan_deductions:
            loan = deduction.loan
            if loan is None or loan.status != 'active':
                continue
            loan.remaining_balance -= deduction.amount
            if loan.remaining_balance <= Decimal('0.00'):
                loan.remaining_balance = Decimal('0.00')
                loan.status = 'paid'
            loan.save(update_fields=['remaining_balance', 'status'])
    
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

    # Fuente identificable de la deducción (no depender solo de prefijos de texto)
    SOURCE_CHOICES = [
        ('auto_attendance', 'Automática - Asistencia'),
        ('auto_loan', 'Automática - Préstamo'),
        ('auto_config', 'Automática - Configuración'),
        ('manual', 'Manual'),
        ('adjustment', 'Ajuste correctivo'),
    ]
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual')

    # Trazabilidad mínima de auditoría
    original_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='payroll_deductions_modified')
    modified_at = models.DateTimeField(null=True, blank=True)

    # Referencia explícita al préstamo (evita matching por monto)
    loan = models.ForeignKey(
        'employees_api.Loan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payroll_deductions',
    )

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
        from django.utils import timezone
        
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
        else:
            # Primera creación: registrar monto original
            if self.original_amount is None:
                self.original_amount = self.amount
        
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
    srl_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('1.20'), help_text='Tasa SRL (riesgo laboral, 1.00-1.30%)')
    auto_close_periods = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Payroll Configuration'
        verbose_name_plural = 'Payroll Configurations'
    
    def __str__(self):
        return f"Config Nómina - {self.tenant}"


class RegaliaPascual(models.Model):
    """Regalía pascual (salario de Navidad) — Art. 219-222 Código de Trabajo RD."""

    STATUS_CHOICES = [
        ('calculated', 'Calculada'),
        ('paid', 'Pagada'),
    ]

    employee = models.ForeignKey(
        'employees_api.Employee',
        on_delete=models.CASCADE,
        related_name='regalias_pascuales',
    )
    year = models.IntegerField(help_text='Año fiscal al que corresponde')
    ordinary_salary_annual = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        help_text='Salario ordinario acumulado en el año (base + comisiones regulares)',
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text='Importe de la regalía (1/12 del salario ordinario anual, con tope)',
    )
    is_tax_exempt = models.BooleanField(default=True, help_text='Exenta de ISR (Art. 222)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='calculated')
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='regalias_paid',
    )
    payment_reference = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Multi-tenant
    tenant = models.ForeignKey(
        'tenants_api.Tenant', on_delete=models.CASCADE, related_name='regalias_pascuales',
    )

    class Meta:
        unique_together = ('employee', 'year')
        ordering = ['-year']

    def __str__(self):
        return f"Regalía {self.year} - {self.employee} - ${self.amount}"

    @classmethod
    def calculate_for_employee(cls, employee, year):
        """Calcula la regalía pascual para un empleado en un año dado.

        Base: salario ordinario acumulado (base + comisiones regulares) en el año.
        Fórmula: base / 12, con tope de 5 salarios mínimos.
        Proporcional si el empleado no trabajó el año completo.
        """
        from apps.employees_api.models import PayrollPeriod
        from decimal import Decimal

        tenant = employee.tenant
        minimum_salary = Decimal('23223.00')  # salario mínimo nacional RD (topes TSS)
        cap = minimum_salary * 5

        # Sumar salarios ordinarios de los períodos del año
        periods = PayrollPeriod.objects.filter(
            employee=employee,
            period_start__year=year,
        )
        ordinary_annual = Decimal('0.00')
        for p in periods:
            ordinary_annual += (p.base_salary or Decimal('0.00')) + (p.commission_earnings or Decimal('0.00'))

        # Si no hay períodos, estimar por meses trabajados reales según fecha de contratación
        if ordinary_annual == Decimal('0.00') and employee.payment_type in ('fixed', 'mixed', 'commission'):
            if employee.hire_date and employee.hire_date.year == year:
                months_worked = 12 - employee.hire_date.month + 1
                if employee.hire_date.day > 15:
                    months_worked = max(1, months_worked - 1)
            elif employee.hire_date and employee.hire_date.year < year:
                months_worked = 12
            else:
                months_worked = 12
            months_worked = max(1, months_worked)
            ordinary_annual = (employee.fixed_salary or Decimal('0.00')) * months_worked

        amount = (ordinary_annual / 12).quantize(Decimal('0.01'))
        if amount > cap:
            amount = cap

        obj, _ = cls.objects.update_or_create(
            employee=employee,
            year=year,
            defaults={
                'tenant': tenant,
                'ordinary_salary_annual': ordinary_annual,
                'amount': amount,
                'is_tax_exempt': True,
                'status': 'calculated',
            },
        )
        return obj

    def mark_as_paid(self, paid_by, reference=None):
        from django.utils import timezone
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.paid_by = paid_by
        self.payment_reference = reference
        self.save(update_fields=['status', 'paid_at', 'paid_by', 'payment_reference', 'updated_at'])


class Liquidacion(models.Model):
    """Liquidación / prestaciones laborales — Art. 75-86, 177-183, 219-223 Código de Trabajo RD."""

    STATUS_CHOICES = [
        ('calculated', 'Calculada'),
        ('paid', 'Pagada'),
    ]

    TERMINATION_TYPE_CHOICES = [
        ('desahucio', 'Desahucio (sin causa)'),
        ('despido_causa', 'Despido con causa'),
        ('despido_sin_causa', 'Despido sin causa'),
        ('dimision_causa', 'Dimisión con causa'),
        ('dimision_sin_causa', 'Dimisión sin causa'),
        ('mutuo_acuerdo', 'Mutuo acuerdo'),
    ]

    employee = models.ForeignKey(
        'employees_api.Employee',
        on_delete=models.CASCADE,
        related_name='liquidaciones',
    )
    tenant = models.ForeignKey(
        'tenants_api.Tenant', on_delete=models.CASCADE, related_name='liquidaciones',
    )
    termination_date = models.DateField()
    termination_type = models.CharField(max_length=20, choices=TERMINATION_TYPE_CHOICES)
    years_of_service = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    months_of_service = models.IntegerField(default=0)
    daily_salary = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Conceptos
    preaviso_days = models.IntegerField(default=0)
    preaviso_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    cesantia_days = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    cesantia_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    vacation_days = models.IntegerField(default=0)
    vacation_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    regalia_proporcional = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    participacion_beneficios = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    asistencia_economica = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text='Asistencia económica Art. 82 (litigio)')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='calculated')
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='liquidaciones_paid',
    )
    payment_reference = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-termination_date']

    def __str__(self):
        return f"Liquidación {self.employee} - {self.termination_type} - ${self.total}"

    @classmethod
    def calculate(cls, employee, termination_date, termination_type, total_utilities=None, total_payroll=None, asistencia_economica=Decimal('0.00'), participacion_exempt=False):
        """Calcula la liquidación según la causa de terminación."""
        from datetime import date, timedelta
        from django.utils import timezone

        tenant = employee.tenant
        # Evitar múltiples liquidaciones activas para la misma terminación
        existing = cls.objects.filter(
            employee=employee,
            termination_date=termination_date,
            status='calculated',
        ).first()
        if existing is not None:
            return existing

        hire_date = employee.hire_date or termination_date

        # Años y meses de servicio
        delta = termination_date - hire_date
        years = delta.days / 365.25
        months = delta.days // 30
        if months < 0:
            months = 0

        # Salario diario (Art. 85: promedio de salarios ordinarios del último año o fracción)
        from apps.employees_api.models import PayrollPeriod
        periods = PayrollPeriod.objects.filter(
            employee=employee,
            period_end__lte=termination_date,
        ).order_by('-period_end')[:12]
        if periods:
            total_ord = sum((p.base_salary or Decimal('0.00')) + (p.commission_earnings or Decimal('0.00')) for p in periods)
            num_periods = len(periods)
            avg_monthly = (total_ord / num_periods) if num_periods else (employee.fixed_salary or Decimal('0.00'))
            daily_salary = (avg_monthly / Decimal('23.83')).quantize(Decimal('0.01'))
        else:
            daily_salary = ((employee.fixed_salary or Decimal('0.00')) / Decimal('23.83')).quantize(Decimal('0.01'))

        # Preaviso y cesantía solo para desahucio, despido sin causa, dimisión con causa, mutuo acuerdo
        # Mutuo acuerdo: no se asignan automáticamente preaviso/cesantía (son pactados)
        applies_prestaciones = termination_type in ('desahucio', 'despido_sin_causa', 'dimision_causa')

        preaviso_days = 0
        cesantia_days = Decimal('0.00')

        if applies_prestaciones:
            # Preaviso (Art. 76)
            if months >= 12:
                preaviso_days = 28
            elif months >= 6:
                preaviso_days = 14
            elif months >= 3:
                preaviso_days = 7

            # Cesantía (Art. 80)
            if months >= 3 and months < 6:
                cesantia_days = Decimal('6')
            elif months >= 6 and months < 12:
                cesantia_days = Decimal('13')
            elif months >= 12:
                full_years = months // 12
                if full_years >= 5:
                    cesantia_days = Decimal('23') * full_years
                else:
                    cesantia_days = Decimal('21') * full_years
                # fracción superior a 3 meses
                remaining_months = months % 12
                if remaining_months > 3:
                    if full_years >= 5:
                        cesantia_days += Decimal('23') * Decimal(remaining_months) / Decimal('12')
                    else:
                        cesantia_days += Decimal('21') * Decimal(remaining_months) / Decimal('12')

        preaviso_amount = (daily_salary * preaviso_days).quantize(Decimal('0.01'))
        cesantia_amount = (daily_salary * cesantia_days).quantize(Decimal('0.01'))

        # Vacaciones no disfrutadas
        vacation_amount = Decimal('0.00')
        vacation_days = 0
        try:
            from apps.employees_api.earnings_models import Vacation
            vac = Vacation.objects.filter(employee=employee, year=termination_date.year).first()
            if vac and vac.status == 'pending':
                vacation_days = vac.days_entitled - vac.days_taken
                if vacation_days < 0:
                    vacation_days = 0
                vacation_amount = (daily_salary * vacation_days).quantize(Decimal('0.01'))
        except Exception:
            pass

        # Regalía proporcional (Art. 219-220): duodécima parte del salario ordinario del año
        regalia = Decimal('0.00')
        year_periods = PayrollPeriod.objects.filter(
            employee=employee,
            period_start__year=termination_date.year,
        )
        ordinary_annual = sum((p.base_salary or Decimal('0.00')) + (p.commission_earnings or Decimal('0.00')) for p in year_periods)
        if ordinary_annual > 0:
            regalia = (Decimal(str(ordinary_annual)) / Decimal('12')).quantize(Decimal('0.01'))
        elif employee.payment_type in ('fixed', 'mixed', 'commission'):
            months_worked = min(months, 12)
            if months_worked > 0:
                regalia = ((employee.fixed_salary or Decimal('0.00')) * Decimal(months_worked) / Decimal('12')).quantize(Decimal('0.01'))

        # Participación en beneficios (10% de utilidades, proporcional)
        participacion = Decimal('0.00')
        # Excepciones Art. 223: empresas industriales/forestales/mineras primeros 3 años,
        # zonas francas, agrícolas con capital < RD$1,000,000
        if not participacion_exempt and total_utilities and total_payroll and total_payroll > 0:
            # Usar remuneración ordinaria (base + comisiones) en lugar de solo salario fijo
            emp_ordinary = (employee.fixed_salary or Decimal('0.00'))
            emp_periods = PayrollPeriod.objects.filter(employee=employee, period_start__year=termination_date.year)
            if emp_periods.exists():
                emp_ordinary += sum((p.commission_earnings or Decimal('0.00')) for p in emp_periods)
            if total_payroll and total_payroll > 0:
                share = emp_ordinary / total_payroll
            else:
                share = Decimal('0.00')
            raw = (Decimal(str(total_utilities)) * Decimal('0.10') * share).quantize(Decimal('0.01'))
            # Tope: 45 días si <3 años, 60 días si >=3 años
            cap_days = 60 if years >= 3 else 45
            cap = (daily_salary * cap_days).quantize(Decimal('0.01'))
            participacion = min(raw, cap)

        total = preaviso_amount + cesantia_amount + vacation_amount + regalia + participacion + (asistencia_economica or Decimal('0.00'))

        obj = cls.objects.create(
            employee=employee,
            tenant=tenant,
            termination_date=termination_date,
            termination_type=termination_type,
            years_of_service=Decimal(str(round(years, 2))),
            months_of_service=months,
            daily_salary=daily_salary,
            preaviso_days=preaviso_days,
            preaviso_amount=preaviso_amount,
            cesantia_days=cesantia_days,
            cesantia_amount=cesantia_amount,
            vacation_days=vacation_days,
            vacation_amount=vacation_amount,
            regalia_proporcional=regalia,
            participacion_beneficios=participacion,
            asistencia_economica=asistencia_economica or Decimal('0.00'),
            total=total,
            status='calculated',
        )
        return obj

    def mark_as_paid(self, paid_by, reference=None):
        from django.utils import timezone
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.paid_by = paid_by
        self.payment_reference = reference
        self.save(update_fields=['status', 'paid_at', 'paid_by', 'payment_reference', 'updated_at'])


class Vacation(models.Model):
    """Vacaciones — Art. 177-183 Código de Trabajo RD."""

    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('enjoyed', 'Disfrutada'),
        ('compensated', 'Compensada'),
    ]

    employee = models.ForeignKey(
        'employees_api.Employee',
        on_delete=models.CASCADE,
        related_name='vacations',
    )
    year = models.IntegerField(help_text='Año al que corresponden las vacaciones')
    days_entitled = models.IntegerField(default=0, help_text='Días de vacaciones correspondientes')
    days_taken = models.IntegerField(default=0, help_text='Días disfrutados')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    TERMINATION_TYPE_CHOICES = [
        ('desahucio', 'Desahucio'),
        ('despido_causa', 'Despido con causa'),
        ('despido_sin_causa', 'Despido sin causa'),
        ('dimision_causa', 'Dimisión con causa'),
        ('dimision_sin_causa', 'Dimisión sin causa'),
        ('mutuo_acuerdo', 'Mutuo acuerdo'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    termination_type = models.CharField(max_length=20, choices=TERMINATION_TYPE_CHOICES, null=True, blank=True)
    payroll_period = models.ForeignKey(
        'employees_api.PayrollPeriod', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='vacations_paid',
    )
    daily_salary = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    is_compensated = models.BooleanField(default=False)
    compensated_at = models.DateTimeField(null=True, blank=True)
    compensated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='vacations_compensated',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    tenant = models.ForeignKey(
        'tenants_api.Tenant', on_delete=models.CASCADE, related_name='vacations',
    )

    class Meta:
        unique_together = ('employee', 'year')
        ordering = ['-year']

    def __str__(self):
        return f"Vacaciones {self.year} - {self.employee} - {self.days_entitled} días"

    @classmethod
    def calculate_for_employee(cls, employee, year):
        """Calcula las vacaciones correspondientes a un empleado en un año."""
        from datetime import date, timedelta
        hire_date = employee.hire_date
        if not hire_date:
            years_of_service = year - (employee.created_at.year if employee.created_at else year)
        else:
            years_of_service = year - hire_date.year
            # Si el aniversario no ha ocurrido aún en diciembre del año objetivo
            if year == hire_date.year:
                years_of_service = 0

        # Días según antigüedad
        if years_of_service >= 5:
            days = 18
        elif years_of_service >= 1:
            days = 14
        elif years_of_service == 0:
            # Proporcional: >5 meses → 6 días, >6 meses → 7 días
            months_worked = 12 - (hire_date.month if hire_date else 1) + 1
            if months_worked > 6:
                days = 7
            elif months_worked > 5:
                days = 6
            else:
                days = 0
        else:
            days = 0

        # Salario diario: para comisionistas, usar promedio de los últimos 12 meses
        if employee.payment_type in ('commission', 'mixed'):
            from apps.employees_api.compensation_models import EmployeeCompensationHistory
            comp = EmployeeCompensationHistory.get_active_compensation(employee=employee)
            base = comp.fixed_salary if comp else (employee.fixed_salary or Decimal('0.00'))
            # promedio diario de salarios devengados en los últimos 12 meses
            from apps.employees_api.models import PayrollPeriod
            periods = PayrollPeriod.objects.filter(employee=employee).order_by('-period_start')[:12]
            if periods:
                total = sum((p.gross_amount or Decimal('0.00')) for p in periods)
                months = len(periods)
                avg_monthly = total / months if months else (employee.fixed_salary or Decimal('0.00'))
                daily_salary = avg_monthly / Decimal('23.83') if avg_monthly else (base / Decimal('23.83'))
            else:
                daily_salary = (employee.fixed_salary or Decimal('0.00')) / Decimal('23.83')
        else:
            daily_salary = (employee.fixed_salary or Decimal('0.00')) / Decimal('23.83')
        paid_amount = (daily_salary * days).quantize(Decimal('0.01'))

        obj, _ = cls.objects.update_or_create(
            employee=employee,
            year=year,
            defaults={
                'tenant': employee.tenant,
                'days_entitled': days,
                'paid_amount': paid_amount,
                'daily_salary': daily_salary,
                'status': 'pending',
            },
        )
        return obj

    def mark_enjoyed(self, start_date, end_date):
        from datetime import date
        days = (end_date - start_date).days + 1
        if days < 7:
            raise ValueError("Las vacaciones no pueden fraccionarse en menos de una semana")
        self.start_date = start_date
        self.end_date = end_date
        self.days_taken = days
        self.status = 'enjoyed'
        self.save(update_fields=['start_date', 'end_date', 'days_taken', 'status', 'updated_at'])

    def compensate(self, paid_by, termination_type=None, payroll_period=None):
        """Compensación de vacaciones no disfrutadas (terminación laboral).
        Solo permitida para causas legales (desahucio, despido sin causa,
        dimisión con causa, mutuo acuerdo)."""
        from django.utils import timezone
        allowed = {'desahucio', 'despido_sin_causa', 'dimision_causa', 'mutuo_acuerdo'}
        if termination_type and termination_type not in allowed:
            raise ValueError("Compensación no permitida para esta causa de terminación")
        if self.status == 'compensated':
            raise ValueError("Ya fue compensada")
        self.termination_type = termination_type
        self.status = 'compensated'
        self.is_compensated = True
        self.compensated_at = timezone.now()
        self.compensated_by = paid_by
        if payroll_period is not None:
            self.payroll_period = payroll_period
        self.save(update_fields=['termination_type', 'status', 'is_compensated', 'compensated_at', 'compensated_by', 'payroll_period', 'updated_at'])
