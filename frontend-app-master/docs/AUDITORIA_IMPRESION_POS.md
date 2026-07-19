# Auditoría Completa del Sistema de Impresión del POS

> **Fecha:** 2026-06-27
> **Auditor:** OpenCode (Build)
> **Propósito:** Auditoría forense del sistema de impresión — por qué funciona en reportes y no en POS

---

## 1. Diagrama de Flujo Actual

```
Usuario hace clic en "Imprimir" (dentro del p-dialog del POS)
    │
    ▼
[1] pos-system.html:698
    (click)="imprimirTicket()"
    │
    ▼
[2] pos-system.ts:618
    imprimirTicket()  (async)
    │
    ├── ¿navigator.serial existe?
    │   ├── SÍ → [3] imprimirTermica() → WebSerial API → ESC/POS raw
    │   │   └── Error ≠ NotFoundError → cae a [4]
    │   └── NO  → [4] directamente
    │
    ▼
[4] imprimirTicketNavegador()
    │
    ├── window.open('', '_blank', 'width=400,height=700')
    │   ├── null → toast "habilita pop-ups" → FIN
    │   └── Window OK → document.write(html) → close() → focus()
    │       │
    │       ▼
    │   setTimeout(() => w.print(), 500)
    │       │
    │       ▼
    │   Browser print dialog → usuario selecciona impresora
    │       │
    │       ▼
    │   @media print en HTML inline → 80mm thermal format
    │
    └── FIN
```

### Flujo Alternativo (nunca ha funcionado — Ctrl+P / File → Print desde el dialog)

```
Usuario hace Ctrl+P o File → Print
    │
    ▼
Navegador aplica @media print del SCSS
    │
    ├── body * { visibility: hidden !important; }
    ├── .receipt, .receipt * { visibility: visible !important; }
    ├── .receipt { position: absolute; left: 0; top: 0; width: 72mm; }
    ├── .receipt-actions { display: none !important; }
    ├── @page { margin: 0; size: 80mm auto; }
    │
    ▼
??? (Nunca se ha verificado que funcione)
```

---

## 2. IMPLEMENTACIONES DE IMPRESIÓN

### Implementación A — Popup window (activa, corregida en esta sesión)
- **Archivo:** `pos-system.ts:634-793`
- **Método:** `imprimirTicketNavegador()`
- **Qué hace:** Abre `window.open('', '_blank', 'width=400,height=700')`, escribe HTML con CSS inline hardcodeado, auto-dispara `window.print()` tras 500ms
- **Estado:** ✅ ACTIVA — corregida en esta sesión

### Implementación B — WebSerial ESC/POS térmico (activa pero no usada)
- **Archivo:** `pos-system.ts:822-908`
- **Método:** `imprimirTermica()`
- **Qué hace:** Usa `navigator.serial.requestPort()` (WebSerial API) para conectar a impresora térmica vía puerto serie a 9600 baud, envía raw ESC/POS commands (initialize, center, double-height, cut) codificados en CP437
- **Estado:** ✅ ACTIVA — solo en Chrome desktop con WebSerial. El catch en `imprimirTicket()` maneja correctamente el fallback a popup

