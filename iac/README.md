# JumpServer Infrastructure as Code (IaC)

This directory contains comprehensive Infrastructure as Code (IaC) configurations for deploying JumpServer across different platforms and orchestrators.

## 🏗️ Available Deployments

### 🐳 Docker Compose
**Location**: `../docker-compose.yml` (root directory)
- **Best for**: Development, testing, small production deployments
- **Features**: Single-host deployment, easy setup, comprehensive configuration
- **Components**: PostgreSQL, Valkey (Redis), JumpServer application

### ☸️ Kubernetes
**Location**: `./kubernetes/`
- **Best for**: Production deployments, high availability, scalability
- **Features**: Auto-scaling, health checks, network policies, monitoring
- **Components**: StatefulSets, Deployments, Services, Ingress, PVCs

### ⛵ Helm Charts
**Location**: `./helm/jumpserver/`
- **Best for**: Kubernetes deployments with package management
- **Features**: Templating, dependency management, easy upgrades
- **Components**: Configurable charts with external database support

## 🚀 Quick Start Guide

### Choose Your Deployment Method

#### 1. Docker Compose (Recommended for Getting Started)
```bash
# Navigate to project root
cd ..

# Copy environment template
cp .env.example .env

# Edit configuration
nano .env

# Create directories and set permissions
mkdir -p custom/docker/stacks/stk-jumpserver-001/{Database/Data,Cache/Data,Application/Data,Application/Logs}
sudo chown -R 1000:1000 custom/docker/stacks/stk-jumpserver-001/

# Deploy
docker-compose up -d

# Access: http://localhost:8080
```

#### 2. Kubernetes (Production Ready)
```bash
# Navigate to Kubernetes directory
cd kubernetes/

# Configure domain (optional)
sed -i 's/jumpserver.yourdomain.com/jumpserver.company.com/g' ingress.yaml

# Deploy with automated script
chmod +x deploy.sh
./deploy.sh -d jumpserver.company.com

# Or deploy manually
kubectl apply -f .

# Access via ingress
```

#### 3. Helm Chart (Package Management)
```bash
# Add Bitnami repository for dependencies
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install from local chart
cd helm/
helm install jumpserver ./jumpserver/ \
  --set jumpserver.ingress.hosts[0].host=jumpserver.company.com \
  --set postgresql.auth.password=SecurePassword123

# Or install with custom values
helm install jumpserver ./jumpserver/ -f custom-values.yaml
```

## 📊 Deployment Comparison

| Feature | Docker Compose | Kubernetes | Helm |
|---------|----------------|------------|------|
| **Complexity** | Low | Medium | Medium |
| **Setup Time** | 5 minutes | 15 minutes | 10 minutes |
| **Scalability** | Limited | Excellent | Excellent |
| **High Availability** | No | Yes | Yes |
| **Auto-scaling** | No | Yes | Yes |
| **Rolling Updates** | Manual | Automatic | Automatic |
| **Monitoring** | Basic | Advanced | Advanced |
| **Backup/Restore** | Manual | Automated | Automated |
| **Multi-host** | No | Yes | Yes |
| **Load Balancing** | External | Built-in | Built-in |

## 🔧 Configuration Options

### Environment Variables

All deployment methods support comprehensive configuration through environment variables:

#### Core Configuration
```bash
# Database
DB_ENGINE=postgresql
DB_HOST=database-host
DB_PORT=5432
DB_NAME=jumpserver
DB_USER=jumpserver
DB_PASSWORD=SecurePassword123

# Cache
CACHE_HOST=cache-host
CACHE_PORT=6379
CACHE_PASSWORD=  # Optional

# JumpServer
SECRET_KEY=YourSecretKey50Characters
BOOTSTRAP_TOKEN=YourBootstrapToken24Chars
LOG_LEVEL=INFO
```

#### Security Settings
```bash
# Authentication
SECURITY_MFA_AUTH=1
SECURITY_MAX_IDLE_TIME=30
SECURITY_MAX_SESSION_TIME=24
SECURITY_WATERMARK_ENABLED=false

# Password Policies
SECURITY_PASSWORD_MIN_LENGTH=8
SECURITY_PASSWORD_UPPER_CASE=true
SECURITY_PASSWORD_LOWER_CASE=true
SECURITY_PASSWORD_NUMBER=true
```

#### Network Configuration
```bash
# Binding
HTTP_BIND_HOST=0.0.0.0
HTTP_LISTEN_PORT=8080
WS_LISTEN_PORT=8070

# External URL
EXTERNAL_URL=https://jumpserver.company.com
```

### Storage Configuration

#### Docker Compose
```yaml
volumes:
  - "${STACK_BINDMOUNTROOT}/${STACK_NAME}/Application/Data:/opt/jumpserver/data:rw"
  - "${STACK_BINDMOUNTROOT}/${STACK_NAME}/Application/Logs:/opt/jumpserver/logs:rw"
```

#### Kubernetes
```yaml
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 50Gi
  storageClassName: shared-storage
```

#### Helm
```yaml
jumpserver:
  persistence:
    enabled: true
    size: 50Gi
    storageClass: "fast-ssd"
```

