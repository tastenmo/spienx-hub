# Git Repository Management

This document describes the git repository management system using GitPython and Celery.

## Overview

The system provides the ability to:
- Create bare and regular git repositories
- Migrate/clone repositories from external sources (GitHub, GitLab, Gitea, etc.)
- Automatically sync repositories with their sources
- Track commits and branches
- Monitor synchronization tasks

## Architecture

### Storage

Git repositories are stored in a named Docker volume:
- **Volume Name**: `git_repos`
- **Mount Point**: `/git`
- **Path Structure**: `/git/{organisation_slug}/{repo_name}`

The volume is mounted on:
- `web` service - for read/write access via gRPC API
- `celery` service - for processing tasks
- `celery-beat` service - for scheduled syncs

### Components

#### Models

**GitRepository**
- Stores repository metadata
- Tracks status: `pending`, `initializing`, `mirroring`, `active`, `failed`, `archived`
- Supports mirror clones and bare repositories
- Records sync timestamps and commit counts

**GitBranch**
- Tracks repository branches
- Records commit hash and default branch flag
- Automatically updated during sync

**GitCommit**
- Stores commit history
- Records author, message, and timestamp
- Used for analytics and history tracking

**SyncTask**
- Tracks individual sync operations
- Records progress and errors
- Linked to Celery task IDs

#### Celery Tasks

**`initialize_repository(repository_id)`**
- Creates a new bare or regular git repository
- Creates directory structure
- Sets repository status to `active`
- Retries up to 3 times on failure

**`migrate_repository(repository_id, force=False)`**
- Clones or mirrors a repository from source
- Supports mirror clones for backup purposes
- Updates repository metadata after clone
- Can force re-clone with `force=True`
- Retries up to 3 times on failure

**`sync_repository(repository_id, sync_task_id=None)`**
- Fetches or pulls latest changes
- Updates commit counts and metadata
- Tracks sync progress via SyncTask model
- Retries up to 3 times on failure

### gRPC API

#### CreateRepository
Creates a new git repository. If `source_url` is provided, migration is triggered; otherwise, an empty repository is initialized.

```protobuf
message CreateRepositoryRequest {
    string name = 1;
    string description = 2;
    string source_url = 3;
    string source_type = 4;  // github, gitlab, gitea, custom
    int32 organisation_id = 5;
    bool is_public = 6;
}

message RepositoryResponse {
    Repository repository = 1;
    string message = 2;
}
```

#### MigrateRepository
Migrates a repository from a source URL (clones or mirrors).

```protobuf
message MigrateRepositoryRequest {
    int32 repository_id = 1;
    string source_url = 2;
    bool force = 3;  // Force re-clone if repo exists
}

message MigrationResponse {
    int32 repository_id = 1;
    string status = 2;
    string message = 3;
    string task_id = 4;  // Celery task ID
}
```

#### SyncRepository
Syncs repository with source (pulls latest changes).

```protobuf
message SyncRepositoryRequest {
    int32 repository_id = 1;
}

message SyncResponse {
    int32 repository_id = 1;
    string status = 2;
    int32 commits_synced = 3;
    string message = 4;
    string task_id = 5;  // Celery task ID
}
```

## Usage Examples

### Initialize a new empty repository

```python
# Via gRPC
request = CreateRepositoryRequest(
    name="my-repo",
    description="My new repository",
    source_url="",  # Empty = no migration
    source_type="github",
    organisation_id=1,
    is_public=True
)
```

### Clone from GitHub

```python
request = CreateRepositoryRequest(
    name="github-mirror",
    description="Mirror of a GitHub repository",
    source_url="https://github.com/user/repo.git",
    source_type="github",
    organisation_id=1,
    is_public=False
)
# Task: initialize_repository → migrate_repository will be triggered
```

### Create a mirror clone

