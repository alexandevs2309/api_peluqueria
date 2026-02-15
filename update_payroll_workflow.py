import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import PayrollPeriod
from apps.tenants_api.models import Tenant
from datetime import date

# Obtener tenant
tenant = Tenant.objects.get(id=2)
print(f"Tenant: {tenant.name}\n")

# Obtener empleados
employees = Employee.objects.filter(tenant=tenant)
print(f"Empleados encontrados: {employees.count()}\n")

# Actualizar períodos existentes a 'pending_approval'
existing_periods = PayrollPeriod.objects.filter(employee__tenant=tenant, status='open')
print(f"Actualizando {existing_periods.count()} períodos existentes...\n")

for period in existing_periods:
    period.status = 'pending_approval'
    period.calculate_amounts()
    period.save()
    print(f"✓ Período {period.id} actualizado: {period.employee.user.full_name} - ${period.net_amount}")

print(f"\n{'='*60}")
print("RESUMEN DE PERÍODOS POR ESTADO")
print(f"{'='*60}\n")

for status_code, status_name in PayrollPeriod.STATUS_CHOICES:
    count = PayrollPeriod.objects.filter(employee__tenant=tenant, status=status_code).count()
    if count > 0:
        print(f"{status_name}: {count} períodos")

print(f"\n{'='*60}")
print("Actualización completada")
print(f"{'='*60}")
