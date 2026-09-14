# Generated for P0 inventory fixes

from django.db import migrations, models


def clean_existing_data(apps, schema_editor):
    Product = apps.get_model('inventory_api', 'Product')
    # Fix negative stock/min_stock before adding CheckConstraint
    Product.objects.filter(stock__lt=0).update(stock=0)
    Product.objects.filter(min_stock__lt=0).update(min_stock=0)
    # Fix empty barcode "" -> None to prevent unique violation
    Product.objects.filter(barcode='').update(barcode=None)
    Product.objects.filter(barcode__regex=r'^\s*$').update(barcode=None)


class Migration(migrations.Migration):

    dependencies = [
        ('inventory_api', '0006_remove_product_unique_sku_per_tenant_and_more'),
    ]

    operations = [
        migrations.RunPython(clean_existing_data, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.CheckConstraint(check=models.Q(('stock__gte', 0)), name='stock_non_negative'),
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.CheckConstraint(check=models.Q(('min_stock__gte', 0)), name='min_stock_non_negative'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['tenant', 'is_active', 'stock', 'min_stock'], name='inv_prod_tenant_stock_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['tenant', 'barcode'], name='inv_prod_tenant_barcode_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['tenant', 'category'], name='inv_prod_tenant_cat_idx'),
        ),
    ]
