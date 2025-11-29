from django.urls import path
from . import views

urlpatterns = [
    path('notifications/', views.NotificationListCreateView.as_view(), name='notifications-list-create'),
    path('notifications/<int:pk>/', views.NotificationDetailView.as_view(), name='notifications-detail'),
    path('templates/', views.NotificationTemplateListView.as_view(), name='notification-templates-list'),
    
    # Nuevos endpoints
    path('preferences/', views.NotificationPreferenceView.as_view(), name='notification-preferences'),
    path('stats/', views.NotificationStatsView.as_view(), name='notification-stats'),
    path('test/', views.SendTestNotificationView.as_view(), name='send-test-notification'),
]
