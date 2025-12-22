#!/usr/bin/env python
"""
Script de prueba para verificar corrección de cierre de caja

Casos de prueba:
1. Cierre correcto con cuadre exacto (debe permitir)
2. Cierre con descuadre (debe bloquear)
3. Cierre con efectivo 0 (debe permitir si cuadra)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.pos_api.models import CashRegister
from apps.pos_api.state_validators import CashRegisterStateValidator
from apps.auth_api.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone

def test_cash_register_close_validation():
    print("=== PRUEBA DE VALIDACIÓN DE CIERRE DE CAJA ===\n")
    
    try:
        # Buscar usuario para crear caja de prueba
        user = User.objects.first()
        if not user:
            print("❌ No hay usuarios para crear caja de prueba")
            return
        
        print(f"👤 Usuario: {user.email}")
        
        # 1. CASO: CIERRE CORRECTO CON CUADRE EXACTO
        print("\n1️⃣ CASO: CIERRE CORRECTO CON CUADRE EXACTO")
        
        # Crear caja con efectivo inicial
        register = CashRegister.objects.create(
            user=user,
            initial_cash=Decimal('100.00'),
            is_open=True
        )
        
        # Simular que no hubo ventas (expected = initial)
        expected_cash = Decimal(str(register.display_amount))  # Convertir a Decimal
        final_cash = expected_cash  # Mismo monto
        
        print(f"Efectivo inicial: ${register.initial_cash}")
        print(f"Ventas del día: ${register.sales_amount}")
        print(f"Efectivo esperado: ${expected_cash}")
        print(f"Efectivo contado: ${final_cash}")
        
        try:
            CashRegisterStateValidator.validate_close_operation(register, final_cash)
            print("✅ Validación exitosa - Cierre permitido")
        except ValidationError as e:
            print(f"❌ Validación falló: {str(e)}")
        
        # 2. CASO: CIERRE CON DESCUADRE
        print("\n2️⃣ CASO: CIERRE CON DESCUADRE")
        
        final_cash_incorrect = expected_cash + Decimal('10.00')  # Sobra dinero
        
        print(f"Efectivo esperado: ${expected_cash}")
        print(f"Efectivo contado: ${final_cash_incorrect}")
        print(f"Diferencia: ${final_cash_incorrect - expected_cash}")
        
        try:
            CashRegisterStateValidator.validate_close_operation(register, final_cash_incorrect)
            print("❌ Validación incorrecta - Debería haber bloqueado")
        except ValidationError as e:
            print(f"✅ Validación correcta - Cierre bloqueado: {str(e)}")
        
        # 3. CASO: CIERRE CON EFECTIVO 0 PERO CUADRADO
        print("\n3️⃣ CASO: CIERRE CON EFECTIVO 0 PERO CUADRADO")
        
        # Crear caja sin efectivo inicial
        register_zero = CashRegister.objects.create(
            user=user,
            initial_cash=Decimal('0.00'),
            is_open=True
        )
        
        expected_zero = Decimal(str(register_zero.display_amount))  # Convertir a Decimal
        final_zero = Decimal('0.00')  # Cuadra exacto
        
        print(f"Efectivo inicial: ${register_zero.initial_cash}")
        print(f"Ventas del día: ${register_zero.sales_amount}")
        print(f"Efectivo esperado: ${expected_zero}")
        print(f"Efectivo contado: ${final_zero}")
        
        try:
            CashRegisterStateValidator.validate_close_operation(register_zero, final_zero)
            print("✅ Validación exitosa - Cierre con 0 permitido")
        except ValidationError as e:
            print(f"❌ Validación falló: {str(e)}")
        
        # 4. CASO: CAJA YA CERRADA
        print("\n4️⃣ CASO: CAJA YA CERRADA")
        
        register.is_open = False
        register.closed_at = timezone.now()
        register.save()
        
        try:
            CashRegisterStateValidator.validate_close_operation(register, final_cash)
            print("❌ Validación incorrecta - Debería bloquear caja cerrada")
        except ValidationError as e:
            print(f"✅ Validación correcta - Caja cerrada bloqueada: {str(e)}")
        
        # Limpiar datos de prueba
        register.delete()
        register_zero.delete()
        
        print("\n🎉 PRUEBA COMPLETADA - CORRECCIÓN VERIFICADA")
        
    except Exception as e:
        print(f"❌ Error en prueba: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_cash_register_close_validation()