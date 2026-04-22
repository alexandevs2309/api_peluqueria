from __future__ import annotations

from .plan_consistency import (
    can_add_employee as _can_add_employee,
    can_add_user as _can_add_user,
    tenant_has_feature,
)


def has_feature(tenant, feature: str) -> bool:
    """
    Safe feature lookup for tenant plan snapshots.
    Missing keys resolve to False instead of None.
    """
    return tenant_has_feature(tenant, feature, default=False)


def can_add_employee(tenant, current_count: int, amount: int = 1) -> bool:
    """
    Returns True when the tenant can add `amount` employees.
    A limit value of 0 means unlimited.
    """
    return _can_add_employee(tenant, count=amount, current_count=current_count)


def can_add_user(tenant, current_count: int, amount: int = 1) -> bool:
    """
    Returns True when the tenant can add `amount` users.
    A limit value of 0 means unlimited.
    """
    return _can_add_user(tenant, count=amount, current_count=current_count)
