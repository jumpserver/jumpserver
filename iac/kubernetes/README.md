# JumpServer Kubernetes Deployment

This directory contains comprehensive Kubernetes manifests and deployment scripts for running JumpServer in a production Kubernetes environment.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Ingress       │    │   LoadBalancer  │    │   NodePort      │
│   Controller    │    │   Service       │    │   Service       │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼───────────────┐
                    │     JumpServer Application  │
                    │     (Deployment - 2+ pods)  │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────┼───────────────┐
                    │             │               │
          ┌─────────▼───────┐   ┌─▼─────────┐   ┌─▼─────────┐
          │   PostgreSQL    │   │  Valkey   │   │  Storage  │
          │  (StatefulSet)  │   │(StatefulSet)│ │   (PVC)   │
          └─────────────────┘   └───────────┘   └───────────┘
```

## 📁 File Structure

```
iac/kubernetes/
├── README.md                 # This documentation
├── deploy.sh                 # Automated deployment script
├── undeploy.sh              # Automated cleanup script
├── kustomization.yaml       # Kustomize configuration
├── namespace.yaml           # Namespace, quotas, and limits
├── configmap.yaml           # Configuration data
├── secrets.yaml             # Sensitive configuration
├── storage.yaml             # Persistent volume claims
├── database.yaml            # PostgreSQL StatefulSet
├── cache.yaml               # Valkey StatefulSet
├── application.yaml         # JumpServer Deployment
├── services.yaml            # Service definitions
├── ingress.yaml             # Ingress configurations
├── networkpolicy.yaml       # Network security policies
├── hpa.yaml                 # Horizontal Pod Autoscaler
└── monitoring.yaml          # Monitoring and metrics
```

## 🚀 Quick Start

### Prerequisites

- Kubernetes cluster (1.20+)
- kubectl configured
- Ingress controller (nginx, traefik, etc.)
- Storage class for persistent volumes
- 4 CPU cores and 8GB RAM minimum

### 1. Clone and Navigate

```bash
git clone https://github.com/jumpserver/jumpserver.git
cd jumpserver/iac/kubernetes
```

### 2. Configure Domain (Optional)

```bash
# Edit ingress.yaml to set your domain
sed -i 's/jumpserver.yourdomain.com/jumpserver.company.com/g' ingress.yaml
```

### 3. Deploy

```bash
# Make scripts executable
chmod +x deploy.sh undeploy.sh

# Deploy with automatic secret generation
./deploy.sh -d jumpserver.company.com

# Or deploy with dry-run first
./deploy.sh --dry-run
```

### 4. Access

```bash
# Get ingress IP
kubectl get ingress -n jumpserver

# Access JumpServer
# https://jumpserver.company.com
# Default: admin / ChangeMe
```

## 🔧 Configuration

### Environment Variables

Key configuration is managed through ConfigMaps and Secrets:

**ConfigMap (jumpserver-config):**
- Database connection settings
- Cache configuration
- Security settings
- Network configuration

**Secrets (jumpserver-secrets):**
- SECRET_KEY (Django secret)
- BOOTSTRAP_TOKEN (JumpServer token)
- Database passwords
- Cache passwords (optional)

### Storage Classes

Update `storage.yaml` with your cluster's storage classes:

```yaml
# For fast SSD storage
storageClassName: fast-ssd

