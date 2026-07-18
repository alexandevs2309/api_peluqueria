# JUSTIFICACIÓN TÉCNICA: Inmutabilidad en Modelo Sale

## Cambios Implementados

### 1. Campo `status` agregado al modelo Sale

**Valores permitidos:**
- `draft`: Venta en borrador (editable/eliminable)
- `confirmed`: Venta confirmada (inmutable)
- `void`: Venta anulada (inmutable)
- `refunded`: Venta reembolsada (inmutable)

**Default:** `confirmed` - Todas las ventas nuevas se crean como confirmadas.

---

## 2. Protección en `save()`

### Lógica implementada:

```
┌─────────────────────────────────────────────────────────────┐
│ CREACIÓN NUEVA (pk=None)                                    │
│ → Establecer status='confirmed' si no se especifica         │
│ → Permitir guardado                                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ MODIFICACIÓN (pk existe)                                    │
│                                                             │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Status anterior = 'draft'                           │   │
│ │ → Permitir cualquier modificación                   │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                             │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Status anterior = 'confirmed'                       │   │
│ │ → Solo permitir cambio a 'void' o 'refunded'       │   │
│ │ → Bloquear modificación de campos financieros       │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                             │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Status anterior = 'void' o 'refunded'               │   │
│ │ → Bloquear cualquier modificación                   │   │
│ │ → Lanzar ValidationError                            │   │
│ └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Transiciones de estado permitidas:

```
draft ──────────> confirmed
                      │
                      ├──────> void
                      │
                      └──────> refunded

void ────────────> [INMUTABLE]
refunded ────────> [INMUTABLE]
```

---

## 3. Protección en `delete()`

**Regla simple:**
- Solo se pueden eliminar ventas con `status='draft'`
- Cualquier otro status lanza `ValidationError`

---

## Compatibilidad con API Existente

### ✅ NO SE ROMPE NADA

1. **Serializers:** No modificados
   - Campo `status` se serializa automáticamente
   - Frontend lo recibe pero no es obligatorio enviarlo

2. **Endpoints:** No modificados
   - Mismas URLs
   - Mismos métodos HTTP
   - Mismas respuestas

3. **Flujo actual:**
   ```
   POST /api/pos/sales/
   {
     "client": 1,
     "details": [...],
     "payments": [...]
   }
   
   → Se crea con status='confirmed' automáticamente
   → Venta queda protegida contra modificaciones
   ```

4. **Comportamiento legacy:**
   - Ventas existentes sin `status` → migración establece 'confirmed'
   - Flujo de creación no cambia
   - Respuestas incluyen nuevo campo `status` (no breaking change)

---

## Beneficios de Seguridad

### 🔒 Protección Financiera

1. **Inmutabilidad automática:**
   - Ventas confirmadas no pueden editarse
   - Totales no pueden modificarse
   - Métodos de pago no pueden cambiarse

2. **Prevención de fraude:**
   - Empleados no pueden alterar ventas pasadas
   - Gerentes no pueden modificar totales después de cierre
   - Auditoría garantizada

3. **Integridad contable:**
   - Estado financiero reconstruible
   - Totales confiables
   - Reconciliación precisa

### 📊 Trazabilidad

1. **Estados claros:**
   - `confirmed`: Venta válida
   - `void`: Venta anulada (mantiene registro)
   - `refunded`: Venta reembolsada (mantiene registro)

2. **Historial preservado:**
   - Ventas anuladas no se eliminan
   - Datos originales intactos
   - Auditoría completa

---

## Casos de Uso

### Caso 1: Creación normal (actual)
```python
# Frontend envía (sin cambios)
POST /api/pos/sales/
{
  "client": 1,
  "total": 100.00,
  "details": [...]
}

# Backend crea con status='confirmed'
# Venta queda inmutable automáticamente
```

### Caso 2: Anulación de venta
```python
# Nuevo flujo (requiere endpoint adicional en futuro)
PATCH /api/pos/sales/123/
{
  "status": "void"
}

# Cambia status a 'void'
# Mantiene datos originales intactos
# No permite más modificaciones
```

### Caso 3: Intento de modificación (bloqueado)
```python
# Alguien intenta modificar total
PATCH /api/pos/sales/123/
{
  "total": 0.00  # Intento de fraude
}

# ValidationError:
# "No se puede modificar una venta con status 'confirmed'"
```

---

## Migración de Datos Existentes

**Estrategia:**
1. Agregar campo `status` con default='confirmed'
2. Todas las ventas existentes quedan como 'confirmed'
3. Quedan protegidas automáticamente
4. No se requiere migración de datos manual

**Rollback seguro:**
- Si se necesita revertir, simplemente eliminar campo `status`
- No hay dependencias críticas
- Código legacy sigue funcionando

---

## Próximos Pasos (Opcionales)

### Mejoras futuras sin romper API:

1. **Endpoint de anulación:**
   ```
   POST /api/pos/sales/{id}/void/
   ```

2. **Endpoint de reembolso:**
   ```
   POST /api/pos/sales/{id}/refund/
   ```

3. **Audit trail:**
   - Integrar con AuditLog existente
   - Registrar cambios de status

4. **Reportes:**
   - Filtrar por status
   - Excluir void/refunded de totales

---

## Conclusión

**Cambios mínimos, máximo impacto:**
- ✅ Inmutabilidad implementada
- ✅ API no rota
- ✅ Frontend no requiere cambios
- ✅ Seguridad financiera mejorada
- ✅ Migración segura
- ✅ Rollback posible

**Riesgo:** BAJO
**Impacto:** ALTO
**Esfuerzo:** MÍNIMO

**Recomendación:** Desplegar inmediatamente.
