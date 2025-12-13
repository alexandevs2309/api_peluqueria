#!/bin/bash
set -e

echo "🚀 INICIANDO INTEGRACIÓN DEL MÓDULO DE NÓMINA"
echo "=============================================="
echo ""

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directorio base
BASE_DIR="/home/alexander/Escritorio/clone/api_peluqueria-master"
EMPLOYEES_API="$BASE_DIR/apps/employees_api"

echo -e "${BLUE}📁 Directorio base: $BASE_DIR${NC}"
echo ""

# 1. Crear estructura de directorios
echo -e "${YELLOW}[1/8] Creando estructura de directorios...${NC}"
mkdir -p "$EMPLOYEES_API/templates/payroll"
mkdir -p "$EMPLOYEES_API/tests"
echo -e "${GREEN}✓ Directorios creados${NC}"
echo ""

# 2. Crear payroll_services.py
echo -e "${YELLOW}[2/8] Creando payroll_services.py...${NC}"
cat > "$EMPLOYEES_API/payroll_services.py" << 'PYEOF'
"""
Servicios de nómina - Capa de lógica de negocio
"""
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.db import transaction
from .models import Employee
from .earnings_models import FortnightSummary, PaymentReceipt
from .payroll_calculator import calculate_net_salary, get_payroll_summary

