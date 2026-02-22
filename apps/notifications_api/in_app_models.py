from django.db import models
from django.conf import settings

class InAppNotification(models.Model):
    TYPE_CHOICES = [
        ('appointment', 'Cita'),
        ('sale', 'Venta'),
        ('system', 'Sistema'),
        ('warning', 'Advertencia'),
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='in_app_notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        return f"{self.recipient.email} - {self.title}"
