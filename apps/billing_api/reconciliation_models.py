from django.db import models
from django.utils import timezone


class ProcessedStripeEvent(models.Model):
    """Registro de eventos Stripe procesados para idempotencia"""
    stripe_event_id = models.CharField(max_length=255, unique=True, db_index=True)
    event_type = models.CharField(max_length=100, db_index=True)
    processed_at = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField()
    
    class Meta:
        ordering = ['-processed_at']
        indexes = [
            models.Index(fields=['stripe_event_id']),
            models.Index(fields=['event_type', 'processed_at']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.stripe_event_id}"


class ReconciliationLog(models.Model):
    """Log de reconciliaciones financieras"""
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    
    # Métricas
    stripe_payments_checked = models.IntegerField(default=0)
    db_invoices_checked = models.IntegerField(default=0)
    discrepancies_found = models.IntegerField(default=0)
    
    # Resultados
    missing_in_db = models.JSONField(default=list)  # Pagos en Stripe no en DB
    missing_in_stripe = models.JSONField(default=list)  # Pagos en DB no en Stripe
    duplicates = models.JSONField(default=list)  # Pagos duplicados
    
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['status', 'started_at']),
        ]
    
    def __str__(self):
        return f"Reconciliation {self.started_at.date()} - {self.status}"


class ReconciliationAlert(models.Model):
    """Alertas de discrepancias financieras"""
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    reconciliation = models.ForeignKey(ReconciliationLog, on_delete=models.CASCADE, related_name='alerts')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    alert_type = models.CharField(max_length=100)  # 'missing_payment', 'duplicate', 'mismatch'
    description = models.TextField()
    details = models.JSONField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['severity', 'resolved']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.severity.upper()} - {self.alert_type}"
