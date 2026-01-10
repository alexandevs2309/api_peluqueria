"""
Validación de calidad para documentación OpenAPI
apps/utils/openapi_validation.py
"""
import requests
from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse


class OpenAPIQualityChecker:
    """Validador de calidad para documentación OpenAPI."""
    
    def __init__(self):
        self.client = Client()
        self.issues = []
    
    def validate_schema(self):
        """Validar que el schema OpenAPI se genera correctamente."""
        try:
            response = self.client.get('/api/schema/')
            if response.status_code != 200:
                self.issues.append(f"Schema endpoint error: {response.status_code}")
                return False
            
            schema = response.json()
            self._validate_schema_structure(schema)
            return len(self.issues) == 0
            
        except Exception as e:
            self.issues.append(f"Schema generation failed: {str(e)}")
            return False
    
    def _validate_schema_structure(self, schema):
        """Validar estructura del schema."""
        required_fields = ['openapi', 'info', 'paths', 'components']
        
        for field in required_fields:
            if field not in schema:
                self.issues.append(f"Missing required field: {field}")
        
        # Validar info
        info = schema.get('info', {})
        if not info.get('title'):
            self.issues.append("Missing API title")
        if not info.get('version'):
            self.issues.append("Missing API version")
    
    def validate_endpoints(self):
        """Validar que endpoints críticos estén documentados."""
        critical_endpoints = [
            '/api/auth/login/',
            '/api/clients/',
            '/api/employees/',
            '/api/payroll/calculations/',
            '/api/pos/sales/',
        ]
        
        schema_response = self.client.get('/api/schema/')
        if schema_response.status_code != 200:
            return False
            
        schema = schema_response.json()
        paths = schema.get('paths', {})
        
        for endpoint in critical_endpoints:
            if endpoint not in paths:
                self.issues.append(f"Critical endpoint not documented: {endpoint}")
    
    def validate_security(self):
        """Validar configuración de seguridad."""
        schema_response = self.client.get('/api/schema/')
        schema = schema_response.json()
        
        # Verificar que JWT esté configurado
        security_schemes = schema.get('components', {}).get('securitySchemes', {})
        if not security_schemes:
            self.issues.append("No security schemes defined")
        
        # Verificar que no haya tokens expuestos en ejemplos
        self._check_for_exposed_secrets(schema)
    
    def _check_for_exposed_secrets(self, schema):
        """Verificar que no haya secretos expuestos."""
        sensitive_patterns = ['sk_', 'pk_', 'token_', 'secret_', 'key_']
        
        def check_dict(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    if isinstance(value, str):
                        for pattern in sensitive_patterns:
                            if pattern in value.lower():
                                self.issues.append(f"Potential secret exposed at {new_path}")
                    else:
                        check_dict(value, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_dict(item, f"{path}[{i}]")
        
        check_dict(schema)
    
    def get_report(self):
        """Generar reporte de validación."""
        return {
            'total_issues': len(self.issues),
            'issues': self.issues,
            'status': 'PASS' if len(self.issues) == 0 else 'FAIL'
        }


# Checklist manual de calidad
QUALITY_CHECKLIST = {
    'ESTRUCTURA': [
        '✓ Título y descripción claros',
        '✓ Versión definida',
        '✓ Tags organizados por dominio',
        '✓ Servidores configurados',
        '✓ Esquemas de seguridad definidos'
    ],
    'ENDPOINTS': [
        '✓ Solo endpoints públicos documentados',
        '✓ Endpoints admin/internos excluidos',
        '✓ Soft delete y restore documentados',
        '✓ Ejemplos realistas sin PII',
        '✓ Respuestas de error documentadas'
    ],
    'SEGURIDAD': [
        '✓ No hay tokens/secretos expuestos',
        '✓ Ejemplos sanitizados',
        '✓ Permisos documentados conceptualmente',
        '✓ Errores 401/403 explicados'
    ],
    'MANTENIBILIDAD': [
        '✓ Serializers reutilizables',
        '✓ Decoradores consistentes',
        '✓ Versionado claro',
        '✓ No sobre-documentación'
    ]
}


def run_quality_check():
    """Ejecutar validación completa."""
    checker = OpenAPIQualityChecker()
    
    print("🔍 Validando schema OpenAPI...")
    checker.validate_schema()
    
    print("🔍 Validando endpoints críticos...")
    checker.validate_endpoints()
    
    print("🔍 Validando seguridad...")
    checker.validate_security()
    
    report = checker.get_report()
    
    if report['status'] == 'PASS':
        print("✅ Documentación OpenAPI: APROBADA")
    else:
        print(f"❌ Documentación OpenAPI: {report['total_issues']} problemas encontrados")
        for issue in report['issues']:
            print(f"  - {issue}")
    
    return report