from django.db import models
from apps.roles_api.models import Role
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model



User = get_user_model()

class Service(models.Model):
    name = models.CharField(max_length=100)
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE, related_name='services')
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        )

    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=50, blank=True, null=True)
    duration = models.PositiveIntegerField(default=30, help_text="Duración en minutos")
    allowed_roles = models.ManyToManyField(Role, blank=True, related_name='services')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        verbose_name = 'Servicio'
        verbose_name_plural = 'Servicios'
        unique_together = ('name', 'tenant')  # Nombre único por tenant
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['tenant']),
        ]


    def __str__(self):
        return self.name


class ServiceEmployee(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='service_employees')
    employee = models.ForeignKey('employees_api.Employee', on_delete=models.CASCADE, related_name='employee_services')
    custom_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('service', 'employee')
        verbose_name = 'Servicio por Empleado'
        verbose_name_plural = 'Servicios por Empleado'

    def __str__(self):
        return f"{self.service.name} - {self.employee.user.email}"

class StylistService(models.Model):
    stylist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stylist_services')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='stylist_services')
    duration = models.DurationField(validators=[MinValueValidator(1)], default='00:30:00')

    class Meta:
        unique_together = ('stylist', 'service')
        verbose_name = 'Servicio de Estilista'
        verbose_name_plural = 'Servicios de Estilistas'

    def __str__(self):
        return f"{self.service} por {self.stylist} ( {self.duration} min)"