from django.contrib import admin
from django.utils.html import format_html
from apps.tenants_api.base_admin import BaseTenantAdmin
from .models import PaymentProvider, Payment, WebhookEvent, PaymentProof

@admin.register(PaymentProvider)
class PaymentProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

@admin.register(Payment)
class PaymentAdmin(BaseTenantAdmin):
    tenant_lookup = "tenant"
    list_display = ['id', 'user', 'amount', 'status', 'provider', 'created_at']
    list_filter = ['status', 'provider', 'created_at']
    search_fields = ['user__email', 'provider_payment_id']
    readonly_fields = [
        'id', 'user', 'subscription', 'provider', 'amount', 'currency', 'status',
        'provider_payment_id', 'provider_customer_id', 'metadata',
        'created_at', 'updated_at', 'completed_at'
    ]

@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ['event_id', 'provider', 'event_type', 'processed', 'created_at']
    list_filter = ['provider', 'processed', 'event_type']
    readonly_fields = ['provider', 'event_id', 'event_type', 'processed', 'data', 'created_at']

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentProof)
class PaymentProofAdmin(admin.ModelAdmin):
    list_display = ['id', 'payment', 'decision', 'amount_provided', 'bank_reference', 'created_at', 'reviewed_by']
    list_filter = ['decision', 'created_at']
    search_fields = ['bank_reference', 'payment__id']
    readonly_fields = [
        'id', 'payment', 'file', 'file_name', 'bank_reference', 'amount_provided',
        'decision', 'decision_note', 'reviewed_by', 'reviewed_at', 'created_at', 'updated_at',
    ]
    actions = ['approve_proof', 'reject_proof']

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description='Aprobar comprobante seleccionado')
    def approve_proof(self, request, queryset):
        from .manual import approve_manual_payment
        from . import emails as manual_emails
        for proof in queryset:
            invoice = proof.payment.invoice if hasattr(proof.payment, 'invoice') else None
            if not invoice:
                self.message_user(request, f'El comprobante {proof.id} no tiene factura asociada.', level='error')
                continue
            if proof.decision != 'pending':
                self.message_user(request, f'El comprobante {proof.id} ya fue resuelto ({proof.decision}).', level='warning')
                continue
            result = approve_manual_payment(invoice, request.user, decision_note='Aprobado desde el panel de administración.')
            if result['ok']:
                access_until = result['data'].get('access_until')
                try:
                    from dateutil import parser
                    access_until = parser.isoparse(access_until) if access_until else None
                except Exception:
                    access_until = None
                try:
                    manual_emails.send_manual_payment_approved_email(invoice.user, invoice.tenant, invoice, proof, access_until)
                except Exception:
                    pass
                self.message_user(request, f'Comprobante {proof.id} aprobado. Plan activado.')
            else:
                self.message_user(request, f'Error al aprobar {proof.id}: {result.get("error")}', level='error')

    @admin.action(description='Rechazar comprobante seleccionado')
    def reject_proof(self, request, queryset):
        from .manual import reject_manual_payment
        from . import emails as manual_emails
        for proof in queryset:
            invoice = proof.payment.invoice if hasattr(proof.payment, 'invoice') else None
            if not invoice:
                self.message_user(request, f'El comprobante {proof.id} no tiene factura asociada.', level='error')
                continue
            if proof.decision != 'pending':
                self.message_user(request, f'El comprobante {proof.id} ya fue resuelto ({proof.decision}).', level='warning')
                continue
            result = reject_manual_payment(invoice, request.user, reason='Rechazado desde el panel de administración.')
            if result['ok']:
                try:
                    manual_emails.send_manual_payment_rejected_email(invoice.user, invoice.tenant, invoice, proof)
                except Exception:
                    pass
                self.message_user(request, f'Comprobante {proof.id} rechazado.')
            else:
                self.message_user(request, f'Error al rechazar {proof.id}: {result.get("error")}', level='error')

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions
