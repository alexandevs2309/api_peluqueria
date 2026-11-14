# AURON_STRESS_LAB_INFRASTRUCTURE.md — AURON Beauty

## 1. Estado actual del VPS (inspección local)

**Nota:** Esta inspección se realizó en el entorno de desarrollo local. Los datos del VPS de producción deben verificarse en el servidor.

### Entorno local (desarrollo)
- **CPU:** 8 cores
- **RAM:** 15 GB total, 5.9 GB libre, 4.8 GB caché
- **Disco:** 109 GB total, 29 GB libre (73% usado)
- **Docker:** v29.9.2, Compose v5.6.1
- **Contenedores activos:** Ninguno

### Arquitectura productiva (según docker-compose.prod.yml)
- **Servicios:** db (PostgreSQL 16), redis (7-alpine), init (migrate+collectstatic), web (Gunicorn 4 workers), celery (2 concurrency), celery-beat, nginx, prometheus, grafana.
- **Red:** `backend` (bridge, aislada).
- **Volúmenes:** postgres_data, redis_data, static_volume, media_volume, prometheus_data, grafana_data.
- **Puertos expuestos:** 80/443 (nginx), 9090 (prometheus), 3000 (grafana).
- **Límites de producción:**
  - db: 1G RAM, 512M reserved
  - redis: 512M RAM, 256M reserved
  - web: 1.5G RAM, 2.0 CPU, 1G reserved
  - celery: 512M RAM, 256M reserved
  - celery-beat: 256M RAM, 128M reserved
  - nginx: 256M RAM, 128M reserved
  - prometheus: 512M RAM, 256M reserved
  - grafana: 256M RAM, 128M reserved
- **Total producción:** ~4.5G RAM, 2.0 CPU

---

## 2. Arquitectura productiva identificada

```
┌─────────────────────────────────────────────────────────┐
│                    VPS (Producción)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │  nginx   │  │ promethe │  │ grafana  │             │
│  │  80/443  │  │  9090    │  │  3000    │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
│       │              │              │                   │
│  ┌────┴──────────────┴──────────────┴────┐             │
│  │           Red: backend (bridge)       │             │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐│             │
│  │  │ web  │ │celery│ │beat  │ │ init ││             │
│  │  │ 8000 │ │      │ │      │ │      ││             │
│  │  └──┬───┘ └──┬───┘ └──┬───┘ └──────┘│             │
│  │     │        │        │               │             │
│  │  ┌──┴────────┴────────┴──┐            │             │
│  │  │   db (PostgreSQL 16)  │            │             │
│  │  │   redis (7-alpine)    │            │             │
│  │  └───────────────────────┘            │             │
│  └───────────────────────────────────────┘             │
│  Volúmenes: postgres_data, redis_data, static_volume,  │
│  media_volume, prometheus_data, grafana_data           │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Diseño del laboratorio (auron-stress-lab)

### Ubicación
`/opt/auron-stress-lab`

### Estructura propuesta
```
/opt/auron-stress-lab/
├── docker-compose.stress.yml
├── .env.stress (credenciales sintéticas, NO de producción)
├── nginx/
│   └── nginx-stress.conf
├── k6/
│   ├── load-test.js
│   ├── stress-test.js
│   └── concurrency-test.js
├── zap/
│   └── zap-config.yaml
├── scripts/
│   ├── seed-data.py
│   ├── cleanup.py
│   └── monitor.sh
└── reports/
    └── (resultados de pruebas)
