from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from apps.roles_api.models import Role
from apps.roles_api.default_permissions import (
    ROLE_PERMISSIONS,
    get_default_permissions_for_role,
)

class Command(BaseCommand):
    help = "Sincroniza roles de roles_api con Group y asigna permisos automáticamente"

    def handle(self, *args, **options):
        for role in Role.objects.filter(name__in=ROLE_PERMISSIONS.keys()):
            group, created = Group.objects.get_or_create(name=role.name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Grupo {role.name} creado"))
            else:
                self.stdout.write(self.style.WARNING(f"ℹ️ Grupo {role.name} ya existía"))

            perms = get_default_permissions_for_role(role.name)
            role.permissions.set(perms)
            group.permissions.set(perms)
            self.stdout.write(self.style.SUCCESS(f"✨ {role.name} actualizado con {role.permissions.count()} permisos"))

        self.stdout.write(self.style.SUCCESS("🎯 Todos los roles sincronizados correctamente"))
