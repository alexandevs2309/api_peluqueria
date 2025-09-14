from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class NotificationTemplate(models.Model):
    """
    Plantillas personalizables para notificaciones
    """
    TEMPLATE_TYPES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
    ]

    NOTIFICATION_TYPES = [
        ('appointment_reminder', 'Recordatorio de Cita'),
        ('appointment_confirmation', 'Confirmación de Cita'),
        ('appointment_cancelled', 'Cita Cancelada'),
        ('appointment_rescheduled', 'Cita Reprogramada'),
        ('payment_received', 'Pago Recibido'),
        ('earnings_available', 'Ganancias Disponibles'),
        ('stock_alert', 'Alerta de Stock'),
        ('subscription_expiring', 'Suscripción Venciendo'),
        ('welcome', 'Bienvenida'),
        ('password_reset', 'Restablecer Contraseña'),
        ('system_maintenance', 'Mantenimiento del Sistema'),
    ]

    name = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    subject = models.CharField(max_length=255, blank=True, null=True)  # Para emails
    body = models.TextField()
    is_html = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Variables disponibles en el template
    available_variables = models.JSONField(default=dict, help_text="Variables disponibles: {{user_name}}, {{appointment_date}}, etc.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_type_display()} - {self.name}"

    class Meta:
        ordering = ['type', 'notification_type']

class Notification(models.Model):
    """
    Notificaciones individuales enviadas a usuarios
    """
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('sent', 'Enviada'),
        ('failed', 'Fallida'),
        ('cancelled', 'Cancelada'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Baja'),
        ('normal', 'Normal'),
        ('high', 'Alta'),
        ('urgent', 'Urgente'),
    ]

    # Destinatario
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')

    # Tipo y template
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE)
    subject = models.CharField(max_length=255)
    message = models.TextField()

    # Estado y prioridad
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')

    # Programación
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    # Contexto (objeto relacionado)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Metadatos
    metadata = models.JSONField(default=dict, help_text="Datos adicionales para personalización")
    error_message = models.TextField(blank=True)

    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.recipient.email} - {self.template.name} ({self.status})"

    def send(self):
        """
        Método para enviar la notificación
        """
        from .services import NotificationService
        service = NotificationService()
        return service.send_notification(self)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['scheduled_at']),
            models.Index(fields=['status', 'priority']),
        ]

class NotificationPreference(models.Model):
    """
    Preferencias de notificación por usuario
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')

    # Canales habilitados
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)

    # Tipos de notificación específicos
    appointment_reminders = models.BooleanField(default=True)
    payment_notifications = models.BooleanField(default=True)
    earnings_notifications = models.BooleanField(default=True)
    system_notifications = models.BooleanField(default=True)
    marketing_notifications = models.BooleanField(default=False)

    # Configuración adicional
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, default='America/Santo_Domingo')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferencias de {self.user.email}"

class NotificationLog(models.Model):
    """
    Log de envíos para auditoría y debugging
    """
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='logs')
    channel = models.CharField(max_length=20, choices=[
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push'),
    ])
    provider = models.CharField(max_length=50, help_text="SendGrid, Twilio, Firebase, etc.")
    external_id = models.CharField(max_length=255, blank=True, help_text="ID del proveedor externo")
    status = models.CharField(max_length=20, choices=[
        ('sent', 'Enviado'),
        ('delivered', 'Entregado'),
        ('failed', 'Falló'),
        ('bounced', 'Rebotado'),
        ('complained', 'Queja'),
    ])
    response_data = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.notification} - {self.channel} ({self.status})"

    class Meta:
        ordering = ['-created_at']
