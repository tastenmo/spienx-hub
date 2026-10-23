# Docker Setup Guide

This project includes Docker configuration for development and production environments.

## Services

- **web**: Django application running with Daphne (ASGI server) on port 8000
- **postgres**: PostgreSQL database on port 5432
- **redis**: Redis cache/message broker and channel layer on port 6379
- **celery**: Celery worker for async tasks
- **celery-beat**: Celery beat scheduler for periodic tasks

## Prerequisites

- Docker (version 20.10+)
- Docker Compose (version 2.0+)
- Local `jsx-builder` and `django-socio-grpc` checkouts alongside `spienx-hub`
  in the same parent directory. The image copies both path dependencies, and
  the application services bind-mount them for development.
- Initialize the shared protobuf submodule with
  `git submodule update --init --recursive` before building. The build context
  includes `spienx-proto/`, which is also available through the `/app` bind mount.

The image uses Poetry 2.2.1 to match the lockfile and installs dependencies with
`--no-root`; Django runs directly from `/app/src`.

## Technology Stack

- **ASGI Server**: Daphne (async HTTP/2 capable)
- **gRPC Support**: Django Socio gRPC with gRPCWeb wrapper
- **gRPCWeb**: Browser-compatible gRPC client support
- **Task Queue**: Celery with Redis broker
- **Database**: PostgreSQL
- **Cache/Message Broker**: Redis

## Getting Started

### 1. Build and Start Services

```bash
docker-compose up -d
```

This will:
- Build the Django web image with git and git-lfs support
- Start all services (PostgreSQL, Redis, Django with Daphne, Celery, Celery Beat)
- Run migrations automatically
- Create the database if needed
- Configure gRPC and gRPCWeb support via django-socio-grpc

### 2. Create Superuser

```bash
docker-compose exec web poetry run python src/manage.py createsuperuser
```

### 3. Access Services

- Django Admin: http://localhost:8000/admin
- PostgreSQL: localhost:5432 (credentials in .env.docker)
- Redis: localhost:6379

Git FastCGI is published on host port 9002 and forwarded to port 9001 inside
the web container. The Git CGI upstream in `nginx/hub.tastenmo.de.conf` uses
`127.0.0.1:9002`. When changing this mapping, update the deployed Nginx
configuration as well, validate it with `nginx -t`, and reload Nginx.

## Environment Configuration

Copy `.env.docker` to `.env` or set environment variables:

```bash
cp .env.docker .env
```

Then modify values as needed for your environment.

## Useful Commands

### View logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f celery
docker-compose logs -f postgres
```

## gRPC and gRPCWeb Support

The application uses Django Socio gRPC with Daphne for gRPC and gRPCWeb support:

- **Protocol**: gRPC (HTTP/2) + gRPCWeb (HTTP/1.1 with special encoding)
- **ASGI Server**: Daphne (runs on port 8000, supports HTTP/2)
- **gRPC Services**: Native gRPC service definitions
- **Browser Support**: gRPCWeb enables browser-based clients
- **Client Library**: Use gRPC clients or gRPCWeb clients from any language

Example gRPCWeb client code (JavaScript):

```javascript
import { YourServiceClient } from './generated/your_service_grpc_web_pb';
import { YourRequest } from './generated/your_service_pb';

const client = new YourServiceClient('http://localhost:8000');

const request = new YourRequest();
request.setField('value');

client.yourMethod(request, {}, (err, response) => {
    if (err) {
        console.error('Error:', err);
    } else {
        console.log('Response:', response);
    }
});
```

Example gRPC client code (Python):

```python
import grpc
from your_service_pb2 import YourRequest
from your_service_pb2_grpc import YourServiceStub

channel = grpc.aio.secure_channel('localhost:8000', grpc.ssl_channel_credentials())
stub = YourServiceStub(channel)

response = await stub.YourMethod(YourRequest(field='value'))
print(response)
```

## Git Support

The Docker container includes:
- **Git**: For version control operations
- **Git LFS**: For large file handling
- **Git Configuration**: Default user configured as `docker@spienx.com`

You can run git commands inside the container:

```bash
docker-compose exec web git status
docker-compose exec web git log --oneline
```

### Run Django management commands

```bash
docker-compose exec web poetry run python src/manage.py <command>
```

### Make migrations

```bash
docker-compose exec web poetry run python src/manage.py makemigrations
docker-compose exec web poetry run python src/manage.py migrate
```

### Stop services

```bash
docker-compose down
```

### Remove volumes (clears database and cache)

```bash
docker-compose down -v
```

## Development

For development, you can modify code locally and the changes will be reflected in the container due to volume mounting.

To rebuild the image after adding dependencies:

```bash
docker-compose build
docker-compose up -d
```

## Production Notes

### Hosting under `https://forge.escad.de/hub/`

Set these values in the project `.env` file:

```dotenv
FORCE_SCRIPT_NAME=/hub
GIT_DOMAIN=forge.escad.de/hub
```

Rebuild and recreate the application services to load the prefix settings:

```bash
docker compose up -d --build web celery celery-beat
docker compose exec web poetry run python manage.py collectstatic --noinput
```

Install the Nginx location snippet and collected static files on the Docker host:

```bash
sudo install -d /etc/nginx/snippets /var/www/spienx-hub/staticfiles
sudo install -m 644 nginx/forge-hub.conf /etc/nginx/snippets/forge-hub.conf
sudo cp -R staticfiles/. /var/www/spienx-hub/staticfiles/
```

Inside the existing **HTTPS server block** in
`/etc/nginx/sites-available/forge.escad.de.conf`, add:

```nginx
include /etc/nginx/snippets/forge-hub.conf;
```

The snippet uses the existing `$connection_upgrade_keepalive` map. It leaves
the other applications on this host unchanged, strips `/hub/` before proxying
to Django on port 8001, and forwards Git FastCGI requests to port 9002.
Django generates prefixed admin and static URLs. Refresh the copied static
files after subsequent `collectstatic` runs. Uploaded media is not served by
this snippet.

Validate before reloading:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

Open `https://forge.escad.de/hub/admin/`. With this deployment enabled, access
the admin through Nginx rather than directly through port 8001.

Before deploying to production:

1. Change `DEBUG=False` in `.env`
2. Generate a new `SECRET_KEY`
3. Update `ALLOWED_HOSTS` with your domain
4. Use strong database password
5. Consider using a separate database backup strategy
6. Set up proper logging and monitoring
7. Use a production-grade web server (gunicorn, uWSGI)

## Troubleshooting

### Port Already in Use

If you get "port already in use" errors, either:
- Change the port mappings in `docker-compose.yml`
- Stop other containers using those ports

Use `docker compose ps -a` and `docker ps` to check failed containers and
published ports. After resolving a conflict affecting the web service,
recreate only that service:

```bash
docker compose up -d --no-deps --force-recreate web
```

Do not remove volumes to resolve a port conflict; doing so can delete database
data.

### Database Connection Failed

Ensure PostgreSQL service is healthy:

```bash
docker-compose exec postgres pg_isready -U spienx
```

If Django reports `could not translate host name "postgres"`, check that the web
container is attached to the same Compose network as PostgreSQL:

```bash
docker inspect spienx-web spienx-postgres --format '{{.Name}} {{json .NetworkSettings.Networks}}'
```

The hostname `postgres` resolves inside the Compose network. A missing web
network attachment can also follow a failed container start caused by a host
port conflict; resolve that conflict and recreate the web service as above.

### Celery not processing tasks

Check Redis is running:

```bash
docker-compose exec redis redis-cli ping
```

Monitor Celery worker:

```bash
docker-compose logs -f celery
```
