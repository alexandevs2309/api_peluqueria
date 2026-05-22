from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory_api', '0003_productcategory_alter_product_category_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='image',
            field=models.ImageField(blank=True, max_length=500, null=True, upload_to='products/'),
        ),
    ]
