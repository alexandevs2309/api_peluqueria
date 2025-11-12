from django.db import models

class BarbershopSettings(models.Model):
    tenant = models.OneToOneField('tenants_api.Tenant', on_delete=models.CASCADE, related_name='barbershop_settings')
    name = models.CharField(max_length=200, blank=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    currency = models.CharField(max_length=3, default='COP')
    currency_symbol = models.CharField(max_length=5, default='$')
    default_commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=40.00)
    default_fixed_salary = models.DecimalField(max_digits=10, decimal_places=2, default=1200000.00)
    business_hours = models.JSONField(default=dict, blank=True)
    contact = models.JSONField(default=dict, blank=True)
    
    # Additional settings
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text='Tax percentage (e.g., 19.00 for 19%)')
    service_discount_limit = models.DecimalField(max_digits=5, decimal_places=2, default=20.00, help_text='Maximum discount percentage')
    cancellation_policy_hours = models.IntegerField(default=24, help_text='Hours before appointment for free cancellation')
    late_arrival_grace_minutes = models.IntegerField(default=15, help_text='Grace period for late arrivals')
    booking_advance_days = models.IntegerField(default=30, help_text='How many days in advance can clients book')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Barbershop Settings'
        verbose_name_plural = 'Barbershop Settings'

    def __str__(self):
        return f"Settings for {self.tenant.name}"