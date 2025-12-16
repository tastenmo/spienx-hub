from django.contrib import admin
from repositories.models import GitRepository, GitBranch, GitCommit, SyncTask


@admin.register(GitRepository)
class GitRepositoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'organisation', 'status', 'source_type', 'is_mirror', 'last_synced_at', 'created_at']
    list_filter = ['status', 'source_type', 'is_mirror', 'is_public', 'organisation', 'created_at']
    search_fields = ['name', 'source_url', 'organisation__name']
    readonly_fields = ['created_at', 'updated_at', 'last_commit_hash']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Repository Information', {
            'fields': ('name', 'description', 'organisation', 'owner')
        }),
        ('Source', {
            'fields': ('source_url', 'source_type', 'local_path')
        }),
        ('Configuration', {
            'fields': ('is_mirror', 'is_bare', 'default_branch', 'is_public')
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Git Metadata', {
            'fields': ('last_synced_at', 'last_commit_hash', 'total_commits')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(GitBranch)
class GitBranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'repository', 'commit_hash', 'is_default', 'last_updated']
    list_filter = ['is_default', 'repository', 'last_updated']
    search_fields = ['name', 'repository__name', 'commit_hash']
    readonly_fields = ['last_updated']
    ordering = ['repository', 'name']


@admin.register(GitCommit)
class GitCommitAdmin(admin.ModelAdmin):
    list_display = ['commit_hash', 'repository', 'author_name', 'committed_at', 'synced_at']
    list_filter = ['repository', 'committed_at', 'synced_at']
    search_fields = ['commit_hash', 'author_name', 'author_email', 'message']
    readonly_fields = ['synced_at']
    ordering = ['-committed_at']


@admin.register(SyncTask)
class SyncTaskAdmin(admin.ModelAdmin):
    list_display = ['repository', 'status', 'commits_synced', 'started_at', 'completed_at', 'created_at']
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
