from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet, WorkScheduleViewSet
from .earnings_views import EarningViewSet, FortnightSummaryViewSet

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet , basename='employee')
router.register(r'schedules', WorkScheduleViewSet , basename='work_schedule')
router.register(r'earnings', EarningViewSet, basename='earning')
router.register(r'fortnight-summaries', FortnightSummaryViewSet, basename='fortnight-summary')

urlpatterns = [
    path('', include(router.urls)),
]