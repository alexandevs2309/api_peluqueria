# Auditoría de Seguridad Extensa — Auron Beauty (beauty.auronsuite.com / api.auronsuite.com)

**Fecha:** 2026-10-11 · **Alcance:** solo lectura (estático + dependencias + pruebas activas no destructivas) · **Autor:** auditoría asistida

## 1. Alcance y método

| Área | Método |
|---|---|
| Backend `api_peluqueria` (Django 5.2 + DRF 3.16, 25 apps) | Revisión estática: authN/authZ/RBAC/aislamiento multi-tenant + inyección/uploads/config/datos |
| Frontend `auron-tailadmin` (Angular 21) | Revisión estática: XSS, almacenamiento de tokens, guards, service worker, sanitización |
| Dependencias (pip 103 / npm 718) | Cruce contra base de vulnerabilidades **OSV** (`api.osv.dev`) |
| Producción en vivo | Pruebas activas **no destructivas**: cabeceras, TLS, CORS, rate-limit, métodos HTTP, endpoints sensibles, enumeración |
| Infra/secretos/CI | Revisión de repos (`.github`, Docker, nginx, scripts, secretos, backup) |

**Regla ejecutada:** no se modificó ningún archivo de la plataforma. Solo se creó este informe.

## 2. Resumen ejecutivo

- **Puntaje de Mozilla Observatory:** `60 (C+) → 115 (A+)`, **0/12 tests fallidos** (verificado con la API `observatory-api.mdn.mozilla.net`).
- **≈40 hallazgos** en código/config/infra (2 Críticos en dependencias + 2 Críticos en infra del VPS (BE-05/F11 nginx sin TLS en origen; F2 superadmin público) + 8 Altos + 1 Alto condicional (BE-04) + 13 Medios + ~17 Bajos) + **16 paquetes en producción con CVEs** (2 críticos) y 11 dev.
- **Puntos fuertes verificados:** aislamiento multi-tenant por JWT+middleware (mismatch bloqueado), RBAC deny-by-default, cookies httpOnly, JWT 30 min con rotación, rate-limit en login (429 en vivo), CORS sin reflexión, webhook Stripe con firma + idempotencia, uploads restringidos, sin SQL dinámico ni ejecución de comandos, cabeceras de seguridad A+.
- **Riesgos principales:** (1) guard de SuperAdmin en frontend es no-op; (2) XSS almacenado potencial vía FullCalendar (`renderEventContent` con `html`); (3) herramientas MCP accesibles con cualquier rol autenticado; (4) flujo 2FA del login no exige el primer factor; (5) credenciales de pago "cifradas" con `django.core.signing` (reversible) y Fernet opcional (plaintext si no se define `FERNET_KEY`); (6) dependencias Python y Angular desactualizadas (django 5.2.11, pillow, PyJWT, swiper, etc.).

## 3. Dependencias — escaneo OSV (2026-10-11)

Fuentes: `requirements.txt` (103 pinneadas) y `package-lock.json` (718). Únicos `GHSA`/`PYSEC` que afectan la versión instalada; los IDs son alias entre bases (el conteo puede incluir duplicados GHSA↔PYSEC).

### 3.1 Producción / runtime (15 paquetes)

