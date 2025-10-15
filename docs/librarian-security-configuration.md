# Security Configuration for The Librarian

Based on the security models and configuration options from `animusuno/smcp`, here are the security features and configurations that The Librarian should support:

## 🔒 Core Security Features

### 1. **Host Binding & Network Security**

#### Default Security Model
- **Default**: `127.0.0.1` (localhost-only) for maximum security
- **External Access**: `0.0.0.0` (all interfaces) with explicit `--allow-external` flag
- **Custom Binding**: Support for specific IP addresses

#### Command Line Options
```bash
# Default: localhost-only (secure)
python librarian.py

# Explicit localhost-only
python librarian.py --host 127.0.0.1

# Allow external connections (use with caution)
python librarian.py --allow-external

# Custom host and port
python librarian.py --host 0.0.0.0 --port 8000
```

#### Environment Variables
```env
# Host binding
LIBRARIAN_HOST=127.0.0.1          # Default: localhost-only
LIBRARIAN_PORT=8000               # Default port
LIBRARIAN_ALLOW_EXTERNAL=false   # Default: false for security
```

### 2. **IP Address Filtering**

#### Access Control Lists (ACLs)
```env
# Allowed IP addresses (comma-separated)
LIBRARIAN_ALLOWED_IPS=192.168.1.0/24,10.0.0.0/8,127.0.0.1

# Blocked IP addresses (comma-separated)
LIBRARIAN_BLOCKED_IPS=192.168.1.100,10.0.0.50

# Enable IP filtering
LIBRARIAN_ENABLE_IP_FILTERING=true
```

#### Implementation
```python
# IP filtering middleware
def check_ip_access(client_ip: str) -> bool:
    """Check if client IP is allowed access."""
    if not os.getenv("LIBRARIAN_ENABLE_IP_FILTERING", "false").lower() == "true":
        return True
    
    allowed_ips = os.getenv("LIBRARIAN_ALLOWED_IPS", "").split(",")
    blocked_ips = os.getenv("LIBRARIAN_BLOCKED_IPS", "").split(",")
    
    # Check blocked first
    for blocked in blocked_ips:
        if blocked and ip_in_network(client_ip, blocked.strip()):
            return False
    
    # Check allowed
    if allowed_ips and allowed_ips[0]:  # If allowed list exists
        for allowed in allowed_ips:
            if allowed and ip_in_network(client_ip, allowed.strip()):
                return True
        return False
    
    return True  # No restrictions if no allowed list
```

### 3. **Authentication & Authorization**

#### API Key Authentication
```env
# API Key configuration
LIBRARIAN_API_KEY_REQUIRED=true
LIBRARIAN_API_KEY=your-secret-api-key
LIBRARIAN_API_KEY_HEADER=X-API-Key

# Multiple API keys (comma-separated)
LIBRARIAN_API_KEYS=key1,key2,key3
```

#### JWT Token Support
```env
# JWT configuration
LIBRARIAN_JWT_SECRET=your-jwt-secret
LIBRARIAN_JWT_EXPIRY=3600  # seconds
LIBRARIAN_JWT_ALGORITHM=HS256
```

#### User Identity Management
```env
# User identity requirements
LIBRARIAN_REQUIRE_USER_ID=true
LIBRARIAN_USER_ID_HEADER=X-User-ID
LIBRARIAN_DEFAULT_USER_ID=anonymous
```

### 4. **Rate Limiting & DDoS Protection**

#### Request Rate Limiting
```env
# Rate limiting configuration
LIBRARIAN_RATE_LIMIT_ENABLED=true
LIBRARIAN_RATE_LIMIT_REQUESTS=100  # requests per window
LIBRARIAN_RATE_LIMIT_WINDOW=60     # seconds
LIBRARIAN_RATE_LIMIT_BURST=20      # burst allowance

# Per-IP rate limiting
LIBRARIAN_RATE_LIMIT_PER_IP=true
LIBRARIAN_RATE_LIMIT_IP_REQUESTS=50
```

#### Concurrent Connection Limits
```env
# Connection limits
LIBRARIAN_MAX_CONNECTIONS=100
LIBRARIAN_MAX_CONNECTIONS_PER_IP=10
LIBRARIAN_CONNECTION_TIMEOUT=300  # seconds
```

### 5. **Request Validation & Sanitization**

