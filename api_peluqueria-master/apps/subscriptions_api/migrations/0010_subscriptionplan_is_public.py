from django.db import migrations, models


def mark_legacy_non_public(apps, schema_editor):
    SubscriptionPlan = apps.get_model('subscriptions_api', 'SubscriptionPlan')
    SubscriptionPlan.objects.filter(name__in=['trial', 'free']).update(is_public=False)


def restore_public_default(apps, schema_editor):
    SubscriptionPlan = apps.get_model('subscriptions_api', 'SubscriptionPlan')
    SubscriptionPlan.objects.filter(name__in=['trial', 'free']).update(is_public=True)


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions_api', '0009_alter_subscriptionplan_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriptionplan',
            name='is_public',
            field=models.BooleanField(default=True, help_text='Visible y elegible en catalogo publico y onboarding'),
        ),
        migrations.RunPython(mark_legacy_non_public, restore_public_default),
    ]
