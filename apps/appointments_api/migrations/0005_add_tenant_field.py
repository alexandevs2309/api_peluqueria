# Generated migration for adding tenant field to Appointment

from django.db import migrations, models
import django.db.models.deletion


def backfill_tenant(apps, schema_editor):
    """
    Backfill tenant desde client.tenant para appointments existentes.
    Seguro: Solo actualiza si client tiene tenant.
    """
    Appointment = apps.get_model('appointments_api', 'Appointment')
    
    updated = 0
    for appointment in Appointment.objects.select_related('client').all():
        if appointment.client and hasattr(appointment.client, 'tenant_id') and appointment.client.tenant_id:
            appointment.tenant_id = appointment.client.tenant_id
            appointment.save(update_fields=['tenant'])
            updated += 1
    
    print(f"✅ Backfilled tenant for {updated} appointments")


class Migration(migrations.Migration):

    dependencies = [
        ('appointments_api', '0004_initial'),  # Ajustar según última migración
        ('tenants_api', '0001_initial'),
    ]

    operations = [
        # Paso 1: Agregar campo tenant como nullable
        migrations.AddField(
            model_name='appointment',
            name='tenant',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='appointments',
                to='tenants_api.tenant'
            ),
        ),
        
        # Paso 2: Backfill datos
        migrations.RunPython(backfill_tenant, reverse_code=migrations.RunPython.noop),
        
        # Paso 3: Hacer campo NOT NULL (después de backfill)
        migrations.AlterField(
            model_name='appointment',
            name='tenant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='appointments',
                to='tenants_api.tenant'
            ),
        ),
        
        # Paso 4: Agregar índice para performance
        migrations.AddIndex(
            model_name='appointment',
            index=models.Index(fields=['tenant', 'date_time'], name='appt_tenant_dt_idx'),
        ),
    ]
