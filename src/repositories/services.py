import os
from django.conf import settings
from django_socio_grpc import generics, proto_serializers
from django_socio_grpc.decorators import grpc_action
from repositories.models import GitRepository, GitMirrorRepository, SyncTask
from repositories.grpc import repositories_pb2
from git import Repo as git_repo
from accounts.models import Organisation
from celery import current_app
import grpc
from rest_framework import serializers


# ============================================================================
# SERIALIZERS
# ============================================================================

class GitRepositorySerializer(proto_serializers.ModelProtoSerializer):
    """Serializer for GitRepository model"""
    git_url = serializers.SerializerMethodField()

    def get_git_url(self, obj) -> str | None:
        return getattr(obj, 'git_url', None)

    class Meta:
        model = GitRepository
        fields = '__all__'
        proto_class = repositories_pb2.GitRepositoryResponse
        proto_class_list = repositories_pb2.GitRepositoryListResponse
        extra_kwargs = {
            'local_path': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
            'git_url': {'read_only': True},
        }


class GitMirrorRepositorySerializer(proto_serializers.ModelProtoSerializer):
    """Serializer for GitMirrorRepository model"""
    class Meta:
        model = GitMirrorRepository
        fields = '__all__'
        proto_class = repositories_pb2.GitRepositoryResponse
        proto_class_list = repositories_pb2.GitRepositoryListResponse
        extra_kwargs = {
            'local_path': {'read_only': True},
            'last_synced_at': {'read_only': True},
            'error_message': {'read_only': True},
            'consecutive_failures': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
        }


class SyncTaskSerializer(proto_serializers.ModelProtoSerializer):
    """Serializer for SyncTask model"""
    class Meta:
        model = SyncTask
        fields = '__all__'
        extra_kwargs = {
            'started_at': {'read_only': True},
            'completed_at': {'read_only': True},
            'error_message': {'read_only': True},
            'commits_synced': {'read_only': True},
            'created_at': {'read_only': True},
        }


# ============================================================================
# ADMINISTRATION SERVICES (AsyncModelService - CRUD)
# ============================================================================

class GitRepositoryAdminService(generics.AsyncModelService):
    """
    Administration service for Git Repositories.
    Provides: List, Retrieve, Create, Update, Delete
    """
    queryset = GitRepository.objects.all()
    serializer_class = GitRepositorySerializer


class GitMirrorRepositoryAdminService(generics.AsyncModelService):
    """
    Administration service for Git Mirror Repositories.
    Provides: List, Retrieve, Create, Update, Delete
    """
    queryset = GitMirrorRepository.objects.all()
    serializer_class = GitMirrorRepositorySerializer


class SyncTaskAdminService(generics.AsyncModelService):
    """
    Administration service for Sync Tasks.
    Provides: List, Retrieve, Create, Update, Delete
    """
    queryset = SyncTask.objects.all()
    serializer_class = SyncTaskSerializer


# ============================================================================
# USAGE SERVICES (AsyncReadOnlyModelService - Read-only)
# ============================================================================

class GitRepositoryReadService(generics.AsyncReadOnlyModelService):
    """
    Read-only service for Git Repositories.
    Provides: List, Retrieve
    """
    queryset = GitRepository.objects.all()
    serializer_class = GitRepositorySerializer


class GitMirrorRepositoryReadService(generics.AsyncReadOnlyModelService):
    """
    Read-only service for Git Mirror Repositories.
    Provides: List, Retrieve
    """
    queryset = GitMirrorRepository.objects.all()
    serializer_class = GitMirrorRepositorySerializer


class SyncTaskReadService(generics.AsyncReadOnlyModelService):
    """
    Read-only service for Sync Tasks.
    Provides: List, Retrieve
    """
    queryset = SyncTask.objects.all()
    serializer_class = SyncTaskSerializer


# ============================================================================
# SPECIALIZED SERVICES
# ============================================================================

