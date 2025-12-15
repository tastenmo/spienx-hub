from django.contrib import admin
from accounts.models import Organisation, UserProfile, OrganisationInvite


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Organization Info', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Details', {
            'fields': ('logo_url', 'website', 'created_by', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'organisation', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'organisation', 'created_at']
    search_fields = ['user__username', 'user__email', 'organisation__name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user', 'organisation')
        }),
        ('Profile', {
            'fields': ('role', 'bio', 'avatar_url', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OrganisationInvite)
class OrganisationInviteAdmin(admin.ModelAdmin):
    list_display = ['email', 'organisation', 'role', 'status', 'invited_by', 'created_at']
    list_filter = ['status', 'role', 'organisation', 'created_at']
    search_fields = ['email', 'organisation__name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Invite Details', {
            'fields': ('organisation', 'email', 'role', 'invited_by')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
