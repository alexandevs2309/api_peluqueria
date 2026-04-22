from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone


PAST_DUE_GRACE_DAYS = 7
SUSPENDED_ARCHIVE_DAYS = 90
DEFAULT_ACTIVE_ACCESS_DAYS = 30
DEFAULT_TRIAL_EXTENSION_DAYS = 7


ACTIVE_STATUSES = {"trial", "active"}
BLOCKED_STATUSES = {"suspended", "archived", "cancelled"}
LIMITED_STATUSES = {"past_due"}
VISIBLE_STATUSES = {"trial", "active", "past_due", "suspended"}


@dataclass
class SubscriptionSyncResult:
    changed_fields: list[str]
    reasons: list[str]

    @property
    def changed(self) -> bool:
        return bool(self.changed_fields)


def _dedupe_fields(fields: list[str]) -> list[str]:
    return list(dict.fromkeys(fields))


def is_subscription_active(tenant) -> bool:
    if tenant is None or getattr(tenant, "deleted_at", None) is not None:
        return False

    now = timezone.now()
    today = now.date()
    status = getattr(tenant, "subscription_status", None)

    if status == "trial":
        return bool(getattr(tenant, "trial_end_date", None) and tenant.trial_end_date >= today)

    if status == "active":
        return bool(getattr(tenant, "access_until", None) and tenant.access_until > now)

    return False


def mark_past_due(tenant, now=None) -> list[str]:
    now = now or timezone.now()
    changed_fields: list[str] = []

    if tenant.subscription_status != "past_due":
        tenant.subscription_status = "past_due"
        changed_fields.append("subscription_status")

    if not tenant.is_active:
        tenant.is_active = True
        changed_fields.append("is_active")

    billing_info = dict(getattr(tenant, "billing_info", None) or {})
    if billing_info.get("past_due_since") is None:
        billing_info["past_due_since"] = now.isoformat()
        tenant.billing_info = billing_info
        changed_fields.append("billing_info")

    return _dedupe_fields(changed_fields)


def suspend_subscription(tenant, now=None) -> list[str]:
    now = now or timezone.now()
    changed_fields: list[str] = []

    if tenant.subscription_status != "suspended":
        tenant.subscription_status = "suspended"
        changed_fields.append("subscription_status")

    if tenant.is_active:
        tenant.is_active = False
        changed_fields.append("is_active")

    billing_info = dict(getattr(tenant, "billing_info", None) or {})
    if billing_info.get("suspended_at") is None:
        billing_info["suspended_at"] = now.isoformat()
        tenant.billing_info = billing_info
        changed_fields.append("billing_info")

    return _dedupe_fields(changed_fields)


def archive_tenant(tenant, now=None) -> list[str]:
    now = now or timezone.now()
    changed_fields: list[str] = []

    if tenant.subscription_status != "archived":
        tenant.subscription_status = "archived"
        changed_fields.append("subscription_status")

    if tenant.is_active:
        tenant.is_active = False
        changed_fields.append("is_active")

    billing_info = dict(getattr(tenant, "billing_info", None) or {})
    if billing_info.get("archived_at") is None:
        billing_info["archived_at"] = now.isoformat()
        tenant.billing_info = billing_info
        changed_fields.append("billing_info")

    return _dedupe_fields(changed_fields)


def extend_subscription(tenant, days: int, now=None) -> list[str]:
    now = now or timezone.now()
    changed_fields: list[str] = []
    days = max(int(days or 0), 0)

    if tenant.subscription_status == "trial":
        base_date = getattr(tenant, "trial_end_date", None) or now.date()
        if base_date < now.date():
            base_date = now.date()
        tenant.trial_end_date = base_date + timedelta(days=days)
        changed_fields.append("trial_end_date")
    else:
        base_time = getattr(tenant, "access_until", None) or now
        if base_time < now:
            base_time = now
        tenant.access_until = base_time + timedelta(days=days)
        changed_fields.append("access_until")

    return _dedupe_fields(changed_fields)


def activate_subscription(tenant, days: int, now=None) -> list[str]:
    now = now or timezone.now()
    days = max(int(days or DEFAULT_ACTIVE_ACCESS_DAYS), 1)
    changed_fields: list[str] = []

    if tenant.subscription_status != "active":
        tenant.subscription_status = "active"
        changed_fields.append("subscription_status")

    if not tenant.is_active:
        tenant.is_active = True
        changed_fields.append("is_active")

    base_time = getattr(tenant, "access_until", None) or now
    if base_time < now:
        base_time = now
    tenant.access_until = base_time + timedelta(days=days)
    changed_fields.append("access_until")

    if tenant.trial_end_date is not None:
        tenant.trial_end_date = None
        changed_fields.append("trial_end_date")

    billing_info = dict(getattr(tenant, "billing_info", None) or {})
    for legacy_key in ("past_due_since", "suspended_at", "archived_at"):
        if legacy_key in billing_info:
            billing_info.pop(legacy_key, None)
            if "billing_info" not in changed_fields:
                changed_fields.append("billing_info")
    tenant.billing_info = billing_info

    return _dedupe_fields(changed_fields)


