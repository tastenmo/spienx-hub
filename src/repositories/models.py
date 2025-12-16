from django.db import models
from accounts.models import Organisation, UserProfile


class GitRepository(models.Model):
    """Model representing a Git repository"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('initializing', 'Initializing'),
        ('mirroring', 'Mirroring'),
        ('active', 'Active'),
        ('failed', 'Failed'),
        ('archived', 'Archived'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='repositories'
    )
    
    # Source repository details
    source_url = models.URLField(help_text="Original repository URL (e.g., GitHub, GitLab)")
    source_type = models.CharField(
        max_length=50,
        choices=[
            ('github', 'GitHub'),
            ('gitlab', 'GitLab'),
            ('gitea', 'Gitea'),
            ('custom', 'Custom Git Server'),
        ],
        default='github'
    )
    
    # Local storage
    local_path = models.CharField(
        max_length=512,
        unique=True,
        help_text="Local file system path"
    )
    
    # Status and metadata
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    is_mirror = models.BooleanField(default=True)
    is_bare = models.BooleanField(default=True)
    
    # Git information
    default_branch = models.CharField(max_length=255, default='main', blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_commit_hash = models.CharField(max_length=40, blank=True)
    total_commits = models.IntegerField(default=0)
    
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
    error_message = models.TextField(blank=True, help_text="Error details if status is failed")

    class Meta:
        ordering = ['-created_at']
        unique_together = [['organisation', 'name']]
        indexes = [
            models.Index(fields=['organisation', 'status']),
            models.Index(fields=['source_url']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.organisation.name}/{self.name}"


class GitBranch(models.Model):
    """Model representing a branch in a repository"""

    repository = models.ForeignKey(
        GitRepository,
        on_delete=models.CASCADE,
        related_name='branches'
    )
    name = models.CharField(max_length=255)
    commit_hash = models.CharField(max_length=40)
    is_default = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = [['repository', 'name']]
        indexes = [
            models.Index(fields=['repository', 'is_default']),
        ]

    def __str__(self):
        return f"{self.repository.name}/{self.name}"


class GitCommit(models.Model):
    """Model representing commits in a repository"""

    repository = models.ForeignKey(
        GitRepository,
        on_delete=models.CASCADE,
        related_name='commits'
    )
    commit_hash = models.CharField(max_length=40, db_index=True)
    author_name = models.CharField(max_length=255)
    author_email = models.EmailField()
    message = models.TextField()
    committed_at = models.DateTimeField()
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-committed_at']
        unique_together = [['repository', 'commit_hash']]
        indexes = [
            models.Index(fields=['repository', 'committed_at']),
            models.Index(fields=['author_email']),
        ]

    def __str__(self):
        return f"{self.repository.name}/{self.commit_hash[:8]}"


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