| Sev | Paquete | Instalado | Hallazgos | Fix sugerido |
|---|---|---|---|---|
| CRITICAL | `swiper` | 11.2.10 | 1 | ≥12.1.2 |
| CRITICAL | `PyJWT` | 2.9.0 | 31 | ≥2.12.0 (2.12–2.15 afectadas→corregidas) |
| HIGH | `Django` | 5.2.11 | 40 | ≥5.2.16 en rama 5.2 LTS (varias corregidas solo en 6.0.x/6.1.x: valorar 6.0 LTS) |
| HIGH | `pillow` | 11.3.0 | 36 | ≥12.x |
| HIGH | `urllib3` | 2.7.0 | 6 | ≥2.8.0 |
| HIGH | `msgpack` | 1.1.2 | 2 | ≥1.2.1 |
| HIGH | `@angular/platform-server` | 21.2.19 | 4 | ≥22.1.4 |
| HIGH | `@angular/router` | 21.2.19 | 1 | ≥22.2.0 |
| HIGH | `nanoid` | 3.3.16 | 1 | ≥5.1.6 |
| HIGH | `source-map-js` | 1.2.1 | 1 | ≥1.2.2 |
| MODERATE | `@angular/common` | 21.2.19 | 1 | ≥22.1.1 |
| MODERATE | `@angular/compiler` | 21.2.19 | 1 | ≥22.1.0 |
| MODERATE | `dompurify` | 3.4.12 | 2 | ≥3.4.16 |
| MODERATE | `djangorestframework` | 3.16.0 | 4 | ≥3.17.2 |
| MODERATE | `idna` | 3.10 | 2 | ≥3.15 |
| LOW | `Pygments` | 2.19.2 | 2 | ≥2.20.0 |

### 3.2 Dev-only (11 paquetes, transitivos de `@angular/build`/karma)

`undici 7.28.0` (15), `hono 4.12.33` (8), `fast-uri 3.1.5` (6), `ip-address 10.4.0` (4), `brace-expansion 1.1.18` (3), `qs 6.15.3` (2), `braces 3.0.3` (1), `engine.io 6.6.9` (1), `http-cache-semantics 4.2.0` (1), `piscina 5.2.0` (1), `proxy-addr 2.0.7` (1). No llegan al bundle de producción (mitigado), pero deben actualizarse en el toolchain.

**Nota:** `pip_audit==2.10.0` ya está en `requirements.txt` — integrarlo como gate del CI (hoy no hay pipeline que lo ejecute en `.github`).

## 4. Backend — AuthN/AuthZ / Multi-tenant (código)

Referencia config: DRF default `IsAuthenticated` + `DualJWTAuthentication`/`JWTAuthentication` (`backend/settings.py:219-242`); SimpleJWT HS256 `JWT_SIGNING_KEY`, access 30 min / refresh 7 días, rotación+blacklist activados (`:259-270`).

| ID | Hallazgo | Sev | Evidencia |
|---|---|---|---|
| AUTHZ-01 | **MCP: cualquier usuario autenticado ejecuta tools de tenant** (`sales_summary`, `employee_performance`, `clients_search`, `inventory_alerts`) — solo `IsAuthenticated`, sin RBAC ni feature | **Alto** | `apps/mcp_api/views.py:93,100,114` |
| AUTH-01 | **Login con 2FA no exige la contraseña**: MFA-verify emite sesión completa solo con TOTP válido; no registra que el paso 1 se completó ni comprueba `is_active` | **Medio** | `apps/auth_api/views.py:798-894` |
| AUTH-02 | Refresh cookie **no rota ni blacklistea** el token (reutiliza el mismo `jti`), anulando `ROTATE_REFRESH_TOKENS` | **Medio** | `apps/auth_api/cookie_views.py:306-324` |
| AUTH-03 | Logout busca `ActiveSession` con el refresh **raw** (se guarda hasheado `:170`) → nunca coincide; la sesión server-side no se revoca | **Bajo** | `apps/auth_api/cookie_views.py:264` |
| AUTH-04 | `lookup-subdomain` (`AllowAny`, `csrf_exempt`) devuelve subdominio+nombre por email → enumeración; en vivo hoy devuelve `{"subdomain":null}` (mitigado por dato o payload distinto) | **Bajo** | `apps/auth_api/cookie_views.py:333-349` |
| TENANT-01 | Filtro de auditoría por `user__tenant` en vez de `tenant` propio del log → logs con `user=NULL` invisibles / logs mostrados al tenant equivocado | **Bajo** | `apps/audit_api/views.py:45`, `apps/subscriptions_api/views.py:460` |
| REG-01 | Registro público crea usuario temporal **`is_superuser=True, is_staff=True, is_email_verified=True`** con `skip_validation=True`, degradado después → ventana de privilegio + sin verificación de email | **Bajo** | `apps/subscriptions_api/registration_views.py:99-130` |

