from django.db import models
from django.contrib.auth.models import User
from guardian.shortcuts import assign_perm, remove_perm


# Standard permission codenames used with django-guardian
PERMISSIONS = {
    'read': 'view',
    'write': 'change',
    'admin': 'delete',  # Admin can delete/manage
}


class Organisation(models.Model):
    """Model representing an organization/workspace"""

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    logo_url = models.URLField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='owned_organisations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    def grant_permission(self, user, permission_level):
        """Grant or update user permission on this organisation."""
        # Remove all existing permissions first
        for perm in PERMISSIONS.values():
            remove_perm(f'accounts.{perm}_organisation', user, self)
        
        # Assign the appropriate permission
        if permission_level in PERMISSIONS:
            assign_perm(f'accounts.{PERMISSIONS[permission_level]}_organisation', user, self)

    def user_permission(self, user):
        """Get user's permission level on this organisation."""
        if user.has_perm('accounts.delete_organisation', self):
            return 'admin'
        elif user.has_perm('accounts.change_organisation', self):
            return 'write'
        elif user.has_perm('accounts.view_organisation', self):
            return 'read'
        return 'none'


class OrganisationMembership(models.Model):
    """Membership of a user in an organisation (permission managed via guardian)."""

    ROLE_CHOICES = [
        ('read', 'Read'),
        ('write', 'Write'),
        ('admin', 'Admin'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='org_memberships'
    )
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='read')
    title = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['user', 'organisation']]
        indexes = [
            models.Index(fields=['organisation', 'role']),
            models.Index(fields=['user', 'organisation', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.organisation.name} ({self.role})"

    def save(self, *args, **kwargs):
        """Sync role with guardian permissions on save."""
        super().save(*args, **kwargs)
        if self.is_active:
            self.organisation.grant_permission(self.user, self.role)
        else:
            # Remove all permissions if membership is inactive
            for perm in PERMISSIONS.values():
                remove_perm(f'accounts.{perm}_organisation', self.user, self.organisation)


class Team(models.Model):
    """Team within an organisation."""

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='teams'
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = [['organisation', 'slug']]
        indexes = [
            models.Index(fields=['organisation', 'slug']),
            models.Index(fields=['organisation', 'is_active']),
        ]

    def __str__(self):
        return f"{self.organisation.name}/{self.slug}"


class TeamMembership(models.Model):
    """Membership of a user in a team inside an organisation."""

    ROLE_CHOICES = [
        ('member', 'Member'),
        ('maintainer', 'Maintainer'),
    ]

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='team_memberships'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['team__name']
        unique_together = [['team', 'user']]
        indexes = [
            models.Index(fields=['team', 'user', 'is_active']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.team} ({self.role})"


class UserProfile(models.Model):
    """Extended user profile with organization and role information (legacy support)"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members'
    )
    bio = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organisation']),
            models.Index(fields=['user', 'organisation']),
        ]

    def __str__(self):
        org_name = self.organisation.name if self.organisation else "No Organisation"
        return f"{self.user.username} ({org_name})"


class OrganisationInvite(models.Model):
    """Model for managing organisation invitations"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]

    ROLE_CHOICES = [
        ('read', 'Read'),
        ('write', 'Write'),
        ('admin', 'Admin'),
    ]

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='invites'
    )
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='read')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_invites'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['organisation', 'email']]
        indexes = [
            models.Index(fields=['organisation', 'status']),
            models.Index(fields=['email', 'status']),
        ]

    def __str__(self):
        return f"{self.email} -> {self.organisation.name} ({self.status})"
