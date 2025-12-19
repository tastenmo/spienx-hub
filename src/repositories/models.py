from django.db import models
from django.conf import settings
from accounts.models import Organisation, UserProfile


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
        return f"https://{domain}/git/{self.organisation.name}/{self.name}.git"


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
