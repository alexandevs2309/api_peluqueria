# 📜 Cumplimiento Legal y Fiscal - República Dominicana

## ⚖️ Marco Legal Dominicano Aplicado

### 1. **Ley 30-26 sobre Renta (ISR)**
**Aplicación:** Cálculo automático de impuesto sobre la renta para empleados.

- **Exención mensual:** RD$40,000 (RD$480,000 anuales) - Art. 222
- **Escalas progresivas 2026-2027:**
  - 0 - RD$480,000: 0% (exento)
  - RD$480,001 - RD$797,760: 15%
  - RD$797,761 - RD$1,595,520: 20%
  - RD$1,595,521 - RD$2,659,200: 25%
  - +RD$2,659,200: 30%

- **Regalía Pascual (Art. 222):**
  - 1/12 del salario ordinario anual
  - **Exenta de ISR** (artículo 222 de la Ley 30-26)
  - Tope máximo configurado en el sistema

### 2. **Ley 87-01 de Seguridad Social (TSS)**
**Aplicación:** Aportaciones mensuales a TSS para empleados.

- **AFP (1.5%):** Aportación individual al fondo de pensiones
- **SFS (2.0%):** Aportación al Sistema de Salud
- **TSS (2.0%):** Aportación al seguro de trabajo riesgos

### 3. **Ley 253-12 sobre Facturación Fiscal (DGII)**
**Aplicación:** Sistema de Comprobantes Fiscales Electrónicos (NCF).

- **Tipos de NCF soportados:**
  | Código | Tipo | Uso | Requiere RNC |
  |--------|------|-----|--------------|
  | B01 | Crédito Fiscal | Clientes con RNC (empresas) | ✅ Obligatorio |
  | B02 | Consumidor Final | Clientes sin RNC (particulares) | ❌ No |
  | B14 | Regímenes Especiales | Entidades con régimen especial | ✅ Obligatorio |
  | B15 | Gubernamentales | Instituciones gubernamentales | ✅ Obligatorio |

- **Validaciones implementadas:**
  - Secuenciación automática y exclusiva por tenant
  - Prevención de duplicados y saltos de secuencia
  - Control de fechas de expiración
  - Validación de RNC antes de emitir NCF

- **NCF Structure:** `B0200000001` (11 caracteres: prefijo + tipo + secuencia)

### 4. **Ley 103-01 sobre Impuesto al Valor Agregado (ITBIS)**
**Aplicación:** Cálculo y recaudo del ITBIS en ventas.

- **Tasa general:** 18%
- **Base gravable:** Precio de venta menos descuentos
- **Devolución:** Sistema de reembolsos con auditoría completa

### 5. **Ley 172-13 de Protección de Datos Personales**
**Aplicación:** Manejo de datos de clientes y empleados.

- **Principios aplicados:**
  - Consentimiento informado para recolección de datos
  - Derechos ARCO (Acceso, Rectificación, Cancelación, Oposición)
  - Aislamiento estricto por tenant (multi-tenancy)
  - Encriptación de datos sensibles en base de datos
  - Registro de auditoría de accesos a datos personales

- **Datos protegidos:**
  - Datos personales: nombre, email, teléfono, dirección
  - Datos biométricos: huellas dactilares (si se usan)
  - Datos financieros: cuentas bancarias, tarjetas
  - Datos sensibles: salud, origen étnico, opiniones políticas

### 6. **Ley 248-05 sobre Trabajo (Código de Trabajo)**
**Aplicación:** Derechos laborales y obligaciones patronales.

- **Horas extras:** 1.5x la hora normal
- **Descanso semanal:** 36 horas continuas (domingo)
- **Bono 14:**
  - 1/12 del salario ordinario anual
  - Pagadero antes del 20 de diciembre
  - **No constituye salario** para efectos de cálculo de prestaciones (Sentencia C-323-17)

- **Aguinaldo (Ley 11-92):**
  - 1/12 del salario ordinario anual
  - Pagadero antes del 20 de diciembre
  - Base: salario ordinario (sin comisiones variables)

- **Indemnizaciones:**
  - Despido injustificado: 3 días por año trabajado
  - Despido justificado: Sin indemnización
  - Renuncia voluntaria: Sin indemnización

### 7. **Resolución 31-20 del DGII**
**Aplicación:** Requisitos fiscales para emisión de comprobantes.

- **Información obligatoria en tickets:**
  - Nombre y RNC del contribuyente emisor
  - Tipo y número de NCF
  - Fecha y hora de emisión
  - Datos del cliente (si aplica)
  - Desglose de impuestos (ITBIS)
  - Monto total

