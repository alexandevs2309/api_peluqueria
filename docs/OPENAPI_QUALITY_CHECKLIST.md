# OpenAPI Quality Validation Checklist

## 1. CHECKLIST DE CALIDAD PROFESIONAL

### ✅ Configuración Base
- [ ] Título, descripción y versión claros
- [ ] Tags organizados por módulo de negocio
- [ ] Servidores de desarrollo y producción configurados
- [ ] Esquemas de autenticación documentados
- [ ] Contacto y licencia especificados

### ✅ Documentación de Endpoints
- [ ] Solo endpoints públicos documentados
- [ ] Endpoints internos/admin excluidos
- [ ] Descripciones claras y concisas
- [ ] Ejemplos realistas (sin datos sensibles)
- [ ] Parámetros requeridos vs opcionales claros

### ✅ Serializers y Esquemas
- [ ] help_text en todos los campos importantes
- [ ] Ejemplos en serializers complejos
- [ ] Validaciones documentadas
- [ ] Campos de solo lectura marcados
- [ ] Tipos de datos correctos

### ✅ Respuestas y Errores
- [ ] Códigos de estado HTTP apropiados
- [ ] Respuestas de error estándar (400, 401, 403, 404, 429)
- [ ] Estructura de paginación documentada
- [ ] Respuestas de éxito con ejemplos

### ✅ Seguridad
- [ ] Sin tokens reales en ejemplos
- [ ] Sin PII en documentación
- [ ] Campos sensibles marcados como write_only
- [ ] Permisos y roles explicados conceptualmente

### ✅ Versionado
- [ ] Estrategia de versionado clara
- [ ] Endpoints deprecados marcados
- [ ] Migración entre versiones documentada
- [ ] Compatibilidad hacia atrás mantenida

## 2. HERRAMIENTAS DE VALIDACIÓN

### Script de Validación Automática

```python
#!/usr/bin/env python
"""
Validador automático de calidad OpenAPI
"""
import json
import requests
from typing import Dict, List, Any

class OpenAPIValidator:
    def __init__(self, schema_url: str):
        self.schema_url = schema_url
        self.schema = self._load_schema()
        self.issues = []
    
    def _load_schema(self) -> Dict[str, Any]:
        """Cargar esquema OpenAPI"""
        response = requests.get(self.schema_url)
        return response.json()
    
    def validate_all(self) -> List[str]:
        """Ejecutar todas las validaciones"""
        self.validate_basic_info()
        self.validate_security()
        self.validate_examples()
        self.validate_responses()
        return self.issues
    
    def validate_basic_info(self):
        """Validar información básica"""
        info = self.schema.get('info', {})
        
        if not info.get('title'):
            self.issues.append("❌ Título faltante")
        
        if not info.get('description'):
            self.issues.append("❌ Descripción faltante")
        
        if not info.get('version'):
            self.issues.append("❌ Versión faltante")
        
        if not info.get('contact'):
            self.issues.append("⚠️ Información de contacto faltante")
    
    def validate_security(self):
        """Validar configuración de seguridad"""
        if 'security' not in self.schema:
            self.issues.append("❌ Esquemas de seguridad no definidos")
        
        # Verificar que no hay tokens reales en ejemplos
        self._check_sensitive_data_in_examples()
    
    def validate_examples(self):
        """Validar calidad de ejemplos"""
        paths = self.schema.get('paths', {})
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                if not isinstance(operation, dict):
                    continue
                
                # Verificar que operaciones importantes tienen ejemplos
                if method.lower() in ['post', 'put', 'patch']:
                    if not self._has_request_example(operation):
                        self.issues.append(f"⚠️ {method.upper()} {path} sin ejemplo de request")
    
    def validate_responses(self):
        """Validar respuestas estándar"""
        paths = self.schema.get('paths', {})
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                if not isinstance(operation, dict):
                    continue
                
                responses = operation.get('responses', {})
                
                # Verificar respuestas de error comunes
                if 'security' in operation or 'security' in self.schema:
                    if '401' not in responses:
                        self.issues.append(f"⚠️ {method.upper()} {path} sin respuesta 401")
                    if '403' not in responses:
                        self.issues.append(f"⚠️ {method.upper()} {path} sin respuesta 403")
    
    def _check_sensitive_data_in_examples(self):
        """Verificar datos sensibles en ejemplos"""
        sensitive_patterns = [
            r'sk_test_[a-zA-Z0-9]+',
            r'sk_live_[a-zA-Z0-9]+',
            r'eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+',
        ]
        
        schema_str = json.dumps(self.schema)
        
        for pattern in sensitive_patterns:
            import re
            if re.search(pattern, schema_str):
                self.issues.append("🚨 CRÍTICO: Datos sensibles encontrados en ejemplos")
                break
    
    def _has_request_example(self, operation: Dict[str, Any]) -> bool:
        """Verificar si operación tiene ejemplo de request"""
        request_body = operation.get('requestBody', {})
        content = request_body.get('content', {})
        
        for media_type, media_def in content.items():
            if 'example' in media_def or 'examples' in media_def:
                return True
        
        return False

# Uso del validador
if __name__ == "__main__":
    validator = OpenAPIValidator("http://localhost:8000/api/schema/")
    issues = validator.validate_all()
    
    if not issues:
        print("✅ Documentación OpenAPI válida")
    else:
        print("❌ Issues encontrados:")
        for issue in issues:
            print(f"  {issue}")
```

