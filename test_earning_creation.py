#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.pos_api.models import Sale, SaleDetail
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import Earning
from apps.services_api.models import Service
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal

print('=== PRUEBA FLUJO POS → EARNINGS ===')

# Estado inicial
earnings_before = Earning.objects.count()
print(f'Total Earnings antes: {earnings_before}')

# Obtener empleado comisionable
employee = Employee.objects.get(id=4)
print(f'Empleado: {employee.user.email}')
print(f'Salary type: {employee.salary_type}')
print(f'Commission %: {employee.commission_percentage}')
print(f'Payment mode: {employee.commission_payment_mode}')

# Obtener servicio
service = Service.objects.first()
if not service:
    print('ERROR: No hay servicios disponibles')
    exit(1)

print(f'Servicio: {service.name} - ${service.price}')

# Crear venta
sale = Sale.objects.create(
    user=employee.user,
    employee=employee,
    total=Decimal('100.00'),
    paid=Decimal('100.00'),
    status='completed',
    earnings_generated=False
)

# Crear detalle de servicio
service_ct = ContentType.objects.get_for_model(Service)
SaleDetail.objects.create(
    sale=sale,
    content_type=service_ct,
    object_id=service.id,
    name=service.name,
    quantity=1,
    price=Decimal('100.00')
)

print(f'Venta creada: #{sale.id}')

# Simular método _create_employee_earning
from apps.pos_api.views import SaleViewSet
viewset = SaleViewSet()
viewset._create_employee_earning(sale, employee.user)

# Verificar resultado
earnings_after = Earning.objects.count()
print(f'Total Earnings después: {earnings_after}')
print(f'Earnings creados: {earnings_after - earnings_before}')

# Verificar earning específico
new_earning = Earning.objects.filter(sale=sale).first()
if new_earning:
    print(f'✅ EARNING CREADO:')
    print(f'   Monto: ${new_earning.amount}')
    print(f'   Tipo: {new_earning.earning_type}')
    print(f'   Porcentaje: {new_earning.percentage}%')
    print(f'   External ID: {new_earning.external_id}')
else:
    print('❌ NO SE CREÓ EARNING')

# Verificar sale
sale.refresh_from_db()
print(f'Sale earnings_generated: {sale.earnings_generated}')

print('=== PRUEBA COMPLETADA ===')