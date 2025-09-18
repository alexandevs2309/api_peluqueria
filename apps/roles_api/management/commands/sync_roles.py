from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from apps.roles_api.models import Role

class Command(BaseCommand):
    help = "Sincroniza roles de roles_api con Group y asigna permisos automáticamente"

    def handle(self, *args, **options):
        # Obtener todos los roles desde roles_api
        for role in Role.objects.all():
            group, created = Group.objects.get_or_create(name=role.name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Grupo {role.name} creado"))
            else:
                self.stdout.write(self.style.WARNING(f"ℹ️ Grupo {role.name} ya existía"))

            # Asignar permisos según rol
            perms = Permission.objects.none()

            if role.name == "Super-Admin":
                perms = Permission.objects.all()
            elif role.name == "Soporte":
                perms |= Permission.objects.filter(codename__icontains="view")
                perms |= Permission.objects.filter(codename__icontains="audit")
            elif role.name == "Client-Admin":
                patterns = ["client", "employee", "appointment", "product", "supplier",
                            "stock", "sale", "saledetail", "cashregister", "payment", 
                            "earning", "service"]
                for pattern in patterns:
                    perms |= Permission.objects.filter(codename__icontains=pattern)
            elif role.name == "Cajera":
                patterns = ["sale", "saledetail", "cashregister", "payment"]
                for pattern in patterns:
                    perms |= Permission.objects.filter(codename__icontains=pattern)
            elif role.name in ["Client-Staff", "Stilista"]:
                patterns = ["appointment", "service", "earning"]
                for pattern in patterns:
                    perms |= Permission.objects.filter(codename__icontains=pattern)
            elif role.name == "Manager":
                patterns = ["employee", "appointment", "sale", "payment"]
                for pattern in patterns:
                    perms |= Permission.objects.filter(codename__icontains=pattern)
            elif role.name == "Admin":
                patterns = ["client", "employee", "appointment", "product"]
                for pattern in patterns:
                    perms |= Permission.objects.filter(codename__icontains=pattern)

            group.permissions.set(perms)
            self.stdout.write(self.style.SUCCESS(f"✨ {role.name} actualizado con {group.permissions.count()} permisos"))

        self.stdout.write(self.style.SUCCESS("🎯 Todos los roles sincronizados correctamente"))
