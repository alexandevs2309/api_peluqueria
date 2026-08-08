from django.urls import path
from . import views
from .sse import notification_sse

urlpatterns = [
    path('', views.NotificationListCreateView.as_view(), name='notifications-list-create'),
    path('<int:pk>/', views.NotificationDetailView.as_view(), name='notifications-detail'),
    path('templates/', views.NotificationTemplateListView.as_view(), name='notification-templates-list'),
    path('preferences/', views.NotificationPreferenceView.as_view(), name='notification-preferences'),
    path('stats/', views.NotificationStatsView.as_view(), name='notification-stats'),
    path('test/', views.SendTestNotificationView.as_view(), name='send-test-notification'),
    path('mark-all-read/', views.MarkAllReadView.as_view(), name='mark-all-read'),
    path('stream/', notification_sse, name='notification-sse'),
]
