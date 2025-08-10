from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet, WorkScheduleViewSet

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet , basename='employee')
router.register(r'schedules', WorkScheduleViewSet , basename='work_schedule')

urlpatterns = [
    path('', include(router.urls)),
]