#!/bin/bash
# post_restore_financial_validation.sh - Validación financiera después de restore
# Ubicación: api_peluqueria/ops/restore/post_restore_financial_validation.sh

set -euo pipefail

LOG_FILE="/var/log/financial_validation.log"
exec 1> >(tee -a "${LOG_FILE}")
exec 2>&1

echo "=== VALIDACIÓN FINANCIERA POST-RESTORE: $(date) ==="

ERRORS=0

# 1. Verificar tablas críticas existen
echo "Test 1: Verificando tablas financieras..."
TABLES=(
    "billing_api_invoice"
    "billing_api_payment"
    "billing_api_processedstripeevent"
    "billing_api_reconciliationlog"
    "billing_api_reconciliationalert"
    "subscriptions_api_subscription"
)

for table in "${TABLES[@]}"; do
    if psql -U postgres -d production -c "\d ${table}" > /dev/null 2>&1; then
        COUNT=$(psql -U postgres -t -c "SELECT COUNT(*) FROM ${table};")
        echo "✅ ${table}: ${COUNT} registros"
    else
        echo "❌ ERROR: Tabla ${table} no existe"
        ERRORS=$((ERRORS + 1))
    fi
done

# 2. Verificar último evento procesado
echo -e "\nTest 2: Verificando eventos Stripe procesados..."
LAST_EVENT=$(psql -U postgres -t -c "SELECT MAX(processed_at) FROM billing_api_processedstripeevent;" | xargs)
if [ -n "${LAST_EVENT}" ]; then
    echo "✅ Último evento procesado: ${LAST_EVENT}"
    
    # Calcular antigüedad
    LAST_EPOCH=$(date -d "${LAST_EVENT}" +%s 2>/dev/null || echo 0)
    NOW_EPOCH=$(date +%s)
    AGE_MINUTES=$(( (NOW_EPOCH - LAST_EPOCH) / 60 ))
    
    echo "   Antigüedad: ${AGE_MINUTES} minutos"
    
    if [ "${AGE_MINUTES}" -gt 30 ]; then
        echo "   ⚠️  WARNING: Último evento tiene más de 30 minutos"
    fi
else
    echo "❌ ERROR: No hay eventos procesados"
    ERRORS=$((ERRORS + 1))
fi

# 3. Verificar integridad referencial
echo -e "\nTest 3: Verificando integridad referencial..."
ORPHAN_PAYMENTS=$(psql -U postgres -t -c "
    SELECT COUNT(*) FROM billing_api_payment p
    LEFT JOIN billing_api_invoice i ON p.invoice_id = i.id
    WHERE i.id IS NULL;
" | xargs)

if [ "${ORPHAN_PAYMENTS}" -eq 0 ]; then
    echo "✅ No hay pagos huérfanos"
else
    echo "⚠️  WARNING: ${ORPHAN_PAYMENTS} pagos sin invoice asociado"
fi

# 4. Ejecutar reconciliación forzada
echo -e "\nTest 4: Ejecutando reconciliación forzada..."
if docker exec api_peluqueria-api-1 python manage.py reconcile_stripe --force 2>&1 | tee /tmp/recon_output.log; then
    echo "✅ Reconciliación completada"
    
    # Verificar resultados
    DISCREPANCIES=$(grep -o "Discrepancias encontradas: [0-9]*" /tmp/recon_output.log | grep -o "[0-9]*" || echo "0")
    echo "   Discrepancias encontradas: ${DISCREPANCIES}"
    
    if [ "${DISCREPANCIES}" -gt 0 ]; then
        echo "   ⚠️  WARNING: Se encontraron discrepancias"
    fi
else
    echo "❌ ERROR: Reconciliación falló"
    ERRORS=$((ERRORS + 1))
fi

# 5. Verificar alertas críticas
echo -e "\nTest 5: Verificando alertas críticas..."
CRITICAL_ALERTS=$(psql -U postgres -t -c "
    SELECT COUNT(*) FROM billing_api_reconciliationalert
    WHERE severity='critical' AND resolved=false;
" | xargs)

if [ "${CRITICAL_ALERTS}" -eq 0 ]; then
    echo "✅ No hay alertas críticas sin resolver"
else
    echo "⚠️  WARNING: ${CRITICAL_ALERTS} alertas críticas sin resolver"
    
    echo -e "\nAlertas críticas:"
    psql -U postgres -c "
        SELECT id, alert_type, description, created_at
        FROM billing_api_reconciliationalert
        WHERE severity='critical' AND resolved=false
        ORDER BY created_at DESC
        LIMIT 5;
    "
fi

# 6. Verificar última reconciliación
echo -e "\nTest 6: Verificando última reconciliación..."
LAST_RECON=$(psql -U postgres -t -c "
    SELECT completed_at FROM billing_api_reconciliationlog
    WHERE status='completed'
    ORDER BY completed_at DESC
    LIMIT 1;
" | xargs)

if [ -n "${LAST_RECON}" ]; then
    echo "✅ Última reconciliación: ${LAST_RECON}"
else
    echo "⚠️  WARNING: No hay reconciliaciones completadas"
fi

# 7. Generar reporte de salud
echo -e "\nTest 7: Generando reporte de salud financiera..."
docker exec api_peluqueria-api-1 python manage.py financial_health_report

# Resumen
echo -e "\n" + "="*50
echo "=== RESUMEN DE VALIDACIÓN ==="
if [ "${ERRORS}" -eq 0 ]; then
    echo "✅ Validación completada: Sistema financiero OK"
    echo "   - Tablas verificadas: ${#TABLES[@]}"
    echo "   - Eventos procesados: OK"
    echo "   - Reconciliación: OK"
    echo "   - Alertas críticas: ${CRITICAL_ALERTS}"
    exit 0
else
    echo "❌ Validación completada: ${ERRORS} errores encontrados"
    echo "   ⚠️  ACCIÓN REQUERIDA: Revisar errores antes de restaurar servicio"
    exit 1
fi
