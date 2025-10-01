from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def employee_report(request):
    """Reporte básico de empleados"""
    return Response({
        'total_employees': 0,
        'active_employees': 0,
        'employees_by_specialty': [],
        'top_performers': []
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sales_report(request):
    """Reporte básico de ventas"""
    return Response({
        'total_sales': 0,
        'monthly_sales': 0,
        'sales_by_day': [],
        'top_services': []
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Estadísticas para dashboard"""
    return Response({
        'total_clients': 0,
        'monthly_appointments': 0,
        'monthly_revenue': 0,
        'active_employees': 0
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reports_by_type(request):
    """Reportes por tipo (appointments, sales, etc.)"""
    report_type = request.GET.get('type', 'general')
    
    if report_type == 'appointments':
        return Response({
            'labels': ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'],
            'data': [0, 0, 0, 0, 0, 0]
        })
    elif report_type == 'sales':
        return Response({
            'labels': ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'],
            'data': [0, 0, 0, 0, 0, 0]
        })
    
    return Response({'data': []})