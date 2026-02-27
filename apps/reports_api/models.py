from django.db import models

class ReportPermission(models.Model):
    """Modelo para permisos de reportes - solo para migrations"""
    
    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            ('view_financial_reports', 'Can view financial reports'),
            ('view_employee_reports', 'Can view employee reports'),
            ('view_sales_reports', 'Can view sales reports'),
            ('view_kpi_dashboard', 'Can view KPI dashboard'),
            ('view_advanced_analytics', 'Can view advanced analytics'),
        ]
