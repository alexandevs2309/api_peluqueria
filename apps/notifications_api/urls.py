from django.urls import path
from . import views

urlpatterns = [
    path('notifications/', views.NotificationListCreateView.as_view(), name='notifications-list-create'),
    path('notifications/<int:pk>/', views.NotificationDetailView.as_view(), name='notifications-detail'),
    path('templates/', views.NotificationTemplateListView.as_view(), name='notification-templates-list'),
]
