# JumpServer Docker Deployment Guide

This guide provides detailed instructions for deploying JumpServer using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB RAM and 2 CPU cores
- 20GB+ available disk space

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/jumpserver/jumpserver.git
cd jumpserver
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit the configuration
nano .env  # or your preferred editor
```

### 3. Generate Security Keys

**Important**: Generate secure random keys for production:

```bash
# Generate SECRET_KEY (50 characters)
openssl rand -base64 50 | tr -d "=+/" | cut -c1-50

# Generate BOOTSTRAP_TOKEN (24 characters)
openssl rand -base64 24 | tr -d "=+/" | cut -c1-24
```

Update these values in your `.env` file.

### 4. Start Services

```bash
# Create required directories
mkdir -p custom/docker/stacks/stk-jumpserver-001/{Database/Data,Redis/Data,Application/Data,Application/Logs}

# Set proper ownership for non-root user (UID:GID 1000:1000 by default)
sudo chown -R 1000:1000 custom/docker/stacks/stk-jumpserver-001/

# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### 5. Access JumpServer

- Web Interface: `http://localhost:8080`
- Default credentials:
  - Username: `admin`
  - Password: `ChangeMe`

**Important**: Change the default password immediately after first login.

## Configuration

### Environment Variables

Key configuration options in `.env`:

#### Database Settings
```bash
DATABASE_PASSWORD=your_secure_password
DATABASE_NAME=jumpserver
DATABASE_USER=jumpserver
```

#### Security Settings
```bash
SECRET_KEY=your_50_character_secret_key
BOOTSTRAP_TOKEN=your_24_character_bootstrap_token
SECURITY_MFA_AUTH=1  # Enable MFA globally
SECURITY_WATERMARK_ENABLED=false  # Disable watermarks by default
```

#### Network Settings
```bash
HTTP_BIND_HOST=0.0.0.0
HTTP_LISTEN_PORT=8080
WS_LISTEN_PORT=8070
EXTERNAL_URL=https://jumpserver.yourdomain.com
```

#### User Configuration
```bash
# Run containers as non-root user (recommended for security)
UID=1000
GID=1000

# To run as root (not recommended for production)
# UID=0
# GID=0
```

### SSL/TLS Configuration

For production deployments, configure SSL/TLS:

1. **Using Reverse Proxy (Recommended)**:
   - Deploy nginx/Apache/Traefik in front of JumpServer
   - Handle SSL termination at the proxy level
   - Forward requests to JumpServer container

2. **Using Docker Compose with SSL**:
   ```yaml
   # Add to docker-compose.yml
   volumes:
     - ./ssl/cert.pem:/opt/jumpserver/ssl/cert.pem:ro
     - ./ssl/key.pem:/opt/jumpserver/ssl/key.pem:ro
   environment:
     - HTTPS_PORT=8443
   ```

## Production Considerations

### High Availability

For production environments:

1. **External Database**: Use managed PostgreSQL service
2. **External Redis**: Use managed Redis service
3. **Load Balancing**: Deploy multiple JumpServer instances
4. **Shared Storage**: Use network storage for session recordings

Example external database configuration:
```bash
# In .env file
DATABASE_HOST=your-postgres-server.com
DATABASE_PORT=5432
REDIS_HOST=your-redis-server.com
REDIS_PORT=6379
```

### Backup Strategy

1. **Database Backup**:
   ```bash
   docker-compose exec Database pg_dump -U jumpserver jumpserver > backup.sql
   ```

2. **Application Data Backup**:
   ```bash
   tar -czf jumpserver-data-backup.tar.gz custom/docker/stacks/stk-jumpserver-001/Application/Data/
   ```

3. **Automated Backups**:
   ```bash
   # Add to crontab
   0 2 * * * /path/to/backup-script.sh
   ```

### Monitoring

Monitor JumpServer health:

```bash
# Check container health
docker-compose ps

# Monitor resource usage
docker stats

# Check application logs
docker-compose logs -f Application

# Health check endpoint
curl http://localhost:8080/api/health/
```

### Security Hardening

1. **Network Security**:
   - Use internal networks for database/redis
   - Expose only necessary ports
   - Implement firewall rules

2. **Container Security**:
   - Run containers as non-root user
   - Use read-only filesystems where possible
   - Regular security updates

3. **Application Security**:
   - Enable MFA for all users
   - Configure strong password policies
   - Regular security audits

## Troubleshooting

### Common Issues

1. **Database Connection Failed**:
   ```bash
   # Check database container
   docker-compose logs Database

   # Verify database is ready
   docker-compose exec Database pg_isready -U jumpserver
   ```

2. **Permission Denied Errors**:
   ```bash
   # Fix volume permissions
   sudo chown -R 1000:1000 custom/docker/stacks/stk-jumpserver-001/
   ```

3. **Memory Issues**:
   ```bash
   # Increase container memory limits
   # Add to docker-compose.yml under services
   deploy:
     resources:
       limits:
         memory: 2G
   ```

### Log Analysis

```bash
# Application logs
docker-compose logs Application

# Database logs
docker-compose logs Database

# Redis logs
docker-compose logs Redis

# Follow logs in real-time
docker-compose logs -f --tail=100
```

### Performance Tuning

1. **Database Optimization**:
   ```sql
   -- Connect to database and run
   ANALYZE;
   VACUUM;
   ```

2. **Redis Optimization**:
   ```bash
   # Monitor Redis performance
   docker-compose exec Redis redis-cli info memory
   ```

## Maintenance

### Updates

```bash
# Pull latest images
docker-compose pull

# Restart services with new images
docker-compose up -d

# Clean up old images
docker image prune -f
```

### Scaling

```bash
# Scale application instances
docker-compose up -d --scale Application=3

# Use load balancer to distribute traffic
```

## Support

- Documentation: https://jumpserver.com/docs
- Community: https://github.com/jumpserver/jumpserver/discussions
- Issues: https://github.com/jumpserver/jumpserver/issues