# For shared storage (NFS, EFS, etc.)
storageClassName: shared-storage
```

### Resource Requirements

**Minimum Resources:**
- Database: 200m CPU, 512Mi RAM
- Cache: 100m CPU, 256Mi RAM  
- Application: 500m CPU, 1Gi RAM

**Production Resources:**
- Database: 1 CPU, 2Gi RAM
- Cache: 500m CPU, 1Gi RAM
- Application: 2 CPU, 4Gi RAM

## 🔒 Security Features

### Network Policies

- **Default Deny**: All traffic blocked by default
- **Application**: Only allows necessary ingress/egress
- **Database**: Only accessible from application pods
- **Cache**: Only accessible from application pods

### Pod Security

- **Non-root containers**: All services run as non-root users
- **Read-only root filesystem**: Where possible
- **Dropped capabilities**: All unnecessary capabilities removed
- **Security contexts**: Proper user/group settings

### Secrets Management

- **Base64 encoded**: All secrets properly encoded
- **Separate secret objects**: Logical separation of concerns
- **TLS certificates**: Support for custom certificates

## 📊 Monitoring & Observability

### Metrics

- **Prometheus integration**: ServiceMonitor for scraping
- **Grafana dashboard**: Pre-configured dashboard
- **Health checks**: Liveness and readiness probes

### Logging

- **Structured logging**: JSON format for easy parsing
- **Log aggregation**: Compatible with ELK, Fluentd
- **Persistent logs**: Stored in persistent volumes

### Alerting

Configure alerts for:
- Pod restarts
- High memory/CPU usage
- Database connectivity
- Cache connectivity
- Failed authentication attempts

## 🔄 Scaling & High Availability

### Horizontal Pod Autoscaler

Automatic scaling based on:
- CPU utilization (70% threshold)
- Memory utilization (80% threshold)
- Custom metrics (active sessions)

### Pod Disruption Budget

- **Minimum available**: 1 pod always running
- **Graceful updates**: Zero-downtime deployments

### Database High Availability

For production, consider:
- External managed database (RDS, Cloud SQL)
- PostgreSQL cluster with replication
- Backup and restore procedures

## 🌐 Ingress Options

### NGINX Ingress Controller

```yaml
annotations:
  nginx.ingress.kubernetes.io/ssl-redirect: "true"
  nginx.ingress.kubernetes.io/proxy-body-size: "100m"
```

### Traefik

```yaml
annotations:
  traefik.ingress.kubernetes.io/router.tls: "true"
  traefik.ingress.kubernetes.io/router.entrypoints: websecure
```

### AWS ALB

```yaml
annotations:
  kubernetes.io/ingress.class: alb
  alb.ingress.kubernetes.io/scheme: internet-facing
```

## 🛠️ Maintenance

### Updates

```bash
# Update images
kubectl set image deployment/jumpserver-application jumpserver=jumpserver/jumpserver:v4.1 -n jumpserver

# Rolling restart
kubectl rollout restart deployment/jumpserver-application -n jumpserver
```

### Backups

```bash
# Database backup
kubectl exec -n jumpserver jumpserver-database-0 -- pg_dump -U jumpserver jumpserver > backup.sql

# Application data backup
kubectl cp jumpserver/jumpserver-application-xxx:/opt/jumpserver/data ./data-backup/
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment jumpserver-application --replicas=5 -n jumpserver

# Update HPA
kubectl patch hpa jumpserver-application-hpa -n jumpserver -p '{"spec":{"maxReplicas":10}}'
```

## 🐛 Troubleshooting

### Common Issues

**Pods not starting:**
```bash
kubectl describe pod -n jumpserver
kubectl logs -n jumpserver deployment/jumpserver-application
```

**Database connection issues:**
```bash
kubectl exec -n jumpserver jumpserver-database-0 -- pg_isready
kubectl logs -n jumpserver jumpserver-database-0
```

**Storage issues:**
```bash
kubectl get pvc -n jumpserver
kubectl describe pvc jumpserver-data-pvc -n jumpserver
```

### Debug Commands

```bash
# Check all resources
kubectl get all -n jumpserver

# Check events
kubectl get events -n jumpserver --sort-by='.lastTimestamp'

# Check network policies
kubectl get networkpolicy -n jumpserver

# Test connectivity
kubectl run debug --image=busybox -n jumpserver --rm -it -- sh
```

## 📚 Advanced Configuration

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

### External Database

```yaml
# Update configmap.yaml
DB_HOST: "external-postgres.company.com"
DB_PORT: "5432"
```

### SSL/TLS Certificates

```bash
# Generate certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt \
  -subj "/CN=jumpserver.company.com"

# Create secret
kubectl create secret tls jumpserver-tls \
  --cert=tls.crt --key=tls.key -n jumpserver
```

## 🤝 Contributing

1. Test changes in development environment
2. Update documentation
3. Follow Kubernetes best practices
4. Submit pull request with detailed description

## 📞 Support

- **Documentation**: [JumpServer Docs](https://jumpserver.com/docs)
- **Community**: [GitHub Discussions](https://github.com/jumpserver/jumpserver/discussions)
- **Issues**: [GitHub Issues](https://github.com/jumpserver/jumpserver/issues)
