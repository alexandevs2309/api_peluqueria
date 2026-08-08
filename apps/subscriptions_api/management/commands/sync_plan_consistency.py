from django.core.management.base import BaseCommand

from apps.subscriptions_api.models import SubscriptionPlan
from apps.subscriptions_api.plan_consistency import (
    collect_plan_feature_keys,
    normalize_features_dict,
    sync_tenant_with_plan,
)
from apps.tenants_api.models import Tenant


class Command(BaseCommand):
    help = (
        "Normalize SubscriptionPlan features and safely audit/sync tenant snapshots. "
        "Runs in dry-run mode unless --apply is provided."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist changes. Without this flag the command only reports what would change.",
        )
        parser.add_argument(
            "--apply-feature-values",
            action="store_true",
            help="When syncing tenants, overwrite feature values to match the plan. Missing keys are always safe to fill.",
        )
        parser.add_argument(
            "--apply-limits",
            action="store_true",
            help="When syncing tenants, overwrite tenant max_employees/max_users to match the plan.",
        )
        parser.add_argument(
            "--tenant-id",
            type=int,
            help="Limit tenant sync to a single tenant id.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        apply_feature_values = options["apply_feature_values"]
        apply_limits = options["apply_limits"]
        tenant_id = options.get("tenant_id")

        self.stdout.write(
            self.style.WARNING(
                "Running in APPLY mode." if apply_changes else "Running in DRY-RUN mode."
            )
        )

        plans = list(SubscriptionPlan.objects.all().order_by("id"))
        if not plans:
            self.stdout.write(self.style.WARNING("No subscription plans found."))
            return

        all_feature_keys = collect_plan_feature_keys(plans)
        self.stdout.write(f"Detected feature keys: {', '.join(all_feature_keys) if all_feature_keys else '(none)'}")

        normalized_plans = 0
        plan_drifts = 0
        for plan in plans:
            normalized_features = normalize_features_dict(plan.features, all_feature_keys)
            if normalized_features == (plan.features or {}):
                continue

            plan_drifts += 1
            self.stdout.write(
                f"[PLAN] {plan.id} {plan.name}: normalize features keys "
                f"({len((plan.features or {}).keys())} -> {len(normalized_features.keys())})"
            )
            if apply_changes:
                plan.features = normalized_features
                plan.save(update_fields=["features", "updated_at"])
                normalized_plans += 1

        tenant_queryset = Tenant.objects.select_related("subscription_plan").order_by("id")
        if tenant_id:
            tenant_queryset = tenant_queryset.filter(id=tenant_id)

        tenant_updates = 0
        tenant_reports = 0
        tenant_errors = 0

        for tenant in tenant_queryset.iterator():
            try:
                result = sync_tenant_with_plan(
                    tenant,
                    all_feature_keys,
                    apply_feature_values=apply_feature_values,
                    apply_limits=apply_limits,
                )
                if not result.notes and not result.changed_fields:
                    continue

                tenant_reports += 1
                joined_notes = " | ".join(result.notes) if result.notes else "no_notes"
                self.stdout.write(
                    f"[TENANT] {result.tenant_id} {result.tenant_name} ({result.plan_name}) -> "
                    f"fields={result.changed_fields or ['none']} | {joined_notes}"
                )

                if apply_changes and result.changed_fields:
                    tenant.save(update_fields=[*result.changed_fields, "updated_at"])
                    tenant_updates += 1
            except Exception as exc:
                tenant_errors += 1
                self.stdout.write(
                    self.style.ERROR(f"[TENANT] {tenant.id} {tenant.name}: error during sync -> {exc}")
                )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Summary"))
        self.stdout.write(f"- Plans with feature drift detected: {plan_drifts}")
        self.stdout.write(f"- Plans normalized: {normalized_plans}")
        self.stdout.write(f"- Tenants with findings: {tenant_reports}")
        self.stdout.write(f"- Tenants updated: {tenant_updates}")
        self.stdout.write(f"- Tenant sync errors: {tenant_errors}")

        if not apply_changes:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run only. Re-run with --apply to persist. "
                    "Use --apply-feature-values and/or --apply-limits only after reviewing drift."
                )
            )
