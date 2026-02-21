from django.contrib import admin
from .models import Invoice, PaymentAttempt
from .reconciliation_admin import *  # Import reconciliation admin classes

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "status", "is_paid", "issued_at", "due_date", "paid_at", "stripe_payment_intent_id")
    list_filter = ("status", "is_paid", "payment_method")
    search_fields = ("user__email", "stripe_payment_intent_id")
    readonly_fields = ("issued_at", "paid_at")

@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = ("invoice", "status", "attempted_at")
    list_filter = ("status",)
