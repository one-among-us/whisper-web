# Use NVIDIA CUDA runtime as base
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Install system dependencies
# 1. Add deadsnakes PPA for Python 3.12
# 2. Install Python 3.12 and other required system libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    curl \
    ca-certificates \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    ffmpeg \
    libmagic1 \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/uv
ENV PATH="/uv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment
# We use /app/.venv and add it to PATH
RUN uv venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv sync --frozen --no-cache

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy the application code
COPY . .

# Create directories for data persistence (matches main.py paths)
RUN mkdir -p /ws/tmp-whisper/audio /ws/tmp-whisper/transcription

# Expose the port from main.py
EXPOSE 49585

# Run the application
CMD ["python", "main.py"]
