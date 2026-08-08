# 📚 API Documentation - Sistema SaaS Peluquerías

## 🚀 Quick Start

### Authentication
```bash
# 1. Registrar tenant
POST /api/subscriptions/register/
{
  "fullName": "Juan Pérez",
  "email": "juan@peluqueria.com",
  "businessName": "Salón Elegante",
  "planType": "basic"
}

# 2. Login
POST /api/auth/login/
{
  "email": "juan@peluqueria.com",
  "password": "password123"
}

# 3. Usar token en headers
Authorization: Bearer <access_token>
```

## 📋 Core Endpoints

### 👥 Clientes
```bash
# Listar clientes
GET /api/clients/

# Crear cliente
POST /api/clients/
{
  "full_name": "María García",
  "email": "maria@email.com",
  "phone": "+1234567890"
}

# Cliente por ID
GET /api/clients/{id}/
```

### 📅 Citas
```bash
# Calendario de citas (FullCalendar compatible)
GET /api/appointments/calendar-events/?start=2024-01-01&end=2024-12-31

# Crear cita
POST /api/appointments/
{
  "client": 1,
  "stylist": 2,
  "service": 3,
  "date": "2024-12-15",
  "time": "14:30:00"
}

# Reprogramar cita
PUT /api/appointments/{id}/reschedule/
{
  "new_date": "2024-12-16",
  "new_time": "15:00:00"
}
```

### 💰 Punto de Venta
```bash
# Crear venta
POST /api/pos/sales/
{
  "client": 1,
  "items": [
    {"service": 1, "quantity": 1, "price": 25.00},
    {"product": 2, "quantity": 2, "price": 15.00}
  ],
  "payment_method": "card",
  "total": 55.00
}

# Estado de caja
GET /api/pos/cash-register/current/
```

### 📊 Reportes y Analytics
```bash
# KPIs principales
GET /api/reports/kpi/

# Analytics avanzado
GET /api/reports/analytics/

# Business Intelligence
GET /api/reports/business-intelligence/

# Métricas en tiempo real
GET /api/reports/realtime/
```

### 🔔 Notificaciones
```bash
# Preferencias de notificaciones
GET /api/notifications/preferences/
PUT /api/notifications/preferences/

# Enviar notificación de prueba
POST /api/notifications/test/
{
  "template": "appointment_reminder",
  "recipient_email": "test@example.com"
}
```

## 🔗 Webhooks

### Stripe Webhooks
```bash
POST /api/billing/stripe/webhook/
# Maneja eventos: payment_succeeded, subscription_updated, etc.
```

### Configuración de Webhooks
```bash
# En tu dashboard de Stripe, configura:
URL: https://tu-dominio.com/api/billing/stripe/webhook/
Eventos: payment_intent.succeeded, customer.subscription.updated
```

## 📈 Casos de Uso Comunes

### Flujo Completo de Cita
```python
# 1. Buscar disponibilidad
GET /api/appointments/stylist/1/availability/?date=2024-12-15

# 2. Crear cita
POST /api/appointments/
{
  "client": 1,
  "stylist": 1,
  "service": 1,
  "date": "2024-12-15",
  "time": "14:30:00"
}

# 3. Automático: Se envía notificación de confirmación
# 4. Automático: Se programa recordatorio 24h antes
```

### Dashboard en Tiempo Real
```javascript
// Obtener KPIs actuales
const kpis = await fetch('/api/reports/kpi/');

// Métricas en tiempo real
const realtime = await fetch('/api/reports/realtime/');

// Próximas citas (2 horas)
const upcoming = await fetch('/api/appointments/?upcoming=2h');
```

## 🔧 Configuración de Desarrollo

### Variables de Entorno Requeridas
```bash
# Django
SECRET_KEY="tu-secret-key-seguro"
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de Datos
DB_NAME=barbershop_db
DB_USER=postgres
DB_PASSWORD=tu-password-seguro

# Redis
REDIS_PASSWORD=tu-redis-password

# Stripe
STRIPE_SECRET_KEY=sk_test_tu_stripe_key
STRIPE_PUBLISHABLE_KEY=pk_test_tu_stripe_key

# Email
SENDGRID_API_KEY=SG.tu_sendgrid_key
SENDGRID_FROM_EMAIL=noreply@tudominio.com
```

### Setup Local
```bash
# 1. Generar configuración segura
./generate-secrets.ps1

# 2. Iniciar servicios
docker-compose up -d

# 3. Crear roles y superusuario
docker-compose exec web python create_initial_roles.py

# 4. Acceder al admin
http://localhost:8000/admin/
```

## 🚨 Rate Limits

- **General**: 10 requests/segundo
- **Autenticación**: 5 requests/minuto
- **Burst**: 20 requests permitidos

## 📱 Códigos de Respuesta

- `200` - OK
- `201` - Creado
- `400` - Bad Request
- `401` - No autorizado
- `403` - Prohibido
- `404` - No encontrado
- `429` - Rate limit excedido
- `500` - Error del servidor

## 🔐 Seguridad

- **JWT Tokens**: 30 minutos de duración
- **Refresh Tokens**: 7 días de duración
- **Rate Limiting**: Configurado por endpoint
- **HTTPS**: Requerido en producción
- **CORS**: Configurado por dominio