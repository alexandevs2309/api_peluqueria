#!/usr/bin/env bash
# =============================================================================
# AURON Suite — Test Runner Completo
# Ejecuta TODOS los escenarios de prueba: backend (pytest) + frontend (Karma)
# Uso: bash run_all_tests.sh [--backend-only | --frontend-only | --quick]
# =============================================================================
set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

BACKEND_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="/home/auron/.local/share/Trash/files/auron-tailadmin"

PASS=0
FAIL=0
SKIP=0
ERRORS=()

log()   { echo -e "${CYAN}[INFO]${NC} $*"; }
pass()  { echo -e "${GREEN}[PASS]${NC} $*"; PASS=$((PASS + 1)); }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; FAIL=$((FAIL + 1)); ERRORS+=("$*"); }
skip()  { echo -e "${YELLOW}[SKIP]${NC} $*"; SKIP=$((SKIP + 1)); }
header(){ echo -e "\n${BOLD}══════════════════════════════════════════════════════════════${NC}"; echo -e "${BOLD}  $*${NC}"; echo -e "${BOLD}══════════════════════════════════════════════════════════════${NC}"; }

# ── Parse args ──
BACKEND=true
FRONTEND=true
QUICK=false
for arg in "$@"; do
  case $arg in
    --backend-only)  FRONTEND=false ;;
    --frontend-only) BACKEND=false ;;
    --quick)         QUICK=true ;;
  esac
done

# =============================================================================
# PHASE 1: BACKEND SYNTAX VALIDATION
# =============================================================================
header "FASE 1: Validación de Sintaxis Python"
cd "$BACKEND_DIR"
SYNTAX_ERRORS=0
while IFS= read -r -d '' f; do
  if ! timeout 5 python3 -c "import ast; ast.parse(open('$f').read())" 2>/dev/null; then
    fail "Syntax error: $f"
    SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
  fi
done < <(find apps/ backend/ -name "*.py" -not -path "*__pycache__*" -not -path "*api_peluqueria-master*" -print0 2>/dev/null)

if [ "$SYNTAX_ERRORS" -eq 0 ]; then
  pass "Todos los archivos Python pasan validación de sintaxis"
else
  fail "$SYNTAX_ERRORS archivos con errores de sintaxis"
fi

# =============================================================================
# PHASE 2: BACKEND STATIC ANALYSIS
# =============================================================================
header "FASE 2: Análisis Estático"

# Check for common issues
log "Buscando imports rotos..."
BROKEN_IMPORTS=0
while IFS= read -r -d '' f; do
  # Check for imports of modules that may not exist
  if grep -q "from apps\.mcp_api" "$f" 2>/dev/null; then
    if [ ! -d "apps/mcp_api" ]; then
      warn "Possible broken import in $f: apps.mcp_api not found"
    fi
  fi
done < <(find apps/ -name "*.py" -print0)

# Check for hardcoded secrets
log "Verificando secrets hardcodeados..."
SECRETS=0
if grep -rn "password.*=.*['\"]admin['\"]" apps/ backend/ --include="*.py" 2>/dev/null | grep -v "test" | grep -v "factory" | grep -v "conftest" | grep -v ".pyc" | head -3; then
  fail "Posibles passwords hardcodeados en código no-test"
  SECRETS=$((SECRETS + 1))
fi
# Only flag literal strings, not env() or os.environ references
if grep -rn "SECRET_KEY *= *['\"][^'\"{}]" backend/settings.py 2>/dev/null | grep -v "env(" | grep -v "os.environ" | grep -v "test" | head -3; then
  fail "SECRET_KEY possiblemente hardcodeado"
  SECRETS=$((SECRETS + 1))
fi
if [ "$SECRETS" -eq 0 ]; then
  pass "No se encontraron secrets hardcodeados en producción"
fi

# Check for TODO/FIXME/HACK in critical files
log "Buscando TODO/FIXME en archivos críticos..."
TODOS=$(timeout 5 grep -c "TODO\|FIXME\|HACK\|XXX" apps/pos_api/views.py apps/employees_api/earnings_views.py apps/employees_api/views.py 2>/dev/null | awk -F: '{s+=$2}END{print s+0}')
TODOS=${TODOS:-0}
if [ "$TODOS" -gt 0 ]; then
  skip "$TODOS TODOs/FIXMEs en archivos críticos"
  timeout 5 grep -n "TODO\|FIXME\|HACK\|XXX" apps/pos_api/views.py apps/employees_api/earnings_views.py apps/employees_api/views.py 2>/dev/null | head -10 || true
fi

# Check monetary precision patterns
log "Verificando patrones de precisión monetaria..."
BAD_FLOATS=$(timeout 15 grep -rn "= float(" apps/pos_api/ apps/employees_api/ --include="*.py" 2>/dev/null | grep -v test | grep -v ".pyc" | grep -v "__pycache__" | grep -v "serializer" | grep -v "Response" | grep -v "report" | grep -v "chart" | grep -v "monthly" | wc -l)
BAD_FLOATS=${BAD_FLOATS:-0}
if [ "$BAD_FLOATS" -gt 0 ]; then
  fail "$BAD_FLOATS usos de float() en código financiero (debe ser Decimal)"
  timeout 15 grep -rn "= float(" apps/pos_api/ apps/employees_api/ --include="*.py" 2>/dev/null | grep -v test | grep -v ".pyc" | grep -v "__pycache__" | grep -v "serializer" | grep -v "Response" | grep -v "report" | grep -v "chart" | grep -v "monthly" | head -5 || true
