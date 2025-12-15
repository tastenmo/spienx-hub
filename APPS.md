# Django Apps Structure

This project is organized into the following Django applications:

## Core App (`src/core`)
Basic application for Django setup and core functionality.

## Accounts App (`src/accounts`)
User management and organization/workspace functionality.

### Models

#### Organisation
Represents organizations or workspaces in the system.
- `name`: Organization name (unique)
- `slug`: URL-friendly identifier (unique)
- `description`: Organization description
- `logo_url`: Logo URL
- `website`: Website URL
- `is_active`: Whether the organization is active
- `created_by`: User who created the organization
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

#### UserProfile
Extended user profile with organization and role information.
- `user`: One-to-one link to Django User
- `organisation`: Foreign key to Organization (nullable)
- `role`: User role (admin, developer, viewer)
- `bio`: User biography
- `avatar_url`: Avatar URL
- `is_active`: Whether the profile is active
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

#### OrganisationInvite
Manage organization membership invitations.
- `organisation`: Foreign key to Organization
- `email`: Email address being invited
- `role`: Role to assign when accepted
- `status`: Invitation status (pending, accepted, declined)
- `invited_by`: User who sent the invitation
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

## Git App (`src/git`)
Git repository management and synchronization.

### Models

#### GitRepository
Represents a Git repository managed by the system.
- `name`: Repository name
- `description`: Repository description
- `organisation`: Foreign key to Organization
- `source_url`: Original repository URL
- `source_type`: Type of source (github, gitlab, gitea, custom)
- `local_path`: Local file system path
- `status`: Repository status (pending, initializing, mirroring, active, failed, archived)
- `is_mirror`: Whether it's a mirror
- `is_bare`: Whether it's a bare repository
- `default_branch`: Default branch name
- `last_synced_at`: Last sync timestamp
- `last_commit_hash`: Hash of last commit
- `total_commits`: Total commit count
- `is_public`: Whether the repository is publicly accessible
- `owner`: Foreign key to UserProfile
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `error_message`: Error details if status is failed

#### GitBranch
Represents a branch in a repository.
- `repository`: Foreign key to GitRepository
- `name`: Branch name
- `commit_hash`: Hash of the commit this branch points to
- `is_default`: Whether this is the default branch
- `last_updated`: Last update timestamp

#### GitCommit
Represents commits in a repository.
- `repository`: Foreign key to GitRepository
- `commit_hash`: Hash of the commit
- `author_name`: Commit author name
- `author_email`: Commit author email
- `message`: Commit message
- `committed_at`: Commit timestamp
- `synced_at`: When the commit was synced to the system

#### SyncTask
Tracks repository synchronization tasks.
- `repository`: Foreign key to GitRepository
- `status`: Task status (pending, running, completed, failed)
- `started_at`: When the sync started
- `completed_at`: When the sync completed
- `error_message`: Error details if failed
- `commits_synced`: Number of commits synced
- `task_id`: Celery task ID
- `created_at`: Creation timestamp

## Admin Interface

Both apps register their models with Django's admin interface:

- Accounts: `/admin/accounts/`
- Git: `/admin/git/`

Access the admin panel at `/admin/` after creating a superuser:

```bash
poetry run python src/manage.py createsuperuser
```

## gRPC Services

The git app provides gRPC services for managing repositories. See `src/git/protos/git.proto` for service definitions.

### Available Endpoints

- `CreateRepository`: Create a new repository
- `GetRepository`: Get repository details
- `ListRepositories`: List repositories
- `MigrateRepository`: Migrate from source
- `SyncRepository`: Sync with source
- `DeleteRepository`: Delete a repository
- `GetRepositoryBranches`: Get all branches
- `GetRepositoryCommits`: Get commits

## Database Schema

All models use the following indexes for optimal performance:

### Accounts
- Organisation: `slug`, `is_active`
- UserProfile: `organisation + role`, `user + organisation`
- OrganisationInvite: `organisation + status`, `email + status`

### Git
- GitRepository: `organisation + status`, `source_url`, `status`
- GitCommit: `repository + committed_at`, `author_email`
- GitBranch: `repository + is_default`
- SyncTask: `repository + status`, `status`
