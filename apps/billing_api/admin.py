from django.contrib import admin
from .models import Invoice, PaymentAttempt

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "status", "is_paid", "issued_at", "due_date", "paid_at")
    list_filter = ("status", "is_paid")
    search_fields = ("user__email",)

@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = ("invoice", "status", "attempted_at")
    list_filter = ("status",)
