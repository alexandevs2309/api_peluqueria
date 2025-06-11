from django.db import models
from apps.clients_api.models import Client
from apps.roles_api.models import Role

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='client_appointments')
    stylist = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='stylist_appointments', limit_choices_to={'name': 'stylist'})
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_appointments')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='scheduled')
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    date_time = models.DateTimeField()

    class Meta:
        unique_together = ['stylist', 'date_time']
        ordering = ['-date_time']

    def __str__(self):
        return f'{self.client} with {self.stylist} at {self.date_time}'