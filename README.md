# Paste Service

A zero-friction paste service built with FastAPI, inspired by [p.est.im](https://github.com/est/p.est.im).

## Features

- 🚀 Simple CLI upload: `echo "Hello" | curl -T - http://localhost:8000/`
- 📝 Markdown rendering with syntax highlighting
- 🖼️ Image upload with automatic dimension extraction
- ⏰ Auto-expiring pastes (default 24 hours)
- 🔒 Secure deletion with unique tokens
- 🗄️ PostgreSQL metadata + local file storage

## Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
# Start all services (PostgreSQL + Paste service)
docker-compose up -d

# Run database migrations
docker-compose exec paste alembic upgrade head

# View logs
docker-compose logs -f paste
```

### Option 2: Local Development

```bash
# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your database settings

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

### Option 3: Using Pre-built Docker Image

```bash
# Pull the image
docker pull ghcr.io/<username>/paste:latest

# Run with PostgreSQL
docker run -d \
  --name paste \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db \
  ghcr.io/<username>/paste:latest
```

## Usage Examples

```bash
# Upload text
echo "Hello World" | curl -T - http://localhost:8000/

# Upload markdown
echo "# Hello" | curl -T - http://localhost:8000/hello.md

# Upload image
curl -T image.png http://localhost:8000/

# Delete paste
curl -X DELETE -H "X-Delete-Token: <token>" http://localhost:8000/<id>
```

## Documentation

- [CLAUDE.md](CLAUDE.md) - Detailed project documentation
- [DEPLOYMENT.md](DEPLOYMENT.md) - Docker deployment guide

## Development

```bash
# Using Makefile
make install     # Install dependencies
make test        # Run tests
make lint        # Run linting
make dev         # Start development server
make up          # Start Docker Compose services
make migrate     # Run database migrations (Docker)
```

## CI/CD

This project uses GitHub Actions for:

- **Continuous Integration**: Run tests and linting on every push
- **Docker Build**: Automatically build multi-architecture Docker images
- **Image Publishing**: Push images to GitHub Container Registry

Images are built for `linux/amd64` and `linux/arm64` platforms.
