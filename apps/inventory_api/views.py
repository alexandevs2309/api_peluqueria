from rest_framework import viewsets, permissions
from .models import Product, Supplier, StockMovement
from .serializers import ProductSerializer, SupplierSerializer, StockMovementSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.db.models import F


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

@api_view(['GET'])
   
def low_stock_alerts(request):
        products = Product.objects.filter(stock__lte=F('min_stock'))
        products = Product.objects.filter(stock__lte=F('min_stock'))
        data = ProductSerializer(products, many=True).data
        return Response(data)


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]

class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.all()
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated]
