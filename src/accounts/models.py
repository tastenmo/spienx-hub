from django.db import models
from django.contrib.auth.models import User


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


class UserProfile(models.Model):
    """Extended user profile with organization and role information"""

    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('developer', 'Developer'),
        ('viewer', 'Viewer'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='developer')
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
    role = models.CharField(max_length=20, choices=UserProfile.ROLE_CHOICES, default='developer')
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