- **Conservación de comprobantes:**
  - Minimo 5 años desde la fecha de emisión
  - Formato digital con firma electrónica
  - Disponibilidad para auditorías de la DGII

---

## 🔐 Medidas de Seguridad y Privacidad

### 1. **Aislamiento Multi-Tenant**
- Cada salón (tenant) opera en un scope de datos completamente aislado
- Filtros automáticos por `tenant_id` en todas las queries
- Prevención de fugas cruzadas de datos

### 2. **Autenticación y Autorización**
- Tokens JWT de doble canal:
  - `httpOnly` cookies (access token)
  - `localStorage` (refresh token)
  - Encriptación de datos sensibles en base de datos (AES-256)
- RBAC (Role-Based Access Control) granular

### 3. **Auditoría y Logs**
- Registro de:
  - Accesos a datos personales
  - Modificaciones a ventas y facturas
  - Cambios en configuración fiscal
  - Operaciones de caja

### 4. **Backups y Recuperación**
- Backups diarios automatizados
- almacenamiento en múltiples regiones
- Recuperación ante desastres (RTO < 4h, RPO < 1h)

---

## 📊 Funcionalidades de Cumplimiento Implementadas

### 1. **POS Fiscal DGII**
- ✅ Secuenciación automática de NCF
- ✅ Emisión de tickets fiscales con estructura oficial
- ✅ Control de caja y arqueo diario
- ✅ Historial de ventas con NCF
- ✅ Reportes fiscales para declaración

### 2. **Nómina y Salarios**
- ✅ Cálculo automático de ISR según tabla vigente
- ✅ Aportaciones a TSS (AFP, SFS, TSS)
- ✅ Generación de boletas de pago
- ✅ Registro de regalías y bonos exentos
- ✅ Reportes fiscales para declaración

### 3. **Protección de Datos**
- ✅ Consentimiento para tratamiento de datos
- ✅ Derechos ARCO implementados
- ✅ Auditoría de accesos a datos personales
- ✅ Exportación de datos personales (GDPR/DR)

---

## 🚨 Notas Legales Importantes

1. **Actualización automática de tablas fiscales:**
   - El sistema recibe actualizaciones de la DGII
   - Tablas ISR actualizadas anualmente (Ley 30-26)
   - Tasa ITBIS ajustada porDecreto (actual: 18%)

2. **Responsabilidad del empleador:**
   - Declarar y pagar impuestos en tiempo y forma
   - Emitir comprobantes fiscales válidos
   - Mantener registros por 5 años
   - Respetar derechos laborales de empleados

3. **Sanciones por incumplimiento:**
   - Multas de la DGII por no emitir NCF
   - Multas de TSS por no aportar
   - Multas de Trabajo por no pagar prestaciones
   - Responsabilidad civil por daños a datos personales

---

## 📝 Documentación Obligatoria Requerida por Ley

### Para cada empleado:
1. ✅ Contrato de trabajo escrito
2. ✅ Boleta de pago mensual
3. ✅ Registro de horas extras
4. ✅ Licencias y permisos registrados
5. ✅ Historial de ajustes salariales

### Para cada cliente:
1. ✅ Consentimiento para tratamiento de datos
2. ✅ Registro de preferencias
3. ✅ Historial de compras
4. ✅ Derechos de acceso y cancelación

### Para la empresa:
1. ✅ Libro de inventarios y balances
2. ✅ Libro de ventas y compras
3. ✅ Registros fiscales (NCF)
4. ✅ Certificados de retenciones
5. ✅ Declaraciones fiscales (mensuales/anuales)

---

## 📞 Contacto y Soporte Legal

Para asesoría legal específica sobre:
- 📄 **Facturación fiscal:** Consultar con contador certificado
- 👥 **Nómina y laboral:** Consultar con abogado laboral
- 🔐 **Privacidad de datos:** Consultar con DPI (Data Protection Officer)
- 🏛️ **Cumplimiento DGII:** Verificar con consultor fiscal

---

## 📅 Actualizaciones Pendientes

- [ ] Integración con API de la DGII para validación de NCF en tiempo real
- [ ] Exportación automática de reportes fiscales para contadores
- [ ] Alertas de vencimiento de NCF
- [ ] Notificaciones de fechas importantes (declaraciones, pagos)

---

**Última actualización:** Noviembre 2026  
**Versión del sistema:** Auron Suite v2.0  
**Aplica a:** República Dominicana
