#!/usr/bin/env python3
"""
Test de Integración Frontend ↔ Backend
Verificar funcionalidades que ya funcionan
"""
import os
import sys
import django
import requests
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.roles_api.models import Role, UserRole

User = get_user_model()

class IntegrationTest:
    def __init__(self):
        self.base_url = "http://localhost:8000/api"
        self.token = None
        self.results = []
        
    def log_result(self, test_name, success, message=""):
        status = "✅" if success else "❌"
        self.results.append((test_name, success, message))
        print(f"{status} {test_name}: {message}")
    
    def test_login_integration(self):
        """Probar login completo"""
        print("\n🔐 INTEGRACIÓN DE LOGIN")
        
        # Crear usuario de prueba si no existe
        try:
            test_user = User.objects.get(email='test@barbershop.com')
        except User.DoesNotExist:
            test_user = User.objects.create_user(
                email='test@barbershop.com',
                password='testpass123',
                full_name='Usuario Test'
            )
            # Asignar rol
            client_admin_role = Role.objects.get(name='Client-Admin')
            UserRole.objects.create(user=test_user, role=client_admin_role)
        
        # Probar login
        login_data = {
            'email': 'test@barbershop.com',
            'password': 'testpass123'
        }
        
        try:
            response = requests.post(f"{self.base_url}/auth/login/", json=login_data)
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('access')
                self.log_result("Login endpoint", True, f"Token obtenido")
                
                # Verificar estructura de respuesta
                required_fields = ['access', 'refresh', 'user']
                has_all_fields = all(field in data for field in required_fields)
                self.log_result("Estructura respuesta", has_all_fields, f"Campos: {list(data.keys())}")
                
                # Verificar datos del usuario
                user_data = data.get('user', {})
                user_fields = ['id', 'email', 'full_name', 'roles']
                has_user_fields = all(field in user_data for field in user_fields)
                self.log_result("Datos usuario", has_user_fields, f"Roles: {len(user_data.get('roles', []))}")
                
            else:
                self.log_result("Login endpoint", False, f"Status {response.status_code}")
        except Exception as e:
            self.log_result("Login endpoint", False, f"Error: {e}")
    
    def test_authenticated_endpoints(self):
        """Probar endpoints que requieren autenticación"""
        print("\n🔒 ENDPOINTS AUTENTICADOS")
        
        if not self.token:
            self.log_result("Token disponible", False, "No hay token para pruebas")
            return
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        endpoints = [
            ('/tenants/', 'Tenants'),
            ('/users/', 'Users'),
            ('/roles/', 'Roles'),
            ('/clients/', 'Clients'),
            ('/employees/', 'Employees'),
            ('/services/', 'Services'),
            ('/appointments/', 'Appointments'),
            ('/pos/sales/', 'POS Sales'),
            ('/inventory/products/', 'Products'),
            ('/subscriptions/plans/', 'Plans'),
        ]
        
        for endpoint, name in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", headers=headers)
                success = response.status_code in [200, 201]
                message = f"Status {response.status_code}"
                if success and response.headers.get('content-type', '').startswith('application/json'):
                    data = response.json()
                    if isinstance(data, dict) and 'results' in data:
                        message += f" - {len(data['results'])} items"
                    elif isinstance(data, list):
                        message += f" - {len(data)} items"
                
                self.log_result(f"{name}", success, message)
            except Exception as e:
                self.log_result(f"{name}", False, f"Error: {str(e)[:50]}")
    
    def test_cors_headers(self):
        """Verificar headers CORS"""
        print("\n🌐 CONFIGURACIÓN CORS")
        
        try:
            response = requests.options(f"{self.base_url}/auth/login/", 
                                      headers={'Origin': 'http://localhost:4200'})
            
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
            }
            
            has_cors = any(cors_headers.values())
            self.log_result("Headers CORS", has_cors, f"Origin: {cors_headers['Access-Control-Allow-Origin']}")
            
        except Exception as e:
            self.log_result("Headers CORS", False, f"Error: {e}")
    
    def test_error_handling(self):
        """Probar manejo de errores"""
        print("\n⚠️ MANEJO DE ERRORES")
        
        # 401 - Sin token
        try:
            response = requests.get(f"{self.base_url}/users/")
            self.log_result("Error 401", response.status_code == 401, f"Status {response.status_code}")
        except Exception as e:
            self.log_result("Error 401", False, f"Error: {e}")
        
        # 400 - Login inválido
        try:
            response = requests.post(f"{self.base_url}/auth/login/", 
                                   json={'email': 'invalid', 'password': 'wrong'})
            self.log_result("Error 400", response.status_code == 400, f"Status {response.status_code}")
        except Exception as e:
            self.log_result("Error 400", False, f"Error: {e}")
    
    def test_data_consistency(self):
        """Verificar consistencia de datos"""
        print("\n📊 CONSISTENCIA DE DATOS")
        
        if not self.token:
            return
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            # Verificar que los datos del backend coincidan con lo esperado
            response = requests.get(f"{self.base_url}/roles/", headers=headers)
            if response.status_code == 200:
                roles = response.json()
                role_names = [role['name'] for role in roles] if isinstance(roles, list) else [role['name'] for role in roles.get('results', [])]
                expected_roles = ['Super-Admin', 'Client-Admin', 'Client-Staff', 'Cajera']
                has_expected = all(role in role_names for role in expected_roles)
                self.log_result("Roles esperados", has_expected, f"Encontrados: {len(role_names)}")
            
        except Exception as e:
            self.log_result("Consistencia datos", False, f"Error: {e}")
    
    def run_integration_tests(self):
        """Ejecutar todas las pruebas de integración"""
        print("🔗 PRUEBAS DE INTEGRACIÓN FRONTEND ↔ BACKEND")
        print("=" * 60)
        
        test_suites = [
            ("Login Integration", self.test_login_integration),
            ("Authenticated Endpoints", self.test_authenticated_endpoints),
            ("CORS Configuration", self.test_cors_headers),
            ("Error Handling", self.test_error_handling),
            ("Data Consistency", self.test_data_consistency),
        ]
        
        for suite_name, test_func in test_suites:
            try:
                test_func()
            except Exception as e:
                print(f"❌ Error en {suite_name}: {e}")
        
        # Resumen
        self.print_summary()
    
    def print_summary(self):
        """Imprimir resumen de integración"""
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE INTEGRACIÓN")
        print("=" * 60)
        
        total = len(self.results)
        passed = sum(1 for _, success, _ in self.results if success)
        percentage = (passed / total) * 100 if total > 0 else 0
        
        print(f"📈 RESULTADOS:")
        print(f"   Total pruebas: {total}")
        print(f"   ✅ Exitosas: {passed}")
        print(f"   ❌ Fallidas: {total - passed}")
        print(f"   📊 Integración: {percentage:.1f}%")
        
        if percentage >= 90:
            status = "🎉 EXCELENTE - Integración completa"
        elif percentage >= 75:
            status = "✅ MUY BUENO - Casi completa"
        elif percentage >= 60:
            status = "⚠️ BUENO - Necesita ajustes"
        else:
            status = "❌ PROBLEMAS - Revisar configuración"
        
        print(f"\n🎯 ESTADO INTEGRACIÓN: {status}")
        
        # Mostrar fallos
        failures = [(name, msg) for name, success, msg in self.results if not success]
        if failures:
            print(f"\n❌ ELEMENTOS PENDIENTES:")
            for name, msg in failures:
                print(f"   • {name}: {msg}")
        
        return percentage >= 85

if __name__ == "__main__":
    tester = IntegrationTest()
    success = tester.run_integration_tests()
    sys.exit(0 if success else 1)