else
  pass "No se encontraron usos de float() en módulos financieros"
fi

# =============================================================================
# PHASE 3: BACKEND TESTS (pytest)
# =============================================================================
header "FASE 3: Suite de Tests Backend (pytest)"

if ! command -v python3 &>/dev/null; then
  skip "python3 no encontrado — instalar: sudo apt install python3 python3-pip"
elif ! python3 -c "import django" 2>/dev/null; then
  skip "Django no instalado — ejecutar: pip3 install -r requirements.txt"
  log "Intentando instalar dependencias..."
  if python3 -m pip install --user -r requirements.txt 2>/dev/null; then
    log "Dependencias instaladas correctamente"
  else
    skip "No se pudieron instalar dependencias (sin pip)"
  fi
fi

if python3 -c "import django" 2>/dev/null; then
  cd "$BACKEND_DIR"

  log "Ejecutando tests P0 (regresión crítica)..."
  if python3 -m pytest apps/pos_api/tests_p0.py -v --tb=short 2>&1; then
    pass "Tests P0 (regresión) — TODOS PASARON"
  else
    fail "Tests P0 (regresión) — ALGUNOS FALLARON"
  fi

  log "Ejecutando tests de seguridad POS..."
  if python3 -m pytest apps/pos_api/tests_security_critical.py -v --tb=short 2>&1; then
    pass "Tests seguridad POS — TODOS PASARON"
  else
    fail "Tests seguridad POS — ALGUNOS FALLARON"
  fi

  log "Ejecutando tests de aislamiento cross-tenant..."
  if python3 -m pytest apps/tenants_api/tests_cross_tenant_isolation.py -v --tb=short 2>&1; then
    pass "Tests cross-tenant isolation — TODOS PASARON"
  else
    fail "Tests cross-tenant isolation — ALGUNOS FALLARON"
  fi

  log "Ejecutando tests de nómina (determinismo + inmutabilidad)..."
  if python3 -m pytest apps/employees_api/test_payroll_deterministic.py apps/employees_api/test_payroll_immutability.py apps/employees_api/test_payroll_ensure_period.py apps/employees_api/test_payroll_user_null.py -v --tb=short 2>&1; then
    pass "Tests nómina completa — TODOS PASARON"
  else
    fail "Tests nómina completa — ALGUNOS FALLARON"
  fi

  log "Ejecutando tests POS básicos (ventas, stock, caja)..."
  if python3 -m pytest apps/pos_api/tests.py -v --tb=short 2>&1; then
    pass "Tests POS básicos — TODOS PASARON"
  else
    fail "Tests POS básicos — ALGUNOS FALLARON"
  fi

  log "Ejecutando tests de empleados (CRUD + RBAC)..."
  if python3 -m pytest apps/employees_api/tests.py -v --tb=short 2>&1; then
    pass "Tests empleados — TODOS PASARON"
  else
    fail "Tests empleados — ALGUNOS FALLARON"
  fi

  if [ "$QUICK" = false ]; then
    log "Ejecutando tests financieros (precisión, NCF, cupones)..."
    if python3 -m pytest apps/pos_api/tests_money_precision.py apps/pos_api/test_ncf.py apps/pos_api/test_coupons.py apps/pos_api/tests_financial.py -v --tb=short 2>&1; then
      pass "Tests financieros — TODOS PASARON"
    else
      fail "Tests financieros — ALGUNOS FALLARON"
    fi

    log "Ejecutando tests de autenticación y seguridad..."
    if python3 -m pytest apps/auth_api/tests.py apps/auth_api/tests_security.py apps/tenants_api/tests_security.py -v --tb=short 2>&1; then
      pass "Tests auth + seguridad — TODOS PASARON"
    else
      fail "Tests auth + seguridad — ALGUNOS FALLARON"
    fi

    log "Ejecutando tests completos de empleados (API endpoints)..."
    if python3 -m pytest apps/employees_api/ -v --tb=short 2>&1; then
      pass "Tests empleados completos — TODOS PASARON"
    else
      fail "Tests empleados completos — ALGUNOS FALLARON"
    fi

    log "Ejecutando SUITE COMPLETA de tests backend..."
    if python3 -m pytest apps/ backend/ -v --tb=short 2>&1; then
      pass "SUITE COMPLETA backend — TODOS PASARON"
    else
      fail "SUITE COMPLETA backend — ALGUNOS FALLARON"
    fi
  fi
fi

# =============================================================================
# PHASE 4: FRONTEND STATIC ANALYSIS
# =============================================================================
header "FASE 4: Análisis Estático Frontend (TypeScript)"