```

### Servicios del laboratorio
- `db-stress`: PostgreSQL 16 (exclusivo, datos sintéticos)
- `redis-stress`: Redis 7 (exclusivo)
- `web-stress`: Gunicorn (backend, build desde el mismo Dockerfile)
- `celery-stress`: Celery worker (concurrency=2)
- `celery-beat-stress`: Celery beat
- `nginx-stress`: Nginx (puerto interno, no público)
- `k6`: Contenedor de pruebas de carga (temporal)
- `zap`: Contenedor OWASP ZAP (temporal)

---

## 4. Diagrama de aislamiento

```
┌─────────────────────────────────────────────────────────────────────┐
│                          VPS                                       │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐  │
│  │     PRODUCCIÓN (intacta)     │  │     STRESS LAB (aislado)     │  │
│  │                             │  │                             │  │
│  │  Red: backend (bridge)      │  │  Red: stress (bridge)       │  │
│  │  ┌─────────────────────┐    │  │  ┌─────────────────────┐    │  │
│  │  │ db (postgres:16)    │    │  │  │ db-stress (pg:16)   │    │  │
│  │  │ redis (7-alpine)    │    │  │  │ redis-stress (7)    │    │  │
│  │  │ web (gunicorn)      │    │  │  │ web-stress (gunicorn)│    │  │
│  │  │ celery, celery-beat │    │  │  │ celery-stress       │    │  │
│  │  │ nginx (80/443)      │    │  │  │ nginx-stress (8080) │    │  │
│  │  │ prometheus, grafana │    │  │  │ k6 (temporal)       │    │  │
│  │  └─────────────────────┘    │  │  │ zap (temporal)      │    │  │
│  │  Volúmenes: prod_*          │  │  └─────────────────────┘    │  │
│  │  Credenciales: .env.prod    │  │  Volúmenes: stress_*         │  │
│  │  Datos: REALES              │  │  Credenciales: .env.stress   │  │
│  └─────────────────────────────┘  │  Datos: SINTÉTICOS          │  │
│                                   └─────────────────────────────┘  │
│  Comunicación: NINGUNA (redes separadas, volúmenes separados)      │
└─────────────────────────────────────────────────────────────────────┘
```

**Aislamiento garantizado por:**
- Redes Docker separadas (`backend` vs `stress`).
- Volúmenes separados (prefijo `stress_`).
- Credenciales separadas (`.env.stress` con valores sintéticos).
- Datos sintéticos (no se copian datos de producción).
- Puertos internos (solo nginx-stress expone 8080, solo para acceso local).

---

## 5. Límites de recursos recomendados

### Reserva para producción (no tocar)
| Servicio | RAM | CPU |
|---|---|---|
| Producción (total) | 4.5 GB | 2.0 CPU |
| Sistema operativo | 1 GB | 0.5 CPU |
| **Total reservado** | **5.5 GB** | **2.5 CPU** |

### Disponible para stress lab (estimado con 15 GB RAM, 8 cores)
| Servicio | RAM | CPU |
|---|---|---|
| db-stress (PostgreSQL) | 512 MB | 0.5 |
| redis-stress | 256 MB | 0.25 |
| web-stress (Gunicorn) | 1 GB | 1.0 |
| celery-stress | 256 MB | 0.25 |
| celery-beat-stress | 128 MB | 0.1 |
| nginx-stress | 128 MB | 0.1 |
| k6 (temporal) | 256 MB | 0.5 |
| zap (temporal) | 512 MB | 0.5 |
| **Total stress lab** | **~3 GB** | **~2.7 CPU** |

### Verificación de recursos
- Si el VPS tiene < 8 GB RAM libre o < 4 cores disponibles, **NO ejecutar** el stress lab en el mismo VPS.
- Alternativa: usar un VPS separado o un servicio de cloud (AWS/GCP) para el laboratorio.

---

## 6. Puertos y redes propuestos

| Servicio | Puerto interno | Puerto host (solo localhost) | Exposición |
|---|---|---|---|
| nginx-stress | 80 | 8080 (127.0.0.1) | Solo local |
| db-stress | 5432 | No expuesto | Solo red interna |
| redis-stress | 6379 | No expuesto | Solo red interna |
| web-stress | 8000 | No expuesto | Solo red interna |
| k6 | — | No expuesto | Solo red interna |
| zap | 8080 (ZAP) | 8090 (127.0.0.1) | Solo local |

**Regla:** Ningún puerto del stress lab se expone públicamente. Solo localhost.

---

## 7. Requisitos de datos sintéticos

### Tenants
- Crear 3-5 tenants sintéticos con nombres ficticios.
- Cada tenant con 1-3 sucursales.

### Usuarios
- 1 superadmin (sintético).
- 3-5 client-admins (uno por tenant).
- 10-20 empleados (cajeros, estilistas, managers).
- 5-10 clientes por tenant.

### Datos operativos
- 50-100 servicios (con categorías y precios).
- 30-50 productos (con stock).
- 100-500 citas (distribuidas en 3 meses).
- 200-1000 ventas (con detalles, pagos, NCF).
- 50-100 empleados con nómina (períodos, deducciones, comisiones).

### Datos de prueba
- Usar `UserFactory` y `Tenant` factories existentes.
- Usar `seed_realistic_data.py` como referencia (pero con datos sintéticos).
- No usar datos reales de clientes ni transacciones.

---

## 8. Riesgos de ejecutar pruebas en el mismo VPS

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Agotamiento de CPU/RAM | Media | Alto | Límites de recursos en Docker, monitoreo |
| Agotamiento de disco | Baja | Alto | Límites de retención (Prometheus 15d, 5GB) |
| Interferencia de red | Baja | Medio | Redes separadas |
| Confusión de credenciales | Baja | Crítico | Credenciales sintéticas, no de producción |
| Daño a datos de producción | Baja | Crítico | Volúmenes separados, no compartir DB |
| OWASP ZAP atacando producción | Media | Crítico | Solo escanear localhost:8080 (stress lab) |

**Recomendación:** Si el VPS tiene menos de 8 GB RAM o 4 cores disponibles, usar un VPS separado para el stress lab.

---

## 9. Comandos necesarios para desplegar staging (NO EJECUTAR)

```bash
# 1. Crear directorio
mkdir -p /opt/auron-stress-lab
cd /opt/auron-stress-lab

