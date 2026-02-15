import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import PayrollPeriod
from apps.tenants_api.models import Tenant
from apps.auth_api.models import User
from datetime import date
from decimal import Decimal

# Obtener tenant y admin
tenant = Tenant.objects.get(id=2)
admin = User.objects.filter(tenant=tenant, is_staff=True).first() or User.objects.filter(tenant=tenant).first()

print(f"Tenant: {tenant.name}")
print(f"Admin: {admin.email}\n")

# Obtener empleados
employees = list(Employee.objects.filter(tenant=tenant))
print(f"Empleados: {len(employees)}\n")

if len(employees) < 3:
    print("Se necesitan al menos 3 empleados para crear ejemplos")
    exit()

# Crear períodos de ejemplo
print("Creando períodos de prueba...\n")

# 1. Período ABIERTO (open)
period1 = PayrollPeriod.objects.create(
    employee=employees[0],
    period_type='biweekly',
    period_start=date(2024, 2, 1),
    period_end=date(2024, 2, 15),
    status='open'
)
period1.calculate_amounts()
period1.save()
print(f"✓ Período ABIERTO creado: {employees[0].user.full_name} - ${period1.net_amount}")

# 2. Período PENDIENTE DE APROBACIÓN (pending_approval)
period2 = PayrollPeriod.objects.create(
    employee=employees[1],
    period_type='biweekly',
    period_start=date(2024, 2, 1),
    period_end=date(2024, 2, 15),
    status='pending_approval',
    submitted_by=admin
)
period2.calculate_amounts()
period2.save()
print(f"✓ Período PENDIENTE creado: {employees[1].user.full_name} - ${period2.net_amount}")

# 3. Período APROBADO (approved)
period3 = PayrollPeriod.objects.create(
    employee=employees[2],
    period_type='biweekly',
    period_start=date(2024, 2, 1),
    period_end=date(2024, 2, 15),
    status='approved',
    submitted_by=admin,
    approved_by=admin
)
period3.calculate_amounts()
period3.save()
print(f"✓ Período APROBADO creado: {employees[2].user.full_name} - ${period3.net_amount}")

# 4. Período PAGADO (paid) - si hay un 4to empleado
if len(employees) >= 4:
    period4 = PayrollPeriod.objects.create(
        employee=employees[3],
        period_type='biweekly',
        period_start=date(2024, 1, 16),
        period_end=date(2024, 1, 31),
        status='paid',
        submitted_by=admin,
        approved_by=admin,
        paid_by=admin,
        payment_method='transfer',
        payment_reference='TRF-001'
    )
    period4.calculate_amounts()
    period4.save()
    print(f"✓ Período PAGADO creado: {employees[3].user.full_name} - ${period4.net_amount}")

print(f"\n{'='*60}")
print("RESUMEN FINAL")
print(f"{'='*60}\n")

for status_code, status_name in PayrollPeriod.STATUS_CHOICES:
    count = PayrollPeriod.objects.filter(employee__tenant=tenant, status=status_code).count()
    if count > 0:
        print(f"{status_name}: {count} período(s)")

print(f"\n{'='*60}")
print("Períodos de prueba creados exitosamente")
print(f"{'='*60}")