class GitRepositoryCreationService(generics.GenericService):
    """Service for creating bare Git repositories"""

    @grpc_action(
        request=[
            {"name": "name", "type": "string"},
            {"name": "organisation_id", "type": "int64"},
            {"name": "description", "type": "string"},
            {"name": "is_public", "type": "bool"},
        ],
        response=[
            {"name": "id", "type": "int64"},
            {"name": "local_path", "type": "string"},
            {"name": "git_url", "type": "string"},
        ],
    )
    async def Create(self, request, context):
        """Create a new bare Git repository"""
        base_dir = getattr(settings, 'GIT_REPOS_DIR', os.path.join(settings.BASE_DIR, 'repos'))
        organisation = await Organisation.objects.aget(id=request.organisation_id)
        
        # Sanitize repository name
        safe_name = "".join([c for c in request.name if c.isalnum() or c in ('-', '_')])
        local_path = os.path.join(base_dir, str(organisation.id), safe_name)
        
        # Create repository record
        repository = GitRepository(
            name=request.name,
            organisation=organisation,
            description=request.description,
            local_path=local_path,
            is_bare=True,
            is_public=request.is_public,
        )
        await repository.asave()
        
        # Dispatch initialization task to Celery
        from repositories.tasks import initialize_repository
        task = initialize_repository.delay(repository.id)
        
        return repositories_pb2.GitRepositoryCreationCreateResponse(
            id=repository.id,
            local_path=repository.local_path,
            git_url=repository.git_url,
        )


class GitMirrorRepositoryMirroringService(generics.GenericService):
    """Service for managing mirror repositories"""

    @grpc_action(
        request=[
            {"name": "name", "type": "string"},
            {"name": "organisation_id", "type": "int64"},
            {"name": "source_url", "type": "string"},
            {"name": "source_type", "type": "string"},
            {"name": "description", "type": "string"},
            {"name": "auto_sync", "type": "bool"},
            {"name": "sync_interval", "type": "int32"},
        ],
        response=[
            {"name": "id", "type": "int64"},
            {"name": "status", "type": "string"},
            {"name": "local_path", "type": "string"},
        ],
    )
    async def CreateMirror(self, request, context):
        """Create a new mirror repository from external source"""
        base_dir = getattr(settings, 'GIT_REPOS_DIR', os.path.join(settings.BASE_DIR, 'repos'))
        organisation = await Organisation.objects.aget(id=request.organisation_id)
        
        # Sanitize repository name
        safe_name = "".join([c for c in request.name if c.isalnum() or c in ('-', '_')])
        local_path = os.path.join(base_dir, str(organisation.id), safe_name)
        
        # Create mirror repository record
        mirror = GitMirrorRepository(
            name=request.name,
            organisation=organisation,
            source_url=request.source_url,
            source_type=request.source_type,
            description=request.description,
            local_path=local_path,
            is_bare=True,
            auto_sync=request.auto_sync,
            sync_interval=request.sync_interval,
            status='initializing',
        )
        await mirror.asave()
        
        # Dispatch mirror cloning task to Celery
        from repositories.tasks import clone_mirror_repository
        task = clone_mirror_repository.delay(mirror.id)
        
        return repositories_pb2.GitMirrorRepositoryMirroringCreateMirrorResponse(
            id=mirror.id,
            status=mirror.status,
            local_path=mirror.local_path,
        )


