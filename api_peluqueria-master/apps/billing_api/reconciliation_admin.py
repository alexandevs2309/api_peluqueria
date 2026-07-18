from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import json
from .reconciliation_models import ProcessedStripeEvent, ReconciliationLog, ReconciliationAlert


class SuperuserReadOnlyAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


@admin.register(ProcessedStripeEvent)
class ProcessedStripeEventAdmin(SuperuserReadOnlyAdmin):
    list_display = ['stripe_event_id', 'event_type', 'processed_at']
    list_filter = ['event_type', 'processed_at']
    search_fields = ['stripe_event_id', 'event_type']
    readonly_fields = ['stripe_event_id', 'event_type', 'processed_at', 'formatted_payload']
    ordering = ['-processed_at']
    
    def formatted_payload(self, obj):
        return format_html('<pre>{}</pre>', json.dumps(obj.payload, indent=2))
    formatted_payload.short_description = 'Payload'


@admin.register(ReconciliationLog)
class ReconciliationLogAdmin(SuperuserReadOnlyAdmin):
    list_display = ['id', 'started_at', 'status_badge', 'discrepancies_found', 'duration']
    list_filter = ['status', 'started_at']
    readonly_fields = [
        'started_at', 'completed_at', 'status', 'stripe_payments_checked',
        'db_invoices_checked', 'discrepancies_found', 'formatted_missing_in_db',
        'formatted_missing_in_stripe', 'formatted_duplicates', 'error_message'
    ]
    ordering = ['-started_at']
    
    def status_badge(self, obj):
        colors = {
            'running': 'blue',
            'completed': 'green',
            'failed': 'red'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.status.upper()
        )
    status_badge.short_description = 'Status'
    
    def duration(self, obj):
        if obj.completed_at:
            delta = obj.completed_at - obj.started_at
            return f"{delta.total_seconds():.1f}s"
        return "Running..."
    duration.short_description = 'Duration'
    
    def formatted_missing_in_db(self, obj):
        return format_html('<pre>{}</pre>', json.dumps(obj.missing_in_db, indent=2))
    formatted_missing_in_db.short_description = 'Missing in DB'
    
    def formatted_missing_in_stripe(self, obj):
        return format_html('<pre>{}</pre>', json.dumps(obj.missing_in_stripe, indent=2))
    formatted_missing_in_stripe.short_description = 'Missing in Stripe'
    
    def formatted_duplicates(self, obj):
        return format_html('<pre>{}</pre>', json.dumps(obj.duplicates, indent=2))
    formatted_duplicates.short_description = 'Duplicates'


@admin.register(ReconciliationAlert)
class ReconciliationAlertAdmin(SuperuserReadOnlyAdmin):
    list_display = ['id', 'severity_badge', 'alert_type', 'reconciliation_link', 'created_at', 'resolved_badge']
    list_filter = ['severity', 'alert_type', 'resolved', 'created_at']
    search_fields = ['description', 'alert_type']
    readonly_fields = ['reconciliation', 'severity', 'alert_type', 'description', 'formatted_details', 'created_at']
    fields = ['reconciliation', 'severity', 'alert_type', 'description', 'formatted_details',
              'created_at', 'resolved', 'resolved_at', 'resolved_by']
    ordering = ['-created_at']
    
    def severity_badge(self, obj):
        colors = {
            'low': 'green',
            'medium': 'orange',
            'high': 'red',
            'critical': 'darkred'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.severity, 'gray'),
            obj.severity.upper()
        )
    severity_badge.short_description = 'Severity'
    
    def resolved_badge(self, obj):
        if obj.resolved:
            return format_html('<span style="color: green;">✓ Resolved</span>')
        return format_html('<span style="color: red;">✗ Pending</span>')
    resolved_badge.short_description = 'Status'
    
    def reconciliation_link(self, obj):
        url = reverse('admin:billing_api_reconciliationlog_change', args=[obj.reconciliation.id])
        return format_html('<a href="{}">Reconciliation #{}</a>', url, obj.reconciliation.id)
    reconciliation_link.short_description = 'Reconciliation'
    
    def formatted_details(self, obj):
        return format_html('<pre>{}</pre>', json.dumps(obj.details, indent=2))
    formatted_details.short_description = 'Details'
