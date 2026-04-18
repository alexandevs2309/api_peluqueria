from functools import wraps

from .utils import create_audit_log, sanitize_audit_data


FINANCIAL_AUDIT_EXCLUDED_FIELDS = {
    'id', 'created_at', 'updated_at', 'issued_at', 'attempted_at',
}


def serialize_financial_instance(instance, *, exclude_fields=None):
    if instance is None:
        return None

    exclude = FINANCIAL_AUDIT_EXCLUDED_FIELDS | set(exclude_fields or [])
    snapshot = {}

    for field in instance._meta.concrete_fields:
        if field.name in exclude:
            continue

        value = getattr(instance, field.name)
        if field.is_relation:
            snapshot[field.name] = getattr(value, 'pk', None) if value is not None else None
        else:
            snapshot[field.name] = value

    return sanitize_audit_data(snapshot)


def build_financial_diff(before, after):
    before = before or {}
    after = after or {}
    changed_fields = {}

    for key in sorted(set(before.keys()) | set(after.keys())):
        if before.get(key) != after.get(key):
            changed_fields[key] = {
                'before': before.get(key),
                'after': after.get(key),
            }

    return changed_fields


def record_financial_audit(*, user, instance, request=None, action='FINANCIAL_CHANGE',
                           description=None, source='SYSTEM', before=None, after=None,
                           extra_data=None):
    before_snapshot = sanitize_audit_data(before or {})
    after_snapshot = sanitize_audit_data(after or {})
    changed_fields = build_financial_diff(before_snapshot, after_snapshot)
    audit_payload = {
        'before': before_snapshot,
        'after': after_snapshot,
        'changed_fields': changed_fields,
    }
    if extra_data:
        audit_payload.update(sanitize_audit_data(extra_data))

    return create_audit_log(
        user=user,
        action=action,
        description=description or f'Financial change on {instance.__class__.__name__}#{instance.pk}',
        content_object=instance,
        request=request,
        source=source,
        extra_data=audit_payload,
    )


class FinancialAuditMixin:
    financial_audit_source = 'SYSTEM'
    financial_audit_exclude_fields = set()

    def get_financial_audit_source(self):
        return self.financial_audit_source

    def get_financial_audit_exclude_fields(self):
        return set(self.financial_audit_exclude_fields)

    def _financial_snapshot(self, instance):
        return serialize_financial_instance(
            instance,
            exclude_fields=self.get_financial_audit_exclude_fields()
        )

    def audit_financial_change(self, *, instance, before=None, after=None, description=None, extra_data=None):
        return record_financial_audit(
            user=self.request.user,
            instance=instance,
            request=self.request,
            source=self.get_financial_audit_source(),
            before=before,
            after=after,
            description=description,
            extra_data=extra_data,
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        before = self._financial_snapshot(instance)
        super().perform_update(serializer)
        serializer.instance.refresh_from_db()
        self.audit_financial_change(
            instance=serializer.instance,
            before=before,
            after=self._financial_snapshot(serializer.instance),
            description=f'Updated financial record {serializer.instance.__class__.__name__}#{serializer.instance.pk}'
        )

    def perform_destroy(self, instance):
        before = self._financial_snapshot(instance)
        description = f'Deleted financial record {instance.__class__.__name__}#{instance.pk}'
        super().perform_destroy(instance)
        record_financial_audit(
            user=self.request.user,
            instance=instance,
            request=self.request,
            source=self.get_financial_audit_source(),
            before=before,
            after={},
            description=description,
        )


def audit_financial_action(*, source='SYSTEM', object_getter=None, description_builder=None, extra_data_builder=None):
    def decorator(func):
        @wraps(func)
        def wrapper(view, request, *args, **kwargs):
            target = object_getter(view, request, *args, **kwargs) if object_getter else view.get_object()
            before = serialize_financial_instance(
                target,
                exclude_fields=getattr(view, 'financial_audit_exclude_fields', set())
            )
            response = func(view, request, *args, **kwargs)

            if getattr(response, 'status_code', 500) >= 400:
                return response

            try:
                target.refresh_from_db()
                after = serialize_financial_instance(
                    target,
                    exclude_fields=getattr(view, 'financial_audit_exclude_fields', set())
                )
            except Exception:
                after = {}

            description = (
                description_builder(view, request, target, response, *args, **kwargs)
                if description_builder else
                f'Financial action on {target.__class__.__name__}#{target.pk}'
            )
            extra_data = (
                extra_data_builder(view, request, target, response, *args, **kwargs)
                if extra_data_builder else
                None
            )
            record_financial_audit(
                user=request.user,
                instance=target,
                request=request,
                source=source,
                before=before,
                after=after,
                description=description,
                extra_data=extra_data,
            )
            return response
        return wrapper
    return decorator
