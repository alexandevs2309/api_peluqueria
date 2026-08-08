"""
Base model y manager para aislamiento multi-tenant.

Uso en modelos nuevos o al refactorizar:

    from apps.core.models import TenantModel

    class MyModel(TenantModel):
        name = models.CharField(max_length=100)
        # tenant FK ya viene de TenantModel

Uso del manager directamente en modelos existentes:

    from apps.core.models import TenantManager

    class Client(models.Model):
        tenant = models.ForeignKey(...)
        objects = TenantManager()

Para queries seguras en vistas:
    Client.objects.for_tenant(request.tenant)
    # equivale a Client.objects.filter(tenant=request.tenant)
    # pero lanza ValueError si tenant es None
"""
from django.db import models


class TenantManager(models.Manager):
    """
    Manager que expone for_tenant(tenant) para queries aisladas.
    No sobreescribe get_queryset() para no romper queries existentes
    que no pasan tenant (admin, tareas Celery, etc.).
    """

    def for_tenant(self, tenant):
        """
        Devuelve queryset filtrado por tenant.
        Lanza ValueError si tenant es None o no tiene id válido,
        para evitar fugas silenciosas entre tenants.
        """
        if tenant is None:
            raise ValueError(
                "for_tenant() requiere un tenant válido. "
                "Usa objects.all() explícitamente si necesitas acceso global."
            )
        if not getattr(tenant, 'id', None):
            raise ValueError(
                f"for_tenant() recibió un tenant sin id válido: {tenant!r}"
            )
        return self.get_queryset().filter(tenant=tenant)

    def for_tenant_or_none(self, tenant):
        """
        Versión segura: devuelve queryset vacío si tenant es None.
        Usar cuando el tenant puede ser None de forma legítima.
        """
        if tenant is None or not getattr(tenant, 'id', None):
            return self.get_queryset().none()
        return self.get_queryset().filter(tenant=tenant)


class TenantModel(models.Model):
    """
    Modelo base abstracto para entidades multi-tenant.
    Agrega FK a tenant y TenantManager.

    Los modelos existentes NO necesitan heredar de esto para seguir funcionando.
    Usar en modelos nuevos o al refactorizar.
    """
    tenant = models.ForeignKey(
        'tenants_api.Tenant',
        on_delete=models.CASCADE,
        db_index=True,
    )

    objects = TenantManager()

    class Meta:
        abstract = True