**Verificado OK:** `TenantMiddleware` (mismatch JWT↔usuario → `TENANT_MISMATCH`, tenants inactivos/suspendidos bloqueados, superadmin sin tenant), RBAC deny-by-default (`TenantPermissionByAction`, `has_object_permission` con `obj.tenant==request.tenant`), reset de contraseña con `default_token_generator` sin host-header injection, lockout + throttle login (5/min en prod), serializers de usuario sin campos sensibles writables, ventas POS re-validan propiedad, exportaciones de reportes scoped por tenant, webhooks Stripe firmados+idempotentes, uploads de pago con allow-list.

## 5. Backend — Inyección / Upload / Config / Secretos (código)

| ID | Hallazgo | Sev | Evidencia |
|---|---|---|---|
| BE-01 | Credenciales de terceros "encriptadas" con `django.core.signing` (base64+HMAC, **reversible** con `SECRET_KEY`) — el docstring lo admite | **Alto** | `apps/payments_api/models.py:9-33` |
| BE-02 | `FERNET_KEY` **opcional** (`default=''`); si falta, las credenciales de pago se guardan **en texto plano** sin error | **Alto** | `backend/settings.py:37`, `apps/settings_api/barbershop_models.py:11-13,30-32` |
| BE-06 | `SECRET_KEY[:10]` impreso en logs de build | **Medio** | `build.sh:29` |
| BE-07 | CSP en `nginx.conf` con `script-src 'unsafe-inline'` | **Medio** | `nginx/nginx.conf:102` |
| BE-08 | Comparaciones de claves (cron/Azul) sin `hmac.compare_digest` (timing) | **Bajo** | `backend/urls.py:96`, `apps/payments_api/views.py:229` |
| BE-09 | Export XLSX sin sanitizar celdas → **fórmula injection** al abrir en Excel | **Bajo** | `apps/reports_api/views.py:834-843` |
| BE-10 | HTML de emails fallback con f-strings sin escape | **Bajo** | `apps/emails/service.py:33-54` |
| BE-11 | Host/port de DB productiva como defaults commiteados (env Aiven) | **Bajo** | `docker-compose.yml:33-34` |
| BE-03 | Grafana/Prometheus publicados en host ports (`3000:3000`, `9090:9090`) con `GF_SECURITY_ADMIN_PASSWORD:-admin` — **activo**: es el compose de producción del VPS | **Alto (activo)** | `docker-compose.prod.yml:183-203` |
| BE-04 | Postgres/Redis publicados sin auth en `ops/docker-compose.production.yml` (**condicional**: no referenciado por `deploy-production.sh`; verificar que no esté en uso en el VPS) | **Alto (condicional)** | `ops/docker-compose.production.yml:13-24` |
| BE-05 | nginx del VPS **solo HTTP**: bloque TLS 443 **comentado** y redirect 301 comentado → tráfico Cloudflare→VPS en claro y respuesta HTTP si se accede directo por IP | **Crítico (activo)** | `nginx/nginx.conf:28-31,108-198`, `docker-compose.prod.yml:154-156` |

**Verificado OK:** sin `os.system`/`subprocess`/`eval`/`pickle`/`yaml.load` inseguro; sin SQL crudo interpolado; sin SSRF por URL de usuario; webhook Stripe firmado+idempotente; uploads de pago con allow-list ext/MIME + fuera de `MEDIA_ROOT`; campos secretos write-only en serializers; `/api/schema|docs|admin|metrics|__debug__` solo bajo `DEBUG`; `ALLOWED_HOSTS` validado, `SECURE_*` activos.

**Aclaración de despliegue (corregida 2026-10-11):** el API **no está en Render**. En producción corre en el **VPS de Interserver** (`api.auronsuite.com` → Cloudflare → VPS) con `docker-compose.prod.yml` + `nginx` (Gunicorn `--workers 4 --threads 4`), `env_file: .env.prod` y volúmenes de Let's Encrypt. Por tanto **BE-03 y BE-05 son hallazgos ACTIVOS** de la ruta de producción (Grafana/Prometheus en host ports; nginx sin TLS en el origen). BE-04/F5 solo aplican si se usa `ops/docker-compose.production.yml` (no lo referencia `deploy-production.sh`; verificar que no esté corriendo en el VPS). `render.yaml`, la entrada `api-peluqueria-p25h.onrender.com` del CSP de `nginx.conf:102` y cualquier otra referencia a Render en esta auditoría son **legacy**: purgarlos.

