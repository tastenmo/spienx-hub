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


class GrpcCorsPreflightMiddleware:
	def __init__(self, app):
		self.app = app

	async def __call__(self, scope, receive, send):
		async def send_with_credentials(message):
			if message.get('type') == 'http.response.start':
				headers = list(message.get('headers', []))
				headers_dict = {key.lower(): value for key, value in headers}
				origin = next(
					(value for key, value in scope.get('headers', []) if key == b'origin'),
					None,
				)

				if origin and b'access-control-allow-origin' not in headers_dict:
					headers.append((b'access-control-allow-origin', origin))
				if b'access-control-allow-credentials' not in headers_dict:
					headers.append((b'access-control-allow-credentials', b'true'))
				message = {**message, 'headers': headers}

			await send(message)

		if scope.get('type') == 'http' and scope.get('method') == 'OPTIONS':
			headers = {
				key.decode('latin1').lower(): value.decode('latin1')
				for key, value in scope.get('headers', [])
			}

			# gRPC-Web preflight requests include this header.
			if headers.get('access-control-request-method'):
				origin = headers.get('origin', '')
				requested_headers = headers.get(
					'access-control-request-headers',
					'content-type,x-grpc-web,x-user-agent,grpc-timeout',
				)

				response_headers = [
					(b'content-type', b'text/plain'),
					(b'content-length', b'0'),
					(b'access-control-allow-methods', b'POST, OPTIONS'),
					(b'access-control-allow-headers', requested_headers.encode('latin1')),
					(b'access-control-allow-origin', origin.encode('latin1') if origin else b'*'),
					(b'access-control-allow-credentials', b'true'),
					(b'access-control-expose-headers', b'*'),
				]

				await send(
					{
						'type': 'http.response.start',
						'status': 200,
						'headers': response_headers,
					}
				)
				await send({'type': 'http.response.body', 'body': b'', 'more_body': False})
				return

		await self.app(scope, receive, send_with_credentials)


# Create gRPC-Web ASGI server with CORS for browser gRPC-Web clients
grpc_server = grpcASGI(django_asgi_app, enable_cors=True)

# Register gRPC services on the real grpcASGI server
# Note: Proto files must be generated first with: python manage.py generateproto
grpc_handlers(grpc_server)

# Wrap the gRPC server with custom preflight handling so browser requests get
# explicit Access-Control-Allow-Headers values instead of a wildcard.
application = GrpcCorsPreflightMiddleware(grpc_server)

