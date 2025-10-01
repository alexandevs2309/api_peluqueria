from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model

User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_for_employee(request):
    """Usuarios disponibles para ser empleados"""
    user = request.user
    if user.tenant:
        users = User.objects.filter(tenant=user.tenant)
    else:
        users = User.objects.none()
    
    return Response([{
        'id': user.id,
        'email': user.email,
        'full_name': user.full_name,
        'tenant_id': user.tenant_id,
        'roles': [{'id': role.id, 'name': role.name} for role in user.roles.all()]
    } for user in users])

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def products_low_stock(request):
    """Productos con stock bajo"""
    from apps.inventory_api.models import Product
    from apps.inventory_api.serializers import ProductSerializer
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