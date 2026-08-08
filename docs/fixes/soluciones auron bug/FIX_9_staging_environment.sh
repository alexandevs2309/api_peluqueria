#!/bin/bash
# ============================================================
# FIX 9: Entorno de staging separado
# PROBLEMA: environment.ts (dev) apunta a api-peluqueria-p25h.onrender.com
#            Cualquier dev local está tocando datos de producción.
# SOLUCIÓN: Crear environment.staging.ts + angular.json configuration
#            Dev local → localhost:8000
#            Staging → staging-api.auron-suite.com (nuevo servicio Render)
#            Producción → api.auron-suite.com
# ============================================================

# 1. Crear frontend-app/src/environments/environment.staging.ts
cat > src/environments/environment.staging.ts << 'EOF'
/**
 * Environment - Staging
 * Conecta a la API de staging (datos de prueba, no producción).
 * Activar con: ng serve --configuration staging
 */
export const environment = {
  production: false,
  apiUrl: 'https://staging-api.auron-suite.com/api',
  wsUrl: 'wss://staging-api.auron-suite.com/ws',
  stripePublishableKey: (window as any).__env?.stripePublishableKey || 'pk_test_STAGING_KEY',
  appName: 'Auron-Suite (Staging)',
  appVersion: '1.0.0-staging',
  enableDebugMode: true,
  enableMockData: false,
  csrfCookieName: 'csrftoken',
  sessionCookieName: 'sessionid',
};
EOF

echo "✅ environment.staging.ts creado"


# 2. Agregar configuración 'staging' a angular.json
# Dentro de "projects" > "auron-suite-web" > "architect" > "build" > "configurations":
cat << 'EOF'
// Agregar en angular.json > configurations:
"staging": {
  "fileReplacements": [
    {
      "replace": "src/environments/environment.ts",
      "with": "src/environments/environment.staging.ts"
    }
  ],
  "optimization": false,
  "sourceMap": true
}
EOF

# Y dentro de "serve" > "configurations":
cat << 'EOF'
"staging": {
  "buildTarget": "auron-suite-web:build:staging"
}
EOF


# 3. Actualizar environment.ts (dev) para apuntar a localhost
cat > src/environments/environment.ts << 'EOF'
/**
 * Environment - Development LOCAL
 * Apunta a localhost. Para conectar a staging: ng serve --configuration staging
 * NUNCA hardcodear URLs de producción aquí.
 */
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api',
  wsUrl: 'ws://localhost:8000/ws',
  stripePublishableKey: process?.env?.['NG_APP_STRIPE_PK'] || 'pk_test_REPLACE_IN_ENV',
  appName: 'Auron-Suite (Dev)',
  appVersion: '1.0.0-dev',
  enableDebugMode: true,
  enableMockData: false,
  csrfCookieName: 'csrftoken',
  sessionCookieName: 'sessionid',
};
EOF

echo "✅ environment.ts actualizado a localhost"


# 4. render.yaml — agregar servicio de staging
cat << 'EOF'
# Agregar al render.yaml existente, como nuevo servicio:
  - type: web
    name: auron-api-staging
    runtime: python
    buildCommand: "./build.sh"
    startCommand: "gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 2 --worker-class gthread --timeout 120"
    healthCheckPath: /api/healthz/
    envVars:
      - key: DEBUG
        value: "False"
      - key: DJANGO_SETTINGS_MODULE
        value: backend.settings
      - key: SENTRY_ENVIRONMENT
        value: staging
      # Las vars sensibles se setean manualmente en Render dashboard:
      # SECRET_KEY, DATABASE_URL (staging DB), REDIS_URL, STRIPE_SECRET_KEY (test)
EOF

echo "✅ Staging environment configurado"
echo ""
echo "PRÓXIMOS PASOS:"
echo "1. Crear base de datos de staging en Render (separada de producción)"
echo "2. Configurar env vars de staging en Render dashboard"
echo "3. ng serve --configuration staging  ← para desarrollo conectado a staging"
echo "4. Nunca usar ng serve (sin config) para tocar datos reales"
