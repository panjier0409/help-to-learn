FROM python:3.12-slim

# Install system dependencies: ffmpeg, yt-dlp
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp \
    && chmod a+rx /usr/local/bin/yt-dlp \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# Copy source code
COPY backend/ ./backend/

# Create storage directories
RUN mkdir -p storage/originals storage/audio storage/temp

ENV STORAGE_BASE_PATH=/app/storage
ENV DATABASE_URL=sqlite:////app/data/data.db

EXPOSE 8000

# Start both the API server and the worker in the same container
CMD ["sh", "-c", "uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 & uv run python backend/worker.py"]
