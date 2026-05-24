from django.db import migrations


def update_supported_languages(apps, schema_editor):
    SystemSettings = apps.get_model('settings_api', 'SystemSettings')
    try:
        settings = SystemSettings.objects.get(pk=1)
        current = settings.supported_languages
        if isinstance(current, list) and current == ['es', 'en']:
            settings.supported_languages = ['es', 'en', 'fr', 'pt', 'de']
            settings.save()
    except SystemSettings.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('settings_api', '0008_readd_barbershopsettings'),
    ]

    operations = [
        migrations.RunPython(update_supported_languages, reverse_code=migrations.RunPython.noop),
    ]
