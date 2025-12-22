#!/usr/bin/env python3
"""
Prueba del escenario EXACTO que ve el frontend:
1. Empleado por comisión con período YA PAGADO
2. Crear nueva venta (como en POS)
3. Consultar earnings_summary (como hace el frontend)
4. Verificar que NO muestre "pending_amount" ni "pending_sale_ids"
"""
import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.pos_api.models import Sale
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import FortnightSummary
from decimal import Decimal

User = get_user_model()

def test_frontend_scenario():
    print("🧪 PRUEBA ESCENARIO FRONTEND")
    print("=" * 50)
    
    # 1. Obtener empleado con período pagado
    user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
    employee = Employee.objects.filter(tenant=user.tenant, salary_type='commission').first()
    
    print(f"👤 Empleado: {employee.user.full_name}")
    print(f"💼 Tipo: {employee.salary_type}")
    
    # 2. Verificar que tiene período pagado
    paid_summary = FortnightSummary.objects.filter(employee=employee, is_paid=True).first()
    if not paid_summary:
        print("❌ No hay período pagado para prueba")
        return
    
    print(f"✅ Período pagado: {paid_summary.fortnight_year}/{paid_summary.fortnight_number}")
    
    # 3. Crear venta nueva (simula POS)
    sale = Sale.objects.create(
        user=user,
        employee=employee,
        total=Decimal('150.00'),
        status='completed',
        period=None  # Sin asignar a período
    )
    print(f"📝 Venta creada: ID={sale.id}, Total=${sale.total}")
    
    # 4. Consultar earnings_summary (simula frontend)
    from apps.employees_api.payments_views import PaymentViewSet
    
    class MockRequest:
        def __init__(self, user):
            self.user = user
            self.GET = {}
    
    viewset = PaymentViewSet()
    viewset.request = MockRequest(user)
    response = viewset.earnings_summary(MockRequest(user))
    
    # 5. Buscar empleado en respuesta
    employees = response.data.get('employees', [])
    emp_data = next((e for e in employees if e['employee_id'] == employee.id), None)
    
    if not emp_data:
        print("❌ Empleado no encontrado en respuesta")
        sale.delete()
        return
    
    # 6. VERIFICAR RESULTADO
    print("\n📊 RESULTADO:")
    print(f"   pending_amount: {emp_data.get('pending_amount', 'N/A')}")
    print(f"   pending_sale_ids: {emp_data.get('pending_sale_ids', 'N/A')}")
    print(f"   payment_status: {emp_data.get('payment_status', 'N/A')}")
    print(f"   services_count: {emp_data.get('services_count', 'N/A')}")
    
    # 7. VALIDAR CORRECCIÓN
    pending_amount = emp_data.get('pending_amount', 0)
    pending_sale_ids = emp_data.get('pending_sale_ids', [])
    
    if pending_amount == 0 and len(pending_sale_ids) == 0:
        print("\n✅ CORRECCIÓN EXITOSA:")
        print("   - No muestra monto pendiente")
        print("   - No muestra ventas pendientes")
        print("   - Frontend mostrará 'Sin ventas en este período'")
    else:
        print("\n❌ CORRECCIÓN FALLIDA:")
        print(f"   - Aún muestra pending_amount: {pending_amount}")
        print(f"   - Aún muestra pending_sale_ids: {pending_sale_ids}")
    
    # 8. Verificar ventas sin período
    ventas_sin_periodo = Sale.objects.filter(
        employee=employee,
        status='completed',
        period__isnull=True
    ).count()
    print(f"\n🔍 Ventas sin período en BD: {ventas_sin_periodo}")
    
    # Limpiar
    sale.delete()
    print(f"🧹 Venta {sale.id} eliminada")

if __name__ == "__main__":
    test_frontend_scenario()