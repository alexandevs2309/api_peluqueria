from django.contrib import admin, messages
from django.utils import timezone
from django import forms
from .models import Tenant
from apps.subscriptions_api.models import PromotionalCredit


class PromotionalCreditInline(admin.TabularInline):
    model = PromotionalCredit
    extra = 0
    readonly_fields = ('months', 'reason', 'campaign_tag', 'created_by', 'created_at', 'used_at')
    can_delete = False
    verbose_name = 'Crédito Promocional'
    verbose_name_plural = 'Créditos Promocionales'

    def has_add_permission(self, request, obj=None):
        return False


class AddPromotionalCreditForm(forms.Form):
    months = forms.IntegerField(min_value=1, max_value=12, label='Meses gratis')
    reason = forms.CharField(widget=forms.Textarea, required=False, label='Motivo')
    campaign_tag = forms.CharField(max_length=50, required=False, label='Tag de campaña')


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "subdomain", "owner", "subscription_plan", "subscription_status", "is_active", "created_at")
    list_filter = ("subscription_plan", "subscription_status", "is_active")
    search_fields = ("name", "subdomain", "owner__email")
    fields = (
        "name",
        "subdomain",
        "owner",
        "subscription_plan",
        "subscription_status",
        "trial_end_date",
        "access_until",
        "max_employees",
        "max_users",
        "is_active",
    )
    inlines = [PromotionalCreditInline]
    
    def get_queryset(self, request):
        """SuperAdmin ve todo, otros usuarios solo su tenant"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'tenant') and request.user.tenant:
            return qs.filter(id=request.user.tenant.id)
        return qs.none()

    def has_add_permission(self, request):
        return request.user.is_superuser and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_delete_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return super().has_change_permission(request, obj)
        if not super().has_change_permission(request, obj):
            return False
        if obj is None:
            return hasattr(request.user, 'tenant') and request.user.tenant is not None
        return hasattr(request.user, 'tenant') and request.user.tenant_id == obj.id

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def add_promotional_credit(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, 'Selecciona exactamente un tenant.', level='ERROR')
            return

        tenant = queryset.first()
        form = AddPromotionalCreditForm(request.POST or None)

        if 'apply' in request.POST:
            form = AddPromotionalCreditForm(request.POST)
            if form.is_valid():
                months = form.cleaned_data['months']
                reason = form.cleaned_data['reason']
                campaign_tag = form.cleaned_data['campaign_tag']

                credit = PromotionalCredit.objects.create(
                    tenant=tenant,
                    months=months,
                    reason=reason or f'Crédito promocional de {months} meses',
                    campaign_tag=campaign_tag or None,
                    created_by=request.user,
                )
                credit.apply()

                self.message_user(
                    request,
                    f'Crédito de {months} meses aplicado a {tenant.name}. '
                    f'Nuevo trial_end_date/access_until extendido.',
                    level='SUCCESS'
                )
                return
        else:
            form = AddPromotionalCreditForm()

        context = {
            'title': f'Agregar crédito promocional a {tenant.name}',
            'form': form,
            'tenant': tenant,
            'opts': self.model._meta,
            'action': 'add_promotional_credit',
        }
        return admin.helpers.render_action_form(request, context, form=form)

    add_promotional_credit.short_description = 'Agregar crédito promocional (solo 1 tenant)'
