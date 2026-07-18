PERMISSION_CAPABILITIES = {
    # Appointments
    'add_appointment': {
        'description': 'Crear citas',
        'endpoints': ['/api/appointments/'],
        'methods': ['POST'],
        'ui_elements': ['create_appointment_button', 'appointment_form']
    },
    'change_appointment': {
        'description': 'Modificar citas',
        'endpoints': ['/api/appointments/{id}/'],
        'methods': ['PUT', 'PATCH'],
        'ui_elements': ['edit_appointment_button', 'appointment_form']
    },
    'delete_appointment': {
        'description': 'Eliminar citas',
        'endpoints': ['/api/appointments/{id}/'],
        'methods': ['DELETE'],
        'ui_elements': ['delete_appointment_button']
    },
    'view_appointment': {
        'description': 'Ver citas',
        'endpoints': ['/api/appointments/', '/api/appointments/{id}/'],
        'methods': ['GET'],
        'ui_elements': ['appointments_list', 'appointment_detail']
    },
    
    # Clients
    'add_client': {
        'description': 'Crear clientes',
        'endpoints': ['/api/clients/'],
        'methods': ['POST'],
        'ui_elements': ['create_client_button', 'client_form']
    },
    'change_client': {
        'description': 'Modificar clientes',
        'endpoints': ['/api/clients/{id}/'],
        'methods': ['PUT', 'PATCH'],
        'ui_elements': ['edit_client_button', 'client_form']
    },
    'view_client': {
        'description': 'Ver clientes',
        'endpoints': ['/api/clients/', '/api/clients/{id}/'],
        'methods': ['GET'],
        'ui_elements': ['clients_list', 'client_detail']
    },
    
    # Employees
    'add_employee': {
        'description': 'Crear empleados',
        'endpoints': ['/api/employees/'],
        'methods': ['POST'],
        'ui_elements': ['create_employee_button', 'employee_form']
    },
    'change_employee': {
        'description': 'Modificar empleados',
        'endpoints': ['/api/employees/{id}/'],
        'methods': ['PUT', 'PATCH'],
        'ui_elements': ['edit_employee_button', 'employee_form']
    },
    'view_employee': {
        'description': 'Ver empleados',
        'endpoints': ['/api/employees/', '/api/employees/{id}/'],
        'methods': ['GET'],
        'ui_elements': ['employees_list', 'employee_detail']
    },
    
    # Reports
    'view_reports': {
        'description': 'Ver reportes',
        'endpoints': ['/api/reports/'],
        'methods': ['GET'],
        'ui_elements': ['reports_menu', 'dashboard_charts']
    },
    
    # Inventory
    'add_product': {
        'description': 'Crear productos',
        'endpoints': ['/api/inventory/'],
        'methods': ['POST'],
        'ui_elements': ['create_product_button', 'product_form']
    },
    'change_product': {
        'description': 'Modificar productos',
        'endpoints': ['/api/inventory/{id}/'],
        'methods': ['PUT', 'PATCH'],
        'ui_elements': ['edit_product_button', 'product_form']
    },
    'view_product': {
        'description': 'Ver inventario',
        'endpoints': ['/api/inventory/', '/api/inventory/{id}/'],
        'methods': ['GET'],
        'ui_elements': ['inventory_list', 'product_detail']
    }
}

# Compatibilidad para código antiguo que importe ROLE_PERMISSIONS desde aquí.
# La fuente de verdad vive en default_permissions.py.
from apps.roles_api.default_permissions import ROLE_PERMISSIONS  # noqa: E402,F401
