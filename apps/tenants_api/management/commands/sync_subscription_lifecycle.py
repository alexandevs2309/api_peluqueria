from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.tenants_api.models import Tenant
from apps.tenants_api.subscription_lifecycle import sync_subscription_state


class Command(BaseCommand):
    help = (
        "Audit and optionally sync tenant subscription lifecycle states. "
        "Runs in dry-run mode unless --apply is provided."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist lifecycle changes. Without this flag the command only reports drift.",
        )
        parser.add_argument(
            "--tenant-id",
            type=int,
            help="Restrict the sync to a single tenant id.",
        )
        parser.add_argument(
            "--include-deleted",
            action="store_true",
            help="Include logically deleted tenants in the audit/sync output.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        tenant_id = options.get("tenant_id")
        include_deleted = options["include_deleted"]
        now = timezone.now()

        self.stdout.write(
            self.style.WARNING(
                "Running in APPLY mode." if apply_changes else "Running in DRY-RUN mode."
            )
        )

        queryset = Tenant.objects.select_related("subscription_plan").order_by("id")
        if tenant_id:
            queryset = queryset.filter(id=tenant_id)
        if not include_deleted:
            queryset = queryset.filter(deleted_at__isnull=True)

        reviewed = 0
        changed = 0
        unchanged = 0
        skipped_deleted = 0

        for tenant in queryset.iterator():
            if tenant.deleted_at is not None and not include_deleted:
                skipped_deleted += 1
                continue

            reviewed += 1
            before_status = tenant.subscription_status
            before_active = tenant.is_active
            before_access_until = tenant.access_until
            before_trial_end_date = tenant.trial_end_date

            result = sync_subscription_state(tenant, now=now, save=apply_changes)
            if result.changed:
                changed += 1
                self.stdout.write("")
                self.stdout.write(
                    f"[TENANT] {tenant.id} {tenant.name}"
                )
                self.stdout.write(
                    "  "
                    f"Before: status={before_status}, is_active={before_active}, "
                    f"access_until={before_access_until}, trial_end_date={before_trial_end_date}"
                )
                self.stdout.write(
                    "  "
                    f"After: status={tenant.subscription_status}, is_active={tenant.is_active}, "
                    f"access_until={tenant.access_until}, trial_end_date={tenant.trial_end_date}"
                )
                self.stdout.write(
                    "  " + f"Reason: {'; '.join(result.reasons)}"
                )
            else:
                unchanged += 1
                self.stdout.write(f"[OK] {tenant.id} {tenant.name}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Summary"))
        self.stdout.write(f"- Tenants reviewed: {reviewed}")
        self.stdout.write(f"- Tenants changed: {changed}")
        self.stdout.write(f"- Tenants unchanged: {unchanged}")
        self.stdout.write(f"- Deleted tenants skipped: {skipped_deleted}")

        if not apply_changes:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run only. Re-run with --apply to persist lifecycle changes."
                )
            )