### Implementación C — @media print desde el dialog (presente pero no verificada)
- **Archivo:** `pos-system.scss:1293-1489`
- **Qué hace:** Define estilos `@media print` para imprimir el ticket directamente desde el `p-dialog` usando `visibility: hidden/visible`
- **Estado:** ⚠️ PRESENTE — nunca se ha verificado que funcione correctamente. Probablemente rota por ViewEncapsulation de Angular (ver Problema CRÍTICO #2)

### Implementación D — Cierre de caja (PDF)
- **Archivo:** `pos-system.ts:1382-1417`
- **Método:** `generarPDFCuadre(data)`
- **Qué hace:** Abre popup, escribe HTML, auto-imprime con `window.onload=function(){window.print();setTimeout(()=>window.close(),1000)}`
- **Estado:** ✅ ACTIVA — mismo patrón que reportes

### Implementación E — Reimpresión desde historial
- **Archivo:** `pos-system.ts:993-1014`
- **Método:** `reimprimirRecibo(ventaId)`
- **Qué hace:** Llama `GET /api/pos/sales/{id}/print_receipt/` (backend), luego `mostrarTicket()` con los datos + `imprimirTicket()`
- **Estado:** ✅ ACTIVA — delega en A para impresión real

---

## 3. PROBLEMAS ENCONTRADOS

### 🔴 CRÍTICO #1 — Sin detección de popup bloqueado (CORREGIDO)

**Archivo:** `pos-system.ts:638` (antes: línea 797)
**Antes:**
```typescript
const w = window.open('', '_blank', 'width=400,height=700')
if (w) {
    w.document.write(html)
    w.document.close()
}
```
**Problema:** No verificaba `if (!w)`. Si el navegador bloqueaba el popup, `w` era `null` y el código no hacía nada. Sin toast, sin error, sin feedback. El usuario hacía clic y no pasaba nada.

**Cómo lo saben los reportes:**
- `client-reports.ts:783`: `if (!ventana) { messageService.add(...) }`
- `admin-reports.ts:708`: `if (!printWindow) { throw new Error('Popup blocked') }`
- `billing-management.ts:742`: `if (!printWindow) { messageService.add(...) }`

**Fix aplicado en esta sesión:** Agregado check `if (!w)` con toast.

---

### 🔴 CRÍTICO #2 — @media print en SCSS con ViewEncapsulation (NO CORREGIDO — requiere Think)

**Archivo:** `pos-system.scss:1293-1489`
**Problema:**
El `p-dialog` de PrimeNG porta su contenido al `document.body` mediante `@angular/cdk/portal`. Los estilos SCSS de Angular usan ViewEncapsulation Emulated por defecto, lo que significa que `.receipt` en el SCSS se compila a `.receipt[_nghost-xxx]`. En el contenido portado del dialog, el atributo `_nghost-xxx` NO está presente → los estilos `@media print` del SCSS **nunca se aplican** al ticket dentro del dialog.

**Impacto:** La función de impresión vía Ctrl+P / File → Print desde el dialog **nunca ha funcionado** porque los estilos CSS de impresión no se aplican al contenido portado.

**¿Por qué funciona en otros componentes?**
- **Reportes, nómina, empleados:** Usan `window.open()` → popup con CSS inline → sin ViewEncapsulation de por medio
- **Admin:** Usan `window.open()` → mismo patrón

**Qué debería pasar según el código:**
```css
body * { visibility: hidden !important; }
.receipt, .receipt * { visibility: visible !important; }
```
Esto ocultaría TODO salvo `.receipt`, posicionando el recibo en la esquina superior izquierda. Pero al estar dentro de un p-dialog portado, los estilos no llegan.

**Solución posible:** La impresión vía popup (Implementación A) es el camino correcto. La ruta del dialog debe considerarse **abandonada** o reemplazarse agregando estilos globales en `styles.scss` (sin ViewEncapsulation) para el @media print si se desea soportar Ctrl+P.

---

### 🔴 CRÍTICO #3 — CSS variables `var(--surface-*)` en popup (CORREGIDO)

**Archivo:** `pos-system.ts:653-745` (antes de la corrección)
**Problema:** El HTML generado para el popup usaba `var(--surface-100)`, `var(--text-color)`, `var(--primary-color-text)`, etc. Estas variables CSS son definidas por PrimeNG en el contexto de la aplicación Angular. En un popup independiente (`window.open`), **NO existen**. Resultado:
- `background: var(--surface-900)` → `transparent`
- `color: var(--primary-color-text)` → `canvastext` (negro, visible por suerte)
- El botón "Imprimir" tenía fondo transparente + borde transparente → INVISIBLE
- El usuario veía el contenido del ticket pero NO los botones de acción

**Por qué los reportes NO tenían este problema:** Los reportes usan auto-print (`setTimeout(() => ventana.print(), 400)`) en vez de botón dentro del popup.

**Fix aplicado en esta sesión:**
- Reemplazadas todas las `var(--surface-*)` con valores hardcodeados
- Ej: `background: #f4f4f5` en vez de `background: var(--surface-100)`
- Eliminados los botones inline del popup (`.actions { display: none; }`)
- Auto-print via `setTimeout(() => w.print(), 500)` como hacen los reportes

---

### 🔴 CRÍTICO #4 — Sin auto-print en popup (CORREGIDO)

**Archivo:** `pos-system.ts:790-793` (antes: botones onclick)
**Antes:** El popup mostraba botones "Imprimir" y "Cerrar" que el usuario debía clickear. Además de ser invisibles (CRÍTICO #3), requerían interacción manual.
**Después:** Auto-trigger de `w.print()` tras 500ms.

**Patrón usado en otros componentes (todos funcionan):**
- `client-reports.ts:795`: `setTimeout(() => ventana.print(), 400)`
- `admin-reports.ts:734-736`: `setTimeout(() => printWindow.print(), 500)`
- `billing-management.ts:754-756`: `setTimeout(() => printWindow.print(), 300)`
- `payroll/periods-list.component.ts:309`: `setTimeout(() => ventana.print(), 300)`

---

### 🟡 ALTO #1 — ImprimirTermica: try/catch parcial que traga errores

**Archivo:** `pos-system.ts:624-628`
```typescript
} catch (e) {
    if ((e as DOMException)?.name === 'NotFoundError') {
        this.messageService.add(...)
        return
    }
}
```
**Problema:** Si `imprimirTermica()` lanza un error que NO es `NotFoundError` (ej: `SecurityError` porque el usuario está en HTTP, `NetworkError` porque el puerto se desconectó), el catch lo atrapa pero NO hace return → el código cae a `imprimirTicketNavegador()`. Esto es funcionalmente correcto (fallback), pero el error se traga silenciosamente. Si hay múltiples fallos, el usuario no recibe diagnóstico.

**Recomendación:** Loggear el error en desarrollo:
```typescript
} catch (e) {
    if ((e as DOMException)?.name === 'NotFoundError') {
        this.messageService.add(...)
        return
    }
    if (!environment.production) console.error('[POS] Thermal print failed:', e)
}
```

---

### 🟡 ALTO #2 — Detecta WebSerial aunque no haya impresora conectada

**Archivo:** `pos-system.ts:619`
```typescript
const serial = (navigator as { serial?: { requestPort: () => Promise<unknown> } }).serial
if (serial) { ... }
```
**Problema:** `navigator.serial` existe en Chrome desktop aunque no haya ninguna impresora USB/serie conectada. Todos los usuarios de Chrome ven el selector de puerto serie al hacer clic en "Imprimir", incluso si quieren imprimir en una impresora de red o PDF. Esto es confuso y rompe el flujo.

**Impacto:** En Chrome:
1. Usuario hace clic en "Imprimir"
2. Aparece el selector de puerto serie del navegador (no el diálogo de impresión)
3. Usuario se confunde, cierra el selector → `NotFoundError` → toast "Selección de puerto cancelada"
4. Usuario nunca llega al diálogo de impresión real

**Solución:** Pedir confirmación antes de activar WebSerial:
```typescript
if (serial && confirm('¿Conectar a impresora térmica USB?')) {
    // intentar térmico
} else {
    this.imprimirTicketNavegador()
}
```

---

### 🟡 ALTO #3 — Cierre de caja: popup sin detección de bloqueo

**Archivo:** `pos-system.ts:1412-1416`
```typescript
const w = window.open('', '_blank')
if (w) {
    w.document.write(...)
    w.document.close()
}
```
**Problema:** No verifica `if (!w)`. Mismo bug que CRÍTICO #1 pero en el método de cierre de caja.

**Severidad:** ALTO porque el cierre de caja es un flujo administrativo que ocurre menos frecuentemente, pero el usuario no recibe feedback si el popup es bloqueado.

---

### 🟡 ALTO #4 — Sin registro de impresiones fallidas

**Backend:** `pos_api/views.py:980-1006`
```python
def print_receipt(self, request, pk=None):
    sale = self.get_object()
    receipt, created = Receipt.objects.get_or_create(...)
    receipt.printed_count += 1
    receipt.last_printed = timezone.now()
    receipt.save()
```
**Problema:** `printed_count` se incrementa CADA VEZ que el frontend llama al endpoint, NO cuando la impresión real ocurre. Si el usuario hace clic en "Reimprimir" 10 veces, `printed_count` marca 10 aunque nunca se haya impreso realmente (popup bloqueado).

**Solución:** Mover el incremento al frontend, después de que `window.print()` se ejecute, o agregar un estado "confirmed" vía `afterprint` event. El backend no tiene forma de saber si la impresión se completó.

---

### 🟡 MEDIO #1 — Sin `@page` size consistente

**Archivo:** `pos-system.scss:1485-1488`
```css
@page {
    margin: 0;
    size: 80mm auto;
}
```
**Problema:** La directiva `@page { size: 80mm auto; }` es ignorada por la mayoría de los navegadores modernos cuando hay `window.print()`. Solo funciona correctamente en Firefox. Chrome y Edge usan el tamaño de página configurado en la impresora o el sistema.

**Impacto:** El usuario debe seleccionar manualmente "80mm x papel continuo" o "Ajustar al ancho" en el diálogo de impresión de Chrome.

---

### 🟡 MEDIO #2 — Codificación CP437 incompleta

**Archivo:** `pos-system.ts:808-828`
```typescript
private encodeCP437(text: string): Uint8Array {
    const cp437Map: Record<string, number> = {
        'á': 0xA0, 'é': 0x82, 'í': 0xA1, 'ó': 0xA2, 'ú': 0xA3,
        'ñ': 0xA4, 'ü': 0x81, 'Á': 0xB5, 'É': 0x90, 'Í': 0xD6,
        'Ó': 0xE0, 'Ú': 0xE9, 'Ñ': 0xA5, 'Ü': 0x9A, '¿': 0xA8,
        '¡': 0xAD, '€': 0x80,
    }
```
**Problema:** El mapeo CP437 tiene solo 17 caracteres. Caracteres comunes en español como `º`, `ª`, `«`, `»`, `—`, `–`, `•`, `·` se convierten a espacio (0x20). Si el nombre del negocio contiene alguno de estos, se pierde.

---

### 🟢 BAJO #1 — Código CSS duplicado

**Archivo:** `pos-system.scss:1211-1215`
```css
@media print {
    .receipt-info-line { font-size: 7px; }
}
```
**Problema:** Este pequeño bloque `@media print` está separado del bloque principal (línea 1293) que contiene el resto de los estilos de impresión. El mismo `font-size: 7px` está repetido en línea 1459 dentro del bloque grande. El bloque pequeño parece ser código residual.

---

### 🟢 BAJO #2 — `printReceipt` llama al backend pero no usa el resultado para imprimir

**Archivo:** `pos-system.ts:993-1014`
```typescript
async reimprimirRecibo(ventaId: number) {
    try {
        const data = await this.api.printReceipt(ventaId)
        this.mostrarTicket(data.sale, data)
        this.messageService.add({ ... })
    } catch (err) { ... }
}
```
**Problema:** La respuesta del backend incluye `business_info` (nombre, dirección, teléfono) y `receipt` (datos del recibo como `printed_count`, `receipt_number`). Pero `mostrarTicket()` solo usa `sale` y `payload` — los datos de `business_info` del backend se ignoran. La info del negocio se toma de `configuracionPos` (que está en frontend), no del backend.

---

### 🟢 BAJO #3 — `auto_print_receipt` sin implementar

**Backend:** `pos_api/models.py:429`
```python
auto_print_receipt = models.BooleanField(default=False)
```
**Frontend:** `pos-system.ts` y `pos-system.html`
**Problema:** El campo `auto_print_receipt` existe en `PosConfiguration` y su serializador, pero NUNCA se usa en el frontend. Después de `confirmarVenta()`, el dialog del ticket se muestra siempre (con el botón "Imprimir"). No hay lógica que verifique esta bandera para imprimir automáticamente al completar la venta.

---

## 4. ARCHIVOS IMPLICADOS

| Archivo | Líneas | Rol | Estado |
|---------|--------|-----|--------|
| `frontend-app/src/app/pages/client/pos/pos-system.ts` | 106, 120, 512-575, 596-616, 618-631, 634-793, 808-828, 822-908, 910-916, 928, 991-1014, 1382-1417 | TODO el sistema de impresión del POS | ✅ Corregido parcialmente |
| `frontend-app/src/app/pages/client/pos/pos-system.html` | 422, 570-701, 698 | Template del dialog + botones | ✅ Sin cambios |
| `frontend-app/src/app/pages/client/pos/pos-system.scss` | 948-1489 | Estilos del recibo + @media print | ⚠️ @media print no funcional |
| `frontend-app/src/app/pages/client/pos/pos.types.ts` | 62-95 | Interfaces TicketItem, TicketData | ✅ Correcto |
| `frontend-app/src/app/pages/client/pos/pos.api.ts` | 39-41 | Método printReceipt() | ✅ Correcto |
| `frontend-app/src/app/core/services/pos/pos.service.ts` | 154-156 | HTTP GET print_receipt | ✅ Correcto |
| `frontend-app/src/app/core/config/api.config.ts` | 76 | Endpoint PRINT_RECEIPT | ✅ Correcto |
| `frontend-app/src/app/core/services/locale/translations.ts` | 1249, 1324, 1346-1363, 1394-1398, 1435-1446 (ES), 3338, 3360-3377, 3408-3412, 3449-3460 (EN) | Traducciones | ✅ Correcto |
| `api_peluqueria/apps/pos_api/views.py` | 31-45, 47-82, 980-1006 | Permission map, _get_business_info, print_receipt action | ✅ Correcto |
| `api_peluqueria/apps/pos_api/models.py` | 399-411, 427-429 | Modelos Receipt, PosConfiguration | ✅ Correcto |
| `api_peluqueria/apps/pos_api/serializers.py` | 291-296, 298-305 | ReceiptSerializer, PosConfigurationSerializer | ✅ Correcto |

---

## 5. CÓDIGO SOSPECHOSO

### 5.1 — Fallback silencioso en imprimirTicket (línea 624-628)
```typescript
} catch (e) {
    if ((e as DOMException)?.name === 'NotFoundError') {
        this.messageService.add(...)
        return
    }
}
```
Los errores no-`NotFoundError` se tragan y caen al popup. Sin logging.

### 5.2 — Sin verificación de popup en cierre de caja (línea 1412)
```typescript
const w = window.open('', '_blank')
if (w) { ... }
```
Falta `else { messageService.add(...) }`.

### 5.3 — WebSerial sin confirmación (línea 619-620)
```typescript
const serial = (navigator as { ... }).serial
if (serial) { ... }
```
Todos los usuarios de Chrome pasan por WebSerial primero. No hay prompt preguntando si quieren usar impresora térmica o impresora normal.

### 5.4 — auto_print_receipt no usado (modelo línea 429)
El backend recolecta la preferencia pero el frontend nunca la consulta.

---

## 6. CÓDIGO MUERTO

### 6.1 — @media print duplicado (SCSS líneas 1211-1215)
```css
@media print {
    .receipt-info-line {
        font-size: 7px;
    }
}
```
Redundante con líneas 1458-1460 dentro del bloque grande.

### 6.2 — Función completa @media print del SCSS (líneas 1293-1489)
Si la impresión se hace exclusivamente vía popup (Implementación A), los `@media print` del SCSS son código muerto. Nunca se ejecutan porque:
1. El popup tiene su propio CSS inline
2. El @media print en el SCSS no se aplica al contenido portado del p-dialog

### 6.3 — auto_print_receipt en backend
Campo en modelo, en serializer, pero sin implementación real.

### 6.4 — botones inline en popup (eliminados en esta sesión)
```html
<button class="btn-print" onclick="window.print()">...</button>
<button class="btn-close" onclick="window.close()">...</button>
```
Reemplazados por auto-print.

---

## 7. MEJOR ARQUITECTURA RECOMENDADA

### Propuesta: PrintService centralizado

**Problema actual:** Cada componente implementa su propia lógica de impresión (reportes, POS, nómina, admin, empleados) con patrones casi idénticos pero con pequeñas diferencias que causan bugs.

**Arquitectura recomendada:**

```
core/services/print/
├── print.service.ts        ← Servicio central
├── print.types.ts          ← Interfaces
├── print-templates/        ← Plantillas HTML
│   ├── pos-ticket.ts       ← Ticket del POS
│   ├── cash-closure.ts     ← Cierre de caja
│   ├── invoice.ts          ← Factura
│   └── receipt.ts          ← Recibo genérico
└── print.utils.ts          ← encodeCP437, escapeHtml
```

**API del servicio:**
```typescript
@Injectable({ providedIn: 'root' })
class PrintService {
    print(html: string, options?: PrintOptions): Promise<boolean>
    // Abre popup, escribe HTML, auto-print, maneja popup blocker
    // Retorna true si se abrió el diálogo de impresión
    
    printThermal(text: string): Promise<boolean>
    // WebSerial ESC/POS con confirmación previa
}

interface PrintOptions {
    width?: number      // default 400
    height?: number     // default 700
    autoPrint?: boolean // default true
    delay?: number      // default 500
    title?: string      // default 'Imprimir'
}
```

**Uso:**
```typescript
// POS
const html = this.generateTicketHtml(ventaActual)
await this.printService.print(html)

// Reportes
const html = this.generarHtmlReporteCajas()
await this.printService.print(html, { width: 800, height: 600 })
```

**Beneficios:**
1. Popup blocker detection centralized — nunca más se olvida
2. CSS variables siempre hardcodeadas
3. WebSerial siempre con confirmación
4. No hay llamadas a `window.open()` ni `window.print()` dispersas
5. Fácil de testear
6. Fácil de extender (ej: agregar QZ Tray, Electron IPC)

---

## 8. PLAN DE CORRECCIÓN (priorizado)

| # | Prioridad | Problema | Acción | Archivo | Líneas |
|---|-----------|----------|--------|---------|--------|
| 1 | 🔴 | Popup blocker sin detectar (cierre de caja) | Agregar `if (!w)` con toast | `pos-system.ts` | 1412-1416 |
| 2 | 🟡 | WebSerial sin confirmación previa | Preguntar antes de activar | `pos-system.ts` | 619-622 |
| 3 | 🟡 | Error silencioso en catch de imprimirTermica | Agregar console.error | `pos-system.ts` | 624-628 |
| 4 | 🟡 | printed_count falso positivo | Mover incremento al frontend post-print | `pos-system.ts` + backend | 995-997 |
| 5 | 🟡 | 80mm size inconsistente en Chrome | Agregar nota en UI o documentación | — | — |
| 6 | 🟡 | CP437 incompleto | Extender mapeo con caracteres comunes | `pos-system.ts` | 808-821 |
| 7 | 🟢 | CSS @media print duplicado | Eliminar bloque redundante | `pos-system.scss` | 1211-1215 |
| 8 | 🟢 | auto_print_receipt sin usar | Implementar en frontend o eliminar | `pos-system.ts` + template | — |
| 9 | 🟢 | printReceipt ignora business_info del backend | Usar datos del backend en mostrarTicket | `pos-system.ts` | 596-614 |
| 10 | 🟢 | Crear PrintService centralizado | Refactor mayor (post-GTM) | `core/services/print/` | Nuevo |

### Estado actual tras esta sesión

| Problema | Estado |
|----------|--------|
| CRÍTICO #1 — Popup blocker sin detectar | ✅ **CORREGIDO** |
| CRÍTICO #2 — @media print en SCSS no aplica al dialog | ❌ Sin corregir (requiere Think — decisión de arquitectura) |
| CRÍTICO #3 — CSS variables en popup | ✅ **CORREGIDO** |
| CRÍTICO #4 — Sin auto-print en popup | ✅ **CORREGIDO** |
| ALTO #1 — Catch parcial | ❌ Sin corregir (bajo impacto) |
| ALTO #2 — WebSerial sin confirmación | ❌ Sin corregir (requiere UX decision) |
| ALTO #3 — Cierre de caja: popup sin detección | ❌ Sin corregir |
| ALTO #4 — printed_count falso positivo | ❌ Sin corregir |
| MEDIO #1 a #2 | ❌ Sin corregir |
| BAJO #1 a #3 | ❌ Sin corregir |

---

## 9. CONCLUSIÓN

La razón por la que "los reportes imprimen y el POS no" tiene 4 causas, todas en la función `imprimirTicketNavegador()`:

1. **Sin popup blocker detection** — el código más crítico. Reportes la tenían, el POS no.
2. **CSS variables indefinidas** — `var(--surface-*)` no existen en el popup. Los botones eran invisibles.
3. **Botón manual en vez de auto-print** — reportes disparan `window.print()` automáticamente; el POS requería clic en botón invisible.
4. **Cascada WebSerial** — Chrome detecta `navigator.serial` y muestra selector de puerto antes de cualquier diálogo de impresión.

Las correcciones 1, 2 y 3 ya están aplicadas en esta sesión. La corrección 4 (WebSerial sin confirmación) queda pendiente.

Para la corrección 4, quieres que la agregue ahora?
