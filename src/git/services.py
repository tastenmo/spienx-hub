from django_socio_grpc.services import Service
from django_socio_grpc.decorators import grpc_action
from django.db.models import Q
from git.models import GitRepository, GitBranch, GitCommit, SyncTask
from accounts.models import Organisation, UserProfile
from git.tasks import initialize_repository, migrate_repository, sync_repository


class GitRepositoryService(Service):
    """gRPC service for Git Repository management"""

    class Meta:
        model = GitRepository

    @grpc_action(
        request=[{"name": "name", "type": str}, 
                 {"name": "description", "type": str},
                 {"name": "source_url", "type": str},
                 {"name": "source_type", "type": str},
                 {"name": "organisation_id", "type": int},
                 {"name": "is_public", "type": bool}],
        response={"repository": GitRepository, "message": str}
    )
    def CreateRepository(self, request, context):
        """Create a new Git repository"""
        try:
            organisation = Organisation.objects.get(id=request.organisation_id)
            
            repo = GitRepository.objects.create(
                name=request.name,
                description=request.description,
                source_url=request.source_url,
                source_type=request.source_type,
                organisation=organisation,
                is_public=request.is_public,
                local_path=f"/git/{organisation.slug}/{request.name}",
                status='pending'
            )
            
            # Trigger initialization task
            if request.source_url:
                # If source URL provided, migrate from source
                migrate_repository.delay(repo.id, force=False)
            else:
                # Otherwise just initialize empty repository
                initialize_repository.delay(repo.id)
            
            return {"repository": repo, "message": "Repository created successfully. Initialization task started."}
        except Organisation.DoesNotExist:
            context.abort(404, "Organisation not found")
        except Exception as e:
            context.abort(400, f"Error creating repository: {str(e)}")

    @grpc_action(
        request=[{"name": "repository_id", "type": int},
                 {"name": "source_url", "type": str},
                 {"name": "force", "type": bool}],
        response={"repository_id": int, "status": str, "message": str, "task_id": str}
    )
    def MigrateRepository(self, request, context):
        """Migrate a repository from source"""
        try:
            repo = GitRepository.objects.get(id=request.repository_id)
            
            # Update status
            repo.status = 'initializing'
            repo.source_url = request.source_url
            repo.save()
            
            # Trigger Celery task for migration
            task = migrate_repository.delay(repo.id, force=request.force)
            
            return {
                "repository_id": repo.id,
                "status": "initializing",
                "message": "Migration started",
                "task_id": str(task.id)
            }
        except GitRepository.DoesNotExist:
            context.abort(404, "Repository not found")
        except Exception as e:
            context.abort(400, f"Error migrating repository: {str(e)}")

    @grpc_action(
        request=[{"name": "repository_id", "type": int}],
        response={"repository_id": int, "status": str, "commits_synced": int, "message": str, "task_id": str}
    )
    def SyncRepository(self, request, context):
        """Sync repository with source"""
        try:
            repo = GitRepository.objects.get(id=request.repository_id)
            
            # Create sync task
            sync_task = SyncTask.objects.create(
                repository=repo,
                status='pending'
            )
            
            # Trigger Celery task for sync
            task = sync_repository.delay(repo.id, sync_task_id=sync_task.id)
            sync_task.task_id = str(task.id)
            sync_task.save()
            
            return {
                "repository_id": repo.id,
                "status": "pending",
                "commits_synced": 0,
                "message": "Sync started",
                "task_id": str(task.id)
            }
        except GitRepository.DoesNotExist:
            context.abort(404, "Repository not found")
        except Exception as e:
            context.abort(400, f"Error syncing repository: {str(e)}")
