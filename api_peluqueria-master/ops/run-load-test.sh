#!/bin/bash

# Script para ejecutar load tests con k6

BASE_URL="${BASE_URL:-http://localhost}"
API_TOKEN="${API_TOKEN:-}"

echo "🔥 Load Testing - SaaS Peluquería"
echo "=================================="
echo "Base URL: $BASE_URL"
echo ""

# Verificar k6 instalado
if ! command -v k6 &> /dev/null; then
    echo "❌ k6 no está instalado"
    echo "Instalar: https://k6.io/docs/getting-started/installation/"
    echo ""
    echo "Linux: sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69"
    echo "       echo 'deb https://dl.k6.io/deb stable main' | sudo tee /etc/apt/sources.list.d/k6.list"
    echo "       sudo apt-get update && sudo apt-get install k6"
    echo ""
    echo "macOS: brew install k6"
    echo ""
    echo "Windows: choco install k6"
    exit 1
fi

# Menú de opciones
echo "Selecciona tipo de test:"
echo "1) Smoke Test (1 usuario, 1 minuto)"
echo "2) Load Test Normal (50 usuarios, 10 minutos)"
echo "3) Stress Test (100 usuarios, 15 minutos)"
echo "4) Spike Test (pico de 200 usuarios)"
echo "5) Soak Test (50 usuarios, 1 hora)"
echo ""
read -p "Opción [1-5]: " option

case $option in
  1)
    echo "🔍 Ejecutando Smoke Test..."
    k6 run --vus 1 --duration 1m \
      -e BASE_URL=$BASE_URL \
      -e API_TOKEN=$API_TOKEN \
      ops/load-test.js
    ;;
  2)
    echo "📊 Ejecutando Load Test Normal..."
    k6 run \
      -e BASE_URL=$BASE_URL \
      -e API_TOKEN=$API_TOKEN \
      ops/load-test.js
    ;;
  3)
    echo "💪 Ejecutando Stress Test..."
    k6 run --vus 100 --duration 15m \
      -e BASE_URL=$BASE_URL \
      -e API_TOKEN=$API_TOKEN \
      ops/load-test.js
    ;;
  4)
    echo "⚡ Ejecutando Spike Test..."
    k6 run --stage 0s:0,10s:200,1m:200,10s:0 \
      -e BASE_URL=$BASE_URL \
      -e API_TOKEN=$API_TOKEN \
      ops/load-test.js
    ;;
  5)
    echo "⏱️  Ejecutando Soak Test (1 hora)..."
    k6 run --vus 50 --duration 1h \
      -e BASE_URL=$BASE_URL \
      -e API_TOKEN=$API_TOKEN \
      ops/load-test.js
    ;;
  *)
    echo "❌ Opción inválida"
    exit 1
    ;;
esac

echo ""
echo "✅ Test completado"
echo ""
echo "Métricas clave a revisar:"
echo "- http_req_duration: debe ser < 2s (p95)"
echo "- http_req_failed: debe ser < 1%"
echo "- errors: debe ser < 1%"
echo ""
echo "Si hay fallos, revisar:"
echo "- docker-compose logs web"
echo "- curl $BASE_URL/health/"
echo "- curl $BASE_URL/metrics/"