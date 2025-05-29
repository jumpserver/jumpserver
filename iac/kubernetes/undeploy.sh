#!/bin/bash

# JumpServer Kubernetes Undeployment Script
# This script removes JumpServer from a Kubernetes cluster

set -euo pipefail

# Configuration
NAMESPACE="jumpserver"
KUBECTL_CMD="kubectl"
DRY_RUN=false
KEEP_DATA=false
KEEP_NAMESPACE=false

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

Remove JumpServer from Kubernetes cluster

OPTIONS:
    -n, --namespace NAMESPACE    Kubernetes namespace (default: jumpserver)
    --dry-run                   Show what would be removed without applying
    --keep-data                 Keep persistent volumes and data
    --keep-namespace            Keep the namespace after cleanup
    -h, --help                  Show this help message

EXAMPLES:
    $0                          # Remove everything including data
    $0 --keep-data             # Remove deployment but keep data
    $0 --dry-run               # Preview what would be removed
    $0 --keep-namespace        # Remove deployment but keep namespace

WARNING: This will permanently delete JumpServer and potentially all data!

EOF
}

confirm_deletion() {
    if [ "$DRY_RUN" = true ]; then
        return 0
    fi
    
    log_warning "This will permanently delete JumpServer from namespace '$NAMESPACE'"
    if [ "$KEEP_DATA" = false ]; then
        log_warning "ALL DATA WILL BE LOST including databases, logs, and configurations!"
    fi
    
    read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirmation
    
    if [ "$confirmation" != "yes" ]; then
        log_info "Operation cancelled"
        exit 0
    fi
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
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_warning "Namespace '$NAMESPACE' does not exist"
        exit 0
    fi
    
    log_success "Prerequisites check passed"
}

remove_component() {
    local component=$1
    local file=$2
    
    log_info "Removing $component..."
    
    if [ "$DRY_RUN" = true ]; then
        echo "Would delete: $file"
        kubectl delete -f "$file" --dry-run=client --ignore-not-found=true
    else
        kubectl delete -f "$file" --ignore-not-found=true
        log_success "$component removed"
    fi
}

remove_pvcs() {
    if [ "$KEEP_DATA" = true ]; then
        log_info "Keeping persistent volume claims (--keep-data specified)"
        return 0
    fi
    
    log_info "Removing persistent volume claims..."
    
    if [ "$DRY_RUN" = true ]; then
        echo "Would delete PVCs in namespace: $NAMESPACE"
        kubectl get pvc -n "$NAMESPACE"
    else
        kubectl delete pvc --all -n "$NAMESPACE" --ignore-not-found=true
        log_success "Persistent volume claims removed"
    fi
}

remove_namespace() {
    if [ "$KEEP_NAMESPACE" = true ]; then
        log_info "Keeping namespace (--keep-namespace specified)"
        return 0
    fi
    
    log_info "Removing namespace..."
    
    if [ "$DRY_RUN" = true ]; then
        echo "Would delete namespace: $NAMESPACE"
    else
        kubectl delete namespace "$NAMESPACE" --ignore-not-found=true
        log_success "Namespace removed"
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
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --keep-data)
                KEEP_DATA=true
                shift
                ;;
            --keep-namespace)
                KEEP_NAMESPACE=true
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
    
    log_info "Starting JumpServer Kubernetes undeployment"
    log_info "Namespace: $NAMESPACE"
    log_info "Dry Run: $DRY_RUN"
    log_info "Keep Data: $KEEP_DATA"
    log_info "Keep Namespace: $KEEP_NAMESPACE"
    
    # Check prerequisites
    check_prerequisites
    
    # Confirm deletion
    confirm_deletion
    
    # Change to script directory
    cd "$(dirname "$0")"
    
    # Remove components in reverse order
    remove_component "Monitoring" "monitoring.yaml"
    remove_component "HPA & PDB" "hpa.yaml"
    remove_component "Ingress" "ingress.yaml"
    remove_component "Services" "services.yaml"
    remove_component "Application" "application.yaml"
    remove_component "Cache" "cache.yaml"
    remove_component "Database" "database.yaml"
    remove_component "Network Policies" "networkpolicy.yaml"
    
    # Remove PVCs if not keeping data
    remove_pvcs
    
    remove_component "Storage" "storage.yaml"
    remove_component "ConfigMaps" "configmap.yaml"
    remove_component "Secrets" "secrets.yaml"
    
    # Remove namespace if not keeping it
    remove_namespace
    
    if [ "$DRY_RUN" = false ]; then
        log_success "JumpServer undeployment completed!"
        
        if [ "$KEEP_DATA" = true ]; then
            log_info "Data has been preserved in persistent volumes"
        fi
        
        if [ "$KEEP_NAMESPACE" = true ]; then
            log_info "Namespace '$NAMESPACE' has been preserved"
        fi
    else
        log_info "Dry run completed. Use without --dry-run to actually remove."
    fi
}

# Run main function
main "$@"
