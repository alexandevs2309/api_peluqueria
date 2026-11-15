from django.contrib import admin
from .models import Tutorial


@admin.register(Tutorial)
class TutorialAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'content_type', 'duration', 'order', 'is_published')
    list_filter = ('module', 'content_type', 'is_published')
    search_fields = ('title', 'description', 'body')
    list_editable = ('order', 'is_published')
    fields = ('module', 'content_type', 'title', 'description', 'body', 'video_url', 'thumbnail_url', 'duration', 'order', 'is_published')
