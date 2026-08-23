"""
Tests for POS monetary precision — backend.

Verifies that DRF DecimalField accepts string monetary values ("19.99")
and rejects values with more than 2 decimal places.
"""
from decimal import Decimal
from django.test import TestCase
from apps.pos_api.serializers import SaleSerializer, SaleDetailSerializer


class MoneyPrecisionTests(TestCase):
    """Test that DRF serializer correctly handles monetary precision."""

    def test_decimal_field_accepts_string_two_decimals(self):
        """DRF DecimalField should accept '19.99' string and produce Decimal('19.99')."""
        field = SaleSerializer().fields['total']
        result = field.to_internal_value('19.99')
        self.assertEqual(result, Decimal('19.99'))

    def test_decimal_field_accepts_string_zero_decimals(self):
        """DRF DecimalField should accept '20' and coerce to Decimal('20.00')."""
        field = SaleSerializer().fields['total']
        result = field.to_internal_value('20')
        self.assertEqual(result, Decimal('20'))

    def test_decimal_field_rejects_three_decimals(self):
        """DRF DecimalField should reject '19.999' (more than 2 decimal places)."""
        field = SaleSerializer().fields['total']
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            field.to_internal_value('19.999')

    def test_decimal_field_rejects_many_decimals(self):
        """DRF DecimalField should reject '33.028200000000005'."""
        field = SaleSerializer().fields['total']
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            field.to_internal_value('33.028200000000005')

    def test_decimal_field_rejects_float_with_artifacts(self):
        """DRF DecimalField should reject a Python float with >2 decimal places."""
        field = SaleSerializer().fields['total']
        from rest_framework.exceptions import ValidationError
        # Python float(19.99 * 3) can have artifacts
        with self.assertRaises(ValidationError):
            field.to_internal_value(59.970000000000006)

    def test_decimal_field_accepts_integer(self):
        """DRF DecimalField should accept integer 0."""
        field = SaleSerializer().fields['total']
        result = field.to_internal_value(0)
        self.assertEqual(result, Decimal('0'))

    def test_detail_price_accepts_string(self):
        """SaleDetail price should accept string '27.99'."""
        field = SaleDetailSerializer().fields['price']
        result = field.to_internal_value('27.99')
        self.assertEqual(result, Decimal('27.99'))

    def test_detail_price_rejects_many_decimals(self):
        """SaleDetail price should reject '27.999'."""
        field = SaleDetailSerializer().fields['price']
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            field.to_internal_value('27.999')

    def test_payment_amount_accepts_string(self):
        """Payment amount should accept string '33.03'."""
        from apps.pos_api.serializers import PaymentSerializer
        field = PaymentSerializer().fields['amount']
        result = field.to_internal_value('33.03')
        self.assertEqual(result, Decimal('33.03'))

    def test_discount_accepts_string(self):
        """Sale discount should accept string '5.00'."""
        field = SaleSerializer().fields['discount']
        result = field.to_internal_value('5.00')
        self.assertEqual(result, Decimal('5.00'))
