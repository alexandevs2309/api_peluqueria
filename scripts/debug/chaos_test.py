#!/usr/bin/env python
"""
CHAOS ENGINEERING - Peor Día Posible
Simula: Stripe caído, Redis lento, 300 usuarios, tenant abusivo, 2M registros
"""
import os
import sys
import django
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.pos_api.models import Sale, SaleDetail
from apps.clients_api.models import Client
from apps.tenants_api.models import Tenant
from apps.services_api.models import Service
import requests

User = get_user_model()

# Configuración
BASE_URL = "http://localhost:8000"
CONCURRENT_USERS = 300
ABUSIVE_TENANT_REQUESTS = 1000  # requests/min
TOTAL_SALES = 2_000_000
DURATION_MINUTES = 5

# Resultados
results = {
    'total_requests': 0,
    'successful': 0,
    'failed': 0,
    'timeouts': 0,
    'errors': {},
    'response_times': [],
    'bottlenecks': []
}

lock = threading.Lock()


def log(message, level="INFO"):
    """Log con timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] [{level}] {message}")


def simulate_stripe_down():
    """Simular Stripe caído (mock)"""
    log("🔴 STRIPE DOWN - Webhooks fallarán", "CRITICAL")
    # En producción: bloquear puerto 443 a Stripe IPs
    return True


def simulate_redis_slow():
    """Simular Redis lento"""
    log("🟡 REDIS SLOW - Cache con latencia 500ms", "WARNING")
    # Agregar delay artificial en cache operations
    from django.core.cache import cache
    original_get = cache.get
    
    def slow_get(*args, **kwargs):
        time.sleep(0.5)  # 500ms delay
        return original_get(*args, **kwargs)
    
    cache.get = slow_get
    return True


def create_test_data():
    """Crear datos de prueba masivos"""
    log(f"📊 Creando {TOTAL_SALES:,} ventas de prueba...")
    
    # Crear superuser
    try:
        user = User.objects.get(email="chaos@test.com")
    except User.DoesNotExist:
        user = User.objects.create_superuser(
            email="chaos@test.com",
            password="chaos123",
            full_name="Chaos User"
        )
    
    # Crear tenant
    tenant, _ = Tenant.objects.get_or_create(
        name="Chaos Test Tenant",
        defaults={
            'is_active': True,
            'owner': user
        }
    )
    
    # Crear clientes
    clients = []
    for i in range(100):
        client, _ = Client.objects.get_or_create(
            tenant=tenant,
            full_name=f"Client {i}",
            defaults={'email': f'client{i}@test.com'}
        )
        clients.append(client)
    
    # Crear servicios
    services = []
    for i in range(20):
        service, _ = Service.objects.get_or_create(
            tenant=tenant,
            name=f"Service {i}",
            defaults={'price': random.randint(10, 100)}
        )
        services.append(service)
    
    log(f"✅ Datos base creados: {len(clients)} clientes, {len(services)} servicios")
    
    # Crear ventas en lotes
    batch_size = 10000
    total_created = Sale.objects.filter(tenant=tenant).count()
    
    if total_created < TOTAL_SALES:
        log(f"⏳ Creando {TOTAL_SALES - total_created:,} ventas adicionales...")
        
        for batch_start in range(total_created, TOTAL_SALES, batch_size):
            sales_batch = []
            for i in range(batch_start, min(batch_start + batch_size, TOTAL_SALES)):
                sale = Sale(
                    tenant=tenant,
                    user=user,
                    client=random.choice(clients),
                    total=random.randint(20, 200),
                    status='confirmed',
                    date_time=timezone.now() - timedelta(days=random.randint(0, 365))
                )
                sales_batch.append(sale)
            
            Sale.objects.bulk_create(sales_batch, ignore_conflicts=True)
            
            if batch_start % 100000 == 0:
                log(f"  📈 Creadas {batch_start:,} / {TOTAL_SALES:,} ventas")
        
        log(f"✅ Total ventas en DB: {Sale.objects.count():,}")
    else:
        log(f"✅ Ya existen {total_created:,} ventas")
    
    return tenant, user, clients, services


def make_request(url, method="GET", data=None, token=None, timeout=5):
    """Hacer request y medir tiempo"""
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    start = time.time()
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=timeout)
        else:
            resp = requests.post(url, json=data, headers=headers, timeout=timeout)
        
        elapsed = (time.time() - start) * 1000  # ms
        
        with lock:
            results['total_requests'] += 1
            results['response_times'].append(elapsed)
            
            if resp.status_code < 400:
                results['successful'] += 1
            else:
                results['failed'] += 1
                error_key = f"{resp.status_code}"
                results['errors'][error_key] = results['errors'].get(error_key, 0) + 1
        
        return resp.status_code, elapsed
    
    except requests.Timeout:
        with lock:
            results['total_requests'] += 1
            results['timeouts'] += 1
        return 'TIMEOUT', timeout * 1000
    
    except Exception as e:
        with lock:
            results['total_requests'] += 1
            results['failed'] += 1
            error_key = str(type(e).__name__)
            results['errors'][error_key] = results['errors'].get(error_key, 0) + 1
        return 'ERROR', 0


def normal_user_behavior(user_id, duration_sec):
    """Simular usuario normal"""
    endpoints = [
        '/api/pos/sales/',
        '/api/clients/',
        '/api/services/',
        '/api/appointments/',
        '/api/reports/dashboard-stats/',
    ]
    
    end_time = time.time() + duration_sec
    request_count = 0
    
    while time.time() < end_time:
        endpoint = random.choice(endpoints)
        url = f"{BASE_URL}{endpoint}"
        
        status, elapsed = make_request(url)
        request_count += 1
        
        # Detectar bottleneck
        if elapsed > 3000:  # >3s
            with lock:
                results['bottlenecks'].append({
                    'endpoint': endpoint,
                    'elapsed_ms': elapsed,
                    'status': status
                })
        
        # Usuario normal espera entre requests
        time.sleep(random.uniform(1, 3))
    
    return request_count


def abusive_tenant_behavior(duration_sec):
    """Simular tenant abusivo (1000 req/min)"""
    log("🔥 TENANT ABUSIVO iniciado - 1000 req/min", "WARNING")
    
    end_time = time.time() + duration_sec
    request_count = 0
    
    while time.time() < end_time:
        # Spam de requests
        url = f"{BASE_URL}/api/pos/sales/"
        make_request(url)
        request_count += 1
        
        # 1000 req/min = 1 req cada 60ms
        time.sleep(0.06)
    
    log(f"🔥 TENANT ABUSIVO completado - {request_count} requests", "WARNING")
    return request_count


def heavy_query_load(duration_sec):
    """Queries pesadas en DB con 2M registros"""
    log("💾 HEAVY QUERIES iniciadas", "WARNING")
    
    end_time = time.time() + duration_sec
    query_count = 0
    
    while time.time() < end_time:
        # Query pesada: ventas del último año con joins
        url = f"{BASE_URL}/api/reports/sales-report/?start_date=2023-01-01&end_date=2024-12-31"
        status, elapsed = make_request(url, timeout=30)
        
        query_count += 1
        
        if elapsed > 10000:  # >10s
            log(f"  ⚠️  Query lenta: {elapsed:.0f}ms", "WARNING")
        
        time.sleep(5)  # Query cada 5s
    
    log(f"💾 HEAVY QUERIES completadas - {query_count} queries", "WARNING")
    return query_count


def run_chaos_test():
    """Ejecutar test de caos completo"""
    log("=" * 80, "INFO")
    log("🔥 INICIANDO CHAOS ENGINEERING TEST", "CRITICAL")
    log("=" * 80, "INFO")
    
    # Fase 1: Preparación
    log("\n📋 FASE 1: PREPARACIÓN")
    tenant, user, clients, services = create_test_data()
    
    # Fase 2: Simular fallos
    log("\n💥 FASE 2: SIMULANDO FALLOS")
    simulate_stripe_down()
    simulate_redis_slow()
    
    # Fase 3: Carga concurrente
    log(f"\n🚀 FASE 3: CARGA CONCURRENTE ({CONCURRENT_USERS} usuarios)")
    log(f"⏱️  Duración: {DURATION_MINUTES} minutos")
    
    duration_sec = DURATION_MINUTES * 60
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=CONCURRENT_USERS + 2) as executor:
        futures = []
        
        # Usuarios normales
        for i in range(CONCURRENT_USERS - 1):
            future = executor.submit(normal_user_behavior, i, duration_sec)
            futures.append(('normal', future))
        
        # Tenant abusivo
        future = executor.submit(abusive_tenant_behavior, duration_sec)
        futures.append(('abusive', future))
        
        # Heavy queries
        future = executor.submit(heavy_query_load, duration_sec)
        futures.append(('heavy', future))
        
        # Monitorear progreso
        completed = 0
        for user_type, future in as_completed([f[1] for f in futures]):
            completed += 1
            progress = (completed / len(futures)) * 100
            log(f"  ⏳ Progreso: {progress:.1f}% ({completed}/{len(futures)})")
    
    elapsed_time = time.time() - start_time
    
    # Fase 4: Análisis
    log("\n📊 FASE 4: ANÁLISIS DE RESULTADOS")
    analyze_results(elapsed_time)


def analyze_results(elapsed_time):
    """Analizar resultados y detectar cuellos de botella"""
    
    log("=" * 80)
    log("📈 RESULTADOS DEL CHAOS TEST")
    log("=" * 80)
    
    # Estadísticas generales
    total = results['total_requests']
    success_rate = (results['successful'] / total * 100) if total > 0 else 0
    
    log(f"\n🔢 ESTADÍSTICAS GENERALES:")
    log(f"  Total requests: {total:,}")
    log(f"  Exitosos: {results['successful']:,} ({success_rate:.1f}%)")
    log(f"  Fallidos: {results['failed']:,}")
    log(f"  Timeouts: {results['timeouts']:,}")
    log(f"  Duración: {elapsed_time:.1f}s")
    log(f"  Throughput: {total/elapsed_time:.1f} req/s")
    
    # Tiempos de respuesta
    if results['response_times']:
        times = sorted(results['response_times'])
        p50 = times[len(times)//2]
        p95 = times[int(len(times)*0.95)]
        p99 = times[int(len(times)*0.99)]
        avg = sum(times) / len(times)
        
        log(f"\n⏱️  TIEMPOS DE RESPUESTA:")
        log(f"  Promedio: {avg:.0f}ms")
        log(f"  P50: {p50:.0f}ms")
        log(f"  P95: {p95:.0f}ms")
        log(f"  P99: {p99:.0f}ms")
        log(f"  Max: {max(times):.0f}ms")
    
    # Errores
    if results['errors']:
        log(f"\n❌ ERRORES DETECTADOS:")
        for error, count in sorted(results['errors'].items(), key=lambda x: x[1], reverse=True):
            log(f"  {error}: {count:,} veces")
    
    # Bottlenecks
    if results['bottlenecks']:
        log(f"\n🚨 CUELLOS DE BOTELLA (>{3000}ms):")
        bottlenecks_by_endpoint = {}
        for b in results['bottlenecks']:
            endpoint = b['endpoint']
            if endpoint not in bottlenecks_by_endpoint:
                bottlenecks_by_endpoint[endpoint] = []
            bottlenecks_by_endpoint[endpoint].append(b['elapsed_ms'])
        
        for endpoint, times in sorted(bottlenecks_by_endpoint.items(), key=lambda x: len(x[1]), reverse=True):
            avg_time = sum(times) / len(times)
            log(f"  {endpoint}: {len(times)} veces (avg: {avg_time:.0f}ms)")
    
    # Diagnóstico
    log(f"\n🔍 DIAGNÓSTICO:")
    
    if success_rate < 95:
        log(f"  🔴 CRÍTICO: Tasa de éxito baja ({success_rate:.1f}%)")
        log(f"     → Sistema no soporta carga concurrente")
    
    if results['timeouts'] > total * 0.05:
        log(f"  🔴 CRÍTICO: Muchos timeouts ({results['timeouts']:,})")
        log(f"     → Queries lentas o DB sobrecargada")
    
    if p95 > 2000:
        log(f"  🟡 ADVERTENCIA: P95 alto ({p95:.0f}ms)")
        log(f"     → Optimizar queries o agregar índices")
    
    if '429' in results['errors']:
        log(f"  🟢 BUENO: Rate limiting funcionando ({results['errors']['429']} bloqueados)")
    
    if '500' in results['errors']:
        log(f"  🔴 CRÍTICO: Errores de servidor ({results['errors']['500']})")
        log(f"     → Revisar logs de aplicación")
    
    # Recomendaciones
    log(f"\n💡 RECOMENDACIONES:")
    
    if p95 > 2000:
        log(f"  1. Agregar índices en campos filtrados frecuentemente")
        log(f"  2. Implementar paginación en endpoints pesados")
        log(f"  3. Agregar cache en queries repetitivas")
    
    if results['timeouts'] > 0:
        log(f"  4. Aumentar workers de Gunicorn")
        log(f"  5. Configurar connection pooling en PostgreSQL")
    
    if success_rate < 99:
        log(f"  6. Implementar circuit breaker para servicios externos")
        log(f"  7. Agregar retry logic en tasks críticas")
    
    log("\n" + "=" * 80)
    
    # Veredicto final
    if success_rate >= 99 and p95 < 2000:
        log("✅ VEREDICTO: Sistema ROBUSTO - Soporta carga extrema")
    elif success_rate >= 95 and p95 < 5000:
        log("🟡 VEREDICTO: Sistema ESTABLE - Mejoras recomendadas")
    else:
        log("🔴 VEREDICTO: Sistema FRÁGIL - Optimización urgente")
    
    log("=" * 80)


if __name__ == '__main__':
    try:
        run_chaos_test()
    except KeyboardInterrupt:
        log("\n⚠️  Test interrumpido por usuario", "WARNING")
        analyze_results(time.time())
    except Exception as e:
        log(f"\n❌ Error fatal: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
