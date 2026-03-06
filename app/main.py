"""Main FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import async_session_maker, engine
from app.routers import paste
from app.services.paste_service import clean_expired

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="Paste Service",
    description="A zero-friction paste service",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(paste.router, tags=["paste"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint with usage information."""
    return {
        "service": "Paste Service",
        "version": "0.1.0",
        "usage": {
            "upload_text": "echo 'Hello World' | curl -T - http://localhost:8000/",
            "upload_file": "curl -T file.txt http://localhost:8000/",
            "upload_image": "curl -T image.png http://localhost:8000/",
            "upload_markdown": "echo '# Hello' | curl -T - http://localhost:8000/hello.md",
            "delete": "curl -X DELETE -H 'X-Delete-Token: <token>' http://localhost:8000/<id>",
            "info": "curl http://localhost:8000/<id>/info",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
