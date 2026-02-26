from apps.pos_api.models import Sale
from apps.employees_api.earnings_models import PayrollPeriod
from decimal import Decimal

# Actualizar venta 53
sale = Sale.objects.get(id=53)
if sale.employee and not sale.commission_rate_snapshot:
    sale.commission_rate_snapshot = sale.employee.commission_rate
    commission_rate = Decimal(str(sale.employee.commission_rate)) / Decimal('100')
    sale.commission_amount_snapshot = sale.total * commission_rate
    
    # Guardar sin validaciones
    Sale.objects.filter(id=sale.id).update(
        commission_rate_snapshot=sale.commission_rate_snapshot,
        commission_amount_snapshot=sale.commission_amount_snapshot
    )
    
    print(f"Venta {sale.id} actualizada:")
    print(f"  Rate: {sale.commission_rate_snapshot}%")
    print(f"  Amount: ${sale.commission_amount_snapshot}")
    
    # Recalcular período
    if sale.period:
        sale.period.calculate_amounts()
        sale.period.save()
        print(f"\nPeríodo recalculado:")
        print(f"  Gross: ${sale.period.gross_amount}")
        print(f"  Commission: ${sale.period.commission_earnings}")
