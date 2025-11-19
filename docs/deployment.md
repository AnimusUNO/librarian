# The Librarian - Deployment Guide

**License**: [CC-BY-SA-4.0](../LICENSE-DOCS)

## Production Deployment

### Prerequisites

- Python 3.10 or higher
- Access to Letta server
- Reverse proxy (nginx, Caddy, etc.) - recommended
- Process manager (systemd, supervisor, etc.) - recommended
- SSL certificate (for HTTPS) - recommended

## Deployment Options

### 1. Direct Deployment

Run The Librarian directly with uvicorn:

```bash
uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
```

### 2. Systemd Service

Create `/etc/systemd/system/librarian.service`:

```ini
[Unit]
Description=The Librarian - OpenAI-Compatible Letta Proxy
After=network.target

[Service]
Type=simple
User=librarian
WorkingDirectory=/opt/librarian
Environment="PATH=/opt/librarian/venv/bin"
ExecStart=/opt/librarian/venv/bin/uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable librarian
sudo systemctl start librarian
sudo systemctl status librarian
```

### 3. Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t librarian .
docker run -d \
  -p 8000:8000 \
  -e LETTA_BASE_URL=https://your-letta-server:8283 \
  -e LETTA_API_KEY=your_api_key \
  --name librarian \
  librarian
```

### 4. Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  librarian:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LETTA_BASE_URL=https://your-letta-server:8283
      - LETTA_API_KEY=your_api_key
      - LIBRARIAN_HOST=0.0.0.0
      - LIBRARIAN_PORT=8000
    restart: unless-stopped
    volumes:
      - ./config:/app/config:ro
```

Run:

```bash
docker-compose up -d
```

## Reverse Proxy Setup

### Nginx Configuration

Create `/etc/nginx/sites-available/librarian`:

```nginx
server {
    listen 80;
    server_name librarian.example.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name librarian.example.com;
    
    ssl_certificate /etc/ssl/certs/librarian.crt;
    ssl_certificate_key /etc/ssl/private/librarian.key;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy settings
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

Enable:

```bash
sudo ln -s /etc/nginx/sites-available/librarian /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Caddy Configuration

Create `Caddyfile`:

```
librarian.example.com {
    reverse_proxy localhost:8000 {
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

## Production Configuration

### Recommended Settings

```bash
# Server
LIBRARIAN_HOST=0.0.0.0
LIBRARIAN_PORT=8000
LIBRARIAN_DEBUG=false
LIBRARIAN_ENABLE_DOCS=false

# Security
LIBRARIAN_API_KEY_REQUIRED=true
LIBRARIAN_API_KEY=<strong_random_key>
LIBRARIAN_RATE_LIMIT_ENABLED=true
LIBRARIAN_RATE_LIMIT_REQUESTS=1000
LIBRARIAN_RATE_LIMIT_WINDOW=3600

# Logging
LIBRARIAN_LOG_LEVEL=INFO
LIBRARIAN_LOG_SECURITY_EVENTS=true
LIBRARIAN_AUDIT_ENABLED=true

# Performance
LIBRARIAN_MAX_CONCURRENT=50
LIBRARIAN_DUPLICATION_THRESHOLD=40
LIBRARIAN_MAX_CLONES_PER_AGENT=5
LIBRARIAN_QUEUE_TIMEOUT=600

# Letta
LETTA_BASE_URL=https://your-letta-server:8283
LETTA_API_KEY=<your_letta_api_key>
LETTA_TIMEOUT=30
```

### Generate Secure API Key

```bash
# Generate random API key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Monitoring

### Health Checks

Monitor the health endpoint:

```bash
curl http://localhost:8000/health
```

### Log Monitoring

Monitor logs:

```bash
# Systemd
sudo journalctl -u librarian -f

# Docker
docker logs -f librarian

# Direct
tail -f /var/log/librarian/librarian.log
```

### Metrics (Future)

When metrics are enabled:

```bash
LIBRARIAN_METRICS_ENABLED=true
LIBRARIAN_METRICS_PORT=9090
```

Access metrics at `http://localhost:9090/metrics`

## Security Best Practices

### 1. Use HTTPS

Always use HTTPS in production:
- Set up SSL/TLS certificate
- Use reverse proxy with SSL termination
- Enable HSTS headers

### 2. Enable Authentication

```bash
LIBRARIAN_API_KEY_REQUIRED=true
LIBRARIAN_API_KEY=<strong_random_key>
```

### 3. Enable Rate Limiting

```bash
LIBRARIAN_RATE_LIMIT_ENABLED=true
LIBRARIAN_RATE_LIMIT_REQUESTS=1000
LIBRARIAN_RATE_LIMIT_WINDOW=3600
```

### 4. IP Filtering

```bash
LIBRARIAN_ENABLE_IP_FILTERING=true
LIBRARIAN_ALLOWED_IPS=192.168.1.0/24,10.0.0.0/8
```

### 5. Security Logging

```bash
LIBRARIAN_LOG_SECURITY_EVENTS=true
LIBRARIAN_AUDIT_ENABLED=true
```

### 6. Firewall

Configure firewall to only allow necessary ports:

```bash
# UFW example
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

## Performance Tuning

### Worker Processes

Adjust based on CPU cores:

```bash
# 4 workers for 4-core system
uvicorn main:app --workers 4
```

### Concurrency Settings

```bash
# High traffic
LIBRARIAN_MAX_CONCURRENT=100
LIBRARIAN_DUPLICATION_THRESHOLD=80
LIBRARIAN_MAX_CLONES_PER_AGENT=10

# Low traffic
LIBRARIAN_MAX_CONCURRENT=10
LIBRARIAN_DUPLICATION_THRESHOLD=8
LIBRARIAN_MAX_CLONES_PER_AGENT=3
```

### Connection Pooling

Configure Letta client connection pooling:

```bash
LETTA_TIMEOUT=30
```

## Backup and Recovery

### Configuration Backup

```bash
# Backup configuration
cp config config.backup
```

### Log Rotation

Configure log rotation in `/etc/logrotate.d/librarian`:

```
/var/log/librarian/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 librarian librarian
}
```

## Troubleshooting Production Issues

### Service Not Starting

```bash
# Check logs
sudo journalctl -u librarian -n 50

# Check configuration
python tests/validate_config.py

# Test Letta connection
curl $LETTA_BASE_URL/health
```

### High Memory Usage

- Reduce `LIBRARIAN_MAX_CONCURRENT`
- Reduce `LIBRARIAN_MAX_CLONES_PER_AGENT`
- Monitor with `htop` or `top`

### Slow Responses

- Check Letta server performance
- Increase `LIBRARIAN_MAX_CONCURRENT`
- Enable auto-duplication
- Check network latency

### Connection Errors

- Verify Letta server is accessible
- Check firewall rules
- Verify API keys
- Check DNS resolution

## Scaling

### Horizontal Scaling

Run multiple instances behind a load balancer:

```nginx
upstream librarian {
    least_conn;
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}
```

### Vertical Scaling

Increase resources:
- More CPU cores → more workers
- More RAM → higher concurrency
- Faster network → lower latency

## Maintenance

### Updates

```bash
# Pull latest changes
git pull

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart librarian
```

### Monitoring

- Monitor health endpoint
- Monitor logs
- Monitor resource usage
- Monitor Letta server status

## Next Steps

- See [Configuration Guide](configuration.md) for configuration options
- See [Architecture](architecture.md) for system architecture
- See [API Reference](api-reference.md) for API documentation

