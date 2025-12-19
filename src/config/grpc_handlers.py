"""
Root gRPC handlers registration
"""
from django_socio_grpc.services import AppHandlerRegistry
from repositories.services import (
    # Admin Services (CRUD)
    GitRepositoryAdminService,
    GitMirrorRepositoryAdminService,
    SyncTaskAdminService,
    # Read-only Services
    GitRepositoryReadService,
    GitMirrorRepositoryReadService,
    SyncTaskReadService,
    # Specialized Services
    GitRepositoryCreationService,
    GitMirrorRepositoryMirroringService,
    GitRepositoryMigrationService,
    GitRepositorySyncService,
    TaskStatusService,
)


def grpc_handlers(server):
    """
    Register all gRPC services with the server.
    This function is called with the grpcASGI instance (which is a grpc.Server).
    """
    # Register git app services - service_file_path points to the grpc module
    app_registry = AppHandlerRegistry('repositories', server)
    
    # Admin Services
    app_registry.register(GitRepositoryAdminService, service_file_path='repositories.grpc')
    app_registry.register(GitMirrorRepositoryAdminService, service_file_path='repositories.grpc')
    app_registry.register(SyncTaskAdminService, service_file_path='repositories.grpc')
    
    # Read-only Services
    app_registry.register(GitRepositoryReadService, service_file_path='repositories.grpc')
    app_registry.register(GitMirrorRepositoryReadService, service_file_path='repositories.grpc')
    app_registry.register(SyncTaskReadService, service_file_path='repositories.grpc')
    
    # Specialized Services
    app_registry.register(GitRepositoryCreationService, service_file_path='repositories.grpc')
    app_registry.register(GitMirrorRepositoryMirroringService, service_file_path='repositories.grpc')
    app_registry.register(GitRepositoryMigrationService, service_file_path='repositories.grpc')
    app_registry.register(GitRepositorySyncService, service_file_path='repositories.grpc')
    app_registry.register(TaskStatusService, service_file_path='repositories.grpc')
