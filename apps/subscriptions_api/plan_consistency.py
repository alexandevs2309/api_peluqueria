from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PLAN_SETTINGS_FEATURES_KEY = "plan_features"

# Features que sólo puede conceder el plan vigente. Si el snapshot las trae pero
# el plan actual no las declare, se consideran revocadas (BE-03).
PREMIUM_ONLY_FEATURES = frozenset({
    "payroll",
    "promotions",
    "multi_location",
    "custom_branding",
    "advanced_reports",
    "priority_support",
    "whatsapp_notifications",
    "export_reports",
    "client_history",
})

FEATURE_ALIASES = {
    "cash_register": ("pos", "pos_system"),
    "pos": ("cash_register", "pos_system"),
    "pos_system": ("cash_register", "pos"),
    "promotions": ("promotions_enabled",),
    "promotions_enabled": ("promotions",),
    "multi_branch": ("multi_location",),
    "multi_location": ("multi_branch",),
    "reports": ("basic_reports", "advanced_reports"),
    "basic_reports": ("reports",),
}


def collect_plan_feature_keys(plans) -> list[str]:
    keys: set[str] = set()
    for plan in plans:
        features = getattr(plan, "features", None)
        if isinstance(features, dict):
            keys.update(str(key) for key in features.keys())
    return sorted(keys)


def normalize_features_dict(raw_features: Any, expected_keys: list[str] | tuple[str, ...]) -> dict[str, bool]:
    normalized: dict[str, bool] = {}
    raw_features = raw_features if isinstance(raw_features, dict) else {}
    for key in expected_keys:
        normalized[key] = bool(raw_features.get(key, False))

    for key, value in raw_features.items():
        normalized[str(key)] = bool(value)

    return normalized


def get_feature_value(features: Any, feature_name: str, default: bool = False) -> bool:
    if not isinstance(features, dict):
        return default
    if feature_name in features:
        return bool(features.get(feature_name, default))

    for alias in FEATURE_ALIASES.get(feature_name, ()):
        if alias in features:
            return bool(features.get(alias, default))

    return default


def is_unlimited_limit(limit: Any) -> bool:
    try:
        return int(limit) == 0
    except (TypeError, ValueError):
        return False


def can_add_with_limit(limit: Any, current_count: int, count: int = 1) -> bool:
    current_count = max(int(current_count or 0), 0)
    count = max(int(count or 0), 0)

    if is_unlimited_limit(limit):
        return True

    try:
        limit_value = int(limit)
    except (TypeError, ValueError):
        return False

    return current_count + count <= limit_value


def can_add_employee(tenant, count: int = 1, current_count: int | None = None) -> bool:
    if tenant is None:
        return False

    if current_count is None:
        current_count = tenant.employees.filter(is_active=True).count() if hasattr(tenant, "employees") else 0

    return can_add_with_limit(getattr(tenant, "max_employees", None), current_count, count)


def can_add_user(tenant, count: int = 1, current_count: int | None = None) -> bool:
    if tenant is None:
        return False

    if current_count is None:
        current_count = tenant.users.filter(is_active=True).count() if hasattr(tenant, "users") else 0

    return can_add_with_limit(getattr(tenant, "max_users", None), current_count, count)


def get_plan_features(plan, expected_keys: list[str] | tuple[str, ...] | None = None) -> dict[str, bool]:
    expected_keys = list(expected_keys or [])
    features = dict(getattr(plan, "features", None) or {})
    # Mapeo aprobado R1 (solo resolución): 'pro' (legacy) -> beneficios equivalentes a Premium,
    # preservando derechos sin degradación y sin alterar registros almacenados.
    if getattr(plan, "name", None) == "pro":
        premium_like = {
            "payroll": True,
            "reports": True,
            "inventory": True,
            "promotions": True,
            "appointments": True,
            "basic_reports": True,
            "cash_register": True,
            "client_history": True,
            "export_reports": True,
            "multi_location": True,
            "custom_branding": True,
            "advanced_reports": True,
            "priority_support": True,
            "whatsapp_notifications": True,
        }
        merged = dict(premium_like)
        merged.update(features)
        # Forzar derechos de R1 (no degradar respecto a Premium)
        for k, v in premium_like.items():
            if v:
                merged[k] = True
        features = merged
    return normalize_features_dict(features, expected_keys)


