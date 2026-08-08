from django.contrib.auth.models import Permission

perms = Permission.objects.filter(codename__in=[
    'refund_sale',
    'view_financial_reports',
    'view_employee_payroll',
    'manage_employee_loans'
])

print(f'Permisos custom encontrados: {perms.count()}/4')
for p in perms:
    print(f'  ✅ {p.content_type.app_label}.{p.codename}')

if perms.count() < 4:
    print('\n⚠️  Faltan permisos custom. Verificar migraciones.')
