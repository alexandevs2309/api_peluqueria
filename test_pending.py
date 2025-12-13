import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.models import Employee
from apps.pos_api.models import Sale

emp = Employee.objects.get(id=4)
print(f'Employee: {emp.user.full_name}')
print(f'Type: {emp.salary_type}, Commission: {emp.commission_percentage}%')

pending = Sale.objects.filter(employee=emp, status='completed', period__isnull=True)
print(f'Pending sales: {pending.count()}')
for s in pending[:5]:
    print(f'  Sale {s.id}: ${s.total}, period={s.period_id}')
