"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialize Django ASGI application early to ensure apps are loaded
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

# Import gRPC components
from django_socio_grpc.grpc_web import grpcASGI
from config.grpc_handlers import grpc_handlers

# Create gRPC-Web ASGI application
application = grpcASGI(django_asgi_app, enable_cors=False)

# Register gRPC services by calling grpc_handlers with the grpcASGI instance
# Note: Proto files must be generated first with: python manage.py generateproto
grpc_handlers(application)

