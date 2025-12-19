"""
Celery tasks for Git repository management.
Handles initialization, cloning mirrors, and syncing.
"""

from celery import shared_task
import os
import shutil
from django.conf import settings
from django.utils import timezone
from repositories.models import GitRepository, GitMirrorRepository, SyncTask
import logging

logger = logging.getLogger(__name__)

GIT_REPOS_DIR = getattr(settings, 'GIT_REPOS_DIR', os.path.join(settings.BASE_DIR, 'repos'))

from git import Repo as GitPythonRepo


# ============================================================================
# BARE REPOSITORY TASKS
# ============================================================================

@shared_task(bind=True, max_retries=3)
def initialize_repository(self, repository_id):
    """
    Initialize a bare Git repository on the filesystem.
    """
    try:
        repo = GitRepository.objects.get(id=repository_id)
        
        # Ensure directory structure exists
        os.makedirs(os.path.dirname(repo.local_path), exist_ok=True)
        
        # Create bare repository
        git_repo = GitPythonRepo.init(repo.local_path, bare=True)
        
        logger.info(f"Repository {repo.name} initialized at {repo.local_path}")
        return {
            'success': True,
            'repository_id': repository_id,
            'message': 'Repository initialized successfully',
            'path': repo.local_path
        }
        
    except GitRepository.DoesNotExist:
        logger.error(f"Repository {repository_id} not found")
        return {'success': False, 'error': 'Repository not found'}
    except Exception as exc:
        logger.error(f"Error initializing repository {repository_id}: {str(exc)}")
        try:
            repo = GitRepository.objects.get(id=repository_id)
            repo.delete()  # Clean up failed repository record
        except:
            pass
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


# ============================================================================
# MIRROR REPOSITORY TASKS
# ============================================================================

@shared_task(bind=True, max_retries=3)
def clone_mirror_repository(self, mirror_id):
    """
    Clone a mirror repository from external source.
    """
    try:
        mirror = GitMirrorRepository.objects.get(id=mirror_id)
        mirror.status = 'initializing'
        mirror.save()
        
        # Ensure directory structure exists
        os.makedirs(os.path.dirname(mirror.local_path), exist_ok=True)
        
        # Clone as mirror (bare repository that mirrors all branches)
        git_repo = GitPythonRepo.clone_from(
            mirror.source_url,
            mirror.local_path,
            mirror=True,
            bare=True,
        )
        
        # Update mirror status
        mirror.status = 'active'
        mirror.last_synced_at = timezone.now()
        mirror.consecutive_failures = 0
        mirror.error_message = ''
        mirror.save()
        
        logger.info(f"Mirror {mirror.name} cloned from {mirror.source_url}")
        return {
            'success': True,
            'mirror_id': mirror_id,
            'message': 'Mirror cloned successfully',
        }
        
    except GitMirrorRepository.DoesNotExist:
        logger.error(f"Mirror {mirror_id} not found")
        return {'success': False, 'error': 'Mirror not found'}
    except Exception as exc:
        logger.error(f"Error cloning mirror {mirror_id}: {str(exc)}")
        try:
            mirror = GitMirrorRepository.objects.get(id=mirror_id)
            mirror.status = 'failed'
            mirror.error_message = str(exc)
            mirror.consecutive_failures += 1
            mirror.save()
            
            # Clean up failed clone directory
            if os.path.exists(mirror.local_path):
                shutil.rmtree(mirror.local_path)
        except:
            pass
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def sync_mirror_repository(self, mirror_id, sync_task_id=None):
    """
    Sync a mirror repository by fetching all updates from source.
    """
    sync_task = None
    try:
        mirror = GitMirrorRepository.objects.get(id=mirror_id)
        
        if sync_task_id:
            sync_task = SyncTask.objects.get(id=sync_task_id)
            sync_task.status = 'running'
            sync_task.started_at = timezone.now()
            sync_task.save()
        
        mirror.status = 'mirroring'
        mirror.save()
        
        # Check if repository exists
        if not os.path.exists(mirror.local_path):
            raise Exception(f"Mirror directory not found: {mirror.local_path}")
        
        # Open and fetch updates
        git_repo = GitPythonRepo(mirror.local_path)
        
        # Fetch all updates from origin
        origin = git_repo.remotes.origin
        origin.fetch(all=True, prune=True)
        
        # Update mirror metadata
        mirror.status = 'active'
        mirror.last_synced_at = timezone.now()
        mirror.consecutive_failures = 0
        mirror.error_message = ''
        mirror.save()
        
        if sync_task:
            sync_task.status = 'completed'
            sync_task.completed_at = timezone.now()
            sync_task.save()
        
        logger.info(f"Mirror {mirror.name} synced successfully")
        return {
            'success': True,
            'mirror_id': mirror_id,
            'message': 'Mirror synced successfully',
        }
        
    except GitMirrorRepository.DoesNotExist:
        logger.error(f"Mirror {mirror_id} not found")
        if sync_task:
            sync_task.status = 'failed'
            sync_task.error_message = 'Mirror not found'
            sync_task.completed_at = timezone.now()
            sync_task.save()
        return {'success': False, 'error': 'Mirror not found'}
    except Exception as exc:
        logger.error(f"Error syncing mirror {mirror_id}: {str(exc)}")
        try:
            mirror = GitMirrorRepository.objects.get(id=mirror_id)
            mirror.status = 'failed'
            mirror.error_message = str(exc)
            mirror.consecutive_failures += 1
            mirror.save()
        except:
            pass
        
        if sync_task:
            sync_task.status = 'failed'
            sync_task.error_message = str(exc)
            sync_task.completed_at = timezone.now()
            sync_task.save()
        
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