# 2. Clonar repositorio (sin modificar producción)
git clone https://github.com/alexandevs2309/api_peluqueria.git backend
cd backend
git checkout master

# 3. Crear .env.stress (credenciales sintéticas)
cat > .env.stress << 'EOF'
SECRET_KEY=stress-lab-secret-key-not-for-production
FERNET_KEY=stress-lab-fernet-key-not-for-production
DEBUG=True
DATABASE_URL=postgres://stress_user:stress_pass@db-stress:5432/stress_db
REDIS_URL=redis://:stress_redis_pass@redis-stress:6379/0
FRONTEND_URL=http://localhost:8080
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
CELERY_BROKER_URL=redis://:stress_redis_pass@redis-stress:6379/0
EOF

# 4. Crear docker-compose.stress.yml (basado en docker-compose.prod.yml con límites)
# ... (adaptar con límites de recursos y red separada)

# 5. Levantar servicios
docker compose -f docker-compose.stress.yml up -d

# 6. Ejecutar migraciones (solo en stress DB)
docker compose -f docker-compose.stress.yml exec web-stress python manage.py migrate

# 7. Crear datos sintéticos
docker compose -f docker-compose.stress.yml exec web-stress python manage.py seed_stress_data

# 8. Ejecutar pruebas k6
docker run --rm -i --network stress grafana/k6 run - < k6/load-test.js

# 9. Ejecutar OWASP ZAP
docker run --rm -t --network stress zaproxy/zap-stable zap-baseline.py -t http://nginx-stress:80

# 10. Apagar y limpiar
docker compose -f docker-compose.stress.yml down -v
```

**Estos comandos NO se han ejecutado.** Requieren autorización explícita.

---

## 10. Procedimiento de apagado y eliminación segura

```bash
# 1. Detener servicios
docker compose -f docker-compose.stress.yml down

# 2. Eliminar volúmenes (datos sintéticos)
docker compose -f docker-compose.stress.yml down -v

# 3. Eliminar imágenes (opcional)
docker rmi $(docker images -q --filter "reference=*stress*")

# 4. Eliminar directorio
rm -rf /opt/auron-stress-lab

# 5. Verificar que producción no fue afectada
docker ps  # solo contenedores de producción
```

---

## Nota sobre el entorno actual

Esta inspección se realizó en el **entorno de desarrollo local**, no en el VPS de producción. Los datos de CPU, RAM y disco corresponden a la máquina local (8 cores, 15 GB RAM, 109 GB disco, 73% usado).

**Para completar esta misión, se requiere:**
1. Acceso SSH al VPS de producción.
2. Inspección de recursos reales del VPS.
3. Verificación de contenedores Docker activos en producción.
4. Autorización explícita para crear el stress lab.

**No se crearon contenedores, volúmenes ni modificaciones. No se tocó producción.**  
**Esperando autorización para construir el laboratorio.**
EOF
echo "Written"