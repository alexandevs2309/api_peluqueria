from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from apps.core.tenant_permissions import tenant_permission
from .models import ProductCategory
from .serializers import ProductCategorySerializer


@api_view(['GET', 'POST'])
@permission_classes([tenant_permission('inventory_api.view_product')])
def categories_list(request):
    tenant = getattr(request, 'tenant', None) or getattr(request.user, 'tenant', None)

    if request.method == 'GET':
        categories = ProductCategory.objects.filter(tenant=tenant, is_active=True)
        serializer = ProductCategorySerializer(categories, many=True)
        return Response(serializer.data)

    # POST - crear categoría
    serializer = ProductCategorySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(tenant=tenant)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'DELETE'])
@permission_classes([tenant_permission('inventory_api.view_product')])
def category_detail(request, pk):
    tenant = getattr(request, 'tenant', None) or getattr(request.user, 'tenant', None)
    try:
        category = ProductCategory.objects.get(pk=pk, tenant=tenant)
    except ProductCategory.DoesNotExist:
        return Response({'error': 'Categoría no encontrada'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        serializer = ProductCategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    category.is_active = False
    category.save()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([tenant_permission('inventory_api.view_product')])
def low_stock_products(request):
    from .models import Product
    from .serializers import ProductSerializer
    from django.db.models import F

    tenant = getattr(request, 'tenant', None) or getattr(request.user, 'tenant', None)
    products = Product.objects.filter(
        stock__lte=F('min_stock'),
        is_active=True,
        tenant=tenant
    )
    serializer = ProductSerializer(products, many=True, context={'request': request})
    return Response({'count': products.count(), 'products': serializer.data})
