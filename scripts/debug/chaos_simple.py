#!/usr/bin/env python
"""
CHAOS TEST SIMPLIFICADO - Solo stress HTTP
"""
import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

BASE_URL = "http://localhost:8000"
CONCURRENT_USERS = 100
DURATION_SEC = 60

# Credenciales para test
TEST_EMAIL = "alejav.zuniga@gmail.com"
TEST_PASSWORD = "baspeka1394"

results = {
    'total': 0,
    'success': 0,
    'failed': 0,
    'timeouts': 0,
    'times': [],
    'errors': {}
}
lock = threading.Lock()
token = None

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_auth_token():
    """Obtener token de autenticación"""
    try:
        resp = requests.post(
            f"{BASE_URL}/api/auth/login/",
            json={'email': TEST_EMAIL, 'password': TEST_PASSWORD},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get('access') or data.get('access_token')
    except Exception as e:
        log(f"❌ Error obteniendo token: {e}")
    return None

def make_request(url, timeout=5):
    start = time.time()
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        elapsed = (time.time() - start) * 1000
        
        with lock:
            results['total'] += 1
            results['times'].append(elapsed)
            if resp.status_code < 400:
                results['success'] += 1
            else:
                results['failed'] += 1
                results['errors'][resp.status_code] = results['errors'].get(resp.status_code, 0) + 1
        
        return resp.status_code, elapsed
    except requests.Timeout:
        with lock:
            results['total'] += 1
            results['timeouts'] += 1
        return 'TIMEOUT', timeout * 1000
    except Exception as e:
        with lock:
            results['total'] += 1
            results['failed'] += 1
        return 'ERROR', 0

def user_load(user_id, duration):
    endpoints = [
        '/api/healthz/',
        '/api/pos/sales/',
        '/api/clients/',
        '/api/services/',
        '/api/appointments/',
    ]
    
    end_time = time.time() + duration
    count = 0
    
    while time.time() < end_time:
        url = f"{BASE_URL}{endpoints[count % len(endpoints)]}"
        make_request(url)
        count += 1
        time.sleep(0.1)
    
    return count

log("🔥 INICIANDO CHAOS TEST AUTENTICADO")
log(f"🔑 Obteniendo token...")

token = get_auth_token()
if not token:
    log("❌ No se pudo obtener token. Abortando.")
    exit(1)

log(f"✅ Token obtenido")
log(f"👥 {CONCURRENT_USERS} usuarios concurrentes")
log(f"⏱️  {DURATION_SEC} segundos")

start = time.time()

with ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
    futures = [executor.submit(user_load, i, DURATION_SEC) for i in range(CONCURRENT_USERS)]
    for f in futures:
        f.result()

elapsed = time.time() - start

log("\n" + "="*60)
log("📊 RESULTADOS")
log("="*60)

total = results['total']
success_rate = (results['success'] / total * 100) if total > 0 else 0

log(f"Total requests: {total:,}")
log(f"Exitosos: {results['success']:,} ({success_rate:.1f}%)")
log(f"Fallidos: {results['failed']:,}")
log(f"Timeouts: {results['timeouts']:,}")
log(f"Throughput: {total/elapsed:.1f} req/s")

if results['times']:
    times = sorted(results['times'])
    log(f"\nTiempos:")
    log(f"  P50: {times[len(times)//2]:.0f}ms")
    log(f"  P95: {times[int(len(times)*0.95)]:.0f}ms")
    log(f"  P99: {times[int(len(times)*0.99)]:.0f}ms")
    log(f"  Max: {max(times):.0f}ms")

if results['errors']:
    log(f"\nErrores:")
    for code, count in results['errors'].items():
        log(f"  {code}: {count}")

log("\n" + "="*60)

if success_rate >= 99:
    log("✅ Sistema ROBUSTO")
elif success_rate >= 95:
    log("🟡 Sistema ESTABLE")
else:
    log("🔴 Sistema FRÁGIL")

log("\n⚠️  IMPORTANTE: Cambia la contraseña inmediatamente")