### Comando de Validación Django

```python
# management/commands/validate_openapi.py
from django.core.management.base import BaseCommand
from django.test import RequestFactory
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.views import SpectacularAPIView

class Command(BaseCommand):
    help = 'Validar calidad de documentación OpenAPI'
    
    def handle(self, *args, **options):
        # Generar esquema
        factory = RequestFactory()
        request = factory.get('/api/schema/')
        
        view = SpectacularAPIView()
        view.request = request
        
        schema = view.get(request).data
        
        # Ejecutar validaciones
        issues = self.validate_schema(schema)
        
        if not issues:
            self.stdout.write(
                self.style.SUCCESS('✅ Documentación OpenAPI válida')
            )
        else:
            self.stdout.write(
                self.style.ERROR('❌ Issues encontrados:')
            )
            for issue in issues:
                self.stdout.write(f"  {issue}")
    
    def validate_schema(self, schema):
        # Implementar validaciones específicas
        issues = []
        
        # Validar tags
        tags = schema.get('tags', [])
        if len(tags) < 5:
            issues.append("⚠️ Pocos tags definidos")
        
        # Validar paths
        paths = schema.get('paths', {})
        if len(paths) < 10:
            issues.append("⚠️ Pocos endpoints documentados")
        
        return issues
```

## 3. TESTS DE DOCUMENTACIÓN

### Tests Automatizados

```python
# tests/test_openapi_quality.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
import json

class OpenAPIQualityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
    
    def test_schema_generation(self):
        """Verificar que el esquema se genera sin errores"""
        response = self.client.get('/api/schema/')
        self.assertEqual(response.status_code, 200)
        
        schema = response.json()
        self.assertIn('openapi', schema)
        self.assertIn('info', schema)
        self.assertIn('paths', schema)
    
    def test_no_sensitive_data_in_schema(self):
        """Verificar que no hay datos sensibles en el esquema"""
        response = self.client.get('/api/schema/')
        schema_str = json.dumps(response.json())
        
        # Patrones sensibles
        sensitive_patterns = [
            'sk_test_', 'sk_live_', 'password123', 
            'secret_key', 'jwt_token'
        ]
        
        for pattern in sensitive_patterns:
            self.assertNotIn(pattern, schema_str.lower())
    
    def test_required_endpoints_documented(self):
        """Verificar que endpoints críticos están documentados"""
        response = self.client.get('/api/schema/')
        schema = response.json()
        paths = schema.get('paths', {})
        
        required_endpoints = [
            '/api/auth/login/',
            '/api/clients/',
            '/api/pos/sales/',
            '/api/payroll/settlements/',
        ]
        
        for endpoint in required_endpoints:
            self.assertIn(endpoint, paths)
    
    def test_common_responses_present(self):
        """Verificar que respuestas comunes están presentes"""
        response = self.client.get('/api/schema/')
        schema = response.json()
        
        # Verificar al menos un endpoint autenticado
        auth_endpoint = schema['paths']['/api/clients/']['get']
        responses = auth_endpoint.get('responses', {})
        
        self.assertIn('401', responses)
        self.assertIn('403', responses)
```

## 4. REVISIONES MANUALES

### Checklist de Revisión Manual

#### 📋 Revisión de Contenido
- [ ] Descripciones en español claro y profesional
- [ ] Ejemplos realistas y útiles
- [ ] Sin jerga técnica innecesaria
- [ ] Consistencia en terminología

#### 📋 Revisión de UX
- [ ] Navegación intuitiva en Swagger UI
- [ ] Agrupación lógica por tags
- [ ] Orden de endpoints sensato
- [ ] Búsqueda funciona correctamente

#### 📋 Revisión de Seguridad
- [ ] Sin credenciales reales
- [ ] Sin información de infraestructura
- [ ] Ejemplos con datos ficticios
- [ ] Campos sensibles ocultos

#### 📋 Revisión de Completitud
- [ ] Todos los endpoints públicos documentados
- [ ] Parámetros de query documentados
- [ ] Headers requeridos especificados
- [ ] Formatos de fecha/hora claros

## 5. MÉTRICAS DE CALIDAD

### KPIs de Documentación
- **Cobertura**: % de endpoints documentados
- **Completitud**: % de endpoints con ejemplos
- **Seguridad**: 0 datos sensibles expuestos
- **Usabilidad**: Tiempo para encontrar endpoint específico
- **Actualización**: Días desde última actualización

### Dashboard de Métricas
```python
def get_documentation_metrics():
    return {
        'total_endpoints': count_total_endpoints(),
        'documented_endpoints': count_documented_endpoints(),
        'endpoints_with_examples': count_endpoints_with_examples(),
        'security_issues': count_security_issues(),
        'last_updated': get_last_update_date(),
    }
```

## 6. PROCESO DE REVISIÓN

### Workflow de Revisión
1. **Desarrollo**: Crear/modificar endpoint
2. **Documentación**: Actualizar serializers y ejemplos
3. **Validación**: Ejecutar tests automáticos
4. **Revisión**: Checklist manual
5. **Aprobación**: Review por senior
6. **Deploy**: Actualizar documentación pública

### Criterios de Aprobación
- ✅ Todos los tests automáticos pasan
- ✅ Checklist manual completado
- ✅ Sin datos sensibles expuestos
- ✅ Ejemplos realistas y útiles
- ✅ Consistencia con estándares existentes