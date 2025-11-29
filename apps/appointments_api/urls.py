from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import AppointmentViewSet

router = DefaultRouter()
router.register(r'appointments', AppointmentViewSet, basename='appointment')

urlpatterns = [
    path('', include(router.urls)),
    
    # Nuevos endpoints para calendario
    path('calendar-events/', views.calendar_events, name='calendar-events'),
    path('<int:pk>/reschedule/', views.reschedule_appointment, name='reschedule-appointment'),
    path('stylist/<int:stylist_id>/schedule/', views.stylist_schedule, name='stylist-schedule'),
]