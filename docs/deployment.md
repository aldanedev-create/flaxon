# Deployment

For generated projects, use the shared `settings.py`, `Flaxon.from_settings()`,
explicit mounts in `app.py`, and `management.py` workflow. See [ORM and project management](guides/orm.md)
for Python migrations, model registration, permission hooks, relationship editing,
and Admin/CMS metadata storage. Backend-only and legacy adapter examples remain supported.

## Overview

Flaxon applications can be deployed in a variety of environments, from a simple development server to scalable production deployments using multiple workers, Docker, reverse proxies, and cloud platforms.

This guide covers the recommended deployment options and production best practices.

---

# Running in Production

## Using the Flaxon CLI

Start a single worker:

```bash
flaxon run app:app --host 0.0.0.0 --port 8000
```

Start multiple workers for improved concurrency:

```bash
flaxon run app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4
```

---

## Running with Uvicorn

Flaxon is an ASGI application. If you do not use the Flaxon CLI, run it with
an ASGI server such as Uvicorn:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

---

# Production Environment Variables

Configure your application using environment variables.

Linux/macOS

```bash
export FLAXON_ENV=production
export FLAXON_DEBUG=false
export FLAXON_SECRET_KEY=your-secret-key
export FLAXON_ALLOWED_HOSTS=api.example.com,example.com
```

Windows PowerShell

```powershell
$env:FLAXON_ENV="production"
$env:FLAXON_DEBUG="false"
$env:FLAXON_SECRET_KEY="your-secret-key"
$env:FLAXON_ALLOWED_HOSTS="api.example.com,example.com"
```

---

# Docker Deployment

## Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .

RUN pip install "flaxon[standard]"

COPY . .

CMD [
    "flaxon",
    "run",
    "app:app",
    "--host",
    "0.0.0.0",
    "--port",
    "8000",
    "--workers",
    "4"
]
```

---

## Build the Image

```bash
docker build -t my-app .
```

---

## Run the Container

```bash
docker run \
    -p 8000:8000 \
    -e FLAXON_ENV=production \
    -e FLAXON_SECRET_KEY=your-secret-key \
    my-app
```

---

# Docker Compose

```yaml
version: "3.8"

services:

  app:
    build: .
    ports:
      - "8000:8000"

    environment:
      FLAXON_ENV: production
      FLAXON_DEBUG: "false"
      FLAXON_SECRET_KEY: ${SECRET_KEY}

    depends_on:
      - db
      - redis

  db:
    image: postgres:16-alpine

    environment:
      POSTGRES_USER: flaxon
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: flaxon

  redis:
    image: redis:7-alpine
```

Start the stack:

```bash
docker compose up -d
```

---

# Reverse Proxy (Nginx)

For production deployments, place Flaxon behind a reverse proxy such as Nginx.

```nginx
server {

    listen 80;

    server_name api.example.com;

    location / {

        proxy_pass http://localhost:8000;

        proxy_set_header Host $host;

        proxy_set_header X-Real-IP $remote_addr;

        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        proxy_set_header X-Forwarded-Proto $scheme;

    }

    location /ws {

        proxy_pass http://localhost:8000;

        proxy_http_version 1.1;

        proxy_set_header Upgrade $http_upgrade;

        proxy_set_header Connection "upgrade";

    }

}
```

---

# Health Checks

Health endpoints allow load balancers, Kubernetes, and monitoring systems to verify that your application is running correctly.

```python
@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }


@app.get("/ready")
async def ready():
    # Check database, cache, or external services.
    return {
        "status": "ready"
    }
```

---

# Deployment Architecture

```text
                Internet
                    │
                    ▼
            Reverse Proxy
            (Nginx / Caddy)
                    │
                    ▼
           Flaxon Application
          (Multiple Workers)
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
   PostgreSQL               Redis
        │                       │
        └───────────────┬───────────────┘
                        ▼
                Background Services
```

---

# Recommended Production Stack

A typical production deployment includes:

- Flaxon
- Python 3.11+
- PostgreSQL
- Redis
- Nginx or Caddy
- Docker (optional)
- HTTPS with TLS
- Monitoring and logging

---

# Cloud Deployment

Flaxon applications can be deployed to many cloud providers, including:

- Render
- Railway
- Fly.io
- DigitalOcean
- AWS
- Azure
- Google Cloud Platform
- Kubernetes

Because Flaxon is ASGI-compatible, it integrates easily with modern deployment platforms.

---

# Performance Recommendations

For best performance:

- Use multiple workers.
- Enable HTTP compression.
- Use asynchronous database drivers.
- Use Redis for caching.
- Enable connection pooling.
- Serve static files through a reverse proxy or CDN.
- Keep CPU-intensive work outside the request lifecycle.

---

# Security Recommendations

Before deploying to production:

- Disable debug mode.
- Generate a strong `SECRET_KEY`.
- Restrict `ALLOWED_HOSTS`.
- Enable HTTPS.
- Keep dependencies up to date.
- Run behind a reverse proxy.
- Configure trusted proxies correctly.
- Store secrets in environment variables.

---

# Production Checklist

Before going live, verify the following:

- ✅ Set `FLAXON_ENV=production` if your application uses environment-specific configuration.
- ✅ Set `FLAXON_DEBUG=false`.
- ✅ Secure `FLAXON_SECRET_KEY`
- ✅ Configure `FLAXON_ALLOWED_HOSTS`
- ✅ HTTPS enabled
- ✅ Reverse proxy configured
- ✅ Multiple workers enabled
- ✅ Health endpoints available
- ✅ Logging configured
- ✅ Database connection pooling enabled
- ✅ Redis configured (optional)
- ✅ Backups configured
- ✅ Monitoring and alerts enabled

---

# Next Steps

After deploying your application, consider exploring:

- Middleware
- Security
- Authentication
- Background Tasks
- WebSockets
- Scaling and Performance
- Monitoring and Observability

These topics are covered in the remaining Flaxon documentation.
