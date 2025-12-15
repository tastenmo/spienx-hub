from django.apps import AppConfig


class GitConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'git'
    
    def ready(self):
        """Import grpc services when app is ready"""
        from . import services  # noqa
