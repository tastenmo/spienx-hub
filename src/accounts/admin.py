from django.contrib import admin
from accounts.models import (
    Organisation,
    UserProfile,
    OrganisationInvite,
    OrganisationMembership,
    Team,
    TeamMembership,
)


class OrganisationMembershipInline(admin.TabularInline):
    model = OrganisationMembership
    extra = 1
    fields = ('user', 'role', 'title', 'is_active')
    autocomplete_fields = ('user',)
    show_change_link = True
    verbose_name = "Member"
    verbose_name_plural = "Members"


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 1
    fields = ('user', 'role', 'is_active')
    autocomplete_fields = ('user',)
    show_change_link = True
    verbose_name = "Team member"
    verbose_name_plural = "Team members"


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    inlines = [OrganisationMembershipInline]
    
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
    list_display = ['user', 'organisation', 'is_active', 'created_at']
    list_filter = ['is_active', 'organisation', 'created_at']
    search_fields = ['user__username', 'user__email', 'organisation__name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user', 'organisation')
        }),
        ('Profile', {
            'fields': ('bio', 'avatar_url', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OrganisationMembership)
class OrganisationMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'organisation', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'organisation', 'created_at']
    search_fields = ['user__username', 'user__email', 'organisation__name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    fieldsets = (
        ('Membership', {
            'fields': ('user', 'organisation', 'role', 'title', 'notes', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'organisation', 'is_active', 'created_at']
    list_filter = ['organisation', 'is_active', 'created_at']
    search_fields = ['name', 'slug', 'organisation__name']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']
    inlines = [TeamMembershipInline]

    fieldsets = (
        ('Team', {
            'fields': ('organisation', 'name', 'slug', 'description', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'team', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'team__organisation', 'team', 'created_at']
    search_fields = ['user__username', 'user__email', 'team__name', 'team__organisation__name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    fieldsets = (
        ('Team Membership', {
            'fields': ('team', 'user', 'role', 'is_active')
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
