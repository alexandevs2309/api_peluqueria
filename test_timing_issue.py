#!/usr/bin/env python3
"""
Script para verificar el problema de sincronización entre:
1. Creación de venta en POS
2. Ejecución asíncrona de Celery (create_earning_from_sale)
3. Consulta inmediata del frontend (earnings_summary)

OBJETIVO: Determinar si el problema es un desfase temporal
"""
import os
import django
import time
import requests
from datetime import datetime
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.pos_api.models import Sale
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import FortnightSummary
from apps.employees_api.tasks import create_earning_from_sale

User = get_user_model()

def test_timing_synchronization():
    """Probar sincronización entre venta, earnings y consulta frontend"""
    
    print("🔍 INICIANDO PRUEBA DE SINCRONIZACIÓN")
    print("=" * 60)
    
    # 1. Obtener datos de prueba
    try:
        user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
        tenant = user.tenant
        employee = Employee.objects.filter(tenant=tenant, is_active=True).first()
        
        if not employee:
            print("❌ No hay empleados activos para prueba")
            return
            
        print(f"👤 Empleado de prueba: {employee.user.full_name}")
        print(f"🏢 Tenant: {tenant.name}")
        print(f"💼 Tipo salario: {employee.salary_type}")
        print(f"📊 Comisión: {employee.commission_percentage}%")
        
    except Exception as e:
        print(f"❌ Error obteniendo datos: {e}")
        return
    
    # 2. CREAR VENTA SIMULADA (como lo hace el POS)
    print("\n📝 PASO 1: Creando venta...")
    
    try:
        # Simular creación de venta
        sale = Sale.objects.create(
            user=user,
            employee=employee,
            total=Decimal('100.00'),
            status='completed',
            closed=False,
            earnings_generated=False
        )
        
        timestamp_venta = datetime.now()
        print(f"✅ Venta creada: ID={sale.id}, Total=${sale.total}")
        print(f"⏰ Timestamp venta: {timestamp_venta.strftime('%H:%M:%S.%f')}")
        
    except Exception as e:
        print(f"❌ Error creando venta: {e}")
        return
    
    # 3. CONSULTA INMEDIATA (como lo hace el frontend)
    print("\n🔍 PASO 2: Consultando earnings_summary INMEDIATAMENTE...")
    
    try:
        # Simular consulta inmediata del frontend
        from apps.employees_api.payments_views import PaymentViewSet
        
        # Crear request mock
        class MockRequest:
            def __init__(self, user):
                self.user = user
                self.GET = {}
        
        mock_request = MockRequest(user)
        payment_viewset = PaymentViewSet()
        payment_viewset.request = mock_request
        
        response = payment_viewset.earnings_summary(mock_request)
        timestamp_consulta = datetime.now()
        
        print(f"⏰ Timestamp consulta: {timestamp_consulta.strftime('%H:%M:%S.%f')}")
        print(f"⚡ Diferencia: {(timestamp_consulta - timestamp_venta).total_seconds():.3f} segundos")
        
        # Buscar empleado en respuesta
        employees = response.data.get('employees', [])
        empleado_data = next((emp for emp in employees if emp['employee_id'] == employee.id), None)
        
        if empleado_data:
            print(f"📊 Datos del empleado en respuesta:")
            print(f"   - pending_amount: {empleado_data.get('pending_amount', 0)}")
            print(f"   - pending_sale_ids: {empleado_data.get('pending_sale_ids', [])}")
            print(f"   - services_count: {empleado_data.get('services_count', 0)}")
            print(f"   - payment_status: {empleado_data.get('payment_status', 'unknown')}")
            
            # VERIFICAR SI LA VENTA APARECE
            if sale.id in empleado_data.get('pending_sale_ids', []):
                print("✅ VENTA DETECTADA: La venta aparece inmediatamente en pending_sale_ids")
            else:
                print("❌ VENTA NO DETECTADA: La venta NO aparece en pending_sale_ids")
                print(f"   Sale ID buscado: {sale.id}")
                print(f"   Sale IDs encontrados: {empleado_data.get('pending_sale_ids', [])}")
        else:
            print("❌ Empleado no encontrado en respuesta")
            
    except Exception as e:
        print(f"❌ Error en consulta inmediata: {e}")
    
    # 4. EJECUTAR TAREA CELERY MANUALMENTE
    print("\n⚙️ PASO 3: Ejecutando tarea Celery manualmente...")
    
    try:
        external_id = f"sale-{sale.id}-{sale.date_time.strftime('%Y%m%d%H%M%S')}"
        
        # Ejecutar tarea de forma síncrona para prueba
        result = create_earning_from_sale(sale.id, external_id)
        timestamp_celery = datetime.now()
        
        print(f"⏰ Timestamp Celery: {timestamp_celery.strftime('%H:%M:%S.%f')}")
        print(f"⚡ Diferencia desde venta: {(timestamp_celery - timestamp_venta).total_seconds():.3f} segundos")
        print(f"📊 Resultado Celery: {result}")
        
    except Exception as e:
        print(f"❌ Error ejecutando Celery: {e}")
    
    # 5. CONSULTA DESPUÉS DE CELERY
    print("\n🔍 PASO 4: Consultando earnings_summary DESPUÉS de Celery...")
    
    try:
        response_post = payment_viewset.earnings_summary(mock_request)
        timestamp_consulta_post = datetime.now()
        
        print(f"⏰ Timestamp consulta post: {timestamp_consulta_post.strftime('%H:%M:%S.%f')}")
        
        employees_post = response_post.data.get('employees', [])
        empleado_data_post = next((emp for emp in employees_post if emp['employee_id'] == employee.id), None)
        
        if empleado_data_post:
            print(f"📊 Datos del empleado DESPUÉS de Celery:")
            print(f"   - pending_amount: {empleado_data_post.get('pending_amount', 0)}")
            print(f"   - pending_sale_ids: {empleado_data_post.get('pending_sale_ids', [])}")
            print(f"   - services_count: {empleado_data_post.get('services_count', 0)}")
            print(f"   - payment_status: {empleado_data_post.get('payment_status', 'unknown')}")
            
            # COMPARAR ANTES Y DESPUÉS
            print(f"\n📈 COMPARACIÓN:")
            print(f"   ANTES  - pending_amount: {empleado_data.get('pending_amount', 0) if empleado_data else 0}")
            print(f"   DESPUÉS - pending_amount: {empleado_data_post.get('pending_amount', 0)}")
            
            if empleado_data and empleado_data_post:
                if empleado_data['pending_amount'] != empleado_data_post['pending_amount']:
                    print("🔄 CAMBIO DETECTADO: El monto cambió después de Celery")
                else:
                    print("🔄 SIN CAMBIO: El monto es igual antes y después de Celery")
    
    except Exception as e:
        print(f"❌ Error en consulta post-Celery: {e}")
    
    # 6. VERIFICAR ESTADO DE LA BASE DE DATOS
    print("\n🗄️ PASO 5: Verificando estado de la base de datos...")
    
    try:
        # Recargar venta
        sale.refresh_from_db()
        print(f"📝 Estado de la venta:")
        print(f"   - earnings_generated: {sale.earnings_generated}")
        print(f"   - period: {sale.period}")
        
        # Verificar FortnightSummary
        summaries = FortnightSummary.objects.filter(employee=employee)
        print(f"📊 FortnightSummary encontrados: {summaries.count()}")
        
        for summary in summaries:
            print(f"   - Año/Quincena: {summary.fortnight_year}/{summary.fortnight_number}")
            print(f"   - Total earnings: {summary.total_earnings}")
            print(f"   - Total services: {summary.total_services}")
            print(f"   - Is paid: {summary.is_paid}")
        
        # Verificar ventas sin período
        ventas_sin_periodo = Sale.objects.filter(
            employee=employee,
            status='completed',
            period__isnull=True
        )
        print(f"🔍 Ventas sin período: {ventas_sin_periodo.count()}")
        for venta in ventas_sin_periodo:
            print(f"   - Sale ID: {venta.id}, Total: ${venta.total}")
            
    except Exception as e:
        print(f"❌ Error verificando BD: {e}")
    
    # 7. CONCLUSIONES
    print("\n" + "=" * 60)
    print("📋 CONCLUSIONES:")
    print("=" * 60)
    
    print("1. ¿La venta aparece inmediatamente en earnings_summary?")
    if empleado_data and sale.id in empleado_data.get('pending_sale_ids', []):
        print("   ✅ SÍ - La venta aparece inmediatamente")
        print("   💡 El problema NO es desfase temporal")
    else:
        print("   ❌ NO - La venta NO aparece inmediatamente")
        print("   💡 Posible problema de filtrado o lógica de consulta")
    
    print("\n2. ¿earnings_summary depende de Earnings creados por Celery?")
    if empleado_data and empleado_data_post:
        if empleado_data['pending_amount'] != empleado_data_post['pending_amount']:
            print("   ✅ SÍ - El monto cambia después de Celery")
            print("   💡 earnings_summary depende de Earnings")
        else:
            print("   ❌ NO - El monto no cambia después de Celery")
            print("   💡 earnings_summary NO depende de Earnings")
    
    print("\n3. Recomendación:")
    if empleado_data and sale.id not in empleado_data.get('pending_sale_ids', []):
        print("   🔧 REVISAR LÓGICA DE FILTRADO en earnings_summary")
        print("   🔧 Verificar que las ventas se asignen correctamente al período")
    else:
        print("   🔧 REVISAR LÓGICA DE CÁLCULO DE MONTOS")
        print("   🔧 Posible problema en _calculate_payment_amount")
    
    # Limpiar datos de prueba
    print(f"\n🧹 Limpiando venta de prueba ID={sale.id}...")
    sale.delete()
    print("✅ Limpieza completada")

if __name__ == "__main__":
    test_timing_synchronization()