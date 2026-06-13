from django.contrib import admin
from .models import Tutorial


@admin.register(Tutorial)
class TutorialAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'duration', 'order', 'is_published')
    list_filter = ('module', 'is_published')
    search_fields = ('title', 'description')
    list_editable = ('order', 'is_published')
