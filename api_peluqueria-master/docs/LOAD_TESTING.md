# Load Testing - Guía Ejecutable

## Instalación de k6

### Linux
```bash
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

### macOS
```bash
brew install k6
```

### Windows
```bash
choco install k6
```

## Ejecución Rápida

```bash
# 1. Configurar variables
export BASE_URL="http://localhost"
export API_TOKEN="tu-token-aqui"

# 2. Ejecutar test interactivo
chmod +x ops/run-load-test.sh
./ops/run-load-test.sh

# 3. O ejecutar directamente
k6 run -e BASE_URL=$BASE_URL -e API_TOKEN=$API_TOKEN ops/load-test.js
```

## Tipos de Tests

### 1. Smoke Test (Validación Básica)
```bash
k6 run --vus 1 --duration 1m ops/load-test.js
```
**Objetivo**: Verificar que el sistema funciona sin carga
**Criterio**: 0% errores

### 2. Load Test (Carga Normal)
```bash
k6 run ops/load-test.js
```
**Objetivo**: Simular 50-100 usuarios concurrentes
**Criterio**: p95 < 2s, errores < 1%

### 3. Stress Test (Límites)
```bash
k6 run --vus 100 --duration 15m ops/load-test.js
```
**Objetivo**: Encontrar punto de quiebre
**Criterio**: Identificar cuando degrada

### 4. Spike Test (Picos)
```bash
k6 run --stage 0s:0,10s:200,1m:200,10s:0 ops/load-test.js
```
**Objetivo**: Validar recuperación ante picos
**Criterio**: Sistema se recupera sin caídas

### 5. Soak Test (Estabilidad)
```bash
k6 run --vus 50 --duration 1h ops/load-test.js
```
**Objetivo**: Detectar memory leaks
**Criterio**: Performance estable durante 1 hora

## Interpretación de Resultados

### Métricas Clave

```
http_req_duration..............: avg=450ms  p(95)=1.2s
http_req_failed................: 0.15%
http_reqs......................: 15000 (250/s)
vus............................: 50
```

**✅ BUENO:**
- p95 < 2s
- Error rate < 1%
- Throughput estable

**⚠️ WARNING:**
- p95 entre 2-3s
- Error rate 1-5%
- Throughput decreciente

**❌ CRÍTICO:**
- p95 > 3s
- Error rate > 5%
- Timeouts frecuentes

## Escenarios de Producción

### 50 Tenants Activos
```bash
# Carga esperada: ~25 requests/segundo
k6 run --vus 50 --duration 10m ops/load-test.js
```

### 100 Tenants Activos
```bash
# Carga esperada: ~50 requests/segundo
k6 run --vus 100 --duration 10m ops/load-test.js
```

### Black Friday (Pico)
```bash
# Simular 3x carga normal
k6 run --stage 1m:50,2m:150,5m:150,2m:50 ops/load-test.js
```

## Monitoreo Durante Tests

### Terminal 1: Load Test
```bash
k6 run ops/load-test.js
```

### Terminal 2: Logs en Tiempo Real
```bash
docker-compose logs -f web
```

### Terminal 3: Métricas del Sistema
```bash
watch -n 2 'curl -s http://localhost/health/ | jq'
```

### Terminal 4: Recursos del Sistema
```bash
docker stats
```

## Análisis Post-Test

### 1. Revisar Health Endpoint
```bash
curl http://localhost/health/ | jq
```

### 2. Verificar Logs de Errores
```bash
docker-compose logs web | grep ERROR | tail -20
```

### 3. Métricas de Base de Datos
```bash
docker exec $(docker ps -q -f name=db) psql -U postgres -d peluqueria_db -c "
SELECT 
  schemaname,
  tablename,
  seq_scan,
  idx_scan,
  n_tup_ins,
  n_tup_upd
FROM pg_stat_user_tables 
ORDER BY seq_scan DESC 
LIMIT 10;"
```

### 4. Verificar Conexiones Activas
```bash
docker exec $(docker ps -q -f name=db) psql -U postgres -c "
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';"
```

## Optimizaciones Basadas en Resultados

### Si p95 > 2s:
1. Revisar queries N+1 en logs
2. Agregar índices faltantes
3. Implementar cache adicional
4. Optimizar serializers

### Si Error Rate > 1%:
1. Revisar logs de errores
2. Verificar timeouts de DB
3. Aumentar workers de Gunicorn
4. Revisar límites de conexiones

### Si Memory Leak (Soak Test):
1. Revisar objetos no liberados
2. Verificar cache sin TTL
3. Revisar Celery tasks
4. Analizar con memory_profiler

## Comandos de Emergencia

### Reiniciar Servicios
```bash
docker-compose restart web celery
```

### Limpiar Cache
```bash
docker exec $(docker ps -q -f name=redis) redis-cli FLUSHALL
```

### Matar Conexiones Idle
```bash
docker exec $(docker ps -q -f name=db) psql -U postgres -c "
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' 
AND state_change < current_timestamp - INTERVAL '5 minutes';"
```

## Frecuencia Recomendada

- **Smoke Test**: Cada deploy
- **Load Test**: Semanal
- **Stress Test**: Mensual
- **Soak Test**: Antes de releases mayores

## Capacidad Actual Estimada

Basado en arquitectura single-instance:
- **Usuarios concurrentes**: 50-100
- **Requests/segundo**: 25-50
- **Tenants soportados**: 50-100
- **Uptime esperado**: 99.5%