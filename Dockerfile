# Use Python 3.12 slim image for smaller size
FROM python:3.12-slim

# Accept build argument for GPU support
ARG USE_GPU=false

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    USE_GPU=${USE_GPU}

# Install system dependencies required for OpenCV, InsightFace, and other libraries
# Build tools are needed for compiling C++ extensions (insightface)
RUN apt-get update && apt-get install -y \
    build-essential \
    g++ \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1 \
    libgthread-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Poetry
RUN pip install poetry

# Configure Poetry to not create virtual environment and increase timeout
RUN poetry config virtualenvs.create false && \
    poetry config installer.max-workers 10 && \
    poetry config installer.parallel true

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies with Poetry (without dev dependencies)
# Conditionally install GPU or CPU group based on USE_GPU env var
# Using verbose mode to see progress and avoid timeout issues
RUN if [ "$USE_GPU" = "true" ]; then \
        echo "Installing with GPU support..." && \
        poetry install --no-interaction --no-ansi --no-root --without dev --with gpu -vv; \
    else \
        echo "Installing with CPU only..." && \
        poetry install --no-interaction --no-ansi --no-root --without dev,gpu --with cpu -vv; \
    fi

# Copy application code
COPY . .

# Create directory for InsightFace models
RUN mkdir -p /root/.insightface/models

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]