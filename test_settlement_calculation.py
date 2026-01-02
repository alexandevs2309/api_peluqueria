#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.payroll_api.models import PayrollSettlement
from apps.payroll_api.services import PayrollSettlementService
from apps.employees_api.models import Employee

print('=== PRUEBA CÁLCULO PERÍODO ===')

employee = Employee.objects.get(id=4)
print(f'Empleado: {employee.user.email}')

# Buscar settlement del empleado
settlement = PayrollSettlement.objects.filter(
    employee=employee,
    status='OPEN'
).first()

if settlement:
    print(f'Settlement encontrado: {settlement.id}')
    print(f'Período: {settlement.period_start} - {settlement.period_end}')
    print(f'Estado antes: {settlement.status}')
    print(f'Monto antes: ${settlement.gross_amount}')
    
    # Calcular usando el servicio
    service = PayrollSettlementService()
    settlement = service.calculate_settlement(settlement)
    
    print(f'Estado después: {settlement.status}')
    print(f'Salario fijo: ${settlement.fixed_salary_amount}')
    print(f'Comisiones: ${settlement.commission_amount}')
    print(f'Monto bruto: ${settlement.gross_amount}')
    print(f'Monto neto: ${settlement.net_amount}')
    
    # Verificar earnings relacionados
    from apps.payroll_api.models import SettlementEarning
    settlement_earnings = SettlementEarning.objects.filter(settlement=settlement)
    print(f'Earnings vinculados: {settlement_earnings.count()}')
    
    for se in settlement_earnings:
        print(f'  - Earning: ${se.earning_amount} (comisión: ${se.commission_amount})')
    
else:
    print('❌ No se encontró settlement para el empleado')

print('=== PRUEBA COMPLETADA ===')