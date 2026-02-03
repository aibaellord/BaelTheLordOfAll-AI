# BAEL Deployment Guide

Complete guide for deploying BAEL v2.1.0 in production.

## Quick Start

### Docker Deployment

```bash
# Clone repository
git clone https://github.com/bael/bael
cd bael

# Build and run with Docker Compose
docker-compose up -d

# Verify deployment
curl http://localhost:8000/health
```

## System Requirements

### Minimum

- **CPU:** 2 cores
- **RAM:** 4 GB
- **Disk:** 10 GB
- **Python:** 3.8+

### Recommended

- **CPU:** 4+ cores
- **RAM:** 8+ GB
- **Disk:** 50 GB SSD
- **Python:** 3.10+

## Docker Deployment

### Single Container

```bash
docker build -t bael:2.1.0 .
docker run -p 8000:8000 -v bael_data:/data bael:2.1.0
```

### Docker Compose

See `docker-compose.yml` for complete setup with:

- BAEL API server
- PostgreSQL database
- Redis cache
- Prometheus monitoring
- Optional: Grafana dashboards

### Environment Variables

```bash
# API Configuration
BAEL_HOST=0.0.0.0
BAEL_PORT=8000
BAEL_LOG_LEVEL=INFO
BAEL_API_KEY=your_secure_key

# Database
DATABASE_URL=postgresql://user:password@localhost/bael
REDIS_URL=redis://localhost:6379

# Monitoring
PROMETHEUS_PORT=9090
ENABLE_TRACING=true

# Security
SECRET_KEY=your_secret_key
ALLOWED_ORIGINS=http://localhost:3000
```

## Kubernetes Deployment

### Prerequisites

```bash
kubectl create namespace bael
kubectl create secret generic bael-config --from-file=config.yaml -n bael
```

### Deploy

```bash
kubectl apply -f k8s/ -n bael
```

### Verify

```bash
kubectl get pods -n bael
kubectl logs -f deployment/bael-api -n bael
kubectl port-forward svc/bael-api 8000:8000 -n bael
```

## Configuration

### API Configuration

```yaml
# config/settings/production.yaml
server:
  host: 0.0.0.0
  port: 8000
  workers: 4
  timeout: 30

database:
  engine: postgresql
  pool_size: 20
  max_overflow: 0
  timeout: 30

cache:
  backend: redis
  ttl: 3600

security:
  api_key_required: true
  rate_limit: 1000
  cors_origins:
    - http://localhost:3000

monitoring:
  metrics_enabled: true
  tracing_enabled: true
  health_check_interval: 30
```

### Database Setup

```bash
# Create database
createdb bael

# Run migrations
python -m alembic upgrade head

# Load initial data
python -m scripts.load_initial_data
```

### Redis Cache

```bash
# Start Redis
redis-server

# Or with Docker
docker run -d -p 6379:6379 redis:7
```

## Monitoring Setup

### Prometheus

```bash
# Start Prometheus
docker run -d -p 9090:9090 \
  -v /path/to/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# Access: http://localhost:9090
```

### Grafana

```bash
# Start Grafana
docker run -d -p 3000:3000 \
  -e GF_SECURITY_ADMIN_PASSWORD=admin \
  grafana/grafana

# Access: http://localhost:3000 (admin/admin)
# Import dashboards from: grafana/dashboards/
```

### Health Checks

```bash
# System health
curl http://localhost:8000/health

# Detailed status
curl http://localhost:8000/v1/stats

# Prometheus metrics
curl http://localhost:8000/metrics
```

## Performance Optimization

### API Optimization

1. **Connection Pooling:**

   ```yaml
   database:
     pool_size: 20
     max_overflow: 10
   ```

2. **Caching:**

   ```python
   # Configure cache TTL
   CACHE_TTL = 3600
   CACHE_MAX_SIZE = 10000
   ```

3. **Workers:**
   ```yaml
   server:
     workers: 4 # CPUs * 2
   ```