## 🔒 Security Best Practices

### Container Security
- **Non-root users**: All containers run as unprivileged users
- **Read-only filesystems**: Where applicable
- **Capability dropping**: Unnecessary capabilities removed
- **Security contexts**: Proper user/group settings

### Network Security
- **Network policies**: Kubernetes deployments include network isolation
- **TLS encryption**: HTTPS/WSS for all communications
- **Internal networks**: Database and cache not exposed externally
- **Firewall rules**: Only necessary ports exposed

### Secrets Management
- **Environment variables**: Sensitive data in secrets/environment files
- **Kubernetes secrets**: Base64 encoded, separate objects
- **Helm secrets**: Support for external secret management
- **Rotation**: Regular secret rotation procedures

## 📈 Monitoring & Observability

### Metrics Collection
```bash
# Prometheus metrics endpoint
curl http://jumpserver:8080/metrics

# Health check endpoint
curl http://jumpserver:8080/api/health/
```

### Logging
```bash
# Docker Compose
docker-compose logs -f jumpserver

# Kubernetes
kubectl logs -f deployment/jumpserver-application -n jumpserver

# Helm
helm status jumpserver
```

### Alerting
Configure alerts for:
- Application health
- Database connectivity
- High resource usage
- Failed authentication attempts
- Certificate expiration

## 🔄 Backup & Recovery

### Database Backup
```bash
# Docker Compose
docker-compose exec database pg_dump -U jumpserver jumpserver > backup.sql

# Kubernetes
kubectl exec -n jumpserver jumpserver-database-0 -- pg_dump -U jumpserver jumpserver > backup.sql
```

### Application Data Backup
```bash
# Docker Compose
tar -czf jumpserver-data.tar.gz custom/docker/stacks/stk-jumpserver-001/Application/Data/

# Kubernetes
kubectl cp jumpserver/jumpserver-application-xxx:/opt/jumpserver/data ./data-backup/
```

### Automated Backups
```bash
# Cron job example
0 2 * * * /path/to/backup-script.sh
```

## 🚀 Scaling & Performance

### Horizontal Scaling

#### Kubernetes HPA
```yaml
spec:
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

#### Manual Scaling
```bash
# Kubernetes
kubectl scale deployment jumpserver-application --replicas=5 -n jumpserver

# Helm
helm upgrade jumpserver ./jumpserver/ --set jumpserver.replicaCount=5
```

### Vertical Scaling
```bash
# Update resource limits
kubectl patch deployment jumpserver-application -n jumpserver -p '{"spec":{"template":{"spec":{"containers":[{"name":"jumpserver","resources":{"limits":{"cpu":"4","memory":"8Gi"}}}]}}}}'
```

### Performance Tuning
- **Database optimization**: Connection pooling, query optimization
- **Cache configuration**: Memory allocation, persistence settings
- **Application tuning**: Worker processes, connection limits

## 🛠️ Maintenance

### Updates
```bash
# Docker Compose
docker-compose pull
docker-compose up -d

# Kubernetes
kubectl set image deployment/jumpserver-application jumpserver=jumpserver/jumpserver:v4.1 -n jumpserver

# Helm
helm upgrade jumpserver ./jumpserver/ --set jumpserver.image.tag=v4.1
```

### Health Checks
```bash
# Check all components
kubectl get all -n jumpserver

# Check specific component health
kubectl describe pod jumpserver-application-xxx -n jumpserver
```

### Troubleshooting
```bash
# View logs
kubectl logs -f deployment/jumpserver-application -n jumpserver

# Debug networking
kubectl exec -it jumpserver-application-xxx -n jumpserver -- nslookup jumpserver-database

# Check resources
kubectl top pods -n jumpserver
```

## 📚 Advanced Configurations

### External Database
```yaml
# Disable internal database
postgresql:
  enabled: false

# Configure external database
externalDatabase:
  enabled: true
  host: "external-postgres.company.com"
  port: 5432
  username: "jumpserver"
  password: "SecurePassword"
  database: "jumpserver"
```

### External Cache
```yaml
# Disable internal cache
redis:
  enabled: false

# Configure external cache
externalCache:
  enabled: true
  host: "external-redis.company.com"
  port: 6379
  password: "CachePassword"
```

### Custom Storage Classes
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: jumpserver-fast
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
```

## 🤝 Contributing

1. **Test thoroughly**: All changes should be tested in development
2. **Update documentation**: Keep README and comments current
3. **Follow conventions**: Use established naming and structure patterns
4. **Security review**: Ensure security best practices are maintained

## 📞 Support

- **Documentation**: [JumpServer Docs](https://jumpserver.com/docs)
- **Community**: [GitHub Discussions](https://github.com/jumpserver/jumpserver/discussions)
- **Issues**: [GitHub Issues](https://github.com/jumpserver/jumpserver/issues)
- **Commercial Support**: [JumpServer Enterprise](https://jumpserver.com/enterprise)

## 📄 License

This IaC configuration is part of JumpServer and follows the same GPL-3.0 license.
