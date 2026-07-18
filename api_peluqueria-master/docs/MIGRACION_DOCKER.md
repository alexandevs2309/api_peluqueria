# Migración de Seguridad - Docker Compose

## Aplicar migración
```bash
docker compose exec web python manage.py migrate auth_api
```

## Ejecutar tests
```bash
docker compose exec web python manage.py test apps.auth_api.tests_security
```
