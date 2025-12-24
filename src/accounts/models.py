from django.db import models
from django.contrib.auth.models import User


# Shared permission levels used across organisations and repositories
PERMISSION_CHOICES = [
    ('none', 'None'),
    ('read', 'Read'),
    ('write', 'Write'),
    ('admin', 'Admin'),
]


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


class OrganisationMembership(models.Model):
    """Membership of a user in an organisation with a permission role."""

    ROLE_CHOICES = PERMISSION_CHOICES

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
    """Extended user profile with organization and role information"""

    ROLE_CHOICES = PERMISSION_CHOICES  # Kept for backward compatibility; prefer OrganisationMembership

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='read')
    bio = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organisation', 'role']),
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

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='invites'
    )
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=PERMISSION_CHOICES, default='read')
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
