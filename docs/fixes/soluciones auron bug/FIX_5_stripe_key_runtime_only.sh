# ============================================================
# FIX 5: Stripe publishable key fuera del bundle JS
# PROBLEMA: environment.prod.ts tiene pk_test_51T9DZb... hardcodeada.
#            Cualquier usuario puede verla en DevTools > Sources.
#            Aunque la pk es "pública por diseño" en Stripe, exponer
#            la clave de TEST en producción indica que el sistema
#            nunca ha cobrado dinero real.
#
# SOLUCIÓN EN 3 PASOS:
# ============================================================

# ---- PASO 1: Rotar la clave en Stripe Dashboard ----
# https://dashboard.stripe.com/test/apikeys
# → "Roll key" en la publishable key actual
# → Copiar la nueva pk_test_... (o mejor: la pk_live_... de producción)


# ---- PASO 2: env-config.sh — agregar stripePublishableKey ----
# Archivo: frontend-app/env-config.sh
# REEMPLAZAR con:

cat << 'EOF'
#!/bin/bash
# env-config.sh - Inyecta variables de entorno en runtime
# Variables configuradas en CI/CD (Vercel env vars, Docker env, K8s ConfigMap)

cat <<ENVEOF > /usr/share/nginx/html/assets/env-config.js
window.__env = {
  apiUrl: '${API_URL:-https://api.auron-suite.com/api}',
  wsUrl: '${WS_URL:-wss://api.auron-suite.com/ws}',
  stripePublishableKey: '${STRIPE_PUBLISHABLE_KEY:-}'
};
ENVEOF

echo "✅ Environment variables injected"
EOF


# ---- PASO 3: environment.prod.ts — leer desde window.__env ----
# Archivo: frontend-app/src/environments/environment.prod.ts
# REEMPLAZAR con:

cat << 'EOF'
/**
 * Environment - Production
 *
 * SEGURIDAD: Ninguna clave sensible debe estar en este archivo.
 * Todas las variables runtime se inyectan via env-config.sh → window.__env
 * Variables de build-time (no sensibles): appName, appVersion, feature flags.
 */
export const environment = {
  production: true,

  // ✅ URLs y claves desde runtime (nunca en bundle)
  apiUrl: (window as any).__env?.apiUrl || 'https://api.auron-suite.com/api',
  wsUrl: (window as any).__env?.wsUrl || 'wss://api.auron-suite.com/ws',

  // ✅ Stripe pk desde runtime — NUNCA hardcodeada aquí
  // En Vercel: Environment Variable STRIPE_PUBLISHABLE_KEY=pk_live_...
  // En Docker: -e STRIPE_PUBLISHABLE_KEY=pk_live_...
  stripePublishableKey: (window as any).__env?.stripePublishableKey || '',

  appName: 'Auron-Suite',
  appVersion: '1.0.0',

  enableDebugMode: false,
  enableMockData: false,

  csrfCookieName: 'csrftoken',
  sessionCookieName: 'sessionid',
};
EOF


# ---- PASO 4: environment.ts (dev) — nunca apuntar a producción ----
# Archivo: frontend-app/src/environments/environment.ts
# REEMPLAZAR con:

cat << 'EOF'
/**
 * Environment - Development
 * Apunta a localhost. Para conectar a staging usar:
 *   ng serve --configuration staging
 */
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api',
  wsUrl: 'ws://localhost:8000/ws',

  // En dev, Stripe siempre usa test key — leer de .env.local o var de entorno
  // NUNCA hardcodear aquí la clave real de staging/producción
  stripePublishableKey: process?.env?.['NG_APP_STRIPE_PK'] || 'pk_test_REPLACE_IN_LOCAL_ENV',

  appName: 'Auron-Suite (Dev)',
  appVersion: '1.0.0-dev',

  enableDebugMode: true,
  enableMockData: false,

  csrfCookieName: 'csrftoken',
  sessionCookieName: 'sessionid',
};
EOF


# ---- PASO 5: .gitignore — verificar que .env.local no se commitee ----
cat << 'EOF'
# Agregar a frontend-app/.gitignore si no está ya:
.env.local
.env.*.local
src/environments/environment.staging.ts
EOF


# ---- VERIFICACIÓN: Comprobar que el bundle no filtra la clave ----
# Ejecutar después de build:
# grep -r "pk_test_\|pk_live_" dist/ && echo "⚠️  CLAVE EN BUNDLE" || echo "✅ Bundle limpio"
