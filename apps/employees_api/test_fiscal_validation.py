from decimal import Decimal
import pytest
from apps.employees_api.earnings_models import FiscalTable, FiscalBracket


@pytest.mark.django_db
def test_fiscal_table_isr_progressive():
    ft = FiscalTable.get_for_year(2026)
    # Exento
    assert ft.calculate_isr(Decimal('400000.00')) == Decimal('0.00')
    # Tramo 15%
    isr = ft.calculate_isr(Decimal('500000.00'))
    assert isr > 0
    # Tramo 25%
    isr2 = ft.calculate_isr(Decimal('1000000.00'))
    assert isr2 > isr


@pytest.mark.django_db
def test_fiscal_table_2027():
    ft = FiscalTable.get_for_year(2027)
    assert ft.exemption_annual == Decimal('480000.00')
    # 27% bracket exists
    assert ft.brackets.filter(rate=Decimal('27.00')).exists()