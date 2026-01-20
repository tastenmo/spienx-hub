import os

from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from accounts.models import Organisation, UserProfile, PERMISSIONS

from git import Repo, InvalidGitRepositoryError, NoSuchPathError


class GitRepository(models.Model):
    """Base model representing a Git repository (bare repository)"""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='repositories'
    )
    
    # Local storage
    local_path = models.CharField(
        max_length=512,
        unique=True,
        help_text="Local file system path where the repository is stored"
    )
    is_bare = models.BooleanField(
        default=True,
        help_text="Whether this is a bare repository (no working directory)"
    )
    
    # Access control
    is_public = models.BooleanField(default=True)
    owner = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name='owned_repositories'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['organisation', 'name']]
        indexes = [
            models.Index(fields=['organisation', 'name']),
        ]

    def __str__(self):
        return f"{self.organisation.name}/{self.name}"
    
    @property
    def git_url(self):
        """Returns the Git clone URL for this repository"""
        domain = settings.GIT_DOMAIN
        return f"https://{domain}/git/{self.organisation.slug}/{self.name}.git"

    def effective_permission(self, user) -> str:
        """Compute highest permission (none/read/write/admin) for a given user on this repo."""
        from accounts.models import OrganisationMembership, TeamMembership  # local import to avoid cycles

        if not user or not getattr(user, 'is_authenticated', False):
            return 'none'
        if getattr(user, 'is_superuser', False):
            return 'admin'

        # Permission ranking helper
        rank = RepositoryAccessPolicy.PERMISSION_RANK

        def bump(current: str, candidate: str | None) -> str:
            if not candidate:
                return current
            return candidate if rank.get(candidate, 0) > rank.get(current, 0) else current

        best = 'none'

        # Public repos guarantee at least read
        if self.is_public:
            best = bump(best, 'read')

        # Membership role
        membership = OrganisationMembership.objects.filter(
            user=user,
            organisation=self.organisation,
            is_active=True,
        ).first()
        if membership:
            best = bump(best, membership.role)

        # Role-based policies
        if membership and membership.role:
            role_policies = RepositoryAccessPolicy.objects.filter(
                repository=self,
                role=membership.role,
            )
            for policy in role_policies:
                best = bump(best, policy.permission)

        # Team-based policies
        team_ids = TeamMembership.objects.filter(
            user=user,
            is_active=True,
            team__organisation=self.organisation,
            team__is_active=True,
        ).values_list('team_id', flat=True)
        if team_ids:
            team_policies = RepositoryAccessPolicy.objects.filter(
                repository=self,
                team_id__in=team_ids,
            )
            for policy in team_policies:
                best = bump(best, policy.permission)

        return best
    
    def get_handler(self) -> 'RepositoryHandler':
        """Get a RepositoryHandler for this repository"""
        from repositories.repo_handlers import RepositoryHandler
        return RepositoryHandler(self.local_path, is_bare=self.is_bare)
    
    def get_content_handler(self) -> 'RepositoryContentHandler':
        """Get a RepositoryContentHandler for browsing repository contents"""
        from repositories.repo_handlers import RepositoryContentHandler
        return RepositoryContentHandler(self.local_path)
    
    def get_refs_handler(self) -> 'RepositoryRefsHandler':
        """Get a RepositoryRefsHandler for accessing branches, tags, and commits"""
        from repositories.repo_handlers import RepositoryRefsHandler
        return RepositoryRefsHandler(self.local_path)
    
    def create_workdir(self, path: str, reference: str = "HEAD") -> Repo:
        """Create a working copy instance for this repository at the given path."""
        handler = self.get_handler()
        return handler.create_workdir(path, reference)
        

class GitMirrorRepository(GitRepository):
    """Model representing a mirrored Git repository from external sources"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('initializing', 'Initializing'),
        ('active', 'Active'),
        ('failed', 'Failed'),
        ('paused', 'Paused'),
    ]

    SOURCE_TYPE_CHOICES = [
        ('github', 'GitHub'),
        ('gitlab', 'GitLab'),
        ('gitea', 'Gitea'),
        ('bitbucket', 'Bitbucket'),
        ('custom', 'Custom Git Server'),
    ]

    # Source repository details
    source_url = models.URLField(
        help_text="Original repository URL (e.g., GitHub, GitLab)"
    )
    source_type = models.CharField(
        max_length=50,
        choices=SOURCE_TYPE_CHOICES,
        default='github'
    )
    
    # Mirror status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Sync information
    last_synced_at = models.DateTimeField(null=True, blank=True)
    sync_interval = models.IntegerField(
        default=3600,
        help_text="Sync interval in seconds (default: 1 hour)"
    )
    auto_sync = models.BooleanField(
        default=True,
        help_text="Automatically sync this mirror on schedule"
    )
    
    # Error tracking
    error_message = models.TextField(
        blank=True,
        help_text="Error details if status is failed"
    )
    consecutive_failures = models.IntegerField(
        default=0,
        help_text="Number of consecutive sync failures"
    )

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['source_url']),
            models.Index(fields=['auto_sync', 'last_synced_at']),
        ]

    def __str__(self):
        return f"{self.organisation.name}/{self.name} (mirror)"


class RepositoryAccessPolicy(models.Model):
    """Repository-level access policies for teams or roles."""

    PERMISSION_CHOICES = [
        ('none', 'None'),
        ('read', 'Read'),
        ('write', 'Write'),
        ('admin', 'Admin'),
    ]
    PERMISSION_RANK = {
        'none': 0,
        'read': 1,
        'write': 2,
        'admin': 3,
    }

    repository = models.ForeignKey(
        GitRepository,
        on_delete=models.CASCADE,
        related_name='access_policies'
    )
    team = models.ForeignKey(
        'accounts.Team',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='repository_policies'
    )
    role = models.CharField(
        max_length=20,
        choices=PERMISSION_CHOICES,
        null=True,
        blank=True,
        help_text="Organisation membership role this policy applies to",
    )
    permission = models.CharField(max_length=20, choices=PERMISSION_CHOICES, default='none')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['repository', 'team', 'role']
        constraints = [
            models.CheckConstraint(
                check=(
                    (models.Q(team__isnull=False) & models.Q(role__isnull=True)) |
                    (models.Q(team__isnull=True) & models.Q(role__isnull=False))
                ),
                name='repository_policy_exactly_one_subject',
            ),
        ]
        unique_together = [
            ['repository', 'team'],
            ['repository', 'role'],
        ]
        indexes = [
            models.Index(fields=['repository', 'team']),
            models.Index(fields=['repository', 'role']),
        ]

    def clean(self):
        team_set = self.team_id is not None
        role_set = bool(self.role)
        if team_set and role_set:
            raise ValidationError("Choose either team or role, not both.")
        if not team_set and not role_set:
            raise ValidationError("You must set either a team or a role.")

    def __str__(self):
        subject = self.team or self.role or "unknown"
        return f"Policy {subject} -> {self.repository} ({self.permission})"


class SyncTask(models.Model):
    """Model for tracking repository sync tasks"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    repository = models.ForeignKey(
        GitRepository,
        on_delete=models.CASCADE,
        related_name='sync_tasks'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    commits_synced = models.IntegerField(default=0)
    task_id = models.CharField(max_length=255, unique=True, blank=True, help_text="Celery task ID")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['repository', 'status']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Sync {self.repository.name} - {self.status}"
