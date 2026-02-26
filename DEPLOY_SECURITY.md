# 🚀 GUÍA DE DESPLIEGUE - CORRECCIONES DE SEGURIDAD

## Comandos Docker Compose

### 1. Backup de base de datos
```bash
docker compose exec -T db pg_dump -U postgres -d peluqueria > backup_$(date +%Y%m%d).sql
```

### 2. Verificar emails duplicados
```bash
docker compose exec web python manage.py shell
```
```python
from apps.auth_api.models import User
from django.db.models import Count

duplicates = User.objects.values('email', 'tenant').annotate(count=Count('id')).filter(count__gt=1)
print(f"Duplicados: {duplicates.count()}")
```

### 3. Aplicar migraciones
```bash
docker compose exec web python manage.py migrate auth_api
```

### 4. Ejecutar tests
```bash
docker compose exec web python manage.py test apps.auth_api.tests_security
```

---

## Opción Automática

### Linux/Mac:
```bash
chmod +x migrate-security.sh
./migrate-security.sh
```

### Windows PowerShell:
```powershell
.\migrate-security.ps1
```

---

## Verificación Post-Migración

```bash
# Verificar constraint
docker compose exec web python manage.py dbshell
```
```sql
\d auth_api_user
-- Debe mostrar: UNIQUE CONSTRAINT (email, tenant_id)
```

---

## Rollback (si es necesario)

```bash
# Restaurar backup
docker compose exec -T db psql -U postgres -d peluqueria < backup_YYYYMMDD.sql

# Revertir migración
docker compose exec web python manage.py migrate auth_api 0005
```
