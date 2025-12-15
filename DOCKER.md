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
- Run: `docker-compose down -v`

### Database Connection Failed

Ensure PostgreSQL service is healthy:

```bash
docker-compose exec postgres pg_isready -U spienx
```

### Celery not processing tasks

Check Redis is running:

```bash
docker-compose exec redis redis-cli ping
```

Monitor Celery worker:

```bash
docker-compose logs -f celery
```
