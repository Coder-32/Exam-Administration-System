# Docker Deployment Guide

## Overview
This guide explains how to build, run, and deploy the Exam Administration System using Docker.

## Table of Contents
1. [Running Locally with Docker](#running-locally-with-docker)
2. [Building for Docker Hub](#building-for-docker-hub)
3. [Pushing to Docker Hub](#pushing-to-docker-hub)
4. [Using from Docker Hub](#using-from-docker-hub)
5. [Production Deployment](#production-deployment)

---

## Running Locally with Docker

### Quick Start
```bash
# Build and start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f exam-admin

# Stop services
docker-compose down
```

### Customizing Configuration
Create a `.env` file from the example:
```bash
cp .env.example .env
```

Edit `.env` to customize:
```env
# Database
POSTGRES_DB=exam_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password

# Application
DB_HOST=db
DB_PORT=5432
PORT=10000
```

### Accessing Services
- **Web UI**: http://localhost:10000
- **PostgreSQL**: localhost:5432

---

## Building for Docker Hub

### Prerequisites
- Docker installed
- Docker Hub account (https://hub.docker.com)
- Application image: `satwik006/exam-administration-system`

### Step 1: Build the Image Locally
```bash
# Build the Docker image
docker build -t satwik006/exam-administration-system:latest .

# Tag with version (optional)
docker build -t satwik006/exam-administration-system:v1.0.0 .
```

### Step 2: Test the Image
```bash
# Run the image locally using docker-compose
docker-compose up -d

# Or manually run with PostgreSQL
docker run -d \
  --name exam-db \
  -e POSTGRES_DB=exam_db \
  -e POSTGRES_PASSWORD=postgres \
  postgres:15

docker run -d \
  --name exam-admin \
  -p 10000:10000 \
  -e DB_HOST=exam-db \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -e DB_NAME=exam_db \
  satwik006/exam-administration-system:latest
```

### Step 3: Verify the Application
```bash
# Check if app is running
curl http://localhost:10000

# View logs
docker logs exam-admin
```

---

## Pushing to Docker Hub

### Step 1: Login to Docker Hub
```bash
docker login
# Enter your Docker Hub credentials
```

### Step 2: Push the Image
```bash
# Push latest tag
docker push satwik006/exam-administration-system:latest

# Push version tag (optional)
docker push satwik006/exam-administration-system:v1.0.0
```

Monitor progress and wait for upload to complete.

### Step 3: Verify on Docker Hub
Visit: https://hub.docker.com/repository/docker/satwik006/exam-administration-system

---

## Using from Docker Hub

### For Users Pulling Your Image

#### Option 1: With Docker Compose (Recommended)
Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    container_name: exam-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: exam_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - db_data:/var/lib/postgresql/data

  exam-admin:
    image: satwik006/exam-administration-system:latest
    container_name: exam-administration-system
    ports:
      - "10000:10000"
    environment:
      - DB_HOST=db
      - DB_USER=postgres
      - DB_PASSWORD=postgres
      - DB_NAME=exam_db
      - DB_PORT=5432
    depends_on:
      db:
        condition: service_started
    volumes:
      - ./schedule_storage:/app/schedule_storage
      - ./database:/app/database

volumes:
  db_data:
```

Start with:
```bash
docker-compose up -d
```

#### Option 2: Direct Docker Run
```bash
# First, start PostgreSQL
docker run -d \
  --name exam-db \
  -e POSTGRES_DB=exam_db \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15

# Then start the app
docker run -d \
  --name exam-admin \
  -p 10000:10000 \
  -e DB_HOST=exam-db \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -e DB_NAME=exam_db \
  --link exam-db \
  satwik006/exam-administration-system:latest
```

---

## Production Deployment

### Container Orchestration
For production with multiple replicas, use Kubernetes or Docker Swarm.

### Environment Variables
Always use strong passwords in production:
```env
POSTGRES_PASSWORD=very_strong_random_password
DB_PASSWORD=very_strong_random_password
FLASK_ENV=production
```

### Persistent Data
- Database data is stored in the `db_data` volume
- Application data in mounted volumes: `./schedule_storage`, `./database`
- Backup regularly:
  ```bash
  docker-compose exec db pg_dump -U postgres exam_db > backup.sql
  ```

### Monitoring
```bash
# View container status
docker-compose ps

# View resource usage
docker stats

# View logs
docker-compose logs --tail=50 -f
```

### Updating the Application
1. Pull the latest image: `docker pull satwik006/exam-administration-system:latest`
2. Restart services: `docker-compose up -d`
3. Check logs: `docker-compose logs -f`

---

## Troubleshooting

### Container fails to start
```bash
docker-compose logs exam-admin
```

### Database connection error
- Ensure `db` service is healthy: `docker-compose ps`
- Check database is running: `docker exec exam-db psql -U postgres -d exam_db`

### Port already in use
Change ports in `docker-compose.yml`:
```yaml
ports:
  - "8000:10000"  # Access via localhost:8000
```

---

## Docker Hub Repository
- **Repository**: https://hub.docker.com/repository/docker/satwik006/exam-administration-system
- **Pull Command**: `docker pull satwik006/exam-administration-system:latest`
