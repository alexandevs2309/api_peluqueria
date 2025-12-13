from django.core.management.base import BaseCommand
from apps.employees_api.models import Employee
from decimal import Decimal


class Command(BaseCommand):
    help = 'Verifica migración de salary_amount a contractual_monthly_salary (dry-run)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== VERIFICACIÓN DE MIGRACIÓN DE SALARIOS ===\n'))
        
        employees = Employee.objects.filter(is_active=True)
        
        self.stdout.write(f"Total empleados activos: {employees.count()}\n")
        self.stdout.write("-" * 80)
        
        for emp in employees:
            old_quincenal = emp.salary_amount
            new_mensual = old_quincenal * Decimal('2') if old_quincenal else Decimal('0')
            frequency = emp.payment_frequency or 'biweekly'
            
            self.stdout.write(f"\n{emp.user.full_name or emp.user.email}")
            self.stdout.write(f"  Email: {emp.user.email}")
            self.stdout.write(f"  Tipo: {emp.salary_type}")
            self.stdout.write(f"  [OLD] salary_amount (quincenal): ${old_quincenal}")
            self.stdout.write(f"  [NEW] contractual_monthly_salary: ${new_mensual}")
            self.stdout.write(f"  payment_frequency: {frequency}")
            
            if emp.salary_type == 'fixed':
                self.stdout.write(self.style.WARNING(f"  ⚠️  Empleado con sueldo fijo - verificar conversión"))
        
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("\n✅ Verificación completada"))
        self.stdout.write("Para aplicar migración: python manage.py migrate")