## 6. Frontend — Angular (código)

| ID | Hallazgo | Sev | Evidencia |
|---|---|---|---|
| FE-01 | `SuperAdminGuard` es **no-op: siempre `return true`** → rutas admin accesibles por cualquier usuario autenticado | **Alto** | `src/app/core/guards/super-admin.guard.ts:22-31` (13 rutas `admin/*` en `app.routes.ts`) |
| FE-02 | **XSS potencial almacenado** en calendario: `client_name`/`service_name` interpolados sin escapar en `renderEventContent` → `html` crudo | **Alto** | `appointments-management.component.ts:149,289` (wired `:93`); patrón menor en `calender.component.ts:177-188` |
| FE-03 | Identidad/rol en `localStorage` "encriptado" con **XOR + salt hardcodeado** (`auron_suite_secure_storage_2026`) → rol forgeable, `auth_token` legible por XSS | **Medio** | `src/app/core/utils/storage.ts:1-13`, `auth.service.ts:246,292-303`, `cookie-login.service.ts:43` |
| FE-04 | Service worker cachea **PII autenticada** (`clients`, `payroll`, `pos/sales`, `reports`, `appointments`; varias con strategy `performance` → cache-first) y **no hay purge al logout** | **Medio** | `public/ngsw-config.json:33-78` |
| FE-05 | `bypassSecurityTrustResourceUrl` sobre URL de video con validación laxa (`isYouTube` solo regex) | **Bajo** | `tutorials-management.component.ts:52-68` |
| FE-06 | "Sanitizador" débil previo a `document.write` en ventana de impresión | **Bajo** | `admin-reports.component.ts:720-745` |
| FE-07 | `SecurityGuard` y `TrialGuard` no-op (siempre allow) en routes sensibles (POS, nómina, reportes) | **Bajo** | `security.guard.ts:28-37`, `trial.guard.ts:5-8` |
| FE-08 | `safeHtml` pipe y `auron-icon` aplican `bypassSecurityTrustHtml` incondicional | **Bajo** | `safe-html.pipe.ts:8`, `auron-icon.component.ts:51-53` |
| FE-09 | Errores CRITICAL a `console.error` con `user_email` incluso en producción | **Bajo** | `error-logger.service.ts:137-145` |

**Verificado OK:** tokens primarios en cookies httpOnly (interceptor no inyecta `Authorization`), CSRF vía `X-CSRFToken` robusto, sin `postMessage`, sin `eval`/`new Function`, sin secretos en fuentes (keys inyectadas por `window.__env`), JSON-LD inyectado con `textContent`, embeds de YouTube validan ID y están limitados por CSP `frame-src`, logger redacta secretos, campos admin enmascarados (write-only).

## 7. Pruebas activas en vivo (no destructivas)

