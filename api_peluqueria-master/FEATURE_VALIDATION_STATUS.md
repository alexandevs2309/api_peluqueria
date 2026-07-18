# Estado de Validacion de Features por Plan

## Implementado

### 1. basic_reports
- Estado: enforced
- Planes: `basic`, `standard`, `premium`
- Backend:
  - `apps/reports_api/views.py`
  - Se protege el acceso a reportes basicos con `@requires_feature('basic_reports')`

### 2. advanced_reports
- Estado: enforced
- Planes: `standard`, `premium`
- Backend:
  - `apps/reports_api/analytics_views.py`
  - Se protege el acceso a reportes avanzados con `@requires_feature('advanced_reports')`

### 3. inventory
- Estado: enforced
- Planes: `standard`, `premium`
- Backend:
  - `apps/inventory_api/views.py`
  - `ProductViewSet`, `SupplierViewSet` y `StockMovementViewSet` usan `HasFeaturePermission`

### 4. cash_register
- Estado: enforced
- Planes: `basic`, `standard`, `premium`
- Backend:
  - `apps/pos_api/views.py`
  - `SaleViewSet`, `CashRegisterViewSet`, `PromotionViewSet` y `PosConfigurationViewSet`

### 5. client_history
- Estado: enforced
- Planes: `basic`, `standard`, `premium`
- Backend:
  - `apps/clients_api/views.py`
  - La accion `history` usa `@requires_feature('client_history')`

### 6. multi_location
- Estado: enforced
- Planes: `standard`, `premium`
- Backend:
  - `apps/settings_api/models.py`
  - La logica de sucursales valida `allows_multiple_branches`

### 7. custom_branding
- Estado: parcialmente enforced
- Planes: `premium`
- Backend:
  - `apps/settings_api/barbershop_views.py`
  - `upload_logo` usa `@requires_feature('custom_branding')`
- Alcance actual:
  - El branding premium cubre logo personalizado
  - No representa branding completo de toda la aplicacion

### 8. max_users
- Estado: enforced
- Planes:
  - `basic`: 16
  - `standard`: 50
  - `premium`: ilimitado

### 9. max_employees
- Estado: enforced
- Planes:
  - `basic`: 8
  - `standard`: 25
  - `premium`: ilimitado
- Nota:
  - La validacion ya toma el plan real como fuente principal

## No Vendido Como Feature Tecnica

### api_access
- Estado: no enforced
- Decision actual:
  - No se vende como parte activa de la oferta comercial
  - No debe aparecer como feature destacada hasta que exista enforcement real

### role_permissions
- Estado: no enforced por plan
- Decision actual:
  - No se vende como feature del plan
  - Requiere una definicion funcional mas precisa antes de monetizarse

### priority_support
- Estado: no tecnico
- Decision actual:
  - No se trata como feature de producto en la oferta principal

### sla_guaranteed
- Estado: no tecnico
- Decision actual:
  - No se trata como feature de producto en la oferta principal

## Resumen Comercial Actual

La oferta comercial debe apoyarse en estas capacidades:
- `basic`: agenda, caja, historial de clientes, reportes basicos, 1 sucursal
- `standard`: todo lo anterior mas inventario, reportes avanzados y multiples sucursales
- `premium`: todo lo anterior con empleados/usuarios ilimitados y logo personalizado

No se debe vender como feature activa del plan:
- `api_access`
- `role_permissions`
- `priority_support`
- `sla_guaranteed`

## Notas

- La oferta publica y los comandos ejecutables de planes ya fueron alineados
- Si se implementan nuevas features monetizables, este documento debe actualizarse junto con el enforcement backend
