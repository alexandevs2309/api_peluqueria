Haz esta QA de `/admin/` en este orden.

**1. Dashboard**
- entra a `/admin/dashboard`
- confirma que carguen métricas
- abre el centro de actividad
- verifica que no aparezcan citas/ventas de tenant
- revisa consola y `network`

**2. Tenants**
- entra a `/admin/tenants`
- busca tenants
- abre uno
- prueba activar/desactivar
- prueba suspender/reactivar si existe esa acción
- confirma que los cambios se reflejen al volver al listado

**3. Tenant Detail**
- entra a `/admin/tenants/:id`
- revisa:
  - datos del tenant
  - plan
  - usuarios
  - facturas
  - logs
  - empleados actuales
- cambia plan si aplica
- confirma que no haya errores de permisos ni datos vacíos raros

**4. Users**
- entra a `/admin/users`
- prueba estos scopes:
  - `Usuarios de plataforma`
  - `Todos los usuarios`
  - tenant específico
- crea un usuario de plataforma
- crea un usuario de tenant
- edita ambos
- verifica que el formulario exija tenant solo cuando corresponde
- elimina uno si quieres probar completo

**5. Billing**
- entra a `/admin/billing`
- carga facturas
- filtra
- abre detalle si existe
- marca una factura como pagada si el flujo lo permite
- genera una nueva si el flujo existe
- revisa si el cambio se refleja

**6. Reports**
- entra a `/admin/reports`
- cambia período/filtros
- valida que carguen métricas
- prueba exporte o impresión
- revisa si hay popup bloqueado o salida vacía

**7. Audit Logs**
- entra a `/admin/audit-logs`
- revisa que cargue el resumen
- prueba filtros
- confirma que el breakdown ya no salga vacío
- valida que el contenido tenga sentido real

**8. System Settings**
- entra a `/admin/settings`
- cambia un valor no sensible
- guarda
- recarga
- confirma persistencia
- prueba tocar una integración sin romperla
- verifica que secretos enmascarados no se sobrescriban mal

**9. System Monitor**
- entra a `/admin/monitor`
- revisa qué servicios salen arriba/abajo
- corre pruebas manuales de integraciones si hay botones
- confirma que `synthetic` esté claro y no se vea como chequeo real
- revisa si alertas cambian con datos reales

**Qué debes vigilar**
- `403`, `401`, `500`
- datos mezclados de tenant
- acciones que aparentan guardar pero no persisten
- botones visibles con permiso roto
- exports vacíos
- settings que se guardan mal
- notificaciones incorrectas para superadmin

**Mi recomendación**
Empieza por este recorrido corto:
1. `dashboard`
2. `tenants`
3. `tenant detail`
4. `users`

Ese camino ya te va a decir rápido si la consola admin está realmente lista.

Si sale cualquier error, me lo mandas igual que hicimos en `/client/` y lo cerramos uno por uno.

---

# Resultado de QA Admin

Fecha de cierre: 03/04/2026

Estado general: Aprobado con correcciones aplicadas

Esta ronda de QA se ejecutó sobre los módulos principales de `/admin/` y se fueron corrigiendo los hallazgos conforme aparecieron. El resultado final es positivo: el panel admin quedó funcionalmente mucho más consistente y sin los errores críticos detectados al inicio.

## Módulos validados

- Dashboard
- Tenants
- Tenant Detail
- Users
- Billing
- System Monitor
- Nombres comerciales de planes en vistas admin

## Incidencias detectadas y corregidas

- `Tenant Detail` intentaba consultar endpoints inexistentes para usuarios y suscripción, generando `404`.
- `Users` fallaba al crear `SuperAdmin` con `400 Bad Request` por validación incorrecta de `tenant`.
- `Users` en scope `Todos los usuarios` intentaba usar `__all__` como tenant real, generando `404`.
- `Billing` tenía acciones incompletas en la tabla de cobranza.
- Varias vistas admin mostraban nombres técnicos de plan como `basic` y `standard` en vez de nombres comerciales.
- `System Monitor` trataba servicios `no configurados` como caídas críticas y marcaba chequeos sintéticos como si fueran verificaciones reales completas.

## Correcciones aplicadas

- Se reemplazaron llamadas inválidas en `tenant-detail` por fuentes reales de datos.
- Se corrigió la creación de `SuperAdmin` para que nazca con flags y validaciones correctas desde el primer guardado.
- Se separó el selector de scope del selector de tenant en `users-management`.
- Se ampliaron las acciones de `billing` con detalle y flujo de cobro más completo.
- Se normalizó la visualización de planes a:
  - `Professional`
  - `Business`
  - `Premium`
  - `Enterprise`
- Se ajustó `System Monitor` para distinguir:
  - caída real
  - no configurado
  - chequeo sintético
  - advertencia operativa

## Estado final recomendado

- Apto para seguir con validación final de negocio
- Sin bloqueos críticos conocidos en los flujos revisados
- Quedan recomendables una pasada corta de regresión y una revisión manual final de:
  - `Reports`
  - `Audit Logs`
  - `System Settings`

## Conclusión

La QA de `/admin/` puede considerarse superada en esta ronda, con correcciones importantes ya integradas. No se cerró solo con observación: se validó, se detectaron fallos reales y se corrigieron en el mismo ciclo, lo cual deja una base bastante más estable para salida interna o siguiente etapa de pruebas.

---

# Go / No-Go

Decisión recomendada: Go condicionado

## Motivo

Los flujos administrativos más sensibles revisados en esta ronda quedaron operativos después de las correcciones:

- navegación y consistencia general de `/admin/`
- gestión de tenants
- detalle de tenant
- creación y edición de usuarios
- cobranza y acciones principales de facturación
- monitor del sistema
- normalización de nombres comerciales de planes

No quedan bloqueos críticos conocidos dentro del alcance validado.

## Condiciones para avanzar con tranquilidad

- ejecutar una regresión corta sobre `Reports`, `Audit Logs` y `System Settings`
- hacer una validación funcional final con datos de negocio reales
- confirmar que no aparezcan nuevos errores `401`, `403`, `404` o `500` en consola durante esa pasada final

## Riesgo residual

Riesgo actual: Bajo a moderado

La base quedó estable en los módulos revisados, pero todavía conviene una última pasada manual en los módulos no profundizados en esta ronda antes de considerar cierre total de QA admin.