def get_tenant_plan_features(tenant, expected_keys: list[str] | tuple[str, ...] | None = None) -> dict[str, bool]:
    """Resuelve features desde el plan vigente, nunca desde un snapshot heredado.

    BE-03: el snapshot de ``settings['plan_features']`` puede contener claves de un
    plan superior tras un downgrade. Si hay plan vigente, ese plan es la única
    fuente de verdad. El mapeo R1 de 'pro' se conserva sólo cuando el plan vigente
    es 'pro' (o no hay plan y el legado 'pro' es lo único que queda).
    """
    expected_keys = list(expected_keys or [])
    settings = getattr(tenant, "settings", None) or {}
    stored_features = settings.get(PLAN_SETTINGS_FEATURES_KEY)
    subscription_plan = getattr(tenant, "subscription_plan", None)
    plan_name = str(getattr(subscription_plan, "name", "") or "").strip().lower()
    tenant_plan_type = str(getattr(tenant, "plan_type", "") or "").lower()

    is_legacy_pro = plan_name == "pro" or (subscription_plan is None and tenant_plan_type == "pro")
    if is_legacy_pro:
        premium_like = normalize_features_dict({
            "payroll": True, "reports": True, "inventory": True, "promotions": True,
            "appointments": True, "basic_reports": True, "cash_register": True, "client_history": True,
            "export_reports": True, "multi_location": True, "custom_branding": True,
            "advanced_reports": True, "priority_support": True, "whatsapp_notifications": True,
        }, expected_keys)
        if subscription_plan is None:
            snapshot = stored_features if isinstance(stored_features, dict) else {}
            merged = dict(snapshot)
            for k, v in premium_like.items():
                if v:
                    merged[k] = True
            return normalize_features_dict(merged, expected_keys)

        merged = dict(get_plan_features(subscription_plan))
        for k, v in premium_like.items():
            if v:
                merged[k] = True
        return normalize_features_dict(merged, expected_keys)

    if subscription_plan is not None:
        # Downgrade: las features premium NO pueden sobrevivir en el snapshot
        # cuando el plan vigente no las concede. El resto de claves del snapshot
        # se conserva por compatibilidad con despliegues que sólo guardan ahí
        # features básicas.
        plan_features = get_plan_features(subscription_plan)
        merged = dict(plan_features)
        if isinstance(stored_features, dict):
            for k, v in stored_features.items():
                if k not in merged and k not in PREMIUM_ONLY_FEATURES:
                    merged[k] = v
        for k in PREMIUM_ONLY_FEATURES:
            merged.setdefault(k, False)
        return normalize_features_dict(merged, expected_keys)

    return normalize_features_dict(stored_features, expected_keys)


def tenant_has_feature(tenant, feature_name: str, default: bool = False) -> bool:
    if tenant is None:
        return default
    return get_feature_value(get_tenant_plan_features(tenant), feature_name, default=default)


def build_plan_settings_snapshot(plan, inherited_at: str | None = None) -> dict[str, Any]:
    return {
        PLAN_SETTINGS_FEATURES_KEY: dict(getattr(plan, "features", None) or {}),
        "plan_price": str(getattr(plan, "price", "")),
        "plan_duration_months": getattr(plan, "duration_month", None),
        "plan_description": getattr(plan, "description", None),
        "plan_type_logic": f"Plan {getattr(plan, 'name', '')} configurado automaticamente",
        "inherited_at": inherited_at,
    }


@dataclass
class TenantSyncResult:
    tenant_id: int
    tenant_name: str
    plan_name: str
    changed_fields: list[str]
    notes: list[str]


def sync_tenant_with_plan(
    tenant,
    expected_keys: list[str] | tuple[str, ...],
    *,
    apply_feature_values: bool = False,
    apply_limits: bool = False,
) -> TenantSyncResult:
    plan = getattr(tenant, "subscription_plan", None)
    changed_fields: list[str] = []
    notes: list[str] = []

    if plan is None:
        return TenantSyncResult(
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            plan_name="without_plan",
            changed_fields=[],
            notes=["tenant_without_subscription_plan"],
        )

    normalized_plan_features = normalize_features_dict(plan.features, expected_keys)
    tenant.settings = dict(getattr(tenant, "settings", None) or {})
    tenant_features = normalize_features_dict(
        tenant.settings.get(PLAN_SETTINGS_FEATURES_KEY),
        expected_keys,
    )

    missing_feature_keys = [key for key in expected_keys if key not in (tenant.settings.get(PLAN_SETTINGS_FEATURES_KEY) or {})]
    different_feature_values = [
        key for key in expected_keys
        if tenant_features.get(key, False) != normalized_plan_features.get(key, False)
    ]

    if missing_feature_keys:
        merged_features = dict(tenant_features)
        for key in missing_feature_keys:
            merged_features[key] = normalized_plan_features.get(key, False)
        tenant.settings[PLAN_SETTINGS_FEATURES_KEY] = merged_features
        changed_fields.append("settings")
        notes.append(f"filled_missing_feature_keys={','.join(sorted(missing_feature_keys))}")

    if different_feature_values:
        notes.append(f"feature_value_drift={','.join(sorted(different_feature_values))}")
        if apply_feature_values:
            tenant.settings[PLAN_SETTINGS_FEATURES_KEY] = dict(normalized_plan_features)
            if "settings" not in changed_fields:
                changed_fields.append("settings")
            notes.append("applied_plan_feature_values")

    if getattr(tenant, "plan_type", None) != getattr(plan, "name", None):
        tenant.plan_type = plan.name
        changed_fields.append("plan_type")
        notes.append(f"plan_type:{getattr(tenant, 'plan_type', None)}->{plan.name}")

    if tenant.max_employees != plan.max_employees:
        notes.append(f"max_employees_drift={tenant.max_employees}->{plan.max_employees}")
        if apply_limits:
            tenant.max_employees = plan.max_employees
            changed_fields.append("max_employees")

    if tenant.max_users != plan.max_users:
        notes.append(f"max_users_drift={tenant.max_users}->{plan.max_users}")
        if apply_limits:
            tenant.max_users = plan.max_users
            changed_fields.append("max_users")

    unique_changed_fields = list(dict.fromkeys(changed_fields))
    return TenantSyncResult(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        plan_name=plan.name,
        changed_fields=unique_changed_fields,
        notes=notes,
    )
