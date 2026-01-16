"""
Root gRPC handlers registration
"""
from django_socio_grpc.services import AppHandlerRegistry
from repositories.services import (
    GitRepositoryService,
    GitMirrorRepositoryService,
    SyncTaskService,
    RepositoryCreationService,
    MirrorRepositoryService,
    TaskStatusService,
)
from documents.services import DocumentReadService


def grpc_handlers(server):
    """
    Register all gRPC services with the server.
    This function is called with the grpcASGI instance (which is a grpc.Server).
    """
    # Register repositories app services - service_file_path points to the grpc module
    app_registry = AppHandlerRegistry('repositories', server)
    
    # Core CRUD Services
    app_registry.register(GitRepositoryService, service_file_path='repositories.grpc')
    app_registry.register(GitMirrorRepositoryService, service_file_path='repositories.grpc')
    app_registry.register(SyncTaskService, service_file_path='repositories.grpc')
    
    # Specialized Services
    app_registry.register(RepositoryCreationService, service_file_path='repositories.grpc')
    app_registry.register(MirrorRepositoryService, service_file_path='repositories.grpc')
    app_registry.register(TaskStatusService, service_file_path='repositories.grpc')

    # Register documents app services
    doc_registry = AppHandlerRegistry('documents', server)
    doc_registry.register(DocumentReadService, service_file_path='documents.grpc')