### Memory Optimization

1. **Garbage Collection:**

   ```python
   import gc
   gc.set_threshold(100000)
   ```

2. **Connection Limits:**
   ```yaml
   database:
     max_connections: 20
   ```

## Backup & Recovery

### Database Backup

```bash
# PostgreSQL
pg_dump bael > backup.sql

# With compression
pg_dump bael | gzip > backup.sql.gz

# Restore
psql bael < backup.sql
```

### Data Volume Backup

```bash
# Docker volume backup
docker run --rm -v bael_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/bael_data.tar.gz /data
```

## Troubleshooting

### API Won't Start

```bash
# Check logs
docker logs bael-api

# Verify configuration
python -c "from config import settings; print(settings)"

# Test database connection
python -c "from db import test_connection; test_connection()"
```

### High Memory Usage

```bash
# Check memory
ps aux | grep python

# Review logs for errors
tail -f logs/bael.log

# Clear cache
curl -X POST http://localhost:8000/admin/cache/clear
```

### Database Connection Issues

```bash
# Check PostgreSQL
psql -h localhost -U user -d bael -c "SELECT 1"

# Check Redis
redis-cli ping

# Verify connection strings
echo $DATABASE_URL
echo $REDIS_URL
```

## Security Considerations

### API Security

1. **API Key Management:**

   ```bash
   # Generate secure key
   python -c "import secrets; print(secrets.token_urlsafe(32))"

   # Set environment variable
   export BAEL_API_KEY="your_key"
   ```

2. **CORS Configuration:**

   ```yaml
   security:
     cors_origins:
       - https://yourdomain.com
     cors_methods:
       - GET
       - POST
     cors_credentials: true
   ```

3. **Rate Limiting:**
   ```yaml
   security:
     rate_limit: 1000 # requests per minute
     rate_limit_burst: 100
   ```

### Database Security

1. **Connection Encryption:**

   ```yaml
   database:
     ssl_mode: require
     ssl_cert: /path/to/cert
   ```

2. **User Permissions:**
   ```sql
   CREATE USER bael WITH PASSWORD 'secure_password';
   GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO bael;
   ```

## Scaling

### Horizontal Scaling

```bash
# Load balancer configuration
# Use nginx or similar

upstream bael {
    server localhost:8000;
    server localhost:8001;
    server localhost:8002;
}

server {
    listen 80;
    location / {
        proxy_pass http://bael;
    }
}
```

### Vertical Scaling

```yaml
# Increase resources
docker run -m 8g --cpus 4 bael:2.1.0
```

## Monitoring & Alerts

### Key Metrics

- API Response Time: p95 < 100ms
- Error Rate: < 0.1%
- Database Connections: < 20
- Memory Usage: < 4GB
- Cache Hit Ratio: > 80%

### Alert Configuration

```yaml
# prometheus/rules.yml
groups:
  - name: bael
    rules:
      - alert: HighErrorRate
        expr: rate(bael_errors_total[5m]) > 0.01
        for: 5m

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, bael_request_duration_seconds) > 1
        for: 5m
```

## Maintenance

### Regular Tasks

1. **Daily:**
   - Check health endpoints
   - Review error logs
   - Monitor resource usage

2. **Weekly:**
   - Database maintenance
   - Cache optimization
   - Backup verification

3. **Monthly:**
   - Performance analysis
   - Security updates
   - Dependency updates

### Upgrading

```bash
# Backup before upgrade
docker-compose down -v && docker-compose up -d

# Migrate data if needed
python -m alembic upgrade head

# Verify deployment
curl http://localhost:8000/health
```

## Support

- 📖 Documentation: https://docs.bael.ai
- 💬 Discord: https://discord.gg/bael
- 🐛 Issues: https://github.com/bael/bael/issues
- 📧 Email: support@bael.ai

---

For more information, see [DEVELOPMENT_SUMMARY.md](DEVELOPMENT_SUMMARY.md)
