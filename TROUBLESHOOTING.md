# BAEL - Troubleshooting Guide

This guide helps you diagnose and resolve common issues with BAEL.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Startup Issues](#startup-issues)
- [API and Connection Issues](#api-and-connection-issues)
- [Performance Issues](#performance-issues)
- [Memory Issues](#memory-issues)
- [Database Issues](#database-issues)
- [LLM Provider Issues](#llm-provider-issues)
- [Plugin Issues](#plugin-issues)
- [Docker Issues](#docker-issues)
- [Production Issues](#production-issues)
- [Debugging Tips](#debugging-tips)

---

## Installation Issues

### Python Version Not Supported

**Problem**: Error about Python version when installing

**Solution**:
```bash
# Check Python version
python --version

# Install Python 3.10+ if needed
# On Ubuntu/Debian
sudo apt update
sudo apt install python3.11

# On macOS with Homebrew
brew install python@3.11

# Verify
python3.11 --version
```

### Dependency Installation Fails

**Problem**: `pip install -r requirements.txt` fails

**Solution**:
```bash
# Upgrade pip
python -m pip install --upgrade pip

# Try installing with verbose output
pip install -r requirements.txt -v

# If specific package fails, install it separately
pip install <package-name> --no-cache-dir

# For SSL errors
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### Missing System Libraries

**Problem**: Errors about missing system libraries (libpq, etc.)

**Solution**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y \
    python3-dev \
    build-essential \
    libpq-dev \
    libssl-dev \
    libffi-dev

# macOS
brew install postgresql openssl

# CentOS/RHEL
sudo yum install -y \
    python3-devel \
    gcc \
    postgresql-devel \
    openssl-devel
```

### Virtual Environment Issues

**Problem**: Virtual environment not working correctly

**Solution**:
```bash
# Remove existing venv
rm -rf venv

# Create fresh virtual environment
python3.11 -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Verify you're in venv
which python  # Should show path in venv directory

# Reinstall dependencies
pip install -r requirements.txt
```

---

## Startup Issues

### BAEL Won't Start

**Problem**: `python main.py` fails or hangs

**Diagnostic Steps**:

1. **Check for specific error messages**:
   ```bash
   python main.py 2>&1 | tee startup.log
   ```

2. **Verify environment configuration**:
   ```bash
   # Check .env file exists
   ls -la .env
   
   # Verify it has required keys
   grep -E "(API_KEY|DATABASE_URL)" .env
   ```

3. **Test database connection**:
   ```python
   python -c "
   from core.persistence_layer import get_database
   db = get_database()
   print('Database connection OK')
   "
   ```

4. **Check port availability**:
   ```bash
   # Check if port 8000 is in use
   lsof -i :8000
   # or
   netstat -an | grep 8000
   
   # Kill process if needed
   kill -9 <PID>
   ```

### Import Errors

**Problem**: `ModuleNotFoundError` or `ImportError`

**Solution**:
```bash
# Ensure you're in the right directory
pwd  # Should be in BaelTheLordOfAll-AI root

# Check PYTHONPATH
echo $PYTHONPATH

# Add current directory to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or add to .env
echo "PYTHONPATH=$(pwd)" >> .env

# Reinstall in development mode
pip install -e .
```

### Environment Variable Not Loaded

**Problem**: Environment variables not being read

**Solution**:
```bash
# Verify .env file format (no spaces around =)
# WRONG: API_KEY = sk-123
# RIGHT: API_KEY=sk-123

# Load environment manually
export $(cat .env | xargs)

# Verify variables are loaded
echo $OPENAI_API_KEY

# Or use python-dotenv
pip install python-dotenv
python -c "from dotenv import load_dotenv; load_dotenv(); print('Loaded')"
```

---

## API and Connection Issues

### API Key Errors

**Problem**: "Invalid API key" or authentication errors

**Solution**:
```bash
# Check API key is set
echo $OPENAI_API_KEY

# Verify format (OpenAI keys start with sk-)
# Example: sk-proj-xxxxxxxxxxxxx

# Test API key directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# If using multiple providers, check each
echo $ANTHROPIC_API_KEY
echo $OPENROUTER_API_KEY
```

### Connection Timeouts

**Problem**: Requests timing out to LLM providers

**Solution**:
```python
# Increase timeout in config
# config/settings/main.yaml
llm:
  timeout: 60  # Increase from default 30

# Or set environment variable
export LLM_TIMEOUT=60

# Check network connectivity
ping api.openai.com
ping api.anthropic.com

# Check for proxy issues
env | grep -i proxy
```

### Rate Limit Errors

**Problem**: "Rate limit exceeded" errors

**Solution**:
```python
# Implement rate limiting
# Add to .env
RATE_LIMIT_REQUESTS=50
RATE_LIMIT_PERIOD=60  # seconds

# Use exponential backoff
# In your code:
import time
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5)
)
async def call_llm():
    # Your LLM call
    pass

# Or switch to different model/provider temporarily
```

### WebSocket Connection Fails

**Problem**: Real-time features not working

**Solution**:
```bash
# Check WebSocket support
curl -i -N -H "Connection: Upgrade" \
    -H "Upgrade: websocket" \
    http://localhost:8000/ws

# Check for reverse proxy issues
# Nginx example:
location /ws {
    proxy_pass http://localhost:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}

# Check firewall rules
sudo ufw status
```

---

## Performance Issues

### Slow Response Times

**Problem**: BAEL taking too long to respond

**Diagnostic**:
```bash
# Enable profiling
export ENABLE_PROFILING=true

# Check performance metrics
curl http://localhost:8000/metrics | grep duration

# View slow queries
tail -f logs/slow_queries.log
```

**Solutions**:

1. **Enable caching**:
   ```python
   # config/settings/main.yaml
   cache:
     enabled: true
     ttl: 3600
     max_size: 1000
   ```

2. **Use faster models**:
   ```python
   # For simple tasks, use GPT-3.5 instead of GPT-4
   llm:
     default_model: gpt-3.5-turbo
     fast_model: gpt-3.5-turbo
     quality_model: gpt-4-turbo
   ```

3. **Enable speculative execution**:
   ```python
   speculative_execution:
     enabled: true
     confidence_threshold: 0.7
   ```

4. **Optimize database queries**:
   ```sql
   -- Add indexes
   CREATE INDEX idx_memory_timestamp ON memory(created_at);
   CREATE INDEX idx_agent_status ON agents(status);
   
   -- Analyze slow queries
   EXPLAIN ANALYZE SELECT * FROM memory WHERE agent_id = 'xyz';
   ```

### High CPU Usage

**Problem**: BAEL consuming too much CPU

**Solution**:
```bash
# Monitor CPU usage
top -p $(pgrep -f "python main.py")

# Limit worker threads
export MAX_WORKERS=4

# Use async instead of sync where possible
# Check for blocking operations
python -m cProfile -o profile.stats main.py
python -m pstats profile.stats

# Reduce concurrent agents
export MAX_CONCURRENT_AGENTS=10
```

### Concurrent Request Limits

**Problem**: Can't handle enough concurrent requests

**Solution**:
```bash
# Increase worker count
gunicorn -w 8 -k uvicorn.workers.UvicornWorker main:app

# Use async workers
export WORKER_CLASS=uvicorn.workers.UvicornWorker

# Scale horizontally with load balancer
# nginx.conf example:
upstream bael {
    server localhost:8000;
    server localhost:8001;
    server localhost:8002;
}
```

---

## Memory Issues

### High Memory Usage

**Problem**: BAEL consuming too much RAM

**Diagnostic**:
```bash
# Monitor memory
ps aux | grep python
free -h

# Check memory by component
python -c "
from core.memory import get_memory_system
mem = get_memory_system()
stats = mem.get_stats()
print(f'Memory usage: {stats}')
"
```

**Solutions**:

1. **Configure memory limits**:
   ```python
   # config/settings/main.yaml
   memory:
     working_memory_size: 100  # Reduce if needed
     max_context_tokens: 50000  # Reduce from 100000
     eviction_policy: lru
   ```

2. **Enable aggressive eviction**:
   ```python
   memory:
     auto_evict: true
     eviction_threshold: 0.8  # Evict when 80% full
     eviction_percentage: 0.3  # Evict 30% when threshold reached
   ```

3. **Clear old memories**:
   ```python
   from core.memory import get_memory_system
   
   mem = get_memory_system()
   # Clear memories older than 30 days
   mem.clear_old(days=30)
   
   # Clear by agent
   mem.clear_agent_memories(agent_id="old_agent")
   ```

4. **Use memory profiling**:
   ```bash
   pip install memory_profiler
   python -m memory_profiler main.py
   ```

### Memory Leaks

**Problem**: Memory continuously growing

**Solution**:
```bash
# Use memory_profiler to find leaks
pip install objgraph
python -c "
import objgraph
objgraph.show_most_common_types(limit=20)
"

# Check for unreleased resources
# Common causes:
# - Unclosed database connections
# - Unreleased file handles
# - Circular references
# - Cached data not being cleared

# Restart workers periodically
export MAX_REQUESTS=1000  # Restart after 1000 requests
export MAX_REQUESTS_JITTER=50
```

---

## Database Issues

### Can't Connect to Database

**Problem**: Database connection errors

**Solution**:
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql
# or
pg_isready

# Test connection
psql -h localhost -U bael_user -d bael_db

# Check connection string
echo $DATABASE_URL
# Should be: postgresql://user:password@host:port/database

# Verify credentials
cat .env | grep DATABASE_URL

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log

# For Docker PostgreSQL
docker logs bael-postgres
```

### Database Migrations Failed

**Problem**: Schema migration errors

**Solution**:
```bash
# Check current schema version
python -c "
from core.persistence_layer import get_database
db = get_database()
print(f'Schema version: {db.get_version()}')
"

# Reset database (CAUTION: loses data)
python -c "
from core.persistence_layer import get_database
db = get_database()
db.reset()
db.init()
"

# Manual migration
psql -d bael_db -f migrations/001_initial.sql

# Backup before migrations
pg_dump bael_db > backup_$(date +%Y%m%d).sql
```

### Slow Database Queries

**Problem**: Database queries taking too long

**Solution**:
```sql
-- Enable query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1s
SELECT pg_reload_conf();

-- Find slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Add missing indexes
CREATE INDEX idx_memory_agent_ts ON memory(agent_id, created_at);
CREATE INDEX idx_tasks_status ON tasks(status);

-- Vacuum and analyze
VACUUM ANALYZE;

-- Update statistics
ANALYZE;
```

---

## LLM Provider Issues

### OpenAI API Errors

**Problem**: Errors calling OpenAI API

**Common Issues**:

1. **Invalid API key**:
   ```bash
   # Verify key format
   echo $OPENAI_API_KEY | grep "^sk-"
   
   # Test directly
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

2. **Rate limits**:
   ```python
   # Implement retry logic
   from openai import RateLimitError
   import time
   
   try:
       response = await client.chat.completions.create(...)
   except RateLimitError:
       time.sleep(20)  # Wait before retry
       response = await client.chat.completions.create(...)
   ```

3. **Model not available**:
   ```python
   # Check available models
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY" \
     | jq '.data[].id'
   
   # Use fallback model
   llm:
     models:
       - gpt-4-turbo
       - gpt-4
       - gpt-3.5-turbo  # Fallback
   ```

### Anthropic API Errors

**Problem**: Issues with Claude API

**Solution**:
```bash
# Verify API key
echo $ANTHROPIC_API_KEY | grep "^sk-ant-"

# Test API
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-opus-20240229","max_tokens":1024,"messages":[{"role":"user","content":"Hello"}]}'

# Check for beta header requirement
# Some features need: anthropic-beta: tools-2024-04-04
```

### Model Context Length Exceeded

**Problem**: "Maximum context length exceeded"

**Solution**:
```python
# Reduce context window
from core.memory import get_memory_system

mem = get_memory_system()
# Compress older messages
compressed = mem.compress_context(max_tokens=50000)

# Use hierarchical summarization
summary = mem.summarize_old_messages(threshold_age=3600)

# Use models with larger context
# GPT-4-turbo: 128K tokens
# Claude 3: 200K tokens

# Configure context limits
llm:
  max_context_tokens: 100000
  context_overflow_strategy: summarize  # or 'truncate'
```

---

## Plugin Issues

### Plugin Won't Load

**Problem**: Custom plugin not loading

**Solution**:
```bash
# Check plugin structure
tree plugins/my-plugin/
# Should have:
# - plugin.yaml
# - __init__.py
# - main.py (or entry point)

# Validate plugin.yaml
python -c "
import yaml
with open('plugins/my-plugin/plugin.yaml') as f:
    config = yaml.safe_load(f)
    print(config)
"

# Check for errors
python -c "
from core.plugins import PluginRegistry
registry = PluginRegistry('plugins')
await registry.load_plugin('my-plugin')
"

# Enable debug logging
export LOG_LEVEL=DEBUG
```

### Plugin Dependency Errors

**Problem**: Plugin missing dependencies

**Solution**:
```bash
# Check plugin requirements
cat plugins/my-plugin/requirements.txt

# Install plugin dependencies
pip install -r plugins/my-plugin/requirements.txt

# Or install all plugin dependencies
find plugins -name requirements.txt -exec pip install -r {} \;
```

---

## Docker Issues

### Container Won't Start

**Problem**: Docker container fails to start

**Solution**:
```bash
# Check container logs
docker logs bael-api

# Check container status
docker ps -a

# Remove and recreate
docker-compose down
docker-compose up -d

# Build fresh image
docker-compose build --no-cache
docker-compose up -d

# Check resource limits
docker stats
```

### Permission Issues in Docker

**Problem**: Permission denied errors in container

**Solution**:
```dockerfile
# In Dockerfile, match user UID
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} bael && \
    useradd -u ${UID} -g bael -m bael
USER bael

# Or run with current user
docker-compose run --user $(id -u):$(id -g) bael
```

### Volume Mount Issues

**Problem**: Files not accessible in container

**Solution**:
```yaml
# docker-compose.yml
volumes:
  - ./:/app  # Mount current directory
  - ./config:/app/config:ro  # Read-only config
  
# Check mounts
docker inspect bael-api | grep -A 10 Mounts
```

---

## Production Issues

### Service Crashes

**Problem**: BAEL crashes in production

**Solution**:
```bash
# Use process manager
pip install supervisor

# supervisord.conf
[program:bael]
command=/path/to/venv/bin/python main.py
autostart=true
autorestart=true
stderr_logfile=/var/log/bael/err.log
stdout_logfile=/var/log/bael/out.log

# Or use systemd
sudo systemctl enable bael
sudo systemctl start bael

# Monitor and auto-restart
while true; do
  python main.py || sleep 5
done
```

### Load Balancer Issues

**Problem**: Load balancer not distributing traffic

**Solution**:
```nginx
# nginx.conf
upstream bael {
    least_conn;  # Use least connections algorithm
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;
}

server {
    location / {
        proxy_pass http://bael;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Health check endpoint
location /health {
    access_log off;
    proxy_pass http://bael/health;
}
```

### Monitoring Not Working

**Problem**: Metrics/monitoring unavailable

**Solution**:
```bash
# Verify metrics endpoint
curl http://localhost:8000/metrics

# Check Prometheus configuration
# prometheus.yml
scrape_configs:
  - job_name: 'bael'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s

# Restart Prometheus
docker restart prometheus

# Check Grafana datasource
# Settings -> Data Sources -> Prometheus
# URL: http://prometheus:9090
```

---

## Debugging Tips

### Enable Debug Logging

```bash
# Environment variable
export LOG_LEVEL=DEBUG

# In code
import logging
logging.basicConfig(level=logging.DEBUG)

# Or in config
# config/settings/main.yaml
logging:
  level: DEBUG
  format: detailed
```

### Interactive Debugging

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use ipdb for better experience
pip install ipdb
import ipdb; ipdb.set_trace()

# Or use IDE debugger (VSCode, PyCharm)
```

### Trace Requests

```python
# Enable request tracing
export ENABLE_TRACING=true

# View traces in logs
tail -f logs/trace.log

# Or use OpenTelemetry
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("operation"):
    # Your code
    pass
```

### Performance Profiling

```bash
# Profile a specific operation
python -m cProfile -o profile.stats main.py

# Analyze results
python -c "
import pstats
stats = pstats.Stats('profile.stats')
stats.sort_stats('cumulative')
stats.print_stats(20)
"

# Or use py-spy for live profiling
pip install py-spy
py-spy top -- python main.py
```

---

## Getting Help

If you're still experiencing issues:

1. **Check Logs**: Always check logs first
   ```bash
   tail -f logs/bael.log
   ```

2. **Search Documentation**: Use grep to search docs
   ```bash
   grep -r "your error" docs/
   ```

3. **GitHub Issues**: Search for similar issues
   - https://github.com/aibaellord/BaelTheLordOfAll-AI/issues

4. **Ask Community**: Post in GitHub Discussions
   - https://github.com/aibaellord/BaelTheLordOfAll-AI/discussions

5. **Create Bug Report**: If it's a new issue
   - See [CONTRIBUTING.md](CONTRIBUTING.md#bug-reports)

---

## Diagnostic Checklist

When reporting issues, include:

- [ ] BAEL version
- [ ] Python version (`python --version`)
- [ ] Operating system
- [ ] Installation method (pip, docker, source)
- [ ] Error messages (full stack trace)
- [ ] Logs (relevant portions)
- [ ] Configuration (sanitized, no API keys)
- [ ] Steps to reproduce
- [ ] Expected vs actual behavior

---

**Last Updated**: February 2026
**Version**: 3.0.0

_For more help, see [FAQ.md](FAQ.md) or [CONTRIBUTING.md](CONTRIBUTING.md)_
