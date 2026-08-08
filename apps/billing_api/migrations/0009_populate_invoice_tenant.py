from django.db import migrations

def populate_tenant(apps, schema_editor):
    Invoice = apps.get_model('billing_api', 'Invoice')
    for invoice in Invoice.objects.filter(tenant__isnull=True):
        if invoice.user and invoice.user.tenant:
            invoice.tenant = invoice.user.tenant
            invoice.save(update_fields=['tenant'])

class Migration(migrations.Migration):

    dependencies = [
        ('billing_api', '0008_rename_billing_api_paypal_event_id_idx_billing_api_paypal__bd2fbf_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_tenant, reverse_code=migrations.RunPython.noop),
    ]
