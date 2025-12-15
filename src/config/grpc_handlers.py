"""
Root gRPC handlers registration
"""
from django_socio_grpc.services import AppHandlerRegistry
from git.services import GitRepositoryService


def grpc_handlers(server):
    """
    Register all gRPC services with the server.
    This function is called with the grpcASGI instance (which is a grpc.Server).
    """
    # Register git app services - service_file_path points to the grpc module
    app_registry = AppHandlerRegistry('git', server)
    app_registry.register(GitRepositoryService, service_file_path='git.grpc')
