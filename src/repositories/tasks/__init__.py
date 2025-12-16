from celery import shared_task
import os
from repositories.models import GitRepository, SyncTask
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

GIT_REPOS_DIR = os.getenv('GIT_REPOS_DIR', '/git')

from git import Repo

# Helper function to get GitPython Repo class
def _get_gitpython_repo():
    """Dynamically import GitPython Repo to avoid namespace collision"""
    return Repo


@shared_task(bind=True, max_retries=3)
def initialize_repository(self, repository_id):
    """
    Initialize a bare git repository
    """
    try:
        repo = GitRepository.objects.get(id=repository_id)
        repo.status = 'initializing'
        repo.save()

        # Ensure directory structure exists
        repo_dir = os.path.join(GIT_REPOS_DIR, repo.local_path.lstrip('/'))
        os.makedirs(os.path.dirname(repo_dir), exist_ok=True)

        GitRepo = _get_gitpython_repo()
        if repo.is_bare:
            # Create bare repository
            git_repo = GitRepo.init(repo_dir, bare=True)
        else:
            # Create normal repository
            git_repo = GitRepo.init(repo_dir)

        repo.status = 'active'
        repo.save()

        logger.info(f"Repository {repo.name} initialized at {repo_dir}")
        return {
            'success': True,
            'repository_id': repository_id,
            'message': 'Repository initialized successfully',
            'path': repo_dir
        }

    except GitRepository.DoesNotExist:
        logger.error(f"Repository {repository_id} not found")
        return {'success': False, 'error': 'Repository not found'}
    except Exception as exc:
        logger.error(f"Error initializing repository: {str(exc)}")
        repo.status = 'failed'
        repo.error_message = str(exc)
        repo.save()
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def migrate_repository(self, repository_id, force=False):
    """
    Migrate/clone or mirror a repository from source
    """
    try:
        repo = GitRepository.objects.get(id=repository_id)
        repo.status = 'mirroring'
        repo.save()

        repo_dir = os.path.join(GIT_REPOS_DIR, repo.local_path.lstrip('/'))
        os.makedirs(os.path.dirname(repo_dir), exist_ok=True)

        # Remove existing repo if force is True
        if force and os.path.exists(repo_dir):
            import shutil
            shutil.rmtree(repo_dir)

        GitRepo = _get_gitpython_repo()
        if repo.is_mirror:
            # Create a mirror clone
            git_repo = GitRepo.clone_from(
                repo.source_url,
                repo_dir,
                mirror=True,
                bare=True
            )
        else:
            # Regular clone
            git_repo = GitRepo.clone_from(
                repo.source_url,
                repo_dir,
                bare=repo.is_bare
            )

        # Update repository metadata
        if git_repo.heads:
            repo.default_branch = git_repo.active_branch.name
        repo.total_commits = sum(1 for _ in git_repo.iter_commits())
        repo.last_synced_at = timezone.now()
        repo.status = 'active'
        repo.save()

        logger.info(f"Repository {repo.name} migrated from {repo.source_url}")
        return {
            'success': True,
            'repository_id': repository_id,
            'message': 'Repository migrated successfully',
            'total_commits': repo.total_commits
        }

    except GitRepository.DoesNotExist:
        logger.error(f"Repository {repository_id} not found")
        return {'success': False, 'error': 'Repository not found'}
    except Exception as exc:
        logger.error(f"Error migrating repository: {str(exc)}")
        repo.status = 'failed'
        repo.error_message = str(exc)
        repo.save()
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def sync_repository(self, repository_id, sync_task_id=None):
    """
    Sync repository with source (pull latest changes)
    """
    sync_task = None
    try:
        repo = GitRepository.objects.get(id=repository_id)
        repo.status = 'mirroring'
        repo.save()

        if sync_task_id:
            sync_task = SyncTask.objects.get(id=sync_task_id)
            sync_task.status = 'running'
            sync_task.started_at = timezone.now()
            sync_task.save()

        repo_dir = os.path.join(GIT_REPOS_DIR, repo.local_path.lstrip('/'))

        if not os.path.exists(repo_dir):
            raise Exception(f"Repository directory not found: {repo_dir}")

        # Open existing repository
        GitRepo = _get_gitpython_repo()
        git_repo = GitRepo(repo_dir)

        # Fetch from origin/source
        if repo.is_mirror:
            # For mirror repos, fetch all
            origin = git_repo.remotes.origin
            origin.fetch(all=True)
        else:
            # For regular repos, pull
            origin = git_repo.remotes.origin
            origin.pull()

        # Update metadata
        repo.total_commits = sum(1 for _ in git_repo.iter_commits())
        repo.last_synced_at = timezone.now()
        if git_repo.heads:
            repo.last_commit_hash = git_repo.head.commit.hexsha[:40]
        repo.status = 'active'
        repo.save()

        if sync_task:
            sync_task.status = 'completed'
            sync_task.completed_at = timezone.now()
            sync_task.commits_synced = repo.total_commits
            sync_task.save()

        logger.info(f"Repository {repo.name} synced successfully")
        return {
            'success': True,
            'repository_id': repository_id,
            'message': 'Repository synced successfully',
            'total_commits': repo.total_commits
        }

    except GitRepository.DoesNotExist:
        logger.error(f"Repository {repository_id} not found")
        if sync_task:
            sync_task.status = 'failed'
            sync_task.error_message = 'Repository not found'
            sync_task.save()
        return {'success': False, 'error': 'Repository not found'}
    except Exception as exc:
        logger.error(f"Error syncing repository: {str(exc)}")
        repo.status = 'failed'
        repo.error_message = str(exc)
        repo.save()
        if sync_task:
            sync_task.status = 'failed'
            sync_task.error_message = str(exc)
            sync_task.save()
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
