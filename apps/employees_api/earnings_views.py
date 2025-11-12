from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from .models import Employee
# from .serializers import EmployeeSerializer

class EarningViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Obtener todas las ganancias"""
        print(f"🔍 DEBUG: User: {request.user}, Tenant: {getattr(request.user, 'tenant', 'NO_TENANT')}")
        
        # Get employees for current tenant
        employees = Employee.objects.filter(
            tenant=request.user.tenant,
            is_active=True
        ).select_related('user')
        
        print(f"📊 DEBUG: Found {employees.count()} employees")
        for emp in employees:
            print(f"👤 Employee: {emp.user.full_name or emp.user.email} - {emp.specialty}")
        
        # Convert to earnings format
        earnings_data = []
        for emp in employees:
            # Map specialty to role
            role = 'stylist'
            specialty_lower = emp.specialty.lower()
            
            if 'admin' in specialty_lower or 'soporte' in specialty_lower:
                role = 'manager'
            elif 'caja' in specialty_lower or 'limpieza' in specialty_lower:
                role = 'assistant'
            elif 'corte' in specialty_lower or 'barber' in specialty_lower:
                role = 'stylist'
            
            # Get default settings from barbershop configuration
            try:
                from apps.settings_api.barbershop_models import BarbershopSettings
                barbershop_settings = BarbershopSettings.objects.get(tenant=request.user.tenant)
                default_commission = float(barbershop_settings.default_commission_rate)
                default_salary = float(barbershop_settings.default_fixed_salary)
            except:
                default_commission = 40.0
                default_salary = 1200000.0
            
            # Use configured payment settings or defaults
            payment_type = emp.payment_type or 'commission'
            commission_rate = float(emp.commission_rate) if emp.commission_rate else default_commission
            fixed_salary = float(emp.fixed_salary) if emp.fixed_salary else default_salary
            
            # Calculate earnings based on payment type
            if payment_type == 'commission':
                total_sales = 2500000  # Sample sales data - should come from actual sales
                total_earned = (total_sales * (commission_rate or 40)) / 100
                services_count = 15
            elif payment_type == 'mixed':
                total_sales = 2500000  # Sample sales data
                commission_earned = (total_sales * (commission_rate or 20)) / 100
                total_earned = (fixed_salary or 800000) + commission_earned
                services_count = 15
            else:  # fixed
                total_sales = 0
                total_earned = fixed_salary or 1200000
                services_count = 0
            
            earnings_data.append({
                'id': emp.id,
                'user_id': emp.user.id,
                'full_name': emp.user.full_name or emp.user.email,
                'email': emp.user.email,
                'role': role,
                'is_active': emp.is_active,
                'payment_type': payment_type,
                'commission_rate': commission_rate,
                'fixed_salary': fixed_salary,
                'total_sales': total_sales,
                'total_earned': total_earned,
                'services_count': services_count,
                'payment_status': 'pending'
            })
        
        print(f"📤 DEBUG: Returning {len(earnings_data)} earnings records")
        return Response(earnings_data)
    
    @action(detail=True, methods=['patch'])
    def mark_paid(self, request, pk=None):
        """Marcar empleado como pagado"""
        try:
            employee = Employee.objects.get(id=pk, tenant=request.user.tenant)
            # Here you would update payment status in a payment record
            # For now, just return success
            return Response({'status': 'paid', 'message': 'Pago marcado correctamente'})
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=404)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Estadísticas de ganancias"""
        return Response({
            'total_earnings': 0,
            'monthly_earnings': 0,
            'top_employees': []
        })

class FortnightSummaryViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Obtener resúmenes quincenales"""
        return Response([])