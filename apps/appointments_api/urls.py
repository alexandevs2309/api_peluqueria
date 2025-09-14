from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AppointmentViewSet, test_appointment

router = DefaultRouter()
router.register(r'appointments', AppointmentViewSet, basename='appointment')

urlpatterns = [
    path('', include(router.urls)),
    path('test/', test_appointment, name='test-appointment'),
]