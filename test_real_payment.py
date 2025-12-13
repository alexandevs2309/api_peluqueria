#!/usr/bin/env python3
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.employees_api.models import Employee
from apps.pos_api.models import Sale
from apps.employees_api.payments_views import PaymentViewSet
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request
import json

User = get_user_model()

def test_real_payment():
    print('💳 TESTING PAGO REAL')
    
    user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
    
    # Obtener empleado con ventas pendientes
    emp = Employee.objects.filter(
        tenant=user.tenant, 
        is_active=True,
        salary_type='commission'
    ).first()
    
    if not emp:
        print('❌ No hay empleados de comisión')
        return
    
    print(f'👤 Empleado: {emp.user.full_name}')
    
    # Obtener ventas pendientes
    pending_sales = Sale.objects.filter(
        employee=emp,
        period__isnull=True,
        status='completed'
    )
    
    if not pending_sales.exists():
        print('❌ No hay ventas pendientes')
        return
    
    sale_ids = list(pending_sales.values_list('id', flat=True))
    total_sales = sum(float(s.total) for s in pending_sales)
    
    print(f'📊 Ventas a pagar: {len(sale_ids)} (${total_sales})')
    print(f'   IDs: {sale_ids}')
    
    # Simular request de pago
    factory = APIRequestFactory()
    payment_data = {
        'employee_id': emp.id,
        'sale_ids': sale_ids,
        'payment_method': 'cash',
        'payment_reference': 'TEST-001',
        'idempotency_key': f'test-{emp.id}-001'
    }
    
    request = factory.post('/api/employees/payments/pay_employee/', 
                          data=json.dumps(payment_data),
                          content_type='application/json')
    request.user = user
    
    # Ejecutar pago
    viewset = PaymentViewSet()
    
    try:
        response = viewset.pay_employee(Request(request))
        print(f'📡 Respuesta: {response.status_code}')
        
        if response.status_code == 200:
            data = response.data
            print('✅ Pago exitoso!')
            print(f'   Status: {data.get("status")}')
            print(f'   Mensaje: {data.get("message")}')
            
            if 'summary' in data:
                summary = data['summary']
                print(f'   Monto bruto: ${summary.get("gross_amount")}')
                print(f'   Monto neto: ${summary.get("net_amount")}')
                print(f'   Recibo: {summary.get("receipt_number")}')
        else:
            print(f'❌ Error: {response.data}')
            
    except Exception as e:
        print(f'❌ Excepción: {str(e)}')
        import traceback
        traceback.print_exc()

def verify_payment_result():
    print('\n🔍 VERIFICANDO RESULTADO DEL PAGO')
    
    user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
    
    # Verificar ventas pendientes después del pago
    pending_sales = Sale.objects.filter(
        employee__tenant=user.tenant,
        period__isnull=True,
        status='completed'
    )
    
    print(f'Ventas pendientes restantes: {pending_sales.count()}')
    
    # Verificar summaries creados
    from apps.employees_api.earnings_models import FortnightSummary
    recent_summaries = FortnightSummary.objects.filter(
        employee__tenant=user.tenant
    ).order_by('-updated_at')[:3]
    
    print('Últimos summaries:')
    for summary in recent_summaries:
        status = '✅ PAGADO' if summary.is_paid else '⏳ PENDIENTE'
        print(f'  - {summary.employee.user.full_name}: ${summary.total_earnings} - {status}')

if __name__ == '__main__':
    test_real_payment()
    verify_payment_result()