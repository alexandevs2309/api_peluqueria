from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from apps.core.tenant_permissions import tenant_permission

@api_view(['GET'])
@permission_classes([tenant_permission('inventory_api.view_product')])
def categories_list(request):
    """Lista de categorías de productos"""
    return Response([
        {'id': 1, 'name': 'Productos de Cabello', 'count': 0},
        {'id': 2, 'name': 'Productos de Barba', 'count': 0},
        {'id': 3, 'name': 'Herramientas', 'count': 0},
        {'id': 4, 'name': 'Accesorios', 'count': 0}
    ])

@api_view(['GET'])
@permission_classes([tenant_permission('inventory_api.view_product')])
def low_stock_products(request):
    """Productos con stock bajo"""
    from .models import Product
    from .serializers import ProductSerializer
    from django.db.models import F
    
    products = Product.objects.filter(
        stock__lte=F('min_stock'),
        is_active=True
    )
    
    if request.user.tenant:
        products = products.filter(tenant=request.user.tenant)
    
    serializer = ProductSerializer(products, many=True)
    return Response({
        'count': products.count(),
        'products': serializer.data
    })
