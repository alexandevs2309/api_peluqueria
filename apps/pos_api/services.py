from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from apps.employees_api.compensation_models import EmployeeCompensationHistory

ZERO = Decimal('0.00')


def _round2(value):
    return (value or ZERO).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class SaleCommissionService:
    """Servicio para calcular y guardar snapshots de comisión en ventas.

    Orden de resolución del porcentaje (obligatorio y verificable):
      1. `ServiceEmployee.commission_percentage` — configuración específica
         del empleado para ese servicio (prevalece si está definida).
      2. `EmployeeCompensationHistory` vigente a la fecha de la venta.
      3. `employee.commission_rate` — tasa global del empleado.

    El tipo de compensación siempre se respeta: solo `commission` y `mixed`
    generan comisión por línea de servicio. Los productos nunca generan
    comisión de servicios.
    """

    SOURCE_SERVICE = 'service'
    SOURCE_HISTORY = 'history'
    SOURCE_GLOBAL = 'global'
    SOURCE_NONE = 'none'

    # ── Resolución de tasa ─────────────────────────────────────────────────
    @staticmethod
    def resolve_commission_rate(employee, service=None, sale_date=None):
        """
        Devuelve (rate, source) para el empleado/servicio en la fecha dada.

        Devuelve (None, SOURCE_NONE) si el empleado no genera comisión.
        """
        if employee is None:
            return None, SaleCommissionService.SOURCE_NONE

        # El tipo de compensación manda: un empleado de sueldo fijo nunca
        # genera comisión por línea de servicio.
        payment_type = employee.payment_type
        if payment_type not in ('commission', 'mixed'):
            return None, SaleCommissionService.SOURCE_NONE

        if sale_date is None:
            sale_date = timezone.now().date()

        # 1. Configuración específica del servicio
        if service is not None:
            try:
                from apps.services_api.models import ServiceEmployee
                se = ServiceEmployee.objects.filter(
                    employee=employee,
                    service=service,
                ).only('commission_percentage').first()
                if se is not None and se.commission_percentage is not None:
                    return se.commission_percentage, SaleCommissionService.SOURCE_SERVICE
            except Exception:
                pass

        # 2. Historial de compensación vigente a la fecha de la venta
        compensation = EmployeeCompensationHistory.get_active_compensation(
            employee=employee,
            date=sale_date,
        )
        if compensation and compensation.commission_rate is not None:
            return compensation.commission_rate, SaleCommissionService.SOURCE_HISTORY

        # 3. Tasa global
        if employee.commission_rate is not None:
            return employee.commission_rate, SaleCommissionService.SOURCE_GLOBAL

        return None, SaleCommissionService.SOURCE_NONE

    # ── Comisión de una línea de venta ─────────────────────────────────────
    @staticmethod
    def calculate_detail_commission(employee, service, line_total, sale_date=None):
        """
        Calcula la comisión de UNA línea de venta.

        Returns:
            (rate, amount, source)
            - Si la línea no genera comisión devuelve (None, None, 'none')
              para que los snapshots queden en NULL y la nómina los ignore.
        """
        line_total = Decimal(str(line_total or 0))

        # Los productos no generan comisión de servicios.
        if service is None:
            return None, None, SaleCommissionService.SOURCE_NONE

        rate, source = SaleCommissionService.resolve_commission_rate(
            employee=employee,
            service=service,
            sale_date=sale_date,
        )
        if rate is None:
            return None, None, SaleCommissionService.SOURCE_NONE

        amount = _round2(line_total * Decimal(str(rate)) / Decimal('100'))
        return rate, amount, source

    # ── Método legacy a nivel de venta (se conserva intacto) ──────────────
    @staticmethod
    def calculate_commission_snapshot(employee, sale_total, sale_date=None):
        """
        Calcula comisión usando historial de compensación vigente
        (método original a nivel de venta, conservado para ventas históricas).

        Returns:
            tuple: (commission_rate, commission_amount)
        """
        if sale_date is None:
            sale_date = timezone.now().date()

        # Obtener compensación vigente en la fecha de venta
        compensation = EmployeeCompensationHistory.get_active_compensation(
            employee=employee,
            date=sale_date
        )

        if compensation:
            # Usar tasa del historial
            commission_rate = compensation.commission_rate
        else:
            # Fallback: usar tasa actual del empleado
            commission_rate = employee.commission_rate

        # Calcular monto de comisión
        commission_rate = commission_rate or Decimal('0.00')
        if employee.payment_type in ['commission', 'mixed']:
            commission_amount = (sale_total * commission_rate) / Decimal('100')
        else:
            commission_amount = Decimal('0.00')

        return commission_rate, commission_amount

    @staticmethod
    def apply_commission_snapshot(sale, employee):
        """
        Aplica snapshot de comisión a nivel de venta.

        IMPORTANTE: si la venta ya tiene comisiones por línea, no se escribe
        snapshot de venta. Esto garantiza la regla de fuente única y evita
        doble conteo en la nómina.
        """
        has_line_commissions = (
            sale.pk is not None
            and sale.details.filter(commission_amount_snapshot__isnull=False).exists()
        )
        if has_line_commissions:
            sale.commission_rate_snapshot = None
            sale.commission_amount_snapshot = None
            return

        if employee and employee.payment_type in ['commission', 'mixed']:
            rate, amount = SaleCommissionService.calculate_commission_snapshot(
                employee=employee,
                sale_total=sale.total,
                sale_date=sale.date_time.date() if sale.date_time else None
            )
            sale.commission_rate_snapshot = rate
            sale.commission_amount_snapshot = amount
        else:
            sale.commission_rate_snapshot = Decimal('0.00')
            sale.commission_amount_snapshot = Decimal('0.00')

    # ── Reembolsos proporcionales ──────────────────────────────────────────
    @staticmethod
    def commission_components(sale):
        """
        Descompone la comisión POSITIVA de una venta en componentes
        (empleado, monto) aplicando la regla de fuente única.

        Returns:
            lista de dicts {'employee': Employee, 'amount': Decimal,
                            'source': str, 'detail': SaleDetail|None}
        """
        components = []

        from apps.pos_api.models import Sale

        source = sale.commission_source

        # Fuente LINE: un componente por línea con snapshot.
        if source == Sale.COMMISSION_SOURCE_LINE:
            for detail in sale.details.filter(
                employee__isnull=False,
                commission_amount_snapshot__isnull=False,
            ):
                components.append({
                    'employee': detail.employee,
                    'amount': _round2(detail.commission_amount_snapshot),
                    'source': 'line',
                    'detail': detail,
                })
            return components

        # Fuente SALE (histórico): un único componente por venta.
        if source == Sale.COMMISSION_SOURCE_SALE:
            if sale.employee_id and sale.commission_amount_snapshot:
                components.append({
                    'employee': sale.employee,
                    'amount': _round2(sale.commission_amount_snapshot),
                    'source': 'sale',
                    'detail': None,
                })
        return components

    @staticmethod
    def refund_commission_components(sale, refund_ratio):
        """
        Descompone la comisión de una venta en componentes (empleado, monto)
        proporcionales al reembolso, aplicando la regla de fuente única.

        Para reembolsos parciales el monto es proporcional; para reembolsos
        totales (ratio = 1) revierte el 100% de la comisión original.

        Returns:
            lista de dicts {'employee': Employee, 'amount': Decimal (negativo),
                            'source': str, 'detail': SaleDetail|None}
        """
        refund_ratio = Decimal(str(refund_ratio or 0))
        if refund_ratio <= 0:
            return []

        components = []
        for component in SaleCommissionService.commission_components(sale):
            amount = -_round2(component['amount'] * refund_ratio)
            if amount == 0:
                continue
            components.append({**component, 'amount': amount})
        return components
