from django.apps import AppConfig


class GitConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'repositories'
    
    def ready(self):
        """Import grpc services when app is ready"""
        try:
            from . import services  # noqa
        except ImportError:
            # Proto files not generated yet
            pass
