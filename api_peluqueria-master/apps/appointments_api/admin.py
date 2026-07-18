from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'client', 'stylist', 'status', 'date_time', 'tenant']
    list_filter = ['status', 'tenant', 'branch']
    search_fields = ['client__full_name', 'stylist__email']
    raw_id_fields = ['client', 'stylist', 'service', 'branch']
