"""
gRPC handlers registration for git app
"""

from git.services import GitRepositoryService


def grpc_handlers(server):
    """
    Register all gRPC service handlers.
    This is called automatically by django-socio-grpc.
    """
    # Services are auto-registered when imported
    # Just import them to ensure they're loaded
    pass