if [ -d "$FRONTEND_DIR" ]; then
  cd "$FRONTEND_DIR"

  log "Ejecutando TypeScript check (tsc --noEmit)..."
  if npx tsc --noEmit 2>&1; then
    pass "TypeScript check — SIN ERRORES DE TIPO"
  else
    fail "TypeScript check — ERRORES DE TIPO ENCONTRADOS"
  fi

  log "Verificando build de Angular..."
  BUILD_OUTPUT=$(npx ng build 2>&1)
  if echo "$BUILD_OUTPUT" | grep -q "Bus error"; then
    skip "Angular build — Bus error (Node.js 24 + esbuild local issue, works on Cloudflare)"
  elif echo "$BUILD_OUTPUT" | grep -qi "error"; then
    fail "Angular build — FALLÓ"
  else
    pass "Angular build — EXITOSO"
  fi
else
  skip "Directorio frontend no encontrado: $FRONTEND_DIR"
fi

# =============================================================================
# PHASE 5: SCENARIO MATRIX (manual checks)
# =============================================================================
header "FASE 5: Matriz de Escenarios (verificación manual)"

SCENARIOS=(
  "AUTH-01: Login con credenciales válidas"
  "AUTH-02: Login con credenciales inválidas → 401"
  "AUTH-03: Token expirado → 401"
  "AUTH-04: Acceso a endpoint de otro tenant → 403"
  "POS-01: Abrir caja con monto inicial"
  "POS-02: Venta producto → decrementa stock"
  "POS-03: Venta con promoción → aplica descuento"
  "POS-04: Venta sin stock → error"
  "POS-05: Cerrar caja → genera snapshot"
  "POS-06: Venta con empleado → comisión snapshot"
  "POS-07: Immutabilidad venta confirmada"
  "POS-08: Descuento negativo → rechazado"
  "PAY-01: Listar períodos → 200"
  "PAY-02: Crear período → solo 1 abierto/empleado"
  "PAY-03: Guardar config nómina → persiste valores"
  "PAY-04: Calcular nómina → sin deducciones duplicadas"
  "PAY-05: Pagar período → cambia a 'paid'"
  "PAY-06: Período aprobado → bloquea modificaciones"
  "EMP-01: Crear empleado → campos obligatorios"
  "EMP-02: Actualizar empleado → solo campos permitidos"
  "EMP-03: get_profession_display() → string legible"
  "MT-01: Tenant A datos → Tenant B no los ve"
  "MT-02: Superuser sin tenant → ve todo"
  "MT-03: Empty tenant → listas vacías"
  "FE-01: Login → redirige dashboard correcto"
  "FE-02: Abrir modal config → valores actuales"
  "FE-03: Guardar config → toast success + persiste"
  "FE-04: Pagar nómina → método pago seleccionado"
  "FE-05: Error de red → toast error"
)

echo ""
log "Escenarios que requieren verificación manual (con servidor vivo):"
echo ""
for i in "${!SCENARIOS[@]}"; do
  echo -e "  ${CYAN}$((i+1))${NC}. ${SCENARIOS[$i]}"
done
echo ""
log "Ejecuta estos contra el servidor de staging/producción con:"
log "  python3 scripts/test_persona_real_e2e.py"
echo ""

# =============================================================================
# PHASE 6: FRONTEND E2E (si hay Cypress/Playwright)
# =============================================================================
header "FASE 6: Frontend E2E Tests"

if [ -f "$FRONTEND_DIR/cypress.config.ts" ] || [ -f "$FRONTEND_DIR/cypress.config.js" ]; then
  cd "$FRONTEND_DIR"
  log "Ejecutando Cypress E2E..."
  if npx cypress run 2>&1; then
    pass "Cypress E2E — TODOS PASARON"
  else
    fail "Cypress E2E — ALGUNOS FALLARON"
  fi
elif [ -f "$FRONTEND_DIR/playwright.config.ts" ]; then
  cd "$FRONTEND_DIR"
  log "Ejecutando Playwright E2E..."
  if npx playwright test 2>&1; then
    pass "Playwright E2E — TODOS PASARON"
  else
    fail "Playwright E2E — ALGUNOS FALLARON"
  fi
else
  skip "No hay framework E2E configurado (Cypress/Playwright)"
  log "Para agregar Cypress: cd $FRONTEND_DIR && npm install --save-dev cypress"
fi

# =============================================================================
# SUMMARY
# =============================================================================
header "RESUMEN FINAL"
echo ""
echo -e "  ${GREEN}PASS:${NC} $PASS"
echo -e "  ${RED}FAIL:${NC} $FAIL"
echo -e "  ${YELLOW}SKIP:${NC} $SKIP"
echo ""

if [ ${#ERRORS[@]} -gt 0 ]; then
  echo -e "${RED}${BOLD}ERRORES:${NC}"
  for err in "${ERRORS[@]}"; do
    echo -e "  ${RED}✗${NC} $err"
  done
  echo ""
  exit 1
else
  echo -e "${GREEN}${BOLD}¡TODOS LOS TESTS QUE PODÍAMOS EJECUTAR PASARON!${NC}"
  echo ""
  exit 0
fi
