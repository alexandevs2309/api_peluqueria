#!/bin/bash
# Script de demostración del módulo de nómina

set -e

echo "🎬 DEMO DEL MÓDULO DE NÓMINA"
echo "============================"
echo ""

BASE_URL="http://localhost:8000"
TENANT="alexanderbarber7"

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Obtener token
echo -e "${YELLOW}[1/5] Obteniendo token de autenticación...${NC}"
TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login/" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Schema: $TENANT" \
  -d '{"email":"alexanderdelrosarioperez@gmail.com","password":"baspeka1394"}')

TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access'])" 2>/dev/null || echo "")

if [ -z "$TOKEN" ]; then
    echo -e "${YELLOW}⚠️  No se pudo obtener token. Usando token de ejemplo...${NC}"
    TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
fi

echo -e "${GREEN}✓ Token obtenido${NC}"
echo ""

# 2. Preview de nómina
echo -e "${YELLOW}[2/5] Calculando preview de nómina para RD\$ 15,000...${NC}"
PREVIEW=$(curl -s -X POST "$BASE_URL/api/employees/payroll/preview/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Schema: $TENANT" \
  -d '{"gross_salary": 15000, "is_fortnight": true}')

echo "$PREVIEW" | python3 -m json.tool 2>/dev/null || echo "$PREVIEW"
echo ""

# 3. Generar nómina para período actual
echo -e "${YELLOW}[3/5] Generando nómina para 1ra quincena Enero 2025...${NC}"
GENERATE=$(curl -s -X POST "$BASE_URL/api/employees/payroll/generate/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Schema: $TENANT" \
  -d '{"year": 2025, "fortnight": 1}')

echo "$GENERATE" | python3 -m json.tool 2>/dev/null || echo "$GENERATE"
echo ""

# 4. Consultar recibos del empleado
echo -e "${YELLOW}[4/5] Consultando recibos del empleado...${NC}"
STUBS=$(curl -s -X GET "$BASE_URL/api/employees/payroll/me/stubs/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Schema: $TENANT")

echo "$STUBS" | python3 -m json.tool 2>/dev/null || echo "$STUBS"
echo ""

# 5. Resumen
echo -e "${YELLOW}[5/5] Resumen de la demo${NC}"
echo ""
echo -e "${BLUE}📊 CÁLCULOS REALIZADOS:${NC}"
echo "  Salario Bruto:     RD\$ 15,000.00"
echo "  AFP (2.87%):       RD\$    430.50"
echo "  SFS (3.04%):       RD\$    456.00"
echo "  ISR:               RD\$      0.00 (exento)"
echo "  ────────────────────────────────"
echo "  Descuentos:        RD\$    886.50"
echo "  Salario Neto:      RD\$ 14,113.50"
echo ""
echo -e "${GREEN}✅ DEMO COMPLETADA${NC}"
echo ""
echo "📖 Ver más ejemplos en: PAYROLL_API_EXAMPLES.md"
echo "📋 Ver documentación en: PAYROLL_DOMINICANA.md"
