# API Versioning Strategy - SaaS Peluquerías

## Principios de Versionado

### 1. CUÁNDO VERSIONAR
**SÍ versionar cuando:**
- Cambios que rompen compatibilidad hacia atrás (breaking changes)
- Cambios en estructura de respuesta que afecten clientes existentes
- Eliminación de campos o endpoints
- Cambios en validaciones que rechacen datos previamente válidos

**NO versionar cuando:**
- Agregar nuevos campos opcionales a respuestas
- Agregar nuevos endpoints
- Mejoras internas sin cambio de contrato
- Corrección de bugs que no afecten el contrato
- Cambios en documentación

### 2. ESTRATEGIA ACTUAL

#### Endpoints Estables (v1 implícito)
```
/api/auth/login/          ✅ Estable
/api/clients/             ✅ Estable  
/api/appointments/        ✅ Estable
/api/pos/sales/           ✅ Estable
/api/payroll/settlements/ ✅ Estable (adaptado internamente)
```

#### Endpoints Versionados Explícitos
```
/api/payroll/v2/settlements/  ✅ Nueva arquitectura interna
/api/reports/v2/analytics/    🔄 Cuando sea necesario
```

### 3. IMPLEMENTACIÓN

#### Estructura de URLs
```python
# backend/urls.py
urlpatterns = [
    path('api/', include([
        # v1 implícito (estable)
        path('auth/', include('apps.auth_api.urls')),
        path('clients/', include('apps.clients_api.urls')),
        
        # v2 explícito (cuando necesario)
        path('payroll/v2/', include('apps.payroll_api.urls_v2')),
    ])),
]
```

#### ViewSets Versionados
```python
# apps/payroll_api/urls_v2.py
from .views_v2 import PayrollSettlementViewSetV2

router = DefaultRouter()
router.register(r'settlements', PayrollSettlementViewSetV2, basename='payroll-settlement-v2')
```

### 4. DEPRECACIÓN GRADUAL

#### Proceso de Deprecación
1. **Anuncio**: Documentar deprecación en OpenAPI
2. **Headers**: Agregar `Deprecation` header
3. **Período**: Mantener 6 meses mínimo
4. **Eliminación**: Solo después de confirmación de migración

#### Ejemplo de Implementación
```python
class DeprecatedViewMixin:
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response['Deprecation'] = 'true'
        response['Sunset'] = '2024-12-31'
        response['Link'] = '</api/v2/endpoint>; rel="successor-version"'
        return response
```

### 5. DOCUMENTACIÓN DE VERSIONES

#### OpenAPI Tags por Versión
```python
SPECTACULAR_SETTINGS = {
    'TAGS': [
        {'name': 'payroll', 'description': '💰 Nómina v1 (estable)'},
        {'name': 'payroll-v2', 'description': '💰 Nómina v2 (nueva arquitectura)'},
    ],
}
```

#### Ejemplos en Documentación
```python
@extend_schema(
    tags=['payroll-v2'],
    summary='Cálculo de nómina v2',
    description='''
    **Nueva arquitectura de nómina con:**
    - Cálculos más precisos
    - Audit trail completo
    - Versionado de cálculos
    
    **Migración desde v1:**
    - `settlement_id` → `calculation_id`
    - Nuevos campos: `version`, `breakdown_available`
    '''
)
```

### 6. CRITERIOS DE DECISIÓN

#### Matriz de Decisión
| Cambio | Impacto | Acción |
|--------|---------|--------|
| Nuevo campo opcional | Bajo | ✅ Sin versionar |
| Campo requerido nuevo | Alto | ❌ Versionar |
| Cambio tipo de dato | Alto | ❌ Versionar |
| Nuevo endpoint | Ninguno | ✅ Sin versionar |
| Eliminar campo | Alto | ❌ Versionar |
| Cambio validación | Medio | 🤔 Evaluar caso |

### 7. HERRAMIENTAS DE MONITOREO

#### Métricas de Uso por Versión
```python
# middleware para tracking
class APIVersionTrackingMiddleware:
    def __call__(self, request):
        version = self.extract_version(request.path)
        # Log usage metrics
        logger.info("api_version_usage", 
                   version=version, 
                   endpoint=request.path)
```

### 8. COMUNICACIÓN CON FRONTEND

#### Headers de Versión
```http
# Request
GET /api/payroll/settlements/
API-Version: 1.0

# Response  
HTTP/1.1 200 OK
API-Version: 1.0
Supported-Versions: 1.0, 2.0
```

#### Documentación para Desarrolladores
- Changelog detallado por versión
- Guías de migración específicas
- Ejemplos de código antes/después
- Fechas de deprecación claras

### 9. TESTING DE COMPATIBILIDAD

#### Tests de Regresión
```python
class APICompatibilityTests(TestCase):
    def test_v1_response_structure_unchanged(self):
        # Verificar que v1 mantiene estructura
        pass
        
    def test_v2_new_features_available(self):
        # Verificar nuevas funcionalidades v2
        pass
```

### 10. ROADMAP DE VERSIONES

#### Planificación
- **v1.0**: Actual (estable hasta 2025-06)
- **v1.1**: Mejoras menores (compatible)
- **v2.0**: Nueva arquitectura payroll (2024-Q2)
- **v2.1**: Reportes avanzados (2024-Q3)

**Regla de oro**: Nunca romper v1 sin migración clara a v2.