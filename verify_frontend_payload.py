#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.pos_api.models import Sale, SaleDetail
import json

print('=== VERIFICACIÓN PAYLOAD FRONTEND ===')

# 1. REVISAR ESTRUCTURA ACTUAL DE VENTA
print('\n1. ESTRUCTURA ACTUAL DE VENTA EN BD:')
print('=' * 50)

recent_sale = Sale.objects.order_by('-date_time').first()
if recent_sale:
    print(f'Venta #{recent_sale.id}:')
    print(f'  Usuario: {recent_sale.user.email}')
    print(f'  Empleado: {recent_sale.employee.user.email if recent_sale.employee else "N/A"}')
    print(f'  Total: ${recent_sale.total}')
    
    print('\n  Detalles guardados:')
    for detail in recent_sale.details.all():
        print(f'    - {detail.name}:')
        print(f'      content_type: {detail.content_type}')
        print(f'      object_id: {detail.object_id}')
        print(f'      price: ${detail.price}')
        print(f'      quantity: {detail.quantity}')
        print(f'      ❌ employee: NO EXISTE')

# 2. SIMULAR PAYLOAD ACTUAL DEL FRONTEND
print('\n\n2. PAYLOAD ACTUAL DEL FRONTEND (SIMULADO):')
print('=' * 50)

current_payload = {
    "client": 1,
    "employee_id": 4,  # Empleado general de la venta
    "payment_method": "cash",
    "discount": 0,
    "total": 200,
    "paid": 200,
    "details": [
        {
            "content_type": "service",
            "object_id": 6,
            "name": "Corte Clásico",
            "quantity": 1,
            "price": 100
            # ❌ FALTA: "employee_id": 4 (estilista específico)
        },
        {
            "content_type": "service", 
            "object_id": 7,
            "name": "Corte Moderno/Fade",
            "quantity": 1,
            "price": 100
            # ❌ FALTA: "employee_id": 3 (estilista específico)
        }
    ],
    "payments": [
        {
            "amount": 200
        }
    ]
}

print('Payload actual:')
print(json.dumps(current_payload, indent=2))

# 3. PAYLOAD NECESARIO PARA SOLUCIÓN
print('\n\n3. PAYLOAD NECESARIO (CON ESTILISTA POR SERVICIO):')
print('=' * 50)

required_payload = {
    "client": 1,
    "employee_id": 1,  # Manager/cajera que cobra
    "payment_method": "cash",
    "discount": 0,
    "total": 200,
    "paid": 200,
    "details": [
        {
            "content_type": "service",
            "object_id": 6,
            "name": "Corte Clásico",
            "quantity": 1,
            "price": 100,
            "employee_id": 4  # ✅ ESTILISTA ESPECÍFICO
        },
        {
            "content_type": "service",
            "object_id": 7, 
            "name": "Corte Moderno/Fade",
            "quantity": 1,
            "price": 100,
            "employee_id": 3  # ✅ ESTILISTA ESPECÍFICO
        }
    ],
    "payments": [
        {
            "amount": 200
        }
    ]
}

print('Payload necesario:')
print(json.dumps(required_payload, indent=2))

# 4. ANÁLISIS DE DIFERENCIAS
print('\n\n4. ANÁLISIS DE DIFERENCIAS:')
print('=' * 50)

print('DIFERENCIAS CLAVE:')
print('  1. Sale.employee_id: Manager/cajera que cobra la venta')
print('  2. SaleDetail.employee_id: Estilista específico que ejecuta cada servicio')
print('  3. Separación clara de responsabilidades:')
print('     - Quien cobra vs quien ejecuta el servicio')

print('\nIMPLICACIONES:')
print('  - Frontend debe enviar employee_id en cada detail de servicio')
print('  - Backend debe persistir este employee_id en SaleDetail')
print('  - Earnings deben usar detail.employee, no sale.employee')

print('\nESTADO ACTUAL:')
print('  ❌ Frontend NO envía employee_id en details')
print('  ❌ SaleDetail NO tiene campo employee')
print('  ❌ Earnings usan ServiceEmployee como fallback')
print('  ❌ Pérdida de información del estilista real')

print('\n=== VERIFICACIÓN COMPLETADA ===')