from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "last_build_at")
    list_filter = ("last_build_at",)
    search_fields = ("title",)
