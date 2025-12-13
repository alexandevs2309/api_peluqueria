"""
URLs limpias y optimizadas para el sistema de pagos
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet, WorkScheduleViewSet
from .payments_views import PaymentViewSet, employee_pending_sales

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'schedules', WorkScheduleViewSet, basename='work_schedule')
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
    # Endpoint específico para ventas pendientes de un empleado
    path('employees/<int:employee_id>/pending-sales/', employee_pending_sales, name='employee-pending-sales'),
]