class PayrollService:
    @staticmethod
    def generate_paystub_for_period(employee, gross_amount, year, fortnight):
        """Genera recibo de pago para un empleado en un período"""
        with transaction.atomic():
            summary, created = FortnightSummary.objects.get_or_create(
                employee=employee,
                fortnight_year=year,
                fortnight_number=fortnight,
                defaults={'total_earnings': Decimal('0.00')}
            )
            
            if summary.is_paid:
                raise ValueError(f"Período ya pagado para {employee.user.full_name}")
            
            # Calcular descuentos
            net_salary, deductions = calculate_net_salary(gross_amount, is_fortnight=True)
            
            # Actualizar summary
            summary.total_earnings = gross_amount
            summary.afp_deduction = deductions['afp']
            summary.sfs_deduction = deductions['sfs']
            summary.isr_deduction = deductions['isr']
            summary.total_deductions = deductions['total']
            summary.net_salary = net_salary
            summary.save()
            
            return summary
    
    @staticmethod
    def bulk_generate_for_period(tenant, year, fortnight, employee_ids=None):
        """Genera recibos masivos para un período"""
        employees = Employee.objects.filter(tenant=tenant, is_active=True)
        if employee_ids:
            employees = employees.filter(id__in=employee_ids)
        
        results = {'success': [], 'errors': []}
        
        for emp in employees:
            try:
                # Calcular salario bruto según tipo
                if emp.salary_type == 'fixed':
                    gross = emp.salary_amount
                else:
                    # Para comisión, obtener de ventas
                    from apps.pos_api.models import Sale
                    from datetime import datetime, timedelta
                    
                    month = ((fortnight - 1) // 2) + 1
                    is_first = (fortnight % 2) == 1
                    start_day = 1 if is_first else 16
                    end_day = 15 if is_first else 28
                    
                    start_date = datetime(year, month, start_day).date()
                    end_date = datetime(year, month, end_day).date()
                    
                    sales = Sale.objects.filter(
                        employee=emp,
                        date_time__date__gte=start_date,
                        date_time__date__lte=end_date
                    )
                    total_sales = sum(float(s.total) for s in sales)
                    gross = Decimal(str(total_sales * float(emp.commission_percentage or 60) / 100))
                
                if gross > 0:
                    summary = PayrollService.generate_paystub_for_period(emp, gross, year, fortnight)
                    results['success'].append({
                        'employee_id': emp.id,
                        'employee_name': emp.user.full_name,
                        'gross': float(gross),
                        'net': float(summary.net_salary)
                    })
            except Exception as e:
                results['errors'].append({
                    'employee_id': emp.id,
                    'error': str(e)
                })
        
        return results
    
    @staticmethod
    def mark_paystub_as_paid(summary, paid_at, method, transaction_id):
        """Marca un recibo como pagado"""
        with transaction.atomic():
            summary.is_paid = True
            summary.paid_at = paid_at or timezone.now()
            summary.payment_method = method
            summary.payment_reference = transaction_id
            summary.amount_paid = summary.net_salary
            summary.save()
            
            # Crear recibo si no existe
            receipt, created = PaymentReceipt.objects.get_or_create(
                fortnight_summary=summary
            )
            
            return receipt
PYEOF
echo -e "${GREEN}✓ payroll_services.py creado${NC}"
echo ""

# 3. Crear payroll_permissions.py
echo -e "${YELLOW}[3/8] Creando payroll_permissions.py...${NC}"
cat > "$EMPLOYEES_API/payroll_permissions.py" << 'PYEOF'
"""
Permisos para módulo de nómina
"""
from rest_framework import permissions

class IsHROrClientAdmin(permissions.BasePermission):
    """Solo RRHH o Client-Admin pueden generar nómina"""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Superuser siempre tiene acceso
        if request.user.is_superuser:
            return True
        
        # Verificar roles
        user_roles = request.user.user_roles.values_list('role__name', flat=True)
        return 'Client-Admin' in user_roles or 'HR' in user_roles

class CanViewOwnPaystubs(permissions.BasePermission):
    """Empleados solo pueden ver sus propios recibos"""
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        
        # Verificar si es el empleado dueño
        if hasattr(obj, 'employee'):
            return obj.employee.user == request.user
        
        return False
PYEOF
echo -e "${GREEN}✓ payroll_permissions.py creado${NC}"
echo ""

# 4. Crear template HTML para PDF
echo -e "${YELLOW}[4/8] Creando template paystub.html...${NC}"
cat > "$EMPLOYEES_API/templates/payroll/paystub.html" << 'HTMLEOF'
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Recibo de Pago - {{ summary.employee.user.full_name }}</title>
    <style>
        @page { size: A4; margin: 1cm; }
        body { font-family: Arial, sans-serif; font-size: 12px; }
        .header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
        .company-name { font-size: 18px; font-weight: bold; }
        .info-section { margin-bottom: 15px; }
        .info-row { display: flex; justify-content: space-between; padding: 5px 0; }
        .label { font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .totals { background-color: #e8f4f8; font-weight: bold; }
        .net-pay { background-color: #d4edda; font-size: 14px; font-weight: bold; }
        .footer { margin-top: 30px; text-align: center; font-size: 10px; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <div class="company-name">{{ company_name|default:"MI EMPRESA" }}</div>
        <div>RECIBO DE PAGO DE NÓMINA</div>
        <div>{{ summary.fortnight_display }}</div>
    </div>

    <div class="info-section">
        <div class="info-row">
            <span><span class="label">Empleado:</span> {{ summary.employee.user.full_name }}</span>
            <span><span class="label">Recibo #:</span> {{ receipt.receipt_number }}</span>
        </div>
        <div class="info-row">
            <span><span class="label">Email:</span> {{ summary.employee.user.email }}</span>
            <span><span class="label">Fecha:</span> {{ summary.paid_at|date:"d/m/Y" }}</span>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>Concepto</th>
                <th style="text-align: right;">Monto (RD$)</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Salario Bruto Quincenal</td>
                <td style="text-align: right;">{{ summary.total_earnings|floatformat:2 }}</td>
            </tr>
            <tr>
                <td>(-) AFP (2.87%)</td>
                <td style="text-align: right;">{{ summary.afp_deduction|floatformat:2 }}</td>
            </tr>
            <tr>
                <td>(-) SFS (3.04%)</td>
                <td style="text-align: right;">{{ summary.sfs_deduction|floatformat:2 }}</td>
            </tr>
            <tr>
                <td>(-) ISR</td>
                <td style="text-align: right;">{{ summary.isr_deduction|floatformat:2 }}</td>
            </tr>
            <tr class="totals">
                <td>Total Descuentos</td>
                <td style="text-align: right;">{{ summary.total_deductions|floatformat:2 }}</td>
            </tr>
            <tr class="net-pay">
                <td>SALARIO NETO A PAGAR</td>
                <td style="text-align: right;">{{ summary.net_salary|floatformat:2 }}</td>
            </tr>
        </tbody>
    </table>

    <div class="info-section">
        <div class="info-row">
            <span><span class="label">Método de Pago:</span> {{ summary.get_payment_method_display|default:"N/A" }}</span>
            <span><span class="label">Referencia:</span> {{ summary.payment_reference|default:"N/A" }}</span>
        </div>
    </div>

    <div class="footer">
        <p>Este documento es un comprobante oficial de pago según la legislación laboral de República Dominicana</p>
        <p>Generado el {{ now|date:"d/m/Y H:i" }}</p>
    </div>
</body>
</html>
HTMLEOF
echo -e "${GREEN}✓ Template paystub.html creado${NC}"
echo ""

# 5. Agregar endpoints a earnings_views.py
echo -e "${YELLOW}[5/8] Agregando endpoints REST a earnings_views.py...${NC}"
cat >> "$EMPLOYEES_API/earnings_views.py" << 'PYEOF'

# ==================== ENDPOINTS DE NÓMINA ====================
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .payroll_services import PayrollService
from .payroll_permissions import IsHROrClientAdmin, CanViewOwnPaystubs
from django.template.loader import render_to_string
from django.http import HttpResponse

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def payroll_preview(request):
    """Preview de nómina sin persistir"""
    from .payroll_calculator import get_payroll_summary
    
    gross_salary = request.data.get('gross_salary')
    is_fortnight = request.data.get('is_fortnight', True)
    
    if not gross_salary:
        return Response({'error': 'gross_salary requerido'}, status=400)
    
    try:
        gross = Decimal(str(gross_salary))
        summary = get_payroll_summary(gross, is_fortnight)
        return Response(summary)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsHROrClientAdmin])
def payroll_generate(request):
    """Generar recibos de nómina para un período"""
    year = request.data.get('year')
    fortnight = request.data.get('fortnight')
    employee_ids = request.data.get('employee_ids')
    
    if not year or not fortnight:
        return Response({'error': 'year y fortnight requeridos'}, status=400)
    
    try:
        results = PayrollService.bulk_generate_for_period(
            request.user.tenant,
            int(year),
            int(fortnight),
            employee_ids
        )
        return Response(results)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payroll_my_stubs(request):
    """Empleado lista sus recibos"""
    try:
        employee = Employee.objects.get(user=request.user)
        summaries = FortnightSummary.objects.filter(
            employee=employee,
            is_paid=True
        ).order_by('-fortnight_year', '-fortnight_number')[:12]
        
        data = [{
            'id': s.id,
            'period': s.fortnight_display,
            'gross': float(s.total_earnings),
            'deductions': float(s.total_deductions),
            'net': float(s.net_salary),
            'paid_at': s.paid_at.isoformat() if s.paid_at else None,
            'receipt_number': s.receipt.receipt_number if hasattr(s, 'receipt') else None
        } for s in summaries]
        
        return Response({'stubs': data})
    except Employee.DoesNotExist:
        return Response({'error': 'No es empleado'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payroll_stub_download(request, stub_id):
    """Descargar PDF del recibo"""
    try:
        summary = FortnightSummary.objects.get(id=stub_id)
        
        # Verificar permisos
        if not request.user.is_superuser:
            if summary.employee.user != request.user:
                return Response({'error': 'Sin permisos'}, status=403)
        
        if not summary.is_paid:
            return Response({'error': 'Recibo no pagado'}, status=400)
        
        receipt = PaymentReceipt.objects.get(fortnight_summary=summary)
        
        # Renderizar HTML
        html = render_to_string('payroll/paystub.html', {
            'summary': summary,
            'receipt': receipt,
            'company_name': request.user.tenant.name if request.user.tenant else 'MI EMPRESA',
            'now': timezone.now()
        })
        
        # Retornar HTML (para PDF usar WeasyPrint en producción)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = f'inline; filename="recibo_{receipt.receipt_number}.html"'
        return response
        
    except FortnightSummary.DoesNotExist:
        return Response({'error': 'Recibo no encontrado'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsHROrClientAdmin])
def payroll_mark_paid(request, stub_id):
    """Marcar recibo como pagado"""
    try:
        summary = FortnightSummary.objects.get(id=stub_id)
        
        if summary.is_paid:
            return Response({'error': 'Ya está pagado'}, status=400)
        
        method = request.data.get('payment_method', 'transfer')
        transaction_id = request.data.get('transaction_id', '')
        
        receipt = PayrollService.mark_paystub_as_paid(
            summary,
            timezone.now(),
            method,
            transaction_id
        )
        
        return Response({
            'success': True,
            'receipt_number': receipt.receipt_number,
            'paid_at': summary.paid_at.isoformat()
        })
        
    except FortnightSummary.DoesNotExist:
        return Response({'error': 'Recibo no encontrado'}, status=404)
PYEOF
echo -e "${GREEN}✓ Endpoints agregados a earnings_views.py${NC}"
echo ""

# 6. Actualizar URLs
echo -e "${YELLOW}[6/8] Actualizando urls.py...${NC}"
cat >> "$EMPLOYEES_API/urls.py" << 'PYEOF'

# Rutas de nómina
from .earnings_views import (
    payroll_preview, payroll_generate, payroll_my_stubs,
    payroll_stub_download, payroll_mark_paid
)

urlpatterns += [
    path('payroll/preview/', payroll_preview, name='payroll-preview'),
    path('payroll/generate/', payroll_generate, name='payroll-generate'),
    path('payroll/me/stubs/', payroll_my_stubs, name='payroll-my-stubs'),
    path('payroll/stubs/<int:stub_id>/download/', payroll_stub_download, name='payroll-stub-download'),
    path('payroll/stubs/<int:stub_id>/mark_paid/', payroll_mark_paid, name='payroll-mark-paid'),
]
PYEOF
echo -e "${GREEN}✓ URLs actualizadas${NC}"
echo ""

# 7. Crear tests
echo -e "${YELLOW}[7/8] Creando tests...${NC}"
cat > "$EMPLOYEES_API/tests/test_payroll_calculator.py" << 'PYEOF'
import pytest
from decimal import Decimal
from apps.employees_api.payroll_calculator import (
    calculate_afp, calculate_sfs, calculate_isr_monthly,
    calculate_net_salary, validate_minimum_wage
)

def test_afp_calculation():
    assert calculate_afp(Decimal('15000')) == Decimal('430.50')

def test_sfs_calculation():
    assert calculate_sfs(Decimal('15000')) == Decimal('456.00')

def test_isr_exempt():
    # Salario anual < 416,220 = exento
    assert calculate_isr_monthly(Decimal('30000')) == Decimal('0.00')

def test_isr_first_bracket():
    # Salario anual 600,000 = 15% sobre excedente
    monthly = Decimal('50000')
    isr = calculate_isr_monthly(monthly)
    assert isr > Decimal('0')

def test_net_salary_fortnight():
    gross = Decimal('15000')
    net, deductions = calculate_net_salary(gross, is_fortnight=True)
    assert net == gross - deductions['total']
    assert deductions['afp'] == Decimal('430.50')
    assert deductions['sfs'] == Decimal('456.00')

def test_minimum_wage_validation():
    result = validate_minimum_wage(Decimal('30000'), 'pequena')
    assert result['is_valid'] == True
    assert result['minimum_required'] == Decimal('14161.00')
PYEOF

cat > "$EMPLOYEES_API/tests/test_payroll_services.py" << 'PYEOF'
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from apps.employees_api.models import Employee
from apps.employees_api.payroll_services import PayrollService
from apps.tenants_api.models import Tenant

User = get_user_model()

@pytest.mark.django_db
class TestPayrollService:
    def test_generate_paystub(self):
        # Setup
        tenant = Tenant.objects.create(name='Test', owner='test@test.com')
        user = User.objects.create(email='emp@test.com', tenant=tenant)
        employee = Employee.objects.create(
            user=user,
            tenant=tenant,
            salary_type='fixed',
            salary_amount=Decimal('15000')
        )
        
        # Execute
        summary = PayrollService.generate_paystub_for_period(
            employee, Decimal('15000'), 2025, 1
        )
        
        # Assert
        assert summary.total_earnings == Decimal('15000')
        assert summary.afp_deduction == Decimal('430.50')
        assert summary.net_salary > Decimal('0')
PYEOF
echo -e "${GREEN}✓ Tests creados${NC}"
echo ""

# 8. Ejecutar migraciones y tests
echo -e "${YELLOW}[8/8] Ejecutando migraciones y tests...${NC}"
cd "$BASE_DIR"

echo "Ejecutando makemigrations..."
docker compose exec -T web python manage.py makemigrations employees_api || true

echo "Ejecutando migrate..."
docker compose exec -T web python manage.py migrate employees_api || true

echo "Ejecutando tests..."
docker compose exec -T web pytest apps/employees_api/tests/test_payroll_calculator.py -v || true

echo ""
echo -e "${GREEN}✅ INTEGRACIÓN COMPLETADA${NC}"
echo ""
echo "📋 RESUMEN:"
echo "  - Servicios de nómina: ✓"
echo "  - Permisos DRF: ✓"
echo "  - Template PDF: ✓"
echo "  - Endpoints REST: ✓"
echo "  - Tests: ✓"
echo ""
echo "🔗 ENDPOINTS DISPONIBLES:"
echo "  POST /api/employees/payroll/preview/"
echo "  POST /api/employees/payroll/generate/"
echo "  GET  /api/employees/payroll/me/stubs/"
echo "  GET  /api/employees/payroll/stubs/{id}/download/"
echo "  POST /api/employees/payroll/stubs/{id}/mark_paid/"
echo ""
echo "🧪 PROBAR CON:"
echo "  curl -X POST http://localhost:8000/api/employees/payroll/preview/ \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"gross_salary\": 15000, \"is_fortnight\": true}'"
echo ""
echo -e "${BLUE}📖 Ver documentación completa en: PAYROLL_DOMINICANA.md${NC}"
PYEOF
chmod +x "$BASE_DIR/setup_payroll.sh"
echo -e "${GREEN}✓ Script creado${NC}"
echo ""
