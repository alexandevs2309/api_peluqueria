import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import Permission
from apps.roles_api.models import Role
from apps.roles_api.permission_config import ROLE_PERMISSIONS

def setup_role_permissions():
    """Asigna permisos automáticamente a cada rol"""
    
    for role_name, permissions in ROLE_PERMISSIONS.items():
        try:
            role = Role.objects.get(name=role_name)
            
            if permissions == 'ALL':
                # Super-Admin tiene todos los permisos
                all_permissions = Permission.objects.all()
                role.permissions.set(all_permissions)
                print(f"✅ {role_name}: {all_permissions.count()} permisos asignados")
            else:
                # Asignar permisos específicos
                role_permissions = []
                for perm_codename in permissions:
                    try:
                        perm = Permission.objects.get(codename=perm_codename)
                        role_permissions.append(perm)
                    except Permission.DoesNotExist:
                        print(f"⚠️  Permiso '{perm_codename}' no existe")
                
                role.permissions.set(role_permissions)
                print(f"✅ {role_name}: {len(role_permissions)} permisos asignados")
                
        except Role.DoesNotExist:
            print(f"❌ Rol '{role_name}' no existe")

if __name__ == '__main__':
    setup_role_permissions()
    print("🎉 Configuración de permisos completada")