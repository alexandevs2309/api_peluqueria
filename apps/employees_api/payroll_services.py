import logging
from decimal import Decimal
from django.db.models import Sum

logger = logging.getLogger(__name__)


class PayrollCalculationService:
    """Servicio para cálculo determinístico de nómina desde snapshots"""
    
    @staticmethod
    def calculate_from_snapshots(period):
        """
        Calcula comisiones exclusivamente desde snapshots
        NO usa Employee como fuente viva
        
        Args:
            period: Instancia de PayrollPeriod
            
        Returns:
            dict con totales calculados
        """
        from apps.pos_api.models import Sale, SaleDetail
        from apps.employees_api.adjustment_models import CommissionAdjustment
        
        # 1. Sumar comisiones desde snapshots de ventas
        import datetime
        from zoneinfo import ZoneInfo
        from django.utils.timezone import make_aware
        try:
            tenant_tz = ZoneInfo(
                getattr(period.employee.tenant, 'timezone', None) or 'America/Santo_Domingo'
            )
        except Exception:
            tenant_tz = ZoneInfo('America/Santo_Domingo')
        
        start_dt = make_aware(
            datetime.datetime.combine(period.period_start, datetime.time.min),
            timezone=tenant_tz
        )
        end_dt = make_aware(
            datetime.datetime.combine(period.period_end, datetime.time.max),
            timezone=tenant_tz
        )
        logger.debug("start_dt=%s, end_dt=%s", start_dt, end_dt)
        
        tenant = period.employee.tenant

        # ── Fuente SALE (ventas históricas) ─────────────────────────────────
        # Snapshots a nivel de venta. Se respetan tal cual: no se recalculan.
        #
        # REGLA DE FUENTE ÚNICA (explícita y verificable en la consulta):
        # una venta con comisiones por línea NUNCA aporta por aquí, aunque
        # por un error llegara con ambos snapshots. Así la nómina no puede
        # duplicar comisiones aunque el dato sea inconsistente.
        sale_source_commission = Sale.objects.filter(
            employee=period.employee,
            date_time__gte=start_dt,
            date_time__lte=end_dt,
            status='confirmed',
            commission_amount_snapshot__isnull=False,
            tenant=tenant
        ).exclude(
            details__commission_amount_snapshot__isnull=False
        ).aggregate(
            total=Sum('commission_amount_snapshot')
        )['total'] or Decimal('0.00')

        # ── Fuente LINE (comisiones por servicio) ───────────────────────────
        # Snapshots a nivel de línea. Una venta con estos snapshots SIEMPRE
        # tiene el snapshot de venta en NULL (garantizado en perform_create),
        # por lo que ambas fuentes son mutuamente excluyentes y NO duplican.
        detail_source_commission = SaleDetail.objects.filter(
            employee=period.employee,
            sale__date_time__gte=start_dt,
            sale__date_time__lte=end_dt,
            sale__status='confirmed',
            sale__tenant=tenant,
            commission_amount_snapshot__isnull=False,
        ).aggregate(
            total=Sum('commission_amount_snapshot')
        )['total'] or Decimal('0.00')

        sales_commission = sale_source_commission + detail_source_commission
        logger.debug(
            "commission sale_source=%s detail_source=%s",
            sale_source_commission, detail_source_commission
        )
        
        # 2. Sumar ajustes (positivos y negativos)
        adjustments_total = CommissionAdjustment.objects.filter(
            payroll_period=period
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # 3. Obtener tipo de pago del empleado (usar snapshot si existe)
        payment_type = period.payment_type_snapshot or period.employee.payment_type

        # 4. Total de comisiones (solo commission/mixed reciben comisión de ventas)
        if payment_type in ['commission', 'mixed']:
            total_commission = sales_commission + adjustments_total
        else:
            total_commission = adjustments_total  # fixed solo recibe ajustes manuales

        # 5. Salario base (si aplica)
        fixed_salary = period.fixed_salary_snapshot \
            if period.fixed_salary_snapshot is not None \
            else period.employee.fixed_salary
        
        base_salary = Decimal('0.00')
        if payment_type in ['fixed', 'mixed']:
            if period.period_type == 'monthly':
                base_salary = fixed_salary
            elif period.period_type == 'biweekly':
                base_salary = fixed_salary / 2
            elif period.period_type == 'weekly':
                base_salary = fixed_salary / 4
        
        return {
            'base_salary': base_salary,
            'commission_earnings': total_commission,
            'sales_commission': sales_commission,
            'sale_source_commission': sale_source_commission,
            'detail_source_commission': detail_source_commission,
            'adjustments': adjustments_total,
            'gross_amount': base_salary + total_commission,
        }
    
    @staticmethod
    def apply_calculation_to_period(period, calculation_result):
        """
        Aplica resultado de cálculo al período
        
        Args:
            period: Instancia de PayrollPeriod
            calculation_result: dict con resultados
        """
        period.base_salary = calculation_result['base_salary']
        period.commission_earnings = calculation_result['commission_earnings']
        period.gross_amount = calculation_result['gross_amount']
        
        # Calcular deducciones y neto
        deductions = period.deductions.all()
        period.deductions_total = sum(d.amount for d in deductions)
        period.net_amount = period.gross_amount - period.deductions_total
