# BAEL Platform - Deployment Procedures Guide

**Version:** 1.0.0
**Status:** Production-Ready
**Date:** February 2, 2026

---

## Table of Contents

1. [Deployment Strategy](#deployment-strategy)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Staging Deployment](#staging-deployment)
4. [Production Deployment](#production-deployment)
5. [Rollback Procedures](#rollback-procedures)
6. [Scaling & Load Balancing](#scaling--load-balancing)
7. [Database Migrations](#database-migrations)
8. [Monitoring & Alerting](#monitoring--alerting)
9. [Disaster Recovery](#disaster-recovery)
10. [Post-Deployment Validation](#post-deployment-validation)

---

## Deployment Strategy

### Blue-Green Deployment

**Advantages:** Zero downtime, instant rollback

```
Blue (Current Production)
    ↓
Green (New Version)
    ↓
Route Traffic to Green
    ↓
Keep Blue as Fallback
    ↓
Decommission Blue after validation
```

### Canary Deployment

**Advantages:** Gradual risk introduction, performance metrics

```
Existing Version (95% traffic)
    ↓
New Version (5% traffic) → Monitor metrics
    ↓
New Version (25% traffic) → Monitor metrics
    ↓
New Version (50% traffic) → Monitor metrics
    ↓
New Version (100% traffic)
    ↓
Retire old version
```

### Rolling Deployment

**Advantages:** Simple, minimal resources

```
Replica 1: Running old version
    ↓
Update Replica 1 to new version
    ↓
Replica 2: Running old version
    ↓
Update Replica 2 to new version
    ...
Until all replicas updated
```

**Recommended:** Blue-green for critical systems, canary for new features

---

## Pre-Deployment Checklist

### Code Quality

- [ ] All tests passing locally (pytest coverage > 80%)
- [ ] Code review approved
- [ ] Type checking clean (mypy)
- [ ] Lint checks clean (flake8)
- [ ] Security scan clean (bandit)
- [ ] No deprecated dependencies
- [ ] Documentation updated
- [ ] API documentation updated
- [ ] Release notes prepared
- [ ] Version bumped

### Infrastructure

- [ ] Database backups created
- [ ] Backup tested and verified
- [ ] Compute resources available
- [ ] Storage capacity verified
- [ ] Network connectivity confirmed
- [ ] SSL certificates valid (> 30 days)
- [ ] Monitoring systems operational
- [ ] Alerting rules configured
- [ ] Runbooks updated
- [ ] Team notified of maintenance window

### Testing

- [ ] Unit tests passed (all phases)
- [ ] Integration tests passed
- [ ] Performance tests acceptable
- [ ] Security tests clean
- [ ] Staging environment mirrors production
- [ ] Load testing completed
- [ ] Failover testing completed
- [ ] Smoke tests defined
- [ ] Rollback tested
- [ ] Monitoring tested

### Documentation

- [ ] Deployment plan documented
- [ ] Known issues documented
- [ ] Rollback procedure documented
- [ ] Scaling parameters documented
- [ ] Health check endpoints documented
- [ ] Support contacts updated
- [ ] Status page prepared
- [ ] Communication plan ready

---

## Staging Deployment

### 1. Build & Push Image

```bash
# Build Docker image
docker build \
  -f docker/Dockerfile \
  -t registry.example.com/bael:v1.0.0-staging \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  .

# Push to registry
docker push registry.example.com/bael:v1.0.0-staging

# Verify image
docker pull registry.example.com/bael:v1.0.0-staging
docker inspect registry.example.com/bael:v1.0.0-staging
```

### 2. Deploy to Staging

```bash
# Switch to staging namespace
kubectl config set-context --current --namespace=staging

# Create/update deployment
kubectl set image deployment/bael-api \
  bael-api=registry.example.com/bael:v1.0.0-staging \
  --record

# Monitor rollout
kubectl rollout status deployment/bael-api --timeout=5m
```

### 3. Verify Deployment

```bash
# Check pod status
kubectl get pods -o wide

# Check service endpoints
kubectl get endpoints bael-api

# Port-forward for local testing
kubectl port-forward service/bael-api 8000:8000

# Health check
curl -i http://localhost:8000/health

# Check application logs
kubectl logs -f deployment/bael-api --tail=50

# Check infrastructure logs
kubectl logs -f deployment/bael-api --previous
```

### 4. Run Smoke Tests

```bash
# API health
curl -f http://localhost:8000/health

# Database connectivity
curl -f http://localhost:8000/health/db

# Cache connectivity
curl -f http://localhost:8000/health/cache

# Workers health
curl -f http://localhost:8001/health

# API response time
time curl http://localhost:8000/api/test

# Load test
ab -n 1000 -c 10 http://localhost:8000/api/test
```

### 5. Performance Baseline

```bash
# Capture metrics
kubectl get --all-namespaces=false --show-kind=false -o json \
  | jq '.items[] | {name: .metadata.name, cpu: .usage.cpu, memory: .usage.memory}' \
  > staging_metrics_baseline.json

# Check database performance
psql -h postgres.staging -U bael -d bael -c "
  SELECT query, calls, mean_time
  FROM pg_stat_statements
  ORDER BY mean_time DESC
  LIMIT 10;"

# Monitor for 15 minutes
watch -n 5 'kubectl top pods'
```

### 6. Data Integrity Check

```bash
# Verify migrations
psql -h postgres.staging -U bael -d bael -c "
  SELECT version, installed_on
  FROM alembic_version
  ORDER BY installed_on DESC LIMIT 5;"

# Check data consistency
psql -h postgres.staging -U bael -d bael -c "
  SELECT table_name, row_count
  FROM pg_stat_user_tables
  WHERE row_count > 0
  ORDER BY row_count DESC LIMIT 10;"

# Validate key metrics
curl http://localhost:8000/api/metrics/summary
```

---

## Production Deployment

### 1. Pre-Deployment Window

**24 hours before:**

- [ ] Announce in #deployments Slack channel
- [ ] Send notification email to stakeholders
- [ ] Brief on-call team
- [ ] Prepare rollback scripts

**1 hour before:**

- [ ] Final health check on all systems
- [ ] Confirm all team members online
- [ ] Start deployment recording
- [ ] Notify users if needed

### 2. Blue-Green Setup

```bash
# Current production: BLUE
# New version: GREEN

# Create green environment
kubectl create namespace bael-green

# Copy secrets and ConfigMaps to green
kubectl get secret -n bael-blue -o yaml | \
  sed 's/namespace: bael-blue/namespace: bael-green/' | \
  kubectl apply -f -

kubectl get configmap -n bael-blue -o yaml | \
  sed 's/namespace: bael-blue/namespace: bael-green/' | \
  kubectl apply -f -

# Deploy to green
kubectl set image deployment/bael-api \
  -n bael-green \
  bael-api=registry.example.com/bael:v1.0.0 \
  --record
```

### 3. Green Validation

```bash
# Wait for readiness
kubectl rollout status deployment/bael-api -n bael-green --timeout=10m

# Health checks
kubectl port-forward -n bael-green service/bael-api 8000:8000 &
curl -f http://localhost:8000/health

# Database integrity
curl -f http://localhost:8000/health/db

# Cache connectivity
curl -f http://localhost:8000/health/cache

# Performance baseline
ab -n 1000 -c 10 http://localhost:8000/api/test

# Metrics comparison with blue
kubectl top pods -n bael-green
kubectl top pods -n bael-blue
```

### 4. Traffic Switch

```bash
# Update service to route to green
kubectl patch service bael-api -n bael \
  -p '{"spec":{"selector":{"version":"green"}}}'

# Verify traffic is flowing
kubectl logs -f deployment/bael-api -n bael-green

# Monitor for 5 minutes
watch -n 5 'kubectl top pods -n bael-green'
```

### 5. Monitor Post-Deployment

```bash
# Monitor error rates
curl http://localhost:9090/api/v1/query?query='rate(http_requests_total{status=~"5.."}[5m])'

# Check latency
curl http://localhost:9090/api/v1/query?query='http_request_duration_seconds_p95'

# Verify no memory leaks
watch -n 30 'kubectl top pods -n bael-green'

# Check database connections
psql -h postgres -U bael -d bael -c "
  SELECT count(*) FROM pg_stat_activity
  WHERE state = 'active';"

# Monitor queue depth
curl http://localhost:8000/api/queue/depth
```

### 6. Final Validation (after 1 hour)

```bash
# All metrics normal: yes/no
# Error rates acceptable: yes/no
# Performance acceptable: yes/no
# Database healthy: yes/no
# No unusual patterns: yes/no

# If all YES → Proceed to cleanup
# If any NO → Execute rollback (see Rollback Procedures)
```

### 7. Cleanup Old Version (BLUE)

```bash
# After 24 hours in green, decommission blue
kubectl delete namespace bael-blue

# Or keep blue for 7 days as fallback
kubectl label deployment bael-api -n bael-blue archived=true
```

---

## Rollback Procedures

### Immediate Rollback (< 5 minutes)

**Use when:** Critical errors, data corruption, or service unavailability

```bash
# Option 1: Switch service back to blue
kubectl patch service bael-api -n bael \
  -p '{"spec":{"selector":{"version":"blue"}}}'

# Verify traffic
kubectl logs -f deployment/bael-api -n bael-blue

# Option 2: Delete green namespace
kubectl delete namespace bael-green

# Restore previous version
kubectl rollout undo deployment/bael-api -n bael-blue
```

### Gradual Rollback (5-30 minutes)

**Use when:** Significant issues detected during canary phase

```bash
# 1. Route 50% traffic back to blue
kubectl patch service bael-api \
  -p '{
    "spec": {
      "selector": {
        "version": "blue": 50,
        "version": "green": 50
      }
    }
  }'

# 2. Monitor metrics for 10 minutes
watch -n 10 'kubectl top pods'

# 3. If still issues, route 100% to blue
kubectl patch service bael-api \
  -p '{"spec":{"selector":{"version":"blue"}}}'

# 4. Investigate and fix issues
git log --oneline -5
git diff HEAD~1
```

### Database Rollback

```bash
# If migrations caused issues:

# 1. Identify last good version
psql -h postgres -U bael -d bael -c "
  SELECT version FROM alembic_version;"

# 2. Rollback migration
python -m alembic downgrade <previous_version>

# 3. Restore from backup if data corrupted
pg_restore -d bael < backups/bael_2026-02-02_pre-deploy.dump

# 4. Verify data integrity
psql -h postgres -U bael -d bael -c "
  SELECT COUNT(*) FROM important_table;"
```

### Automation Rollback Script

```bash
#!/bin/bash
# auto_rollback.sh

set -e

VERSION=$1
NAMESPACE=${2:-bael}

if [ -z "$VERSION" ]; then
    echo "Usage: ./auto_rollback.sh <version>"
    exit 1
fi

echo "Rolling back to version: $VERSION"

# Get previous deployment
PREV_VERSION=$(kubectl rollout history deployment/bael-api -n $NAMESPACE | tail -2 | head -1)

# Perform rollback
kubectl rollout undo deployment/bael-api -n $NAMESPACE --to-revision=$PREV_VERSION

# Wait for rollout
kubectl rollout status deployment/bael-api -n $NAMESPACE

# Verify health
kubectl port-forward service/bael-api 8000:8000 &
sleep 5
curl -f http://localhost:8000/health || exit 1

echo "✓ Rollback complete"
```

---

## Scaling & Load Balancing

### Horizontal Scaling

```bash
# Manual scaling
kubectl scale deployment bael-api --replicas=10

# Check HPA status
kubectl get hpa

# Adjust HPA targets
kubectl patch hpa bael-api \
  -p '{"spec":{"minReplicas":3,"maxReplicas":20}}'

# Monitor scaling
watch -n 5 'kubectl get hpa -w'
```

### Vertical Scaling

```bash
# Increase resource limits
kubectl set resources deployment/bael-api \
  --limits=cpu=4000m,memory=4Gi \
  --requests=cpu=2000m,memory=2Gi

# Check current usage
kubectl top pods

# Right-size based on usage
kubectl describe node <node-name>
```

### Load Balancer Configuration

```yaml
# Kubernetes Load Balancer Service
apiVersion: v1
kind: Service
metadata:
  name: bael-api
spec:
  type: LoadBalancer
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 3600
  selector:
    app: bael-api
  ports:
    - port: 80
      targetPort: 8000
      name: http
    - port: 443
      targetPort: 8443
      name: https
```

---

## Database Migrations

### Pre-Migration Steps

```bash
# 1. Backup current database
pg_dump -h postgres -U bael bael > backups/pre-migration.dump

# 2. Test migration on staging
python -m alembic upgrade head --sql > migration_script.sql

# 3. Verify no data loss
psql -h postgres -U bael bael < migration_script.sql

# 4. Document migration
echo "Migration: Add user_profile table" > MIGRATION_LOG.md
```

### Running Migration

```bash
# 1. Prepare application
kubectl scale deployment/bael-api --replicas=0
# Wait for graceful shutdown
sleep 10

# 2. Run migration
python -m alembic upgrade head

# 3. Verify success
psql -h postgres -U bael bael -c "
  SELECT table_name FROM information_schema.tables
  WHERE table_schema = 'public';"

# 4. Restart application
kubectl scale deployment/bael-api --replicas=5

# 5. Monitor startup
kubectl logs -f deployment/bael-api
```

### Rollback Migration

```bash
# If migration fails:

# 1. Identify migration version
python -m alembic current

# 2. Rollback to previous
python -m alembic downgrade -1

# 3. Restore data if needed
pg_restore -d bael < backups/pre-migration.dump

# 4. Fix application code
git checkout <previous-commit>

# 5. Redeploy application
kubectl set image deployment/bael-api \
  bael-api=registry.example.com/bael:<previous-version>
```

---

## Monitoring & Alerting

### Key Metrics to Monitor

| Metric               | Threshold | Action                  |
| -------------------- | --------- | ----------------------- |
| HTTP Error Rate      | > 0.1%    | Page on-call            |
| API Latency p95      | > 1s      | Investigate scaling     |
| Database Connections | > 80      | Scale workers           |
| Queue Depth          | > 1000    | Scale workers           |
| Memory Usage         | > 80%     | Investigate memory leak |
| Disk Usage           | > 85%     | Cleanup old data        |
| Cache Hit Rate       | < 50%     | Review cache strategy   |

### Alert Rules

```yaml
# Prometheus alert rules
groups:
  - name: bael.rules
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.001
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 1
        for: 5m
        annotations:
          summary: "API latency exceeds 1s"

      - alert: DatabaseDown
        expr: pg_up == 0
        for: 1m
        annotations:
          summary: "PostgreSQL is down"
```

### Notification Channels

```
Prometheus → Alertmanager
    ├→ PagerDuty (critical)
    ├→ Slack #alerts (warning)
    ├→ Email (critical + warning)
    └→ SMS (critical only)
```

---

## Disaster Recovery

### RTO & RPO Targets

| Scenario           | RTO    | RPO                       |
| ------------------ | ------ | ------------------------- |
| Single pod failure | 1 min  | 0 (stateless)             |
| Node failure       | 5 min  | 0 (replicated)            |
| Database failure   | 15 min | 5 min                     |
| Region failure     | 1 hour | 15 min                    |
| Data corruption    | 30 min | 5 min (daily incremental) |

### Backup Strategy

```bash
# Daily full backup
0 2 * * * /scripts/backup_full.sh

# Hourly incremental backup
0 * * * * /scripts/backup_incremental.sh

# Verify backups
0 3 * * * /scripts/verify_backups.sh

# Test restore
0 4 * * 0 /scripts/test_restore.sh
```

### Restore Procedure

```bash
# 1. List available backups
ls -lh backups/

# 2. Restore from backup
pg_restore \
  -h postgres-new \
  -U bael \
  -d bael \
  backups/bael_2026-02-02_02-00-00.dump

# 3. Verify integrity
psql -h postgres-new -U bael -d bael -c "
  SELECT COUNT(*) FROM pg_tables
  WHERE schemaname = 'public';"

# 4. Restore application data
kubectl set image deployment/bael-api \
  bael-api=registry.example.com/bael:stable

# 5. Monitor recovery
kubectl logs -f deployment/bael-api
```

---

## Post-Deployment Validation

### Automated Validation

```bash
#!/bin/bash
# post_deploy_validation.sh

set -e

NAMESPACE=${1:-bael}
TIMEOUT=600

echo "Starting post-deployment validation..."

# 1. Check deployment status
echo "✓ Checking deployment status..."
kubectl rollout status deployment/bael-api -n $NAMESPACE --timeout=${TIMEOUT}s

# 2. Check pod health
echo "✓ Checking pod health..."
UNHEALTHY=$(kubectl get pods -n $NAMESPACE -l app=bael-api \
  -o jsonpath='{.items[?(@.status.conditions[*].status!="True")].metadata.name}' | wc -w)
[ $UNHEALTHY -eq 0 ] || { echo "Unhealthy pods found!"; exit 1; }

# 3. API health check
echo "✓ Checking API health..."
curl -f http://localhost:8000/health || { echo "API health check failed!"; exit 1; }

# 4. Database connectivity
echo "✓ Checking database connectivity..."
curl -f http://localhost:8000/health/db || { echo "DB check failed!"; exit 1; }

# 5. Error rate check
echo "✓ Checking error rates..."
ERROR_RATE=$(curl -s http://localhost:9090/api/v1/query?query='rate(http_requests_total{status=~"5.."}[5m])' \
  | jq '.data.result[0].value[1]' | tr -d '"')
[ $(echo "$ERROR_RATE < 0.001" | bc) -eq 1 ] || { echo "High error rate!"; exit 1; }

# 6. Performance check
echo "✓ Checking performance metrics..."
LATENCY=$(curl -s http://localhost:9090/api/v1/query?query='http_request_duration_seconds_p95' \
  | jq '.data.result[0].value[1]' | tr -d '"')
[ $(echo "$LATENCY < 1" | bc) -eq 1 ] || { echo "High latency!"; exit 1; }

echo "✅ All validations passed!"
```

### Manual Validation Checklist

- [ ] All pods running
- [ ] No pending pods
- [ ] Health endpoints responding
- [ ] Database queries functional
- [ ] Cache working
- [ ] Workers processing tasks
- [ ] Error rates normal
- [ ] Latency acceptable
- [ ] Memory usage stable
- [ ] Log output normal
- [ ] No warnings in logs
- [ ] External services accessible
- [ ] API responses correct format
- [ ] Authentication working
- [ ] Authorization working

---

## Summary

BAEL deployment procedures support:

- **Zero-downtime deployments** (blue-green strategy)
- **Gradual rollout** (canary for features)
- **Fast rollback** (< 5 minutes)
- **Database safety** (migrations + backups)
- **Automatic scaling** (HPA with metrics)
- **Comprehensive monitoring** (Prometheus + Grafana)
- **Disaster recovery** (hourly backups, restore < 30 min)

---

**Last Updated:** February 2, 2026
**Version:** 1.0.0
**Status:** Production-Ready
