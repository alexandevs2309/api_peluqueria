from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from .models import Employee

class EarningViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Obtener todas las ganancias"""
        return Response([])
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Estadísticas de ganancias"""
        return Response({
            'total_earnings': 0,
            'monthly_earnings': 0,
            'top_employees': []
        })

class FortnightSummaryViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Obtener resúmenes quincenales"""
        return Response([])