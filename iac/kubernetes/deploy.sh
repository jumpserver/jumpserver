#!/bin/bash

# JumpServer Kubernetes Deployment Script
# This script deploys JumpServer to a Kubernetes cluster

set -euo pipefail

# Configuration
NAMESPACE="jumpserver"
KUBECTL_CMD="kubectl"
DRY_RUN=false
SKIP_SECRETS=false
INGRESS_CLASS="nginx"
DOMAIN="jumpserver.local"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy JumpServer to Kubernetes cluster

OPTIONS:
    -n, --namespace NAMESPACE    Kubernetes namespace (default: jumpserver)
    -d, --domain DOMAIN         Domain name for ingress (default: jumpserver.local)
    -i, --ingress-class CLASS   Ingress class (default: nginx)
    --dry-run                   Show what would be deployed without applying
    --skip-secrets              Skip secrets deployment (use existing)
    -h, --help                  Show this help message

EXAMPLES:
    $0                                          # Deploy with defaults
    $0 -d jumpserver.company.com               # Deploy with custom domain
    $0 --dry-run                               # Preview deployment
    $0 --skip-secrets -d prod.jumpserver.com   # Deploy without secrets

EOF
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check if namespace exists
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_warning "Namespace '$NAMESPACE' already exists"
    fi
    
    log_success "Prerequisites check passed"
}

generate_secrets() {
    log_info "Generating secrets..."
    
    # Generate SECRET_KEY (50 characters)
    SECRET_KEY=$(openssl rand -base64 50 | tr -d "=+/" | cut -c1-50)
    SECRET_KEY_B64=$(echo -n "$SECRET_KEY" | base64 -w 0)
    
    # Generate BOOTSTRAP_TOKEN (24 characters)
    BOOTSTRAP_TOKEN=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-24)
    BOOTSTRAP_TOKEN_B64=$(echo -n "$BOOTSTRAP_TOKEN" | base64 -w 0)
    
    # Generate database password
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
    DB_PASSWORD_B64=$(echo -n "$DB_PASSWORD" | base64 -w 0)
    
    # Update secrets file
    sed -i.bak \
        -e "s|SECRET_KEY:.*|SECRET_KEY: $SECRET_KEY_B64|" \
        -e "s|BOOTSTRAP_TOKEN:.*|BOOTSTRAP_TOKEN: $BOOTSTRAP_TOKEN_B64|" \
        -e "s|DB_PASSWORD:.*|DB_PASSWORD: $DB_PASSWORD_B64|" \
        -e "s|POSTGRES_PASSWORD:.*|POSTGRES_PASSWORD: $DB_PASSWORD_B64|" \
        secrets.yaml
    
    log_success "Secrets generated and updated in secrets.yaml"
    log_warning "Please save these credentials securely:"
    echo "  SECRET_KEY: $SECRET_KEY"
    echo "  BOOTSTRAP_TOKEN: $BOOTSTRAP_TOKEN"
    echo "  DB_PASSWORD: $DB_PASSWORD"
}

update_ingress_domain() {
    log_info "Updating ingress configuration for domain: $DOMAIN"
    
    # Update ingress files
    sed -i.bak \
        -e "s|jumpserver\.yourdomain\.com|$DOMAIN|g" \
        -e "s|jumpserver-ws\.yourdomain\.com|ws.$DOMAIN|g" \
        -e "s|ingressClassName:.*|ingressClassName: $INGRESS_CLASS|" \
        ingress.yaml
    
    log_success "Ingress configuration updated"
}

deploy_component() {
    local component=$1
    local file=$2
    
    log_info "Deploying $component..."
    
    if [ "$DRY_RUN" = true ]; then
        echo "Would apply: $file"
        kubectl apply -f "$file" --dry-run=client
    else
        kubectl apply -f "$file"
        log_success "$component deployed"
    fi
}

wait_for_rollout() {
    local resource=$1
    
    log_info "Waiting for $resource to be ready..."
    
    if [ "$DRY_RUN" = false ]; then
        kubectl rollout status "$resource" -n "$NAMESPACE" --timeout=300s
        log_success "$resource is ready"
    fi
}

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -d|--domain)
                DOMAIN="$2"
                shift 2
                ;;
            -i|--ingress-class)
                INGRESS_CLASS="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --skip-secrets)
                SKIP_SECRETS=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    log_info "Starting JumpServer Kubernetes deployment"
    log_info "Namespace: $NAMESPACE"
    log_info "Domain: $DOMAIN"
    log_info "Ingress Class: $INGRESS_CLASS"
    log_info "Dry Run: $DRY_RUN"
    
    # Check prerequisites
    check_prerequisites
    
    # Change to script directory
    cd "$(dirname "$0")"
    
    # Generate secrets if not skipping
    if [ "$SKIP_SECRETS" = false ]; then
        generate_secrets
    fi
    
    # Update ingress domain
    update_ingress_domain
    
    # Deploy components in order
    deploy_component "Namespace" "namespace.yaml"
    
    if [ "$SKIP_SECRETS" = false ]; then
        deploy_component "Secrets" "secrets.yaml"
    fi
    
    deploy_component "ConfigMaps" "configmap.yaml"
    deploy_component "Storage" "storage.yaml"
    deploy_component "Network Policies" "networkpolicy.yaml"
    deploy_component "Database" "database.yaml"
    deploy_component "Cache" "cache.yaml"
    deploy_component "Application" "application.yaml"
    deploy_component "Services" "services.yaml"
    deploy_component "Ingress" "ingress.yaml"
    deploy_component "HPA & PDB" "hpa.yaml"
    deploy_component "Monitoring" "monitoring.yaml"
    
    # Wait for deployments
    if [ "$DRY_RUN" = false ]; then
        wait_for_rollout "statefulset/jumpserver-database"
        wait_for_rollout "statefulset/jumpserver-cache"
        wait_for_rollout "deployment/jumpserver-application"
        
        log_success "JumpServer deployment completed!"
        log_info "Access JumpServer at: https://$DOMAIN"
        log_info "Default credentials: admin / ChangeMe"
        log_warning "Please change the default password after first login"
        
        # Show service status
        kubectl get pods -n "$NAMESPACE"
        kubectl get services -n "$NAMESPACE"
        kubectl get ingress -n "$NAMESPACE"
    else
        log_info "Dry run completed. Use without --dry-run to actually deploy."
    fi
}

# Run main function
main "$@"
