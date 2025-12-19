from django.contrib import admin
from repositories.models import GitRepository, GitMirrorRepository, SyncTask


@admin.register(GitRepository)
class GitRepositoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'organisation', 'is_bare', 'is_public', 'owner', 'created_at']
    list_filter = ['is_bare', 'is_public', 'organisation', 'created_at']
    search_fields = ['name', 'organisation__name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'local_path', 'git_url']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Repository Information', {
            'fields': ('name', 'description', 'organisation', 'owner')
        }),
        ('Storage', {
            'fields': ('local_path', 'is_bare')
        }),
        ('Access Control', {
            'fields': ('is_public',)
        }),
        ('Git URL', {
            'fields': ('git_url',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(GitMirrorRepository)
class GitMirrorRepositoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'organisation', 'source_type', 'status', 'auto_sync', 'last_synced_at', 'created_at']
    list_filter = ['status', 'source_type', 'auto_sync', 'organisation', 'created_at']
    search_fields = ['name', 'source_url', 'organisation__name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'local_path', 'git_url', 'last_synced_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Repository Information', {
            'fields': ('name', 'description', 'organisation', 'owner')
        }),
        ('Mirror Source', {
            'fields': ('source_url', 'source_type')
        }),
        ('Storage', {
            'fields': ('local_path', 'is_bare')
        }),
        ('Sync Configuration', {
            'fields': ('auto_sync', 'sync_interval')
        }),
        ('Status', {
            'fields': ('status', 'error_message', 'consecutive_failures', 'last_synced_at')
        }),
        ('Git URL', {
            'fields': ('git_url',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SyncTask)
class SyncTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'repository', 'status', 'commits_synced', 'started_at', 'completed_at', 'created_at']
    list_filter = ['status', 'repository', 'created_at']
    search_fields = ['repository__name', 'task_id', 'error_message']
    readonly_fields = ['created_at', 'started_at', 'completed_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Task Information', {
            'fields': ('repository', 'status', 'task_id')
        }),
        ('Progress', {
            'fields': ('commits_synced', 'started_at', 'completed_at')
        }),
        ('Error', {
            'fields': ('error_message',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
