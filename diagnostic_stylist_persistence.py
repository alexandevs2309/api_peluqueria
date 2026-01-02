#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.pos_api.models import Sale, SaleDetail
from apps.employees_api.models import Employee
from apps.services_api.models import ServiceEmployee

print('=== REVISIÓN PERSISTENCIA ESTILISTA EN POS ===')

# 1. REVISAR ESTRUCTURA DE MODELOS
print('\n1. ESTRUCTURA DE MODELOS:')
print('=' * 50)

print('Sale model fields:')
sale_fields = [f.name for f in Sale._meta.fields]
print(f'  - {sale_fields}')

print('\nSaleDetail model fields:')
detail_fields = [f.name for f in SaleDetail._meta.fields]
print(f'  - {detail_fields}')

print('\n❌ PROBLEMA IDENTIFICADO:')
print('  - Sale.employee: empleado general de la venta (quien cobra)')
print('  - SaleDetail NO tiene campo employee (estilista específico del servicio)')

# 2. REVISAR VENTAS RECIENTES
print('\n\n2. VENTAS RECIENTES:')
print('=' * 50)

recent_sales = Sale.objects.order_by('-date_time')[:3]

for sale in recent_sales:
    print(f'\nVenta #{sale.id}:')
    print(f'  Usuario que cobra: {sale.user.email if sale.user else "N/A"}')
    print(f'  Empleado asignado: {sale.employee.user.email if sale.employee else "N/A"}')
    print(f'  Fecha: {sale.date_time}')
    
    print('  Servicios:')
    for detail in sale.details.filter(content_type__model='service'):
        print(f'    - {detail.name} (${detail.price})')
        print(f'      Estilista específico: NO PERSISTIDO ❌')
        
        # Buscar en ServiceEmployee para ver quién debería ser
        try:
            service_employee = ServiceEmployee.objects.filter(
                service_id=detail.object_id
            ).first()
            if service_employee:
                print(f'      Debería ser: {service_employee.employee.user.email}')
            else:
                print(f'      Sin ServiceEmployee configurado')
        except:
            print(f'      Error buscando ServiceEmployee')

# 3. REVISAR LÓGICA ACTUAL DE EARNINGS
print('\n\n3. LÓGICA ACTUAL DE EARNINGS:')
print('=' * 50)

print('Problema en _create_employee_earning:')
print('  1. Busca ServiceEmployee por service_id')
print('  2. Si no encuentra, usa sale.employee (empleado general)')
print('  3. Pero sale.employee puede ser el manager/cajera')
print('  4. NO hay persistencia del estilista real por servicio')

# 4. VERIFICAR PAYLOAD ESPERADO
print('\n\n4. PAYLOAD ESPERADO DEL FRONTEND:')
print('=' * 50)

print('Estructura actual en SaleDetailSerializer:')
print('  - content_type: "service"')
print('  - object_id: ID del servicio')
print('  - name: nombre del servicio')
print('  - quantity: cantidad')
print('  - price: precio')
print('  - ❌ FALTA: employee_id del estilista')

# 5. DIAGNÓSTICO FINAL
print('\n\n5. DIAGNÓSTICO FINAL:')
print('=' * 50)

print('PROBLEMAS IDENTIFICADOS:')
print('  A) MODELO: SaleDetail NO tiene campo employee')
print('  B) SERIALIZER: No acepta employee_id en el payload')
print('  C) LÓGICA: Usa ServiceEmployee como fallback, no como fuente de verdad')
print('  D) PERSISTENCIA: El estilista real se pierde después de la venta')

print('\nSOLUCIONES NECESARIAS:')
print('  1. Agregar campo employee a SaleDetail')
print('  2. Modificar SaleDetailSerializer para aceptar employee_id')
print('  3. Actualizar lógica de earnings para usar detail.employee')
print('  4. Migración de datos existentes')

print('\nIMPACTO:')
print('  - Estilistas no aparecen en nómina correctamente')
print('  - Comisiones se asignan al empleado incorrecto')
print('  - Pérdida de trazabilidad servicio-estilista')

print('\n=== REVISIÓN COMPLETADA ===')