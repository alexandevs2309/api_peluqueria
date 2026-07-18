from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('pos_api', '0022_add_discount_reason_and_increase_max_digits'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='points_earned',
            field=models.PositiveIntegerField(default=0, help_text='Puntos de lealtad ganados en esta venta'),
        ),
        migrations.AddField(
            model_name='sale',
            name='points_redeemed',
            field=models.PositiveIntegerField(default=0, help_text='Puntos de lealtad canjeados en esta venta'),
        ),
    ]
