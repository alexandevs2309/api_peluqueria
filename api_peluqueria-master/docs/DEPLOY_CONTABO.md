# Guía de Despliegue en Contabo VPS

## Requisitos VPS

- **RAM:** 8GB mínimo (recomendado 16GB)
- **CPU:** 4 cores mínimo (recomendado 8 cores)
- **Disco:** 100GB SSD mínimo
- **OS:** Ubuntu 22.04 LTS
- **IP:** Pública estática

---

## Paso 1: Preparar VPS (30 min)

### 1.1 Conectar por SSH
```bash
ssh root@TU_IP_VPS
```

### 1.2 Actualizar sistema
```bash
apt update && apt upgrade -y
```

### 1.3 Instalar Docker
```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Instalar Docker Compose
apt install docker-compose-plugin -y

# Verificar
docker --version
docker compose version
```

### 1.4 Crear usuario no-root
```bash
adduser deploy
usermod -aG docker deploy
usermod -aG sudo deploy

# Cambiar a usuario deploy
su - deploy
```

### 1.5 Configurar firewall
```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

---

## Paso 2: Configurar Dominio (15 min)

### 2.1 En Cloudflare (o tu DNS)
```
Tipo: A
Nombre: @
Contenido: TU_IP_VPS
Proxy: Activado (nube naranja)

Tipo: A
Nombre: www
Contenido: TU_IP_VPS
Proxy: Activado
```

### 2.2 Configurar SSL en Cloudflare
```
SSL/TLS → Overview → Full (Strict)
SSL/TLS → Edge Certificates → Always Use HTTPS: ON
```

### 2.3 Crear Page Rule (Bypass cache API)
```
URL: *tudominio.com/api/*
Settings: Cache Level = Bypass
```

---

## Paso 3: Clonar Proyecto (10 min)

```bash
cd /home/deploy
git clone https://github.com/TU_USUARIO/TU_REPO.git app
cd app
```

---

## Paso 4: Configurar .env (20 min)

### 4.1 Copiar template
```bash
cp .env.contabo .env.prod
```

### 4.2 Generar SECRET_KEY
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 4.3 Editar .env.prod
```bash
nano .env.prod
```

**CAMBIAR OBLIGATORIO:**
```bash
SECRET_KEY="<pegar secret key generado>"
ALLOWED_HOSTS=tudominio.com,www.tudominio.com
CSRF_TRUSTED_ORIGINS=https://tudominio.com,https://www.tudominio.com
CORS_ALLOWED_ORIGINS=https://tudominio.com

DB_PASSWORD="<generar password seguro>"
REDIS_PASSWORD="<generar password seguro>"
GRAFANA_PASSWORD="<generar password seguro>"

STRIPE_SECRET_KEY=sk_live_<tu_key_real>
STRIPE_PUBLISHABLE_KEY=pk_live_<tu_key_real>
STRIPE_WEBHOOK_SECRET=whsec_<tu_webhook_secret>

SENDGRID_API_KEY=SG.<tu_api_key>
SENDGRID_FROM_EMAIL=noreply@tudominio.com

SENTRY_DSN=https://<tu_sentry_dsn>
```

---

## Paso 5: Configurar nginx SSL (30 min)

### 5.1 Instalar Certbot
```bash
sudo apt install certbot -y
```

### 5.2 Obtener certificado
```bash
sudo certbot certonly --standalone -d tudominio.com -d www.tudominio.com
```

### 5.3 Editar nginx.conf
```bash
nano nginx/nginx.conf
```

**Agregar bloque SSL:**
```nginx
server {
    listen 443 ssl http2;
    server_name tudominio.com www.tudominio.com;
    
    ssl_certificate /etc/letsencrypt/live/tudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tudominio.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # ... resto de configuración
}

server {
    listen 80;
    server_name tudominio.com www.tudominio.com;
    return 301 https://$server_name$request_uri;
}
```

### 5.4 Montar certificados en docker-compose.contabo.yml
```yaml
nginx:
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    - /etc/letsencrypt:/etc/letsencrypt:ro
    - static_volume:/code/staticfiles
    - media_volume:/code/media
```

---

## Paso 6: Build y Deploy (20 min)

### 6.1 Build imágenes
```bash
docker compose -f docker-compose.yml -f docker-compose.contabo.yml build
```

### 6.2 Iniciar servicios
```bash
docker compose -f docker-compose.yml -f docker-compose.contabo.yml up -d
```

### 6.3 Verificar containers
```bash
docker compose ps
```

**Todos deben estar "running" o "healthy"**

---

## Paso 7: Validaciones POST-Despliegue (30 min)

### 7.1 Test healthcheck
```bash
curl https://tudominio.com/api/healthz/
# Debe devolver: {"status": "ok"}
```

### 7.2 Test login
```bash
curl -X POST https://tudominio.com/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"test123"}'
# Debe devolver token
```

### 7.3 Verificar cookies
```bash
curl -v https://tudominio.com/api/auth/login/ \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"test123"}' \
  2>&1 | grep -i "set-cookie"
# Debe mostrar: Set-Cookie: sessionid=...; Secure; HttpOnly
```

### 7.4 Test CSRF
```bash
# Obtener CSRF token
curl -c cookies.txt https://tudominio.com/api/auth/csrf/

# Usar token
curl -b cookies.txt -X POST https://tudominio.com/api/pos/sales/ \
  -H "X-CSRFToken: <token>" \
  -H "Content-Type: application/json" \
  -d '{...}'
# No debe dar 403
```

### 7.5 Verificar Celery
```bash
docker compose exec celery celery -A backend inspect active
# Debe mostrar workers activos
```

### 7.6 Verificar PostgreSQL
```bash
docker compose exec db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
# count debe ser < 80
```

### 7.7 Verificar Redis persistencia
```bash
docker compose exec redis redis-cli -a ${REDIS_PASSWORD} CONFIG GET save
# Debe mostrar: "900 1 300 10 60 10000"
```

### 7.8 Verificar memory usage
```bash
docker stats --no-stream
# Total < 6GB (si VPS tiene 8GB)
```

### 7.9 Test Stripe webhook
```bash
# En Stripe Dashboard:
# Webhooks → Add endpoint
# URL: https://tudominio.com/api/payments/webhook/
# Events: payment_intent.succeeded, payment_intent.payment_failed

# Test con Stripe CLI
stripe listen --forward-to https://tudominio.com/api/payments/webhook/
stripe trigger payment_intent.succeeded
```

### 7.10 Verificar Grafana
```bash
# Abrir en navegador
https://tudominio.com:3000
# Login: admin / <GRAFANA_PASSWORD>
```

---

## Paso 8: Configurar Backups Automáticos (30 min)

### 8.1 Crear script backup
```bash
nano /home/deploy/backup.sh
```

```bash
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/deploy/backups"
mkdir -p ${BACKUP_DIR}

# Backup PostgreSQL
docker compose exec -T db pg_dump -U postgres barbershop_db | gzip > ${BACKUP_DIR}/db_${TIMESTAMP}.sql.gz

# Backup media files
tar -czf ${BACKUP_DIR}/media_${TIMESTAMP}.tar.gz media/

# Limpiar backups > 7 días
find ${BACKUP_DIR} -name "*.gz" -mtime +7 -delete

echo "Backup completado: ${TIMESTAMP}"
```

### 8.2 Dar permisos
```bash
chmod +x /home/deploy/backup.sh
```

### 8.3 Configurar cron
```bash
crontab -e
```

```cron
# Backup diario a las 2 AM
0 2 * * * /home/deploy/backup.sh >> /home/deploy/backup.log 2>&1
```

---

## Paso 9: Monitoreo (15 min)

### 9.1 Configurar alertas Grafana
```
Grafana → Alerting → Contact points
Agregar email o Slack
```

### 9.2 Crear alerta CPU
```
Alert rule:
- Metric: container_cpu_usage_seconds_total
- Condition: > 80%
- For: 5 minutes
- Action: Notify admin
```

### 9.3 Crear alerta Memory
```
Alert rule:
- Metric: container_memory_usage_bytes
- Condition: > 6GB
- For: 5 minutes
- Action: Notify admin
```

---

## Paso 10: Renovación SSL Automática

### 10.1 Test renovación
```bash
sudo certbot renew --dry-run
```

### 10.2 Configurar cron
```bash
sudo crontab -e
```

```cron
# Renovar SSL cada 3 meses
0 3 1 */3 * certbot renew --quiet && docker compose restart nginx
```

---

## Comandos Útiles

### Ver logs
```bash
# Todos los servicios
docker compose logs -f

