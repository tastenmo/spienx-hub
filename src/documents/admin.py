from django.contrib import admin
from .models import Document, Build, Page, Section, ContentBlock


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "source")
    search_fields = ("title",)


@admin.register(Build)
class BuildAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "reference", "language", "version", "last_build_at")
    list_filter = ("last_build_at", "language")
    search_fields = ("document__title", "reference", "commit_hash", "version")


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "path", "build")
    search_fields = ("title", "path")
    list_filter = ("build",)


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "page", "sphinx_id", "hash")
    search_fields = ("title", "sphinx_id", "hash")
    list_filter = ("page",)


@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display = ("content_hash",)
    search_fields = ("content_hash",)