| Prueba | Resultado |
|---|---|
| Observatory (API oficial) | `grade=A+ score=115 tests_failed=0 tests_passed=12` (historia: C+ 60 → A+ 115) |
| HTTP→HTTPS | 301 en `beauty.*` y `api.*` |
| TLS | Cloudflare edge (h2/h3); HSTS API `max-age=31536000; includeSubDomains; preload`; frontend `max-age=15768000` |
| Cabeceras frontend | 1 sola CSP enforcing (sin unsafe-inline/unsafe-eval en script-src), XFO DENY, nosniff, referrer-policy, permissions-policy |
| Cabeceras API | XFO DENY, nosniff, COOP same-origin, referrer-policy; sin CSP (correcto para API) |
| CORS | Sin reflexión en suffix/null/http/subdominio/case; `ACAO` exacto `https://beauty.auronsuite.com` con `credentials:true`; métodos amplios pero solo con origen permitido |
| Rate-limit login | 4 intentos fallidos → **429** `RATE_LIMIT_EXCEEDED` ("expected available in 46 seconds"); OPTIONS también throttled |
| Métodos HTTP | GET en login → 405 (`Allow: POST, OPTIONS`); TRACE → 405; PUT/DELETE en GET-only → 403 |
| Endpoints sensibles | 401: mcp/chat, active-sessions, permissions, audit, notifications, reports/admin, tenants/admin/users, clients, pos/sales; `cron/run` → 503 (requiere X-Cron-Key); `system-settings` → 403; `plans/public-catalog` → 200 (público) |
| Enumeración | `reset-password`: mensajes **distintos** entre email existente/inexistente (`"Correo enviado para restablecer contraseña."` vs `"Correo enviado si el usuario existe."`) → oráculo leve de enumeración |
| SPA fallback | `/.env`, `/.git/config`, `/server-status` → 200 con `index.html` (sin fuga de contenido); `wp-login.php` → 403 (WAF) |
| `security.txt` | No existe (devuelve fallback del SPA); `robots.txt` real; `ngsw.json` expuesto (config SW, sin datos) |
| Health | `/api/healthz/` → 200 `{"database":"ok","cache":"ok","app":"ok"}` |

## 8. Infraestructura / Secretos / CI-CD

| ID | Hallazgo | Sev | Evidencia |
|---|---|---|---|
| F1 | **Verificador SCRAM de Postgres commiteado** (`pgbouncer/userlist.txt`, incluido en `.git/index` y en la imagen pgbouncer) | **Alto** | `pgbouncer/userlist.txt:1`, `pgbouncer/Dockerfile:4` |
| F2 | **Super-admin de fábrica con password público** (`admin@admin.com` / `admin123`, `role='SuperAdmin'`) creado por `deploy-production.sh:71-72` — es el script de despliegue del VPS (**activo**): si se ejecutó, existe un superadmin con credenciales públicas en la DB de producción | **Crítico (activo)** | `deploy-production.sh:69-76`, `scripts/create_superadmin.py:15,20`, `bootstrap.sh:47-48` |
| F3 | **`.env.prod` (todos los secretos) empaquetado en backups subidos a S3 sin cifrar** | **Alto** | `scripts/backup-production.sh:72-77,105-108` |
| F4 | Backups de DB solo comprimidos (gzip `-Ft -z`/`pg_dump|gzip`), **sin cifrado en reposo** en S3 | **Medio** | `ops/backup/backup_db.sh:24`, `pg_backup_daily.sh:44,57` |
| F5 | Puertos PG/Redis publicados al host (`5432`/`6379`) y **Redis sin password** en el compose de producción | **Medio** | `ops/docker-compose.production.yml:13-14,23-24,28` |
| F6 | **Endpoint real de DB de producción** (Aiven) como default en `docker-compose.yml` y filtrado por CSP (`connect-src … *.aivencloud.com`) | **Medio** | `docker-compose.yml:33-34`; `auron-tailadmin/public/_headers:7` |
| F7 | Grafana con `GF_SECURITY_ADMIN_PASSWORD:-admin` (también en el compose activo `docker-compose.prod.yml:198`) + imágenes `:latest` + contenedores como root | **Medio (activo en parte)** | `docker-compose.prod.yml:198`, `docker-compose.yml:177,179,165`, `nginx/Dockerfile:1`, `ops/Dockerfile.prometheus:1` |
| F8 | **CI/CD: actions de terceros por tag (no SHA)** y sin bloque `permissions:` explícito | **Medio** | `.github/workflows/ci-cd.yml:41,44,49,82,102,113`; `deploy.yml:11-38` |
| F9 | Credenciales de pasarelas de pago en **columnas plaintext** de la DB (migraciones) | **Medio** | `apps/settings_api/migrations/0015_add_payment_provider_credentials.py:20-87` |
| F11 | nginx de producción **solo HTTP** (bloque 443 comentado, redirect 301 comentado) — mismo hallazgo que BE-05, ahora activo | **Crítico (activo)** | `nginx/nginx.conf:28-31,115-198` |
| F9b | Defaults débiles: `DB_PASSWORD default='postgres'`, `JWT_SIGNING_KEY default=SECRET_KEY` (mitigados por validación de arranque) | **Bajo** | `backend/settings.py:364,257` |
| F10 | Parte de `SECRET_KEY` en logs de build (duplicado de BE-06) | **Bajo** | `build.sh:29` |
| F12 | `.gitignore` incompleto (frontend sin `.env*/.dev.vars`; backend sin `pgbouncer/userlist.txt`) | **Bajo** | `.gitignore` (ambos repos) |

