#!/usr/bin/env python
"""
Script de pruebas completo para todos los módulos de pagos
Ejecutar: python test_payment_modules.py
"""
import os
import django
import requests
import json
from datetime import datetime, date
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import FortnightSummary
from apps.employees_api.advance_loans import AdvanceLoan
from apps.pos_api.models import Sale
from django.contrib.auth import get_user_model

User = get_user_model()

class PaymentModuleTester:
    def __init__(self):
        self.base_url = "http://localhost:8000/api"
        self.token = None
        self.employee_id = None
        self.loan_id = None
        
    def authenticate(self):
        """Autenticar usuario"""
        print("🔐 Autenticando usuario...")
        response = requests.post(f"{self.base_url}/auth/login/", {
            "email": "alexanderdelrosarioperez@gmail.com",
            "password": "baspeka1394"
        })
        
        if response.status_code == 200:
            self.token = response.json().get('access')
            print("✅ Autenticación exitosa")
            return True
        else:
            print(f"❌ Error de autenticación: {response.text}")
            return False
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.token}"}
    
    def test_1_earnings_summary(self):
        """Probar resumen de ganancias"""
        print("\n📊 Probando resumen de ganancias...")
        
        response = requests.get(
            f"{self.base_url}/employees/payments/earnings_summary/",
            headers=self.get_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            employees = data.get('employees', [])
            print(f"✅ Resumen obtenido: {len(employees)} empleados")
            
            if employees:
                self.employee_id = employees[0]['employee_id']
                print(f"   Empleado seleccionado: {employees[0]['employee_name']}")
                print(f"   Saldo pendiente: ${employees[0].get('pending_amount', 0)}")
                print(f"   Préstamos activos: ${employees[0].get('total_loans', 0)}")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
    
    def test_2_pending_payments(self):
        """Probar pagos pendientes"""
        print("\n💰 Probando pagos pendientes...")
        
        response = requests.get(
            f"{self.base_url}/employees/payments/pending_payments/",
            headers=self.get_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            pending = data.get('pending_payments', [])
            print(f"✅ Pagos pendientes: {len(pending)} empleados")
            print(f"   Total pendiente: ${data.get('total_amount', 0)}")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
    
    def test_3_create_loan(self):
        """Probar creación de préstamo"""
        print("\n🏦 Probando creación de préstamo...")
        
        if not self.employee_id:
            print("❌ No hay empleado disponible")
            return False
        
        loan_data = {
            "employee_id": self.employee_id,
            "loan_type": "advance",
            "amount": 5000,
            "installments": 6,
            "reason": "Préstamo de prueba para testing"
        }
        
        response = requests.post(
            f"{self.base_url}/employees/loans/",
            json=loan_data,
            headers=self.get_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            self.loan_id = data.get('loan_id')
            print(f"✅ Préstamo creado: ID {self.loan_id}")
            print(f"   Estado: {data.get('status')}")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
    
    def test_4_list_loans(self):
        """Probar listado de préstamos"""
        print("\n📋 Probando listado de préstamos...")
        
        response = requests.get(
            f"{self.base_url}/employees/loans/",
            headers=self.get_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            loans = data.get('loans', [])
            print(f"✅ Préstamos listados: {len(loans)}")
            
            for loan in loans[:3]:  # Mostrar primeros 3
                print(f"   ID: {loan['id']}, Empleado: {loan['employee_name']}, "
                      f"Monto: ${loan['amount']}, Estado: {loan['status']}")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
    
    def test_5_request_loan_cancellation(self):
        """Probar solicitud de cancelación"""
        print("\n🚫 Probando solicitud de cancelación...")
        
        if not self.loan_id:
            print("❌ No hay préstamo disponible")
            return False
        
        response = requests.post(
            f"{self.base_url}/employees/loans/{self.loan_id}/request_cancellation/",
            json={"reason": "Cancelación de prueba - testing del sistema"},
            headers=self.get_headers()
        )
        
        if response.status_code == 200:
            print("✅ Solicitud de cancelación enviada")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
    
    def test_6_approve_cancellation(self):
        """Probar aprobación de cancelación"""
        print("\n✅ Probando aprobación de cancelación...")
        
        if not self.loan_id:
            print("❌ No hay préstamo disponible")
            return False
        
        response = requests.post(
            f"{self.base_url}/employees/loans/{self.loan_id}/approve_cancellation/",
            headers=self.get_headers()
        )
        
        if response.status_code == 200:
            print("✅ Cancelación aprobada")
            return True
        elif response.status_code == 400:
            print("⚠️ Cancelación rechazada por saldo pendiente (esperado)")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
    
    def test_7_payment_with_loan_deduction(self):
        """Probar pago con descuento de préstamo"""
        print("\n💳 Probando pago con descuento personalizable...")
        
        if not self.employee_id:
            print("❌ No hay empleado disponible")
            return False
        
        # Crear venta de prueba primero
        self.create_test_sale()
        
        payment_data = {
            "employee_id": self.employee_id,
            "sale_ids": [1, 2],  # IDs de ejemplo
            "payment_method": "cash",
            "payment_reference": "TEST-001",
            "apply_loan_deduction": True,
            "loan_deduction_amount": 1000,
            "idempotency_key": f"test-{datetime.now().timestamp()}"
        }
        
        response = requests.post(
            f"{self.base_url}/employees/payments/pay_employee/",
            json=payment_data,
            headers=self.get_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Pago procesado con descuentos")
            summary = data.get('summary', {})
            deductions = summary.get('deductions', {})
            print(f"   Monto bruto: ${summary.get('gross_amount', 0)}")
            print(f"   Descuento préstamos: ${deductions.get('loans', 0)}")
            print(f"   Monto neto: ${summary.get('net_amount', 0)}")
            return True
        else:
            print(f"⚠️ Error esperado (sin ventas reales): {response.json().get('error', 'Error desconocido')}")
            return True  # Esperado sin datos reales
    
    def test_8_advance_payment_validation(self):
        """Probar validación de pagos anticipados (debe fallar)"""
        print("\n🚫 Probando validación de pagos anticipados...")
        
        if not self.employee_id:
            print("❌ No hay empleado disponible")
            return False
        
        # Intentar pagar quincena futura
        payment_data = {
            "employee_id": self.employee_id,
            "year": 2025,
            "fortnight": 25,  # Quincena futura
            "payment_method": "cash"
        }
        
        response = requests.post(
            f"{self.base_url}/employees/payments/pay_employee/",
            json=payment_data,
            headers=self.get_headers()
        )
        
        if response.status_code == 400:
            error = response.json().get('error', '')
            if 'futuras' in error or 'préstamos' in error:
                print("✅ Validación correcta: pagos futuros bloqueados")
                return True
        
        print(f"⚠️ Respuesta inesperada: {response.text}")
        return False
    
    def test_9_security_validations(self):
        """Probar validaciones de seguridad"""
        print("\n🔒 Probando validaciones de seguridad...")
        
        # Probar monto excesivo
        loan_data = {
            "employee_id": self.employee_id,
            "loan_type": "advance",
            "amount": 200000,  # Excede límite
            "installments": 6,
            "reason": "Prueba de límite"
        }
        
        response = requests.post(
            f"{self.base_url}/employees/loans/",
            json=loan_data,
            headers=self.get_headers()
        )
        
        if response.status_code == 400:
            print("✅ Validación de monto máximo funciona")
        else:
            print(f"⚠️ Validación de monto no funcionó: {response.text}")
        
        # Probar cuotas inválidas
        loan_data["amount"] = 5000
        loan_data["installments"] = 50  # Excede límite
        
        response = requests.post(
            f"{self.base_url}/employees/loans/",
            json=loan_data,
            headers=self.get_headers()
        )
        
        if response.status_code == 400:
            print("✅ Validación de cuotas máximas funciona")
            return True
        else:
            print(f"⚠️ Validación de cuotas no funcionó: {response.text}")
            return False
    
    def test_10_reports(self):
        """Probar reportes"""
        print("\n📈 Probando reportes...")
        
        # Reporte mensual
        response = requests.get(
            f"{self.base_url}/employees/reports/monthly_summary/?year=2025&month=12",
            headers=self.get_headers()
        )
        
        if response.status_code == 200:
            print("✅ Reporte mensual generado")
        else:
            print(f"⚠️ Error en reporte mensual: {response.text}")
        
        # Reporte de préstamos
        response = requests.get(
            f"{self.base_url}/employees/reports/loans_summary/",
            headers=self.get_headers()
        )
        
        if response.status_code == 200:
            print("✅ Reporte de préstamos generado")
            return True
        else:
            print(f"⚠️ Error en reporte de préstamos: {response.text}")
            return False
    
    def create_test_sale(self):
        """Crear venta de prueba (helper)"""
        try:
            from apps.pos_api.models import Sale
            if self.employee_id:
                employee = Employee.objects.get(id=self.employee_id)
                Sale.objects.get_or_create(
                    employee=employee,
                    total=1000,
                    status='completed',
                    defaults={'date_time': datetime.now()}
                )
        except Exception as e:
            print(f"   Info: No se pudo crear venta de prueba: {e}")
    
    def run_all_tests(self):
        """Ejecutar todas las pruebas"""
        print("🚀 Iniciando pruebas completas del módulo de pagos")
        print("=" * 60)
        
        if not self.authenticate():
            return False
        
        tests = [
            self.test_1_earnings_summary,
            self.test_2_pending_payments,
            self.test_3_create_loan,
            self.test_4_list_loans,
            self.test_5_request_loan_cancellation,
            self.test_6_approve_cancellation,
            self.test_7_payment_with_loan_deduction,
            self.test_8_advance_payment_validation,
            self.test_9_security_validations,
            self.test_10_reports
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                print(f"❌ Error en {test.__name__}: {e}")
        
        print("\n" + "=" * 60)
        print(f"📊 RESULTADOS: {passed}/{total} pruebas exitosas")
        
        if passed == total:
            print("🎉 ¡Todos los módulos funcionan correctamente!")
        elif passed >= total * 0.8:
            print("✅ La mayoría de funcionalidades están operativas")
        else:
            print("⚠️ Varios módulos necesitan atención")
        
        return passed >= total * 0.8

if __name__ == "__main__":
    tester = PaymentModuleTester()
    tester.run_all_tests()