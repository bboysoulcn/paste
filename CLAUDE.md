# Paste Service

A zero-friction paste service built with FastAPI, PostgreSQL, and local file storage.

## Features

- **Simple text upload**: `echo "Hello" | curl -T - http://localhost:8000/`
- **File upload with extension**: `curl -T file.txt http://localhost:8000/`
- **Image upload**: `curl -T image.png http://localhost:8000/`
- **Markdown rendering**: Files with `.md` extension render as HTML in browsers
- **Auto-expiration**: Pastes expire after 24 hours (configurable)
- **Secure deletion**: Each paste has a unique delete token

## Project Structure

```
paste/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration settings (pydantic-settings)
│   ├── models.py            # SQLAlchemy models
│   ├── database.py          # Database connection (async)
│   ├── routers/
│   │   ├── __init__.py
│   │   └── paste.py         # Paste API endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── paste_service.py # Business logic
│   │   └── image_utils.py   # Image dimension extraction (Pillow)
│   └── templates/           # (Note: markdown rendering is inline in router)
├── storage/                 # Local file storage directory
├── alembic/                 # Database migrations
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── tests/
│   ├── __init__.py
│   └── test_paste.py        # Test suite (pytest + httpx)
├── pyproject.toml           # Project dependencies
├── alembic.ini              # Alembic configuration
└── .env.example             # Environment variables template
```

## Setup

### 1. Install dependencies

```bash
pip install -e .
```

Or with dev dependencies:

```bash
pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your settings
```

Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string (asyncpg format)
- `STORAGE_PATH`: Directory for file storage (default: `./storage`)
- `EXPIRATION_HOURS`: Paste expiration time (default: 24)
- `ID_LENGTH`: Length of generated paste IDs (default: 6)
- `MAX_FILE_SIZE`: Maximum file size in bytes (default: 10485760 = 10MB)

### 3. Run database migrations

```bash
alembic upgrade head
```

### 4. Start the server

```bash
uvicorn app.main:app --reload
```

## API Usage

### Upload text

```bash
echo "Hello World" | curl -T - http://localhost:8000/
```

Response:
```json
{
  "url": "http://localhost:8000/abc123",
  "raw_url": "http://localhost:8000/abc123",
  "id": "abc123",
  "delete_token": "..."
}
```

### Upload with specific filename

```bash
echo "# Test" | curl -T - http://localhost:8000/test.md
```

### Upload image

```bash
curl -T image.png http://localhost:8000/
```

Response includes dimensions:
```json
{
  "url": "http://localhost:8000/xyz789",
  "id": "xyz789",
  "width": 1920,
  "height": 1080,
  "delete_token": "..."
}
```

### Retrieve paste

```bash
curl http://localhost:8000/<id>
```

For markdown files, open in browser for rendered HTML, or use curl for raw markdown.

### Get paste info

```bash
curl http://localhost:8000/<id>/info
```

### Delete paste

```bash
curl -X DELETE -H "X-Delete-Token: <token>" http://localhost:8000/<id>
```

## Database Schema

### `pastes` table

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `paste_id` | String(32) | Unique public identifier |
| `filename` | String(512) | Optional filename |
| `content_type` | String(128) | MIME type |
| `file_size` | Integer | Size in bytes |
| `image_width` | Integer | Image width (if applicable) |
| `image_height` | Integer | Image height (if applicable) |
| `delete_token` | String(64) | Deletion token |
| `expires_at` | DateTime | Expiration timestamp |
| `created_at` | DateTime | Creation timestamp |
| `storage_path` | String(1024) | Path to stored file |

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test
pytest tests/test_paste.py::test_upload_text_paste
```

## Key Implementation Details

### Content Type Detection
- Images are detected using PIL (Pillow) magic bytes
- Filename extensions provide hints for text-based content
- Default: `text/plain`

### ID Generation
- Uses `secrets.token_urlsafe()` for cryptographic randomness
- Configurable length (default: 6 characters)
- Collision handling: regenerates ID if already exists

### Markdown Rendering
- Uses the `markdown` library with extensions: `fenced_code`, `nl2br`, `sane_lists`
- GitHub-like CSS styling
- Detects browser vs CLI via `Accept` header

### Background Cleanup
- Expired pastes are cleaned via background tasks after each upload
- Could be extended with a scheduled task (APScheduler, cron, etc.)

### Async Support
- SQLAlchemy with asyncpg driver
- AsyncSession for database operations
- Fully async API endpoints

## Development

### Adding new API endpoints

1. Add route to `app/routers/paste.py` or create new router
2. Add business logic to `app/services/paste_service.py`
3. Update tests in `tests/test_paste.py`

### Database migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Configuration

Add new settings to `app/config.py`:

```python
class Settings(BaseSettings):
    new_setting: str = "default_value"
```

Then use via `get_settings()`:

```python
settings = get_settings()
value = settings.new_setting
```
