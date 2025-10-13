from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone

User = get_user_model()

class AuditLog(models.Model):
    """Modelo unificado para todos los logs de auditoría del sistema"""
    
    ACTION_CHOICES = [
        ('CREATE', 'Creación'),
        ('UPDATE', 'Actualización'),
        ('DELETE', 'Eliminación'),
        ('VIEW', 'Visualización'),
        ('LOGIN', 'Inicio de sesión'),
        ('LOGOUT', 'Cierre de sesión'),
        ('LOGIN_FAILED', 'Fallo de inicio de sesión'),
        ('PASSWORD_CHANGE', 'Cambio de contraseña'),
        ('ROLE_ASSIGN', 'Asignación de rol'),
        ('ROLE_REMOVE', 'Remoción de rol'),
        ('PERMISSION_GRANT', 'Concesión de permiso'),
        ('PERMISSION_REVOKE', 'Revocación de permiso'),
        ('SETTING_UPDATE', 'Actualización de configuración'),
        ('SUBSCRIPTION_CREATE', 'Creación de suscripción'),
        ('SUBSCRIPTION_UPDATE', 'Actualización de suscripción'),
        ('SUBSCRIPTION_CANCEL', 'Cancelación de suscripción'),
        ('SUBSCRIPTION_RENEW', 'Renovación de suscripción'),
        ('MFA_ENABLE', 'Activación de MFA'),
        ('MFA_DISABLE', 'Desactivación de MFA'),
        ('ADMIN_ACTION', 'Acción administrativa'),
        ('INTEGRATION_ERROR', 'Error de integración'),
        ('PERFORMANCE_ALERT', 'Alerta de rendimiento'),
        ('SYSTEM_ERROR', 'Error del sistema'),
        ('STRIPE_ERROR', 'Error de Stripe'),
        ('PAYPAL_ERROR', 'Error de PayPal'),
        ('TWILIO_ERROR', 'Error de Twilio'),
        ('SENDGRID_ERROR', 'Error de SendGrid'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="Usuario que realizó la acción"
    )
    
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        help_text="Tipo de acción realizada"
    )
    
    description = models.TextField(
        help_text="Descripción detallada de la acción"
    )
    
    # Campos para relación genérica con cualquier modelo
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Tipo de objeto relacionado"
    )
    
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="ID del objeto relacionado"
    )
    
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Información adicional
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Dirección IP del usuario"
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text="User agent del cliente"
    )
    
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Datos adicionales en formato JSON"
    )
    
    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text="Fecha y hora de la acción"
    )
    
    # Campo para identificar la fuente original
    source = models.CharField(
        max_length=50,
        choices=[
            ('AUTH', 'Autenticación'),
            ('ROLES', 'Roles y permisos'),
            ('SETTINGS', 'Configuración'),
            ('SUBSCRIPTIONS', 'Suscripciones'),
            ('USERS', 'Usuarios'),
            ('SYSTEM', 'Sistema'),
            ('INTEGRATIONS', 'Integraciones'),
            ('PERFORMANCE', 'Rendimiento'),
        ],
        default='SYSTEM',
        help_text="Origen del log"
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"
