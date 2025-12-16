"""
Root gRPC handlers registration
"""
from django_socio_grpc.services import AppHandlerRegistry
from repositories.services import GitRepositoryService, GitRepositoryCreationService


def grpc_handlers(server):
    """
    Register all gRPC services with the server.
    This function is called with the grpcASGI instance (which is a grpc.Server).
    """
    # Register git app services - service_file_path points to the grpc module
    app_registry = AppHandlerRegistry('repositories', server)
    app_registry.register(GitRepositoryService, service_file_path='repositories.grpc')
    app_registry.register(GitRepositoryCreationService, service_file_path='repositories.grpc')