class GitRepositoryMigrationService(generics.GenericService):
    """Service for migrating repositories"""

    @grpc_action(
        request=[
            {"name": "repository_id", "type": "int64"},
            {"name": "new_organisation_id", "type": "int64"},
        ],
        response=[
            {"name": "success", "type": "bool"},
            {"name": "new_local_path", "type": "string"},
            {"name": "message", "type": "string"},
        ],
    )
    async def Migrate(self, request, context):
        """Migrate a repository to a different organisation"""
        try:
            repository = await GitRepository.objects.aget(id=request.repository_id)
            new_organisation = await Organisation.objects.aget(id=request.new_organisation_id)
            
            base_dir = getattr(settings, 'GIT_REPOS_DIR', os.path.join(settings.BASE_DIR, 'repos'))
            safe_name = "".join([c for c in repository.name if c.isalnum() or c in ('-', '_')])
            new_local_path = os.path.join(base_dir, str(new_organisation.id), safe_name)
            
            # Move repository on filesystem
            if os.path.exists(repository.local_path):
                os.makedirs(os.path.dirname(new_local_path), exist_ok=True)
                os.rename(repository.local_path, new_local_path)
            
            # Update repository record
            repository.organisation = new_organisation
            repository.local_path = new_local_path
            await repository.asave()
            
            return repositories_pb2.GitRepositoryMigrationResponse(
                success=True,
                new_local_path=new_local_path,
                message=f"Repository migrated to {new_organisation.name}",
            )
        except Exception as e:
            return repositories_pb2.GitRepositoryMigrationResponse(
                success=False,
                new_local_path="",
                message=f"Migration failed: {str(e)}",
            )

    @grpc_action(
        request=[
            {"name": "name", "type": "string"},
            {"name": "organisation_id", "type": "int64"},
            {"name": "source_url", "type": "string"},
            {"name": "description", "type": "string"},
        ],
        response=[
            {"name": "success", "type": "bool"},
            {"name": "local_path", "type": "string"},
            {"name": "message", "type": "string"},
        ],
    )
    async def MigrateFromExternal(self, request, context):
        """Migrate (clone --bare) a repository from an external git server"""
        try:
            organisation = await Organisation.objects.aget(id=request.organisation_id)
            
            base_dir = getattr(settings, 'GIT_REPOS_DIR', os.path.join(settings.BASE_DIR, 'repos'))
            safe_name = "".join([c for c in request.name if c.isalnum() or c in ('-', '_')])
            local_path = os.path.join(base_dir, str(organisation.id), safe_name)
            
            # Create directories
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Clone as bare repository
            import subprocess
            result = subprocess.run(
                ['git', 'clone', '--bare', request.source_url, local_path],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                return repositories_pb2.GitRepositoryMigrationMigrateFromExternalResponse(
                    success=False,
                    local_path="",
                    message=f"Clone failed: {result.stderr}",
                )
            
            # Create repository record
            repository = await GitRepository.objects.acreate(
                name=request.name,
                description=request.description,
                organisation=organisation,
                local_path=local_path,
                is_bare=True,
                is_public=True,
            )
            
            return repositories_pb2.GitRepositoryMigrationMigrateFromExternalResponse(
                success=True,
                local_path=local_path,
                message=f"Repository cloned from external source",
            )
        except Exception as e:
            return repositories_pb2.GitRepositoryMigrationMigrateFromExternalResponse(
                success=False,
                local_path="",
                message=f"Migration failed: {str(e)}",
            )


class GitRepositorySyncService(generics.GenericService):
    """Service for syncing mirror repositories"""

    @grpc_action(
        request=[
            {"name": "mirror_id", "type": "int64"},
        ],
        response=[
            {"name": "task_id", "type": "int64"},
            {"name": "status", "type": "string"},
        ],
    )
    async def SyncNow(self, request, context):
        """Trigger an immediate sync for a mirror repository"""
        try:
            mirror = await GitMirrorRepository.objects.aget(id=request.mirror_id)
            
            # Create sync task
            sync_task = SyncTask(
                repository=mirror,
                status='pending',
            )
            await sync_task.asave()
            
            # Dispatch sync task to Celery
            from repositories.tasks import sync_mirror_repository
            task = sync_mirror_repository.delay(mirror.id, sync_task.id)
            sync_task.task_id = task.id
            await sync_task.asave()
            
            return repositories_pb2.GitRepositorySyncResponse(
                task_id=sync_task.id,
                status=sync_task.status,
            )
        except GitMirrorRepository.DoesNotExist:
            return repositories_pb2.GitRepositorySyncResponse(
                task_id=0,
                status='failed',
            )


class TaskStatusService(generics.GenericService):
    """Service for monitoring task progress"""

    @grpc_action(
        request=[
            {"name": "task_id", "type": "int64"},
        ],
        response=[
            {"name": "id", "type": "int64"},
            {"name": "status", "type": "string"},
            {"name": "error_message", "type": "string"},
            {"name": "started_at", "type": "string"},
            {"name": "completed_at", "type": "string"},
            {"name": "commits_synced", "type": "int32"},
            {"name": "repository_id", "type": "int64"},
        ],
    )
    async def GetStatus(self, request, context):
        """Get the status of a sync task"""
        try:
            sync_task = await SyncTask.objects.aget(id=request.task_id)
            
            return repositories_pb2.TaskStatusResponse(
                id=sync_task.id,
                status=sync_task.status,
                error_message=sync_task.error_message or '',
                started_at=sync_task.started_at.isoformat() if sync_task.started_at else '',
                completed_at=sync_task.completed_at.isoformat() if sync_task.completed_at else '',
                commits_synced=sync_task.commits_synced,
                repository_id=sync_task.repository.id,
            )
        except SyncTask.DoesNotExist:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Task {request.task_id} not found")
    
    @grpc_action(
        request=[
            {"name": "repository_id", "type": "int64"},
        ],
        response=[
            {"name": "task_count", "type": "int32"},
        ],
    )
    async def GetRepositoryTasks(self, request, context):
        """Get all sync tasks for a repository"""
        try:
            repository = await GitRepository.objects.aget(id=request.repository_id)
            
            task_count = await SyncTask.objects.filter(repository=repository).acount()
            
            return repositories_pb2.RepositoryTasksResponse(task_count=task_count)
        except GitRepository.DoesNotExist:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Repository {request.repository_id} not found")