**Verificado OK:** sin `.env`/`.env.prod` commiteados (solo `.env.example`; los secretos reales viven en el `.env.prod` del VPS), sin claves/`.pem`/tokens en repos, remotes sin credenciales, contenedores como `appuser`/`1000:1000` (salvo monitoring), pgbouncer con `scram-sha-256`, CI sin `pull_request_target` ni echo de secretos, `wrangler.jsonc` sin secrets, validación de arranque de settings (falla con placeholders en prod), backups con checksum + retención 30 días.

## 9. Recomendaciones priorizadas

**Inmediato (Crítico/Alto):**
1. **AUTHZ-01** — Aplicar RBAC (`TenantPermissionByAction` + `permission_map`) y `HasFeaturePermission` a `mcp_api`.
2. **FE-01** — Implementar `SuperAdminGuard` real (denegar si `role !== 'SUPER_ADMIN'`; no confiar en role client-side, revalidar con `/auth/verify/`).
3. **FE-02** — Escapar `client_name`/`service_name` en `renderEventContent` (o usar DOM seguro); auditar cómo se almacenan en backend.
4. **BE-01/BE-02** — Exigir `FERNET_KEY` en producción (validación de arranque) y migrar credenciales guardadas con `signing`/plaintext a Fernet real.
5. **Dependencias** — Actualizar Django ≥5.2.16 (valorar 6.0 LTS), pillow ≥12, PyJWT ≥2.12, urllib3 ≥2.8, swiper ≥12.1.2, dompurify ≥3.4.16, DRF ≥3.17.2, y Angular 21→22 (patch). Activar `pip-audit` y un escáner npm en CI.
6. **BE-06** — Quitar `SECRET_KEY[:10]` de `build.sh`.

**Corto plazo (Medio):**
7. **AUTH-01/02/03** — Fijar flujo 2FA (bandera server-side del primer factor, `is_active`), rotar/blacklistear refresh cookie, corregir logout hash.
8. **FE-03** — No confiar `role` en localStorage (validar server-side); mover `auth_token` fuera de JS si aplica.
9. **FE-04** — Purga de caché del SW al logout y revisar strategies `performance` sobre PII.
10. **VPS/Infra (BE-03/05, F2, F11)** — En el VPS: activar TLS en origen (descomentar bloque 443 + certbot), limitar firewall a IPs de Cloudflare para `80/443` y no exponer `3000`/`9090` (bind localhost o WireGuard), fijar `GRAFANA_PASSWORD` fuerte en `.env.prod`, borrar/rotar el superusuario `admin@admin.com` si `deploy-production.sh` se ejecutó, y purgar `render.yaml` + entradas `onrender` del CSP de `nginx.conf`.

**Higiene (Bajo):**
11. Mensajes únicos de reset de contraseña; `hmac.compare_digest`; sanitizar celdas XLSX contra fórmulas; escapar emails fallback; añadir `/.well-known/security.txt`; política de contraseñas completa; TENANT-01/REG-01/AUTH-04 ; FE-05..09; F9b/F10/F12.

**Pronto (Alto):**
12. **F1** — Rotar la contraseña de Postgres, eliminar `pgbouncer/userlist.txt` del historial y de la imagen.
13. **F2** — Quitar la creación de super-admin con credenciales por defecto de `deploy-production.sh` (generar y rotar).
14. **F3/F4** — No empaquetar `.env.prod` en backups; cifrar backups (KMS/`--sse`) y restringir S3.
15. **F5** — No publicar 5432/6379; `requirepass` en Redis (y en el archivo activo de producción).

