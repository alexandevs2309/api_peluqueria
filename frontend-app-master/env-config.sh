#!/bin/bash
# env-config.sh - Inyecta variables de entorno en runtime
# 
# USO:
# 1. Configurar variables en CI/CD (Vercel, Docker, K8s)
# 2. Ejecutar este script antes de servir la app
# 3. Variables disponibles en window.__env

cat <<EOF > /usr/share/nginx/html/env-config.js
window.__env = {
  apiUrl: '${API_URL:-https://api-peluqueria-p25h.onrender.com/api}',
  wsUrl: '${WS_URL:-wss://api-peluqueria-p25h.onrender.com/ws}',
  stripePublishableKey: '${STRIPE_PUBLISHABLE_KEY:-}',
  logrocketAppId: '${LOGROCKET_APP_ID:-}'
};
EOF

echo "✅ Environment variables injected"
