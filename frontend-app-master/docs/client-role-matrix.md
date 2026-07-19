# Matriz de Roles Cliente

Fecha de referencia: 2026-04-18

Este documento describe el alcance operativo real esperado para los roles del panel cliente.

## Roles

### CLIENT_ADMIN

Acceso total al tenant.

Puede usar:
- Dashboard completo
- Citas
- POS / caja
- Clientes
- Servicios
- Productos
- Empleados
- Turnos
- Nómina
- Reportes
- Configuración
- Perfil / cambio de clave / ayuda

### Manager

Rol operativo amplio sin configuración del negocio.

Puede usar:
- Dashboard de negocio
- Citas
- POS / caja
- Clientes
- Servicios
- Productos
- Empleados
- Turnos
- Nómina
- Reportes
- Perfil / cambio de clave / ayuda

No debe usar:
- Configuración del negocio

### Cajera

Rol de operación comercial y atención.

Puede usar:
- Dashboard operativo
- Citas
- POS / caja
- Clientes
- Servicios
- Productos
- Perfil / cambio de clave / ayuda

No debe usar:
- Empleados
- Turnos
- Nómina
- Reportes
- Configuración

Notas:
- POS depende del feature `cash_register`
- Productos depende del feature `inventory`

### Estilista

Rol de atención individual.

Puede usar:
- Dashboard restringido
- Citas
- Clientes
- Perfil / cambio de clave / ayuda

No debe usar:
- POS / caja
- Servicios como gestión
- Productos
- Empleados
- Turnos
- Nómina
- Reportes
- Configuración

Notas:
- El dashboard restringido no debe mostrar ventas, métricas globales ni datos privados del negocio.

### CLIENT_STAFF

Rol base de apoyo operativo.

Puede usar:
- Dashboard restringido
- Citas
- Clientes
- Perfil / cambio de clave / ayuda

No debe usar:
- POS / caja
- Productos
- Servicios como gestión
- Empleados
- Turnos
- Nómina
- Reportes
- Configuración

### Utility

Rol interno no operativo del negocio.

Puede usar:
- Perfil
- Cambio de clave
- Ayuda

No debe usar:
- Dashboard
- Citas
- POS / caja
- Clientes
- Servicios
- Productos
- Empleados
- Turnos
- Nómina
- Reportes
- Configuración

Notas:
- `Utility` existe para acceso mínimo de cuenta, no para operación del negocio.
- Si en el futuro se crea un módulo de tareas internas, este rol puede ampliarse allí.

## Criterios

- Los roles no administrativos no deben ver métricas financieras o de negocio salvo necesidad directa.
- El menú visible, las rutas y el comportamiento del dashboard deben coincidir con esta matriz.
- Los permisos de frontend no sustituyen permisos de backend. Los endpoints sensibles deben seguir protegidos del lado servidor.