**Medio plazo:**
16. **F6** — Mover endpoint de DB fuera del repo/CSP; **F8** — pinear actions a SHA y añadir `permissions:`; **F7** — quitar `:latest`, no correr monitoring como root, fijar `GRAFANA_PASSWORD`; **F9** — migrar credenciales de pago a cifrado real (BE-01/BE-02) y cifrar en reposo; **F11** — corregir/eliminar bloque TLS comentado; **F12** — completar `.gitignore`.

---

*Fuentes: revisión estática de ambos repos, escaneo OSV, pruebas activas no destructivas en producción, y Mozilla Observatory (API oficial). Todo solo lectura; no se modificó código de la plataforma.*

---

## Anexo — Estado de remediación y despliegue (2026-10-11)

### A.1 Producción real (verificado por SSH)
El backend **no** corre en Render **ni en Docker**. Es una instalación **nativa** en un VPS de Interserver (`162.35.187.40`, Ubuntu 24.04):

- App en `/opt/auron-api` (usuario `auron`, venv `.venv`), `EnvironmentFile=/opt/auron-api/.env`.
- systemd: `auron-api` (gunicorn en `127.0.0.1:8000`), `auron-celery`, `auron-celery-beat`.
- nginx con **TLS real** (certificado Cloudflare Origin) y redirección HTTP→HTTPS.
- PostgreSQL 16 + Redis, ambos solo en `localhost`. UFW activo (solo 22/80/443).
- Backups diarios `pg_dump` (desde hoy **cifrados**, ver A.3).
- El código se despliega **por copia** (la carpeta del VPS no es repo git).

**Implicación:** los hallazgos ligados a Docker/Render — **BE-03** (Grafana/Prometheus), **BE-05/F11** (nginx con TLS comentado), **F2** (`admin@admin.com`) y **BE-06** (`build.sh`) — **no aplican** a producción. Confirmado también: `/metrics` da 404 y no existe superusuario de fábrica.

### A.2 Tanda 1 — fixes de código (aplicados y desplegados al VPS)
| Hallazgo | Fix aplicado | Archivos |
|---|---|---|
| FE-01 `SuperAdminGuard` no-op | Guard deniega a no-SUPER_ADMIN en cliente (redirige a `/auth/access`); SSR permisivo para hidratación | `auron-tailadmin/src/app/core/guards/super-admin.guard.ts` |
| FE-02 XSS FullCalendar | `escapeHtml()` aplicado a título/hora en ambos calendarios | `appointments-management.component.ts`, `calender.component.ts` |
| AUTHZ-01 MCP sin RBAC | Nuevo permiso `McpIsTenantAdmin` (solo CLIENT_ADMIN/SUPER_ADMIN/superusuario) en las 3 vistas MCP | `api_peluqueria/apps/mcp_api/views.py` |
| BE-01/BE-02 credenciales en claro | `FERNET_KEY` **obligatoria y validada** en producción; `_encrypt_value` y `EncryptedFieldMixin`/`SystemSettings` cifran con Fernet real, con fallback de lectura para valores antiguos (signing/plaintext); nunca texto plano en prod (RuntimeError) | `backend/settings.py`, `settings_api/barbershop_models.py`, `settings_api/models.py`, `payments_api/models.py` |

> Nota: `settings.py` en el VPS tenía una **personalización local** (`PUBLIC_FRONTEND_ORIGIN_DEFAULTS` con `beauty.auronsuite.com`). El despliegue aplicó **solo el bloque de `FERNET_KEY`**, preservando esa personalización.

