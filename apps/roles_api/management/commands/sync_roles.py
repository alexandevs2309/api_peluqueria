from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from apps.roles_api.models import Role
from django.db import transaction

class Command(BaseCommand):
    help = "Sincroniza roles canónicos del sistema con permisos automáticos"

    # FUENTE DE VERDAD ÚNICA - Roles canónicos del sistema
    ROLES = {
        "SUPER_ADMIN": {
            "display": "Super Administrador",
            "description": "Administrador de la plataforma SaaS",
            "scope": "GLOBAL",
            "permissions": "all"
        },
        "SUPPORT": {
            "display": "Soporte Técnico",
            "description": "Personal de soporte (solo lectura)",
            "scope": "GLOBAL",
            "permissions": ["view_*", "audit_*"]
        },
        "CLIENT_ADMIN": {
            "display": "Administrador Cliente",
            "description": "Dueño de peluquería (administrador del tenant)",
            "scope": "TENANT",
            "permissions": [
                "*_client", "*_employee", "*_appointment", "*_product", "*_supplier",
                "*_stock", "*_sale", "*_saledetail", "*_cashregister", "*_payment",
                "*_earning", "*_service", "*_tenant", "*_payrollpayment", "*_advanceloan"
            ]
        },
        "MANAGER": {
            "display": "Encargado",
            "description": "Encargado de sucursal",
            "scope": "TENANT",
            "permissions": [
                "view_*", "*_employee", "*_appointment", "*_sale", "*_payment",
                "*_earning", "*_service", "view_payrollpayment"
            ]
        },
        "CLIENT_STAFF": {
            "display": "Empleado",
            "description": "Empleado de peluquería (estilista, etc.)",
            "scope": "TENANT",
            "permissions": [
                "view_appointment", "change_appointment", "*_earning", "view_service",
                "view_client", "view_sale", "view_payrollpayment"
            ]
        },
        "CASHIER": {
            "display": "Cajero/a",
            "description": "Personal de caja (solo POS)",
            "scope": "TENANT",
            "permissions": [
                "*_sale", "*_saledetail", "*_cashregister", "*_payment",
                "view_client", "view_service", "view_product"
            ]
        }
    }

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write("🔄 Sincronizando roles canónicos...")
            
            for role_code, role_data in self.ROLES.items():
                # Crear/actualizar Role
                role, created = Role.objects.get_or_create(
                    name=role_code,
                    defaults={
                        'description': role_data['description'],
                        'scope': role_data['scope']
                    }
                )
                
                # Sincronizar con Django Group
                group, group_created = Group.objects.get_or_create(name=role_code)
                
                # Asignar permisos
                permissions = self._get_permissions(role_data['permissions'])
                group.permissions.set(permissions)
                
                status = "✅ Creado" if created else "🔄 Actualizado"
                self.stdout.write(f"{status}: {role_code} ({role_data['display']}) - {permissions.count()} permisos")
            
            self.stdout.write(self.style.SUCCESS(f"🎯 {len(self.ROLES)} roles sincronizados correctamente"))

    def _get_permissions(self, permission_patterns):
        """Obtiene permisos basado en patrones o 'all'"""
        if permission_patterns == "all":
            return Permission.objects.all()
        
        permissions = Permission.objects.none()
        
        for pattern in permission_patterns:
            if pattern.startswith("*_"):
                # Patrón: *_model → add_model, change_model, delete_model, view_model
                model_name = pattern[2:]
                permissions |= Permission.objects.filter(codename__endswith=f"_{model_name}")
            elif pattern.endswith("_*"):
                # Patrón: action_* → action_cualquier_modelo
                action = pattern[:-2]
                permissions |= Permission.objects.filter(codename__startswith=f"{action}_")
            else:
                # Patrón exacto: view_client
                permissions |= Permission.objects.filter(codename=pattern)
        
        return permissions.distinct()