#### Input Validation
```env
# Request validation
LIBRARIAN_VALIDATE_REQUESTS=true
LIBRARIAN_MAX_REQUEST_SIZE=10485760  # 10MB
LIBRARIAN_MAX_MESSAGE_LENGTH=10000   # characters
LIBRARIAN_ALLOWED_MODELS=gpt-3.5-turbo,gpt-4,gpt-4-turbo
```

#### Content Filtering
```env
# Content filtering
LIBRARIAN_FILTER_PROFANITY=true
LIBRARIAN_FILTER_PII=true
LIBRARIAN_BLOCKED_PATTERNS=malicious_pattern1,malicious_pattern2
```

### 6. **Logging & Monitoring**

#### Security Logging
```env
# Security logging
LIBRARIAN_LOG_SECURITY_EVENTS=true
LIBRARIAN_LOG_FAILED_AUTH=true
LIBRARIAN_LOG_RATE_LIMITS=true
LIBRARIAN_LOG_IP_FILTERING=true

# Log levels
LIBRARIAN_LOG_LEVEL=INFO
LIBRARIAN_SECURITY_LOG_LEVEL=WARNING
```

#### Audit Trail
```env
# Audit configuration
LIBRARIAN_AUDIT_ENABLED=true
LIBRARIAN_AUDIT_LOG_FILE=/var/log/librarian/audit.log
LIBRARIAN_AUDIT_RETENTION_DAYS=90
```

### 7. **SSL/TLS Configuration**

#### HTTPS Enforcement
```env
# SSL/TLS configuration
LIBRARIAN_FORCE_HTTPS=true
LIBRARIAN_SSL_CERT_PATH=/etc/ssl/certs/librarian.crt
LIBRARIAN_SSL_KEY_PATH=/etc/ssl/private/librarian.key
LIBRARIAN_SSL_CIPHERS=ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512
```

#### Security Headers
```env
# Security headers
LIBRARIAN_SECURITY_HEADERS=true
LIBRARIAN_CORS_ENABLED=false
LIBRARIAN_CORS_ORIGINS=https://trusted-domain.com
```

### 8. **Firewall Integration**

#### UFW Integration (Ubuntu)
```bash
# UFW rules for The Librarian
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 8000/tcp  # Block direct access to Librarian
sudo ufw enable
```

#### iptables Integration (CentOS/RHEL)
```bash
# iptables rules
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8000 -j DROP
sudo service iptables save
```

## 🚀 Startup Flags & Configuration

### Command Line Arguments
```bash
# Security flags
--allow-external              # Allow external connections
--host HOST                   # Bind to specific host
--port PORT                   # Bind to specific port
--require-auth                # Require authentication
--api-key KEY                 # Set API key
--rate-limit RATE             # Set rate limit
--max-connections MAX         # Set max connections
--ip-whitelist IPS            # Comma-separated IP whitelist
--ip-blacklist IPS            # Comma-separated IP blacklist
--ssl-cert PATH               # SSL certificate path
--ssl-key PATH                # SSL key path
--force-https                  # Force HTTPS
--log-security                # Enable security logging
--audit-log                   # Enable audit logging
```

### Environment Variables Matrix

| Variable | Default | Description |
|----------|---------|-------------|
| `LIBRARIAN_HOST` | `127.0.0.1` | Host to bind to |
| `LIBRARIAN_PORT` | `8000` | Port to bind to |
| `LIBRARIAN_ALLOW_EXTERNAL` | `false` | Allow external connections |
| `LIBRARIAN_ENABLE_IP_FILTERING` | `false` | Enable IP address filtering |
| `LIBRARIAN_ALLOWED_IPS` | `` | Comma-separated allowed IPs |
| `LIBRARIAN_BLOCKED_IPS` | `` | Comma-separated blocked IPs |
| `LIBRARIAN_API_KEY_REQUIRED` | `false` | Require API key authentication |
| `LIBRARIAN_API_KEY` | `` | Default API key |
| `LIBRARIAN_API_KEYS` | `` | Multiple API keys (comma-separated) |
| `LIBRARIAN_RATE_LIMIT_ENABLED` | `false` | Enable rate limiting |
| `LIBRARIAN_RATE_LIMIT_REQUESTS` | `100` | Requests per window |
| `LIBRARIAN_RATE_LIMIT_WINDOW` | `60` | Rate limit window (seconds) |
| `LIBRARIAN_MAX_CONNECTIONS` | `100` | Maximum concurrent connections |
| `LIBRARIAN_MAX_CONNECTIONS_PER_IP` | `10` | Max connections per IP |
| `LIBRARIAN_FORCE_HTTPS` | `false` | Force HTTPS connections |
| `LIBRARIAN_SSL_CERT_PATH` | `` | SSL certificate path |
| `LIBRARIAN_SSL_KEY_PATH` | `` | SSL key path |
| `LIBRARIAN_LOG_SECURITY_EVENTS` | `true` | Log security events |
| `LIBRARIAN_AUDIT_ENABLED` | `false` | Enable audit logging |
| `LIBRARIAN_VALIDATE_REQUESTS` | `true` | Validate incoming requests |
| `LIBRARIAN_MAX_REQUEST_SIZE` | `10485760` | Max request size (bytes) |
| `LIBRARIAN_ALLOWED_MODELS` | `` | Comma-separated allowed models |

