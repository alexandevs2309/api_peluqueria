from django.urls import path , include
from rest_framework.routers import DefaultRouter
from .views import ServiceViewSet, ServiceCategoryViewSet


router = DefaultRouter()
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'service-categories', ServiceCategoryViewSet, basename='service-category')
urlpatterns = [
    path('', include(router.urls)),
]