The system automatically creates a mirror clone if the repository is configured with `is_mirror=True`. A mirror clone:
- Uses the `--mirror` flag in git
- Pushes to all branches
- Suitable for backups
- Can be used as a source for other clones

```python
repo = GitRepository.objects.create(
    name="github-mirror",
    description="GitHub repository mirror",
    source_url="https://github.com/user/repo.git",
    source_type="github",
    organisation=org,
    is_mirror=True,
    is_bare=True,
    local_path="/git/myorg/github-mirror"
)
# Celery task will mirror the repository
```

### Sync an existing repository

```python
request = SyncRepositoryRequest(
    repository_id=1
)
# Task: sync_repository will be triggered
# Creates a SyncTask to track progress
```

## Configuration

### Environment Variables

```env
# Path where git repositories are stored
GIT_REPOS_DIR=/git

# Celery settings
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### Settings (config/settings.py)

```python
GIT_REPOS_DIR = os.getenv('GIT_REPOS_DIR', '/git')

CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
```

## Error Handling

### Task Retry Strategy

All git tasks implement automatic retry with exponential backoff:
- Initial retry: 60 seconds
- Second retry: 120 seconds (2 minutes)
- Third retry: 240 seconds (4 minutes)

### Status Transitions

```
pending → initializing → active (success)
          ↓
        failed (with error_message)

pending → mirroring → active (success)
         ↓
       failed (with error_message)
```

### Common Errors

**"Repository directory not found"**
- Usually means initialize_repository failed
- Check error_message field in GitRepository model

**"Permission denied"**
- SSH key issues for private repositories
- May need Git credentials setup in container

**"Connection refused"**
- Network issues accessing source repository
- Check source_url and network connectivity

## Performance Considerations

### Volume Performance
The `git_repos` volume uses local driver, providing:
- Fast read/write access
- Direct file system operations
- Suitable for bare repositories (no working directory)

### Task Processing
- Tasks run asynchronously via Celery
- Multiple workers can process tasks in parallel
- SyncTask model allows tracking progress

### Database Indexes
- `git_gitrepository`: `organisation + status`, `source_url`, `status`
- `git_gitcommit`: `repository + committed_at`, `author_email`
- `git_gitbranch`: `repository + is_default`
- `git_synctask`: `repository + status`, `status`

## Monitoring

### Check Task Status

```python
from git.models import SyncTask
task = SyncTask.objects.get(repository_id=1)
print(f"Status: {task.status}")
print(f"Commits synced: {task.commits_synced}")
print(f"Error: {task.error_message}")
```

### Monitor Repository State

```python
from git.models import GitRepository
repo = GitRepository.objects.get(id=1)
print(f"Status: {repo.status}")
print(f"Last synced: {repo.last_synced_at}")
print(f"Total commits: {repo.total_commits}")
print(f"Last commit: {repo.last_commit_hash}")
```

### View Celery Task Details

```python
from celery.result import AsyncResult
task_id = "abc123..."
result = AsyncResult(task_id)
print(f"State: {result.state}")
print(f"Result: {result.result}")
print(f"Error: {result.info}")
```

## Security Considerations

### Private Repositories

For private repositories:
1. Configure SSH keys in the Docker container
2. Use SSH URLs: `git@github.com:user/repo.git`
3. Or use HTTPS with personal access tokens

### Access Control

- `is_public` flag controls visibility
- Owner field tracks who created the repository
- Use Django's permission system for role-based access

## Troubleshooting

### Repositories not syncing

1. Check Celery worker logs: `docker-compose logs celery`
2. Verify Redis is running: `docker-compose ps`
3. Check SyncTask error messages
4. Check network connectivity to source

### High disk usage

1. Check repository sizes: `du -sh /git/*`
2. Consider archive policy for inactive repositories
3. Remove failed migration attempts

### Slow performance

1. Check volume performance
2. Monitor Celery task queue
3. Consider splitting large repositories
4. Use shallow clones for very large repositories