## 🔧 Implementation Examples

### Basic Security Configuration
```env
# .env file for basic security
LIBRARIAN_HOST=127.0.0.1
LIBRARIAN_PORT=8000
LIBRARIAN_ALLOW_EXTERNAL=false
LIBRARIAN_ENABLE_IP_FILTERING=true
LIBRARIAN_ALLOWED_IPS=192.168.1.0/24,10.0.0.0/8
LIBRARIAN_API_KEY_REQUIRED=true
LIBRARIAN_API_KEY=your-secret-key
LIBRARIAN_RATE_LIMIT_ENABLED=true
LIBRARIAN_RATE_LIMIT_REQUESTS=100
LIBRARIAN_LOG_SECURITY_EVENTS=true
```

### Production Security Configuration
```env
# .env file for production
LIBRARIAN_HOST=0.0.0.0
LIBRARIAN_PORT=8000
LIBRARIAN_ALLOW_EXTERNAL=true
LIBRARIAN_ENABLE_IP_FILTERING=true
LIBRARIAN_ALLOWED_IPS=192.168.1.0/24,10.0.0.0/8,172.16.0.0/12
LIBRARIAN_API_KEY_REQUIRED=true
LIBRARIAN_API_KEYS=prod-key-1,prod-key-2,prod-key-3
LIBRARIAN_RATE_LIMIT_ENABLED=true
LIBRARIAN_RATE_LIMIT_REQUESTS=1000
LIBRARIAN_RATE_LIMIT_WINDOW=60
LIBRARIAN_MAX_CONNECTIONS=500
LIBRARIAN_MAX_CONNECTIONS_PER_IP=50
LIBRARIAN_FORCE_HTTPS=true
LIBRARIAN_SSL_CERT_PATH=/etc/ssl/certs/librarian.crt
LIBRARIAN_SSL_KEY_PATH=/etc/ssl/private/librarian.key
LIBRARIAN_AUDIT_ENABLED=true
LIBRARIAN_AUDIT_LOG_FILE=/var/log/librarian/audit.log
LIBRARIAN_LOG_SECURITY_EVENTS=true
LIBRARIAN_VALIDATE_REQUESTS=true
LIBRARIAN_MAX_REQUEST_SIZE=52428800  # 50MB
```

### Development Security Configuration
```env
# .env file for development
LIBRARIAN_HOST=127.0.0.1
LIBRARIAN_PORT=8000
LIBRARIAN_ALLOW_EXTERNAL=false
LIBRARIAN_ENABLE_IP_FILTERING=false
LIBRARIAN_API_KEY_REQUIRED=false
LIBRARIAN_RATE_LIMIT_ENABLED=false
LIBRARIAN_LOG_SECURITY_EVENTS=true
LIBRARIAN_AUDIT_ENABLED=false
LIBRARIAN_VALIDATE_REQUESTS=true
LIBRARIAN_LOG_LEVEL=DEBUG
```

## 🛡️ Security Best Practices

### 1. **Default Secure Configuration**
- Always default to localhost-only binding
- Require explicit flags for external access
- Enable IP filtering by default in production
- Log all security events

### 2. **Layered Security**
- Network-level: Firewall rules
- Application-level: IP filtering, rate limiting
- Transport-level: SSL/TLS encryption
- Authentication-level: API keys, JWT tokens

### 3. **Monitoring & Alerting**
- Log all authentication attempts
- Monitor rate limit violations
- Track IP filtering blocks
- Alert on suspicious activity

### 4. **Regular Security Updates**
- Keep dependencies updated
- Monitor security advisories
- Regular security audits
- Penetration testing

This security configuration provides comprehensive protection while maintaining the flexibility needed for different deployment scenarios, from development to production environments.