### A.3 Remediación de infraestructura aplicada hoy
| Ítem | Acción | Verificación |
|---|---|---|
| **V1** | `cryptography==50.0.2` instalada en el venv (faltaba, por eso el cifrado estaba inerte) + `FERNET_KEY` generada y añadida a `/opt/auron-api/.env` (chmod 600) | Cifrado Fernet real confirmado en los 3 modelos; API `healthz 200` |
| **V3** | `backups/backup-postgres.sh` reescrito: cifrado **AES-256** (openssl), clave en `/root/.auron_backup_key` (600), verificación de integridad, retención 14 días y copia **offsite opcional** vía rclone | Backup de prueba cifrado y descifrado OK (88 tablas) |
| **C1** | Dependencias vulnerables actualizadas: `Django 5.2.18`, `DRF 3.17.2`, `PyJWT 2.15.1`, `urllib3 2.8.0`, `pillow 12.3.0`, `msgpack 1.2.3`, `idna 3.20`, `Pygments 2.21.0`, `multidict 6.9.1` (todas ≥ a los mínimos recomendados) | `pip-audit`: **sin vulnerabilidades conocidas**; `manage.py check` OK |
| **C2** | Fixes de la tanda 1 desplegados: backend por copia (LF) al VPS + reinicio; frontend (FE-01/FE-02) por commit `55a0254` a `main` (Cloudflare) | Backend: `healthz 200`, MCP anónimo `401`; frontend: build de Cloudflare |

**Pendientes (decididos por el usuario):**
- **V2** — rotación de la contraseña root del VPS (quedó expuesta) + endurecer SSH (`PasswordAuthentication no`): **lo hará el usuario**.
- **V3b** — copia offsite cifrada: **rclone v1.60.1 ya instalado** en el VPS; pendiente crear bucket/Application Key en **Backblaze B2** y configurar el remote (ver A.4).
- Guardar la clave de backups `/root/.auron_backup_key` y `FERNET_KEY` en un gestor de secretos.

### A.4 Seguimiento — frontend (google fonts, dependencias) y hallazgos posteriores

| Ítem | Acción | Verificación |
|---|---|---|
| **Fuentes CSP / Service Worker** | Fuente **Outfit auto-hospedada** (`public/fonts/outfit-*.woff2`) con `@font-face` locales; se eliminó el `@import` de Google Fonts y el preconnect; CSP añadió `fonts.gstatic.com` en `connect-src` (mitigación previa) | CSS desplegado `styles-KYVLP6IB.css`: 2 `@font-face` → `/fonts/`, **0** referencias a `gstatic`/`googleapis`; `/fonts/outfit-latin.woff2` HTTP 200; navegador: **0 errores, 0 violaciones CSP** (commits `528efcd`, `c7132ac`) |
| **Dependencias frontend (npm audit)** | Angular **21.2.25** (parche), swiper **12.2.0**, dompurify **3.4.16**, nanoid **3.3.20**, source-map-js **1.2.2**, postcss **8.5.29**, `@angular/cli`/`build` **21.2.26**, `@angular/cdk` **21.2.14** (máx. publicado) | Build local `ng build` OK y desplegado (`main-C2GFR4BW.js`, `styles-KYVLP6IB.css`); `npm audit`: de **34 vulnerabilidades a 1 familia residual** |
| **Residual dev-only** | `braces` (stack-exhaustion DoS) vía `chokidar` → `karma` (runner de tests de desarrollo) | **No entra al bundle de producción**; el fix exige `karma@4` (breaking). Aceptado como riesgo residual o pendiente de migrar `ng test` |
| **SW auto-actualización** | `ngsw-worker.js` cambió de hash con el nuevo `@angular/service-worker@21.2.25` | Los Service Workers ya instalados se actualizan en la próxima visita y descartan la CSP/versión viejas |
| **YouTube metadata 503** | El endpoint devuelve 503 **intencional**: `YOUTUBE_API_KEY` ausente en `/opt/auron-api/.env` | **No es regresión**; pendiente generar API key de YouTube Data v3 y añadirla al `.env` + reiniciar `auron-api` |

**Commits de seguimiento:** `api_peluqueria` `f0041dc` (tanda 1 + informe + requirements C1); `auron-tailadmin` `528efcd` (fuentes Outfit locales) y `c7132ac` (dependencias + lock actualizados).