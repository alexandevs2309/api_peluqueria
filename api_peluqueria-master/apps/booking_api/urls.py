from django.urls import path
from . import views

urlpatterns = [
    path('<slug:subdomain>/info/', views.tenant_info, name='booking-tenant-info'),
    path('<slug:subdomain>/services/', views.public_services, name='booking-services'),
    path('<slug:subdomain>/stylists/', views.public_stylists, name='booking-stylists'),
    path('<slug:subdomain>/availability/', views.availability, name='booking-availability'),
    path('<slug:subdomain>/book/', views.book_appointment, name='booking-book'),
]
