# BAEL Platform - Complete Setup & Deployment Guide

**Version:** 1.0.0
**Status:** Production-Ready
**Date:** February 2, 2026

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Pre-Installation Checklist](#pre-installation-checklist)
3. [Local Development Setup](#local-development-setup)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Configuration Management](#configuration-management)
7. [Running Tests](#running-tests)
8. [Monitoring & Logging](#monitoring--logging)
9. [Troubleshooting](#troubleshooting)
10. [Production Deployment Checklist](#production-deployment-checklist)

---

## System Requirements

### Minimum Requirements

- **OS:** macOS 12+, Ubuntu 20.04+, or Windows 10/11 with WSL2
- **CPU:** 4 cores minimum (8+ recommended)
- **RAM:** 8GB minimum (16GB+ recommended)
- **Disk:** 20GB free space

### Software Requirements

- **Python:** 3.10 or 3.11
- **Docker:** 20.10+ (for containerized deployment)
- **Docker Compose:** 2.0+ (for multi-container setup)
- **PostgreSQL:** 14+
- **Redis:** 7+
- **Kubernetes:** 1.24+ (for K8s deployment)
- **kubectl:** Matching K8s version

### Optional Tools

- **Helm:** 3.0+ (for K8s package management)
- **Terraform:** 1.0+ (for infrastructure-as-code)
- **git:** 2.30+

---

## Pre-Installation Checklist

```bash
# Check Python version
python --version  # Should be 3.10 or 3.11

# Check Docker installation
docker --version
docker-compose --version

# Check database connectivity
psql --version
redis-cli --version

# Verify disk space
df -h

# Check network connectivity
curl -I https://github.com
```

---

## Local Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/bael.git
cd BaelTheLordOfAll-AI
```

### 2. Create Virtual Environment

```bash
# Using Python venv
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
# Install from requirements.txt
pip install --upgrade pip
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov pytest-asyncio
pip install flake8 pylint mypy black
```

### 4. Set Up Local Databases

```bash
# PostgreSQL setup
createdb bael_dev
psql bael_dev < scripts/init_db.sql

# Or using Docker
docker run -d \
  --name bael-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:14-alpine

# Redis setup
docker run -d \
  --name bael-redis \
  -p 6379:6379 \
  redis:7-alpine
```

### 5. Configure Environment

```bash
# Create .env file
cp config/settings/.env.template config/settings/.env.local

# Edit configuration
nano config/settings/.env.local

# Required environment variables:
# DATABASE_URL=postgresql://user:password@localhost:5432/bael_dev
# REDIS_URL=redis://localhost:6379/0
# LOG_LEVEL=DEBUG
# ENVIRONMENT=development
```

### 6. Initialize Application

```bash
# Run migrations
python -m alembic upgrade head

# Seed test data (optional)
python scripts/seed_data.py

# Verify setup
python -c "from core import *; print('✓ Core modules imported successfully')"
```

### 7. Start Development Server

```bash
# Using uvicorn
uvicorn api.server:app --reload --port 8000

# Or using built-in server
python main.py
```

**Verification:**

```bash
# Health check
curl http://localhost:8000/health

# Should return:
# {"status": "healthy", "version": "1.0.0", "timestamp": "2026-02-02T..."}
```

---

## Docker Deployment

### 1. Build Docker Image

```bash
# Standard build
docker build -f docker/Dockerfile -t bael:latest .

# With build arguments
docker build \
  -f docker/Dockerfile \
  -t bael:1.0.0 \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  .

# For production registry
docker build -t registry.example.com/bael:latest .
```

### 2. Run with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f bael-api

# Stop services
docker-compose down

# Full cleanup
docker-compose down -v
```

**Services:**

- **bael-api:** Main application (port 8000)
- **postgres:** Database (port 5432)
- **redis:** Cache (port 6379)
- **prometheus:** Metrics (port 9090)
- **grafana:** Dashboard (port 3000)

### 3. Container Health Checks

```bash
# Check container status
docker-compose ps

# View container logs
docker logs bael-api

# Enter container shell
docker exec -it bael-api bash

# Check health endpoint
curl http://localhost:8000/health
```

### 4. Scale Services

```bash
# Scale worker replicas
docker-compose up -d --scale bael-worker=3

# Scale specific service
docker-compose up -d --scale redis=2
```

---

## Kubernetes Deployment

### 1. Create Namespace

```bash
kubectl create namespace bael
kubectl config set-context --current --namespace=bael
```

### 2. Create Secrets

```bash
# Database credentials
kubectl create secret generic db-credentials \
  --from-literal=url=postgresql://bael:password@postgres:5432/bael \
  --from-literal=user=bael \
  --from-literal=password=secure_password

# Redis credentials
kubectl create secret generic redis-credentials \
  --from-literal=url=redis://redis:6379/0

# API keys
kubectl create secret generic api-keys \
  --from-literal=jwt-secret=your_jwt_secret_here \
  --from-literal=api-key=your_api_key_here
```

### 3. Deploy Application

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployments.yaml
kubectl apply -f k8s/services.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/ingress.yaml

# Or using Helm
helm install bael ./helm/bael \
  --namespace bael \
  --values helm/values.yaml
```

### 4. Verify Deployment

```bash
# Check deployments
kubectl get deployments
kubectl get pods
kubectl get services

# Check logs
kubectl logs -f deployment/bael-api

# Port forward for local testing
kubectl port-forward service/bael-api 8000:8000

# Health check
curl http://localhost:8000/health
```

### 5. Scaling & Updates

```bash
# Manual scaling
kubectl scale deployment bael-api --replicas=5

# Check HPA status
kubectl get hpa

# View metrics
kubectl top nodes
kubectl top pods

# Update image
kubectl set image deployment/bael-api \
  bael-api=bael:1.1.0 \
  --record

# Monitor rollout
kubectl rollout status deployment/bael-api

# Rollback if needed
kubectl rollout undo deployment/bael-api
```

---

## Configuration Management

### Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:password@host:5432/db
REDIS_URL=redis://host:6379/0
LOG_LEVEL=INFO
ENVIRONMENT=production

# Optional
API_PORT=8000
MAX_WORKERS=4
BATCH_SIZE=100
CACHE_TTL=3600
REQUEST_TIMEOUT=30
```

### Configuration Files

```
config/
├── settings/
│   ├── base.py          # Base configuration
│   ├── development.py   # Dev overrides
│   ├── staging.py       # Staging overrides
│   └── production.py    # Production overrides
├── profiles/            # User profiles
├── secrets/             # Secrets management
└── settings.yaml        # YAML configuration
```

### Loading Configuration

```python
# Automatic detection based on ENVIRONMENT
from config import settings

# Override specific settings
settings.LOG_LEVEL = "DEBUG"
settings.DATABASE_URL = "postgresql://..."

# Load from file
from config import load_config
config = load_config("config/settings.yaml")
```

---

## Running Tests

### Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_phase1_infrastructure.py -v

# Run with coverage
pytest tests/ --cov=core --cov-report=html

# Run with specific markers
pytest tests/ -m unit -v
```

### Integration Tests

```bash
# Run integration tests
pytest tests/ -m integration -v

# With Docker services running
docker-compose up -d postgres redis
pytest tests/ -m integration --tb=short
```

### Test Coverage

```bash
# Generate coverage report
pytest tests/ --cov=core --cov-report=term-missing

# Coverage threshold check
pytest tests/ --cov=core --cov-fail-under=80

# HTML coverage report
pytest tests/ --cov=core --cov-report=html
open htmlcov/index.html
```

### Performance Tests

```bash
# Run performance benchmarks
pytest tests/ -m performance --benchmark-only

# With profiling
pytest tests/ -m performance --profile
```

---

## Monitoring & Logging

### Prometheus Metrics

```bash
# Access Prometheus UI
http://localhost:9090

# Query metrics
curl http://localhost:9090/api/v1/query?query=up

# Custom metrics
from prometheus_client import Counter, Histogram

request_count = Counter('requests_total', 'Total requests')
request_duration = Histogram('request_duration_seconds', 'Request duration')
```

### Grafana Dashboards

```bash
# Access Grafana
http://localhost:3000

# Default credentials: admin/admin

# Import dashboards
1. Click "+" → "Import"
2. Enter dashboard ID or upload JSON
3. Select Prometheus data source
4. Save dashboard
```

### Logging

```bash
# Structured logging
from core.logging import get_logger

logger = get_logger(__name__)

logger.info("Application started", extra={
    'version': '1.0.0',
    'environment': 'production'
})

# Log levels
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")

# View logs
docker-compose logs -f
kubectl logs -f deployment/bael-api
```

---

## Troubleshooting

### Common Issues

#### Database Connection Errors

```bash
# Check PostgreSQL
psql -h localhost -U postgres -d bael

# Check connection string
echo $DATABASE_URL

# Verify network
telnet localhost 5432

# Docker: check postgres service
docker-compose logs postgres
```

#### Redis Connection Errors

```bash
# Check Redis
redis-cli ping

# Check connectivity
telnet localhost 6379

# View Redis logs
docker-compose logs redis
```

#### High Memory Usage

```bash
# Monitor memory
docker stats

# Check for memory leaks
python -m memory_profiler main.py

# Restart service
docker-compose restart bael-api
```

#### Slow Queries

```bash
# Enable query logging
SET log_statement = 'all';

# Check query performance
EXPLAIN ANALYZE SELECT ...;

# View slow query log
tail -f logs/slow_queries.log
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Verbose output
python main.py --verbose

# Interactive debugging
python -m pdb main.py
```

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/health/db

# Cache health
curl http://localhost:8000/health/cache

# Full system status
curl http://localhost:8000/status
```

---

## Production Deployment Checklist

### Pre-Deployment

- [ ] All tests passing (pytest coverage > 80%)
- [ ] Security scans completed (trivy, bandit)
- [ ] Code review approved
- [ ] Migrations tested in staging
- [ ] Database backups in place
- [ ] Secrets configured properly
- [ ] SSL/TLS certificates valid
- [ ] DNS records updated
- [ ] Load balancer configured
- [ ] Monitoring configured

### Deployment

```bash
# 1. Build and test Docker image
docker build -t registry/bael:1.0.0 .
docker run --rm registry/bael:1.0.0 pytest tests/

# 2. Push to registry
docker push registry/bael:1.0.0

# 3. Deploy to staging
kubectl set image deployment/bael-api \
  bael-api=registry/bael:1.0.0 \
  --namespace staging \
  --record

# 4. Run smoke tests
./scripts/smoke_tests.sh

# 5. Deploy to production
kubectl set image deployment/bael-api \
  bael-api=registry/bael:1.0.0 \
  --namespace production \
  --record

# 6. Verify deployment
kubectl rollout status deployment/bael-api -n production
```

### Post-Deployment

- [ ] Health checks passing
- [ ] Metrics being collected
- [ ] No error spike in logs
- [ ] Performance meets SLA
- [ ] Backup verified
- [ ] Team notified
- [ ] Document deployment
- [ ] Schedule post-mortem if needed

### Rollback Procedure

```bash
# Quick rollback
kubectl rollout undo deployment/bael-api

# Specific revision
kubectl rollout history deployment/bael-api
kubectl rollout undo deployment/bael-api --to-revision=2

# Verify rollback
kubectl rollout status deployment/bael-api
```

---

## Additional Resources

- **API Documentation:** [docs/API_DOCUMENTATION.py](../docs/API_DOCUMENTATION.py)
- **Architecture Guide:** [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
- **Kubernetes Guide:** [k8s/README.md](../k8s/README.md)
- **Docker Guide:** [docker/README.md](../docker/README.md)

---

## Support & Contact

- **Issues:** GitHub Issues
- **Discussions:** GitHub Discussions
- **Documentation:** [docs/](../docs/)
- **Examples:** [examples/](../examples/)

---

**Last Updated:** February 2, 2026
**Maintained By:** BAEL Development Team
