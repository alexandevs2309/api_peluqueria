from django.db import models


class Tutorial(models.Model):
    class ModuleChoices(models.TextChoices):
        APPOINTMENTS = 'appointments', 'Citas'
        EMPLOYEES = 'employees', 'Empleados'
        POS = 'pos', 'POS / Ventas'
        INVENTORY = 'inventory', 'Inventario'
        SERVICES = 'services', 'Servicios'
        CLIENTS = 'clients', 'Clientes'
        REPORTS = 'reports', 'Reportes'
        SETTINGS = 'settings', 'Configuración'
        PAYROLL = 'payroll', 'Nómina'
        SUBSCRIPTIONS = 'subscriptions', 'Suscripciones'

    module = models.CharField(
        max_length=30,
        choices=ModuleChoices.choices,
        verbose_name='Módulo'
    )
    title = models.CharField(max_length=200, verbose_name='Título')
    description = models.TextField(blank=True, verbose_name='Descripción')
    video_url = models.URLField(verbose_name='URL del video (YouTube embed)')
    thumbnail_url = models.URLField(blank=True, verbose_name='URL del thumbnail')
    duration = models.CharField(max_length=20, blank=True, verbose_name='Duración (ej: 3:45)')
    order = models.PositiveIntegerField(default=0, verbose_name='Orden')
    is_published = models.BooleanField(default=True, verbose_name='Publicado')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tutorial'
        verbose_name_plural = 'Tutoriales'
        ordering = ['module', 'order']

    def __str__(self):
        return f'[{self.get_module_display()}] {self.title}'
