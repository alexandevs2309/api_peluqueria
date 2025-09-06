from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import models
from .models import Product, StockMovement
from django.core.mail import send_mail
from django.conf import settings

@receiver(post_save, sender=StockMovement)
def check_low_stock_after_movement(sender, instance, created, **kwargs):
    """Verificar stock bajo después de un movimiento de inventario"""
    if created and instance.quantity < 0:  # Solo para salidas de stock
        product = instance.product
        
        if product.is_below_min_stock:
            # Crear alerta de stock bajo
            create_low_stock_alert(product)

@receiver(pre_save, sender=Product)
def check_low_stock_on_update(sender, instance, **kwargs):
    """Verificar stock bajo al actualizar un producto"""
    if instance.pk:  # Solo para actualizaciones, no creaciones
        try:
            old_product = Product.objects.get(pk=instance.pk)
            # Si el stock cambió y ahora está bajo
            if (old_product.stock != instance.stock and 
                instance.is_below_min_stock and 
                not old_product.is_below_min_stock):
                create_low_stock_alert(instance)
        except Product.DoesNotExist:
            pass

def create_low_stock_alert(product):
    """Crear alerta de stock bajo"""
    # Aquí puedes implementar diferentes tipos de alertas:
    
    # 1. Log en consola (para desarrollo)
    print(f"⚠️ ALERTA: Stock bajo para {product.name}")
    print(f"   Stock actual: {product.stock}")
    print(f"   Stock mínimo: {product.min_stock}")
    
    # 2. Email a administradores (si está configurado)
    if hasattr(settings, 'ADMIN_EMAIL') and settings.ADMIN_EMAIL:
        try:
            send_mail(
                subject=f'Alerta de Stock Bajo - {product.name}',
                message=f'''
                El producto {product.name} (SKU: {product.sku}) tiene stock bajo.
                
                Stock actual: {product.stock}
                Stock mínimo: {product.min_stock}
                
                Por favor, reabastecer lo antes posible.
                ''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=True
            )
        except Exception as e:
            print(f"Error enviando email de alerta: {e}")
    
    # 3. Crear notificación en base de datos (opcional)
    create_notification_record(product)

def create_notification_record(product):
    """Crear registro de notificación en base de datos"""
    try:
        from apps.audit_api.models import AuditLog
        from django.contrib.contenttypes.models import ContentType
        
        AuditLog.objects.create(
            user=None,  # Sistema
            action='LOW_STOCK_ALERT',
            description=f'Stock bajo para {product.name}. Stock: {product.stock}, Mínimo: {product.min_stock}',
            content_type=ContentType.objects.get_for_model(product),
            object_id=product.id,
            source='SYSTEM',
            extra_data={
                'product_name': product.name,
                'current_stock': product.stock,
                'min_stock': product.min_stock,
                'sku': product.sku
            }
        )
    except Exception as e:
        print(f"Error creando registro de notificación: {e}")

# Función para obtener productos con stock bajo
def get_low_stock_products():
    """Obtener todos los productos con stock bajo"""
    return Product.objects.filter(
        stock__lte=models.F('min_stock'),
        is_active=True
    )

# Función para generar reporte de stock bajo
def generate_low_stock_report():
    """Generar reporte de productos con stock bajo"""
    low_stock_products = get_low_stock_products()
    
    if not low_stock_products.exists():
        return "✅ Todos los productos tienen stock suficiente"
    
    report = "⚠️ PRODUCTOS CON STOCK BAJO:\n\n"
    for product in low_stock_products:
        report += f"• {product.name} (SKU: {product.sku})\n"
        report += f"  Stock actual: {product.stock}\n"
        report += f"  Stock mínimo: {product.min_stock}\n"
        report += f"  Diferencia: {product.min_stock - product.stock}\n\n"
    
    return report