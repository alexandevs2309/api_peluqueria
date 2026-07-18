from django.db import models
from django.conf import settings

class Client(models.Model):
    GENDER_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('O', 'Otro'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='clients', db_index=True, null=True, blank=True)
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE, related_name='clients', db_index=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    birthday = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    preferred_stylist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='preferred_clients', db_index=True)
    loyalty_points = models.PositiveIntegerField(default=0)
    last_visit = models.DateTimeField(blank=True, null=True)
    source = models.CharField(max_length=100, blank=True, null=True, help_text="Ej: Instagram, Referido, Tráfico local")

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='clients_created', db_index=True)
    branch = models.ForeignKey('settings_api.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='branch_clients')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

class LoyaltyTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('earned', 'Earned'),
        ('redeemed', 'Redeemed'),
    ]
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='loyalty_transactions', db_index=True)
    sale = models.ForeignKey('pos_api.Sale', on_delete=models.SET_NULL, null=True, blank=True, related_name='loyalty_transactions', db_index=True)
    points = models.PositiveIntegerField()
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.client.full_name} - {self.transaction_type}: {self.points} pts"
  