# Solo web
docker compose logs -f web

# Solo errores
docker compose logs -f | grep -i error
```

### Restart servicios
```bash
# Todos
docker compose restart

# Solo web
docker compose restart web
```

### Actualizar código
```bash
git pull
docker compose build web celery celery-beat
docker compose up -d
```

### Backup manual
```bash
/home/deploy/backup.sh
```

### Restore backup
```bash
# Listar backups
ls -lh /home/deploy/backups/

# Restore
gunzip < /home/deploy/backups/db_20260226_020000.sql.gz | \
  docker compose exec -T db psql -U postgres barbershop_db
```

---

## Troubleshooting

### Containers no inician
```bash
docker compose logs web
# Revisar errores
```

### OOM (Out of Memory)
```bash
# Verificar memory
free -h

# Reducir workers en docker-compose.contabo.yml
# workers=4 → workers=2
```

### Cookies no funcionan
```bash
# Verificar ALLOWED_HOSTS
docker compose exec web python manage.py shell
>>> from django.conf import settings
>>> print(settings.ALLOWED_HOSTS)

# Verificar dominio en .env.prod
```

### Stripe webhooks fallan
```bash
# Verificar signature
docker compose logs web | grep stripe

# Verificar STRIPE_WEBHOOK_SECRET en .env.prod
```

---

## Checklist Final

- [ ] VPS con 8GB+ RAM
- [ ] Docker instalado
- [ ] Dominio apuntando a VPS
- [ ] Cloudflare configurado (SSL Full Strict)
- [ ] .env.prod configurado (SECRET_KEY, passwords, Stripe, etc)
- [ ] Certificado SSL obtenido
- [ ] nginx.conf con SSL
- [ ] Containers corriendo
- [ ] Healthcheck OK
- [ ] Login funciona
- [ ] Cookies funcionan
- [ ] CSRF funciona
- [ ] Celery activo
- [ ] PostgreSQL < 80 conexiones
- [ ] Redis con persistencia
- [ ] Memory < 80% VPS
- [ ] Stripe webhook configurado
- [ ] Grafana accesible
- [ ] Backups automáticos configurados
- [ ] SSL auto-renovación configurada
- [ ] Monitoreo activo

---

## Soporte

Si algo falla:
1. Revisar logs: `docker compose logs -f`
2. Verificar .env.prod
3. Verificar ALLOWED_HOSTS
4. Verificar certificado SSL
5. Verificar memory disponible

**Tiempo total estimado:** 3-4 horas
