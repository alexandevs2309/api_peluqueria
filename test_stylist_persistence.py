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
import json

print('=== PRUEBA PERSISTENCIA ESTILISTA POR SERVICIO ===')

# 1. VERIFICAR CAMPO EMPLOYEE EN SALEDETAIL
print('\n1. VERIFICACIÓN DEL MODELO:')
print('=' * 50)

detail_fields = [f.name for f in SaleDetail._meta.fields]
print(f'Campos de SaleDetail: {detail_fields}')

if 'employee' in detail_fields:
    print('✅ Campo employee agregado correctamente')
else:
    print('❌ Campo employee NO encontrado')
    exit(1)

# 2. OBTENER EMPLEADOS Y SERVICIOS
print('\n2. CONFIGURACIÓN DE PRUEBA:')
print('=' * 50)

employees = Employee.objects.filter(is_active=True)[:2]
if len(employees) < 2:
    print('❌ Se necesitan al menos 2 empleados activos')
    exit(1)

manager = employees[0]  # Quien cobra
stylist = employees[1]  # Quien ejecuta el servicio

print(f'Manager (cobra): {manager.user.email}')
print(f'Estilista (ejecuta): {stylist.user.email}')

# Configurar estilista para comisiones
stylist.salary_type = 'commission'
stylist.commission_payment_mode = 'PER_PERIOD'
stylist.commission_percentage = Decimal('50.00')
stylist.save()

service = Service.objects.first()
if not service:
    print('❌ No hay servicios disponibles')
    exit(1)

print(f'Servicio: {service.name} - ${service.price}')

# 3. CREAR VENTA CON ESTILISTA ESPECÍFICO
print('\n3. CREANDO VENTA CON ESTILISTA ESPECÍFICO:')
print('=' * 50)

# Estado inicial
earnings_before = Earning.objects.count()
print(f'Earnings antes: {earnings_before}')

# Crear venta
sale = Sale.objects.create(
    user=manager.user,      # Manager cobra
    employee=manager,       # Manager asignado a la venta
    total=Decimal('150.00'),
    paid=Decimal('150.00'),
    status='completed',
    earnings_generated=False
)

# Crear detalle CON empleado específico
service_ct = ContentType.objects.get_for_model(Service)
detail = SaleDetail.objects.create(
    sale=sale,
    content_type=service_ct,
    object_id=service.id,
    name=service.name,
    quantity=1,
    price=Decimal('150.00'),
    employee=stylist  # ✅ ESTILISTA ESPECÍFICO PERSISTIDO
)

print(f'Venta creada: #{sale.id}')
print(f'  Manager que cobra: {sale.employee.user.email}')
print(f'  Estilista del servicio: {detail.employee.user.email}')

# 4. PROBAR LÓGICA DE EARNINGS
print('\n4. PROBANDO LÓGICA DE EARNINGS:')
print('=' * 50)

from apps.pos_api.views import SaleViewSet
viewset = SaleViewSet()
viewset._create_employee_earning(sale, None)

# Verificar resultados
earnings_after = Earning.objects.count()
print(f'Earnings después: {earnings_after}')
print(f'Earnings creados: {earnings_after - earnings_before}')

# Verificar earning específico
new_earning = Earning.objects.filter(sale=sale).first()
if new_earning:
    print(f'✅ EARNING CREADO CORRECTAMENTE:')
    print(f'   Empleado: {new_earning.employee.user.email}')
    print(f'   Monto: ${new_earning.amount}')
    print(f'   Porcentaje: {new_earning.percentage}%')
    print(f'   Descripción: {new_earning.description}')
    
    # Verificar que se asignó al estilista correcto
    if new_earning.employee == stylist:
        print('✅ Earning asignado al ESTILISTA correcto')
    else:
        print('❌ Earning asignado al empleado incorrecto')
else:
    print('❌ NO se creó earning')

# 5. MOSTRAR PAYLOAD NECESARIO PARA FRONTEND
print('\n5. PAYLOAD NECESARIO PARA FRONTEND:')
print('=' * 50)

required_payload = {
    "client": 1,
    "employee_id": manager.id,  # Manager que cobra
    "payment_method": "cash",
    "discount": 0,
    "total": 150,
    "paid": 150,
    "details": [
        {
            "content_type": "service",
            "object_id": service.id,
            "name": service.name,
            "quantity": 1,
            "price": 150,
            "employee_id": stylist.id  # ✅ ESTILISTA ESPECÍFICO
        }
    ],
    "payments": [
        {
            "amount": 150
        }
    ]
}

print('Payload requerido:')
print(json.dumps(required_payload, indent=2))

print('\n6. VERIFICACIÓN FINAL:')
print('=' * 50)

# Verificar persistencia
detail.refresh_from_db()
print(f'Detalle persistido:')
print(f'  Servicio: {detail.name}')
print(f'  Empleado: {detail.employee.user.email if detail.employee else "N/A"}')
print(f'  Precio: ${detail.price}')

print('\n✅ IMPLEMENTACIÓN COMPLETADA')
print('PRÓXIMOS PASOS:')
print('1. Modificar frontend POS para enviar employee_id en cada detail')
print('2. Separar claramente "quien cobra" vs "quien ejecuta"')
print('3. Probar flujo completo POS → Earnings → Payroll')

print('\n=== PRUEBA COMPLETADA ===')