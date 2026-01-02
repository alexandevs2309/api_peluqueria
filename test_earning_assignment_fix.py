#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.pos_api.models import Sale, SaleDetail
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import Earning
from apps.services_api.models import Service, ServiceEmployee
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal

print('=== PRUEBA CORRECCIÓN BUG ASIGNACIÓN EARNINGS ===')

# Configurar dos empleados diferentes
employee1 = Employee.objects.get(id=4)  # Empleado existente
employee2 = Employee.objects.filter(
    tenant=employee1.tenant,
    is_active=True
).exclude(id=employee1.id).first()

if not employee2:
    print('❌ Se necesitan al menos 2 empleados para la prueba')
    exit(1)

# Configurar employee2 para comisiones
employee2.salary_type = 'commission'
employee2.commission_payment_mode = 'PER_PERIOD'
employee2.commission_percentage = Decimal('30.00')  # 30% diferente al 40% del employee1
employee2.save()

print(f'Empleado 1: {employee1.user.email} (40% comisión)')
print(f'Empleado 2: {employee2.user.email} (30% comisión)')

# Obtener servicios
services = Service.objects.filter(tenant=employee1.tenant)[:2]
if len(services) < 2:
    print('❌ Se necesitan al menos 2 servicios para la prueba')
    exit(1)

service1, service2 = services[0], services[1]
print(f'Servicio 1: {service1.name}')
print(f'Servicio 2: {service2.name}')

# Crear relaciones ServiceEmployee
ServiceEmployee.objects.get_or_create(
    service=service1,
    employee=employee1,
    defaults={'commission_percentage': Decimal('40.00')}
)

ServiceEmployee.objects.get_or_create(
    service=service2,
    employee=employee2,
    defaults={'commission_percentage': Decimal('30.00')}
)

print('✅ Relaciones ServiceEmployee creadas')

# Estado inicial
earnings_before = Earning.objects.count()
print(f'Total Earnings antes: {earnings_before}')

# Crear venta con manager (diferente a los empleados de servicios)
manager = Employee.objects.filter(
    tenant=employee1.tenant,
    user__is_staff=True
).first()

if not manager:
    # Usar employee1 como manager para la prueba
    manager = employee1

# Crear venta
sale = Sale.objects.create(
    user=manager.user,  # Manager cobra la venta
    employee=manager,   # Manager asignado a la venta
    total=Decimal('200.00'),
    paid=Decimal('200.00'),
    status='completed',
    earnings_generated=False
)

# Crear detalles de servicios ejecutados por empleados diferentes
service_ct = ContentType.objects.get_for_model(Service)

SaleDetail.objects.create(
    sale=sale,
    content_type=service_ct,
    object_id=service1.id,
    name=service1.name,
    quantity=1,
    price=Decimal('100.00')  # Servicio 1: $100 por employee1 (40% = $40)
)

SaleDetail.objects.create(
    sale=sale,
    content_type=service_ct,
    object_id=service2.id,
    name=service2.name,
    quantity=1,
    price=Decimal('100.00')  # Servicio 2: $100 por employee2 (30% = $30)
)

print(f'Venta creada: #{sale.id}')
print(f'Manager que cobra: {manager.user.email}')

# Ejecutar método corregido
from apps.pos_api.views import SaleViewSet
viewset = SaleViewSet()
viewset._create_employee_earning(sale, None)

# Verificar resultados
earnings_after = Earning.objects.count()
print(f'Total Earnings después: {earnings_after}')
print(f'Earnings creados: {earnings_after - earnings_before}')

# Verificar earnings específicos
new_earnings = Earning.objects.filter(sale=sale).order_by('employee__id')

print('\n=== EARNINGS CREADOS ===')
for earning in new_earnings:
    print(f'Empleado: {earning.employee.user.email}')
    print(f'Monto: ${earning.amount}')
    print(f'Porcentaje: {earning.percentage}%')
    print(f'Descripción: {earning.description}')
    print('---')

# Verificar asignación correcta
employee1_earnings = new_earnings.filter(employee=employee1)
employee2_earnings = new_earnings.filter(employee=employee2)

print('\n=== VERIFICACIÓN ===')
if employee1_earnings.exists():
    print(f'✅ Employee1 recibió earning: ${employee1_earnings.first().amount}')
else:
    print('❌ Employee1 NO recibió earning')

if employee2_earnings.exists():
    print(f'✅ Employee2 recibió earning: ${employee2_earnings.first().amount}')
else:
    print('❌ Employee2 NO recibió earning')

print('=== PRUEBA COMPLETADA ===')