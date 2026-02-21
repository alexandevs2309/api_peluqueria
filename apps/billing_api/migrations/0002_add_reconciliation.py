# Generated migration for reconciliation models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing_api', '0001_initial'),  # Adjust to your last migration
    ]

    operations = [
        # Add stripe_payment_intent_id to Invoice
        migrations.AddField(
            model_name='invoice',
            name='stripe_payment_intent_id',
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        
        # Create ProcessedStripeEvent model
        migrations.CreateModel(
            name='ProcessedStripeEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stripe_event_id', models.CharField(db_index=True, max_length=255, unique=True)),
                ('event_type', models.CharField(db_index=True, max_length=100)),
                ('processed_at', models.DateTimeField(auto_now_add=True)),
                ('payload', models.JSONField()),
            ],
            options={
                'ordering': ['-processed_at'],
            },
        ),
        
        # Create ReconciliationLog model
        migrations.CreateModel(
            name='ReconciliationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('running', 'Running'), ('completed', 'Completed'), ('failed', 'Failed')], default='running', max_length=20)),
                ('stripe_payments_checked', models.IntegerField(default=0)),
                ('db_invoices_checked', models.IntegerField(default=0)),
                ('discrepancies_found', models.IntegerField(default=0)),
                ('missing_in_db', models.JSONField(default=list)),
                ('missing_in_stripe', models.JSONField(default=list)),
                ('duplicates', models.JSONField(default=list)),
                ('error_message', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['-started_at'],
            },
        ),
        
        # Create ReconciliationAlert model
        migrations.CreateModel(
            name='ReconciliationAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('severity', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], max_length=20)),
                ('alert_type', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('details', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('resolved', models.BooleanField(default=False)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('resolved_by', models.CharField(blank=True, max_length=255)),
                ('reconciliation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='billing_api.reconciliationlog')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        
        # Add indexes
        migrations.AddIndex(
            model_name='processedevent',
            index=models.Index(fields=['stripe_event_id'], name='billing_api_stripe_idx'),
        ),
        migrations.AddIndex(
            model_name='processedevent',
            index=models.Index(fields=['event_type', 'processed_at'], name='billing_api_event_type_idx'),
        ),
        migrations.AddIndex(
            model_name='reconciliationlog',
            index=models.Index(fields=['status', 'started_at'], name='billing_api_recon_status_idx'),
        ),
        migrations.AddIndex(
            model_name='reconciliationalert',
            index=models.Index(fields=['severity', 'resolved'], name='billing_api_alert_severity_idx'),
        ),
        migrations.AddIndex(
            model_name='reconciliationalert',
            index=models.Index(fields=['created_at'], name='billing_api_alert_created_idx'),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['stripe_payment_intent_id'], name='billing_api_stripe_payment_idx'),
        ),
    ]