def get_access_level(tenant, now=None) -> str:
    now = now or timezone.now()

    if tenant is None:
        return "blocked"

    if getattr(tenant, "deleted_at", None) is not None:
        return "hidden"

    status = getattr(tenant, "subscription_status", None)

    if status == "trial":
        trial_end_date = getattr(tenant, "trial_end_date", None)
        if trial_end_date is None:
            return "limited"
        return "full" if trial_end_date >= now.date() else "blocked"

    if status == "active":
        access_until = getattr(tenant, "access_until", None)
        if access_until is None:
            return "limited"
        return "full" if access_until > now else "limited"

    if status == "past_due":
        return "limited"

    if status in {"archived", "cancelled"}:
        return "hidden"

    if status == "suspended":
        return "blocked"

    return "blocked"


def sync_subscription_state(tenant, now=None, *, save: bool = True) -> SubscriptionSyncResult:
    now = now or timezone.now()
    changed_fields: list[str] = []
    reasons: list[str] = []

    if tenant.deleted_at is not None:
        archive_fields = archive_tenant(tenant, now=now)
        if archive_fields:
            changed_fields.extend(archive_fields)
            reasons.append("deleted_tenant -> archived")
    else:
        status = getattr(tenant, "subscription_status", None)
        access_until = getattr(tenant, "access_until", None)
        trial_end_date = getattr(tenant, "trial_end_date", None)
        billing_info = dict(getattr(tenant, "billing_info", None) or {})
        past_due_since_raw = billing_info.get("past_due_since")
        suspended_at_raw = billing_info.get("suspended_at")

        if status == "trial":
            if trial_end_date is None:
                tenant.trial_end_date = now.date() + timedelta(days=DEFAULT_TRIAL_EXTENSION_DAYS)
                changed_fields.append("trial_end_date")
                reasons.append("trial_without_trial_end_date -> assigned today+7d")
            elif trial_end_date < now.date():
                suspend_fields = suspend_subscription(tenant, now=now)
                changed_fields.extend(suspend_fields)
                reasons.append("trial_expired -> suspended")

        elif status == "active":
            if access_until is None:
                tenant.access_until = now + timedelta(days=DEFAULT_ACTIVE_ACCESS_DAYS)
                changed_fields.append("access_until")
                reasons.append("active_without_access_until -> assigned now+30d")
            elif access_until <= now:
                overdue_days = (now - access_until).days
                if overdue_days <= PAST_DUE_GRACE_DAYS:
                    past_due_fields = mark_past_due(tenant, now=now)
                    changed_fields.extend(past_due_fields)
                    reasons.append("expired_within_grace -> past_due")
                else:
                    suspend_fields = suspend_subscription(tenant, now=now)
                    changed_fields.extend(suspend_fields)
                    reasons.append("expired_beyond_grace -> suspended")

        elif status == "past_due":
            if access_until and access_until > now:
                activation_fields = activate_subscription(tenant, days=0, now=now)
                changed_fields.extend(activation_fields)
                reasons.append("past_due_but_access_restored -> active")
            else:
                past_due_since = timezone.datetime.fromisoformat(past_due_since_raw) if past_due_since_raw else None
                if past_due_since is None and access_until is not None:
                    past_due_since = access_until
                if past_due_since is None:
                    past_due_fields = mark_past_due(tenant, now=now)
                    changed_fields.extend(past_due_fields)
                    reasons.append("past_due_without_marker -> assigned marker")
                elif now - past_due_since > timedelta(days=PAST_DUE_GRACE_DAYS):
                    suspend_fields = suspend_subscription(tenant, now=now)
                    changed_fields.extend(suspend_fields)
                    reasons.append("past_due_grace_exceeded -> suspended")

        elif status == "suspended":
            suspended_at = timezone.datetime.fromisoformat(suspended_at_raw) if suspended_at_raw else None
            if suspended_at is None:
                suspend_fields = suspend_subscription(tenant, now=now)
                changed_fields.extend(suspend_fields)
                reasons.append("suspended_without_marker -> assigned marker")
            elif now - suspended_at >= timedelta(days=SUSPENDED_ARCHIVE_DAYS):
                archive_fields = archive_tenant(tenant, now=now)
                changed_fields.extend(archive_fields)
                reasons.append("suspended_too_long -> archived")

        elif status == "archived":
            archive_fields = archive_tenant(tenant, now=now)
            changed_fields.extend(archive_fields)

        elif status == "cancelled":
            if tenant.is_active:
                tenant.is_active = False
                changed_fields.append("is_active")
                reasons.append("legacy_cancelled_but_active -> deactivated")

        if tenant.subscription_status in ACTIVE_STATUSES.union(LIMITED_STATUSES) and not tenant.is_active:
            tenant.is_active = True
            changed_fields.append("is_active")
            reasons.append("active_like_status_but_inactive -> activated")
        elif tenant.subscription_status in BLOCKED_STATUSES and tenant.is_active:
            tenant.is_active = False
            changed_fields.append("is_active")
            reasons.append("blocked_status_but_active -> deactivated")

    changed_fields = _dedupe_fields(changed_fields)
    reasons = list(dict.fromkeys(reasons))

    if changed_fields and save:
        tenant.save(update_fields=[*changed_fields, "updated_at"])

    return SubscriptionSyncResult(changed_fields=changed_fields, reasons=reasons)
