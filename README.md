# Face Recognition API

API for face recognition with PostgreSQL backend using FastAPI and InsightFace.

## Features

- User authentication with JWT tokens
- Face enrollment and biometric authentication
- Face quality validation
- Anti-spoofing detection
- Secure face embedding encryption
- Multiple input formats (base64 or file upload)

## Quick Start

### Using Docker

```bash
# Build and start
docker-compose -f docker-compose.app.yml up -d --build

# View logs
docker-compose -f docker-compose.app.yml logs -f

# Stop
docker-compose -f docker-compose.app.yml down
```

### Local Development

```bash
# Install dependencies
uv pip install -e .

# Run migrations
task migrate

# Start server
task run
```

## API Documentation

Once running, access the interactive API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Environment Variables

Copy `.env.docker.example` to `.env` and configure:

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT secret key
- `FACE_ENCRYPTION_KEY`: Fernet encryption key for face embeddings

## License

MIT