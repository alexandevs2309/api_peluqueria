from rest_framework import serializers
from .models import Invoice, PaymentAttempt


class PaymentAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAttempt
        fields = "__all__"
        read_only_fields = ["id", "attempted_at"]


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ["id", "user", "amount", "description", "due_date", "is_paid", "issued_at"]
        read_only_fields = ["id", "user", "is_paid", "issued_at"]