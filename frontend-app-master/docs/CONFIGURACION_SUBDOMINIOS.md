# 🌐 CONFIGURACIÓN DE SUBDOMINIOS MULTI-TENANT

## Arquitectura Implementada

**Detección automática de tenant desde:**
1. Subdominio del host (ej: `barberia-juan.app.com`)
2. Header `X-Tenant-Subdomain` (fallback)
3. Campo `tenant_subdomain` en body (fallback)

---

## Configuración de Desarrollo

### Opción 1: Hosts locales (Recomendado)

**Windows:** `C:\Windows\System32\drivers\etc\hosts`
```
127.0.0.1 tenant1.localhost
127.0.0.1 tenant2.localhost
127.0.0.1 admin.localhost
```

**Linux/Mac:** `/etc/hosts`
```
127.0.0.1 tenant1.localhost
127.0.0.1 tenant2.localhost
127.0.0.1 admin.localhost
```

**Acceso:**
- `http://tenant1.localhost:4200` → Tenant 1
- `http://tenant2.localhost:4200` → Tenant 2
- `http://admin.localhost:4200` → SuperAdmin

### Opción 2: Header HTTP (Desarrollo)

**Frontend interceptor:**
```typescript
// src/app/core/interceptors/tenant.interceptor.ts
export class TenantInterceptor implements HttpInterceptor {
  intercept(req: HttpRequest<any>, next: HttpHandler) {
    const tenant = 'mi-tenant'; // Obtener de config
    const cloned = req.clone({
      setHeaders: { 'X-Tenant-Subdomain': tenant }
    });
    return next.handle(cloned);
  }
}
```

---

## Configuración de Producción

### DNS Wildcard

**Configurar en tu proveedor DNS:**
```
A     @              → IP_SERVIDOR
A     *              → IP_SERVIDOR
CNAME admin          → app.tudominio.com
```

**Resultado:**
- `app.tudominio.com` → Landing/Admin
- `barberia-juan.tudominio.com` → Tenant "barberia-juan"
- `salon-maria.tudominio.com` → Tenant "salon-maria"

### Nginx

```nginx
server {
    listen 80;
    server_name ~^(?<tenant>.+)\.tudominio\.com$;
    
    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Tenant-Subdomain $tenant;
    }
}
```

### Docker Compose

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

---

## Frontend: Sin cambios necesarios

**El login actual funciona sin modificaciones:**
```typescript
this.authService.loginSecure({ email, password }).subscribe({
  // Backend detecta tenant automáticamente
});
```

---

## Testing

### Test con subdominios locales:
```bash
curl -H "Host: tenant1.localhost" http://localhost:8000/api/auth/login/ \
  -d '{"email":"admin@tenant1.com","password":"pass123"}'
```

### Test con header:
```bash
curl -H "X-Tenant-Subdomain: tenant1" http://localhost:8000/api/auth/login/ \
  -d '{"email":"admin@tenant1.com","password":"pass123"}'
```

---

## Migración desde campo manual

**Antes (campo visible):**
```json
{
  "email": "user@mail.com",
  "password": "pass123",
  "tenant_subdomain": "mi-tenant"
}
```

**Ahora (detección automática):**
```json
{
  "email": "user@mail.com",
  "password": "pass123"
}
```

**Backward compatible:** Si se envía `tenant_subdomain`, se usa ese valor.

---

## Ventajas de esta arquitectura

✅ UX perfecto (sin campo tenant visible)
✅ Seguridad multi-tenant nativa
✅ Escalable (wildcard DNS)
✅ Backward compatible
✅ Estándar SaaS profesional
