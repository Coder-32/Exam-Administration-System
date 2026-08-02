# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Install system dependencies
# libpq-dev: required for psycopg2 compilation
# tesseract-ocr + libtesseract-dev: required for pytesseract OCR feature
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    curl \
    libpq-dev \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY CONFIG.py .
COPY static/ ./static/
COPY templates/ ./templates/
COPY service/ ./service/
COPY database/ ./database/
COPY schedule_storage/ ./schedule_storage/

# Create necessary directories
RUN mkdir -p schedule_storage database

# Expose port (Internal Container Port)
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Health check (Checking internal port 5000)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000')" || exit 1

# Run Flask application with gunicorn on internal port 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
