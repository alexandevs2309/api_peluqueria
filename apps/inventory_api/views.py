from rest_framework import viewsets, permissions
from apps.audit_api.mixins import AuditLoggingMixin
from apps.roles_api.permissions import role_permission_for
from .models import Product, Supplier, StockMovement
from .serializers import ProductSerializer, SupplierSerializer, StockMovementSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action, api_view
from django.db.models import Q
from rest_framework.response import Response
from django.db.models import F
from rest_framework import status


class ProductViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Product.objects.filter(tenant=self.request.user.tenant)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Obtener productos con stock bajo"""
        products = Product.objects.filter(
            stock__lte=F('min_stock'),
            is_active=True
        )
        serializer = ProductSerializer(products, many=True)
        return Response({
            'count': products.count(),
            'products': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        """Ajustar stock de un producto"""
        product = self.get_object()
        quantity = request.data.get('quantity', 0)
        reason = request.data.get('reason', 'Ajuste manual')
        
        if not isinstance(quantity, (int, float)):
            return Response(
                {'error': 'La cantidad debe ser un número'}, 
                status=400
            )
        
        # Crear movimiento de stock
        StockMovement.objects.create(
            product=product,
            quantity=quantity,
            reason=reason
        )
        
        # Actualizar stock
        product.stock += quantity
        product.save()
        
        return Response({
            'detail': f'Stock ajustado. Nuevo stock: {product.stock}',
            'new_stock': product.stock
        })
    
    @action(detail=False, methods=['get'])
    def stock_report(self, request):
        """Reporte general de inventario"""
        from django.db.models import Sum, Count
        
        total_products = Product.objects.filter(is_active=True).count()
        low_stock_count = Product.objects.filter(
            stock__lte=F('min_stock'),
            is_active=True
        ).count()
        
        total_value = Product.objects.filter(is_active=True).aggregate(
            total=Sum(F('stock') * F('price'))
        )['total'] or 0
        
        return Response({
            'total_products': total_products,
            'low_stock_count': low_stock_count,
            'total_inventory_value': float(total_value),
            'low_stock_percentage': (low_stock_count / total_products * 100) if total_products > 0 else 0
        })
    
    @action(detail=False, methods=['get'])
    def search_by_barcode(self, request):
        """Buscar producto por código de barras"""
        barcode = request.query_params.get('barcode')
        if not barcode:
            return Response({'error': 'Código de barras requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            product = Product.objects.get(
                barcode=barcode,
                tenant=request.user.tenant,
                is_active=True
            )
            serializer = ProductSerializer(product)
            return Response(serializer.data)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Producto no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )

@api_view(['GET'])
def low_stock_alerts(request):
    """API endpoint para alertas de stock bajo"""
    products = Product.objects.filter(
        stock__lte=F('min_stock'),
        is_active=True
    )
    data = ProductSerializer(products, many=True).data
    return Response({
        'count': products.count(),
        'products': data
    })


class SupplierViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Supplier.objects.filter(tenant=self.request.user.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.all()
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated]
