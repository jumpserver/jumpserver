#!/bin/bash

# JumpServer Docker Hub Publishing Script
# This script builds and publishes JumpServer Docker images to Docker Hub
# It supports both versioned tags and 'latest' tag
# The script is idempotent and handles authentication automatically

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYPROJECT_FILE="${PROJECT_ROOT}/pyproject.toml"
DOCKERFILE="${PROJECT_ROOT}/Dockerfile"

# Docker Hub configuration
DOCKER_REGISTRY="docker.io"
DOCKER_NAMESPACE="${DOCKER_NAMESPACE:-jumpserver}"
IMAGE_NAME="${IMAGE_NAME:-jumpserver}"
DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Function to extract version from pyproject.toml
get_version() {
    if [[ ! -f "${PYPROJECT_FILE}" ]]; then
        log_error "pyproject.toml not found at ${PYPROJECT_FILE}"
        exit 1
    fi

    local version
    version=$(grep '^version = ' "${PYPROJECT_FILE}" | sed 's/version = "\(.*\)"/\1/')

    if [[ -z "${version}" ]]; then
        log_error "Could not extract version from pyproject.toml"
        exit 1
    fi

    echo "${version}"
}

# Function to check if Docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running or not accessible"
        exit 1
    fi

    log_info "Docker is available and running"
}

# Function to authenticate with Docker Hub
authenticate_docker_hub() {
    log_info "Checking Docker Hub authentication..."

    # Check if already logged in
    if docker system info | grep -q "Username:"; then
        local current_user
        current_user=$(docker system info | grep "Username:" | awk '{print $2}')
        log_success "Already authenticated as: ${current_user}"
        return 0
    fi

    # Check for environment variables
    if [[ -n "${DOCKER_USERNAME:-}" && -n "${DOCKER_PASSWORD:-}" ]]; then
        log_info "Using environment variables for authentication"
        echo "${DOCKER_PASSWORD}" | docker login "${DOCKER_REGISTRY}" -u "${DOCKER_USERNAME}" --password-stdin
        log_success "Successfully authenticated with Docker Hub"
        return 0
    fi

    # Check for Docker Hub token
    if [[ -n "${DOCKER_HUB_TOKEN:-}" ]]; then
        log_info "Using Docker Hub token for authentication"
        echo "${DOCKER_HUB_TOKEN}" | docker login "${DOCKER_REGISTRY}" -u "${DOCKER_USERNAME:-}" --password-stdin
        log_success "Successfully authenticated with Docker Hub using token"
        return 0
    fi

    # Interactive login
    log_warning "No authentication credentials found in environment variables"
    log_info "Please log in to Docker Hub manually:"
    docker login "${DOCKER_REGISTRY}"
    log_success "Successfully authenticated with Docker Hub"
}

# Function to check if image already exists
image_exists() {
    local tag="$1"
    local full_image="${DOCKER_REGISTRY}/${DOCKER_NAMESPACE}/${IMAGE_NAME}:${tag}"

    if docker manifest inspect "${full_image}" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to build Docker image
build_image() {
    local version="$1"
    local build_args="$2"
    local tags=("$@")
    tags=("${tags[@]:2}")  # Remove first two arguments

    log_info "Building Docker image for version: ${version}"

    # Prepare build command
    local build_cmd="docker build"
    build_cmd+=" --file ${DOCKERFILE}"
    build_cmd+=" --build-arg VERSION=${version}"

    # Add additional build args if provided
    if [[ -n "${build_args}" ]]; then
        build_cmd+=" ${build_args}"
    fi

    # Add tags
    for tag in "${tags[@]}"; do
        local full_tag="${DOCKER_REGISTRY}/${DOCKER_NAMESPACE}/${IMAGE_NAME}:${tag}"
        build_cmd+=" --tag ${full_tag}"
        log_info "Will tag as: ${full_tag}"
    done

    # Add context
    build_cmd+=" ${PROJECT_ROOT}"

    log_info "Executing: ${build_cmd}"
    eval "${build_cmd}"

    log_success "Successfully built Docker image"
}

# Function to push Docker image
push_image() {
    local tags=("$@")

    for tag in "${tags[@]}"; do
        local full_tag="${DOCKER_REGISTRY}/${DOCKER_NAMESPACE}/${IMAGE_NAME}:${tag}"

        log_info "Pushing image: ${full_tag}"
        docker push "${full_tag}"
        log_success "Successfully pushed: ${full_tag}"
    done
}

# Function to cleanup local images (optional)
cleanup_images() {
    local tags=("$@")

    if [[ "${CLEANUP_LOCAL_IMAGES:-false}" == "true" ]]; then
        log_info "Cleaning up local images..."
        for tag in "${tags[@]}"; do
            local full_tag="${DOCKER_REGISTRY}/${DOCKER_NAMESPACE}/${IMAGE_NAME}:${tag}"
            docker rmi "${full_tag}" || true
        done
        log_success "Local images cleaned up"
    fi
}

# Main function
main() {
    log_info "Starting JumpServer Docker Hub publishing process"

    # Parse command line arguments
    local force_build=false
    local skip_latest=false
    local build_args=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --force)
                force_build=true
                shift
                ;;
            --skip-latest)
                skip_latest=true
                shift
                ;;
            --build-args)
                build_args="$2"
                shift 2
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --force         Force rebuild even if image exists"
                echo "  --skip-latest   Skip building/pushing 'latest' tag"
                echo "  --build-args    Additional build arguments"
                echo "  --help, -h      Show this help message"
                echo ""
                echo "Environment Variables:"
                echo "  DOCKER_USERNAME     Docker Hub username"
                echo "  DOCKER_PASSWORD     Docker Hub password"
                echo "  DOCKER_HUB_TOKEN    Docker Hub access token"
                echo "  DOCKER_NAMESPACE    Docker Hub namespace (default: jumpserver)"
                echo "  IMAGE_NAME          Image name (default: jumpserver)"
                echo "  CLEANUP_LOCAL_IMAGES Clean up local images after push (default: false)"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Validate environment
    check_docker

    # Get version
    local version
    version=$(get_version)
    log_info "Detected version: ${version}"

    # Prepare tags
    local tags=("${version}")
    if [[ "${skip_latest}" == "false" ]]; then
        tags+=("latest")
    fi

    # Check if images already exist (unless force build)
    if [[ "${force_build}" == "false" ]]; then
        local all_exist=true
        for tag in "${tags[@]}"; do
            if ! image_exists "${tag}"; then
                all_exist=false
                break
            fi
        done

        if [[ "${all_exist}" == "true" ]]; then
            log_warning "All images already exist. Use --force to rebuild."
            log_info "Existing tags: ${tags[*]}"
            exit 0
        fi
    fi

    # Authenticate with Docker Hub
    authenticate_docker_hub

    # Build image
    build_image "${version}" "${build_args}" "${tags[@]}"

    # Push images
    push_image "${tags[@]}"

    # Cleanup if requested
    cleanup_images "${tags[@]}"

    log_success "JumpServer Docker images published successfully!"
    log_info "Published tags: ${tags[*]}"
    log_info "Full image names:"
    for tag in "${tags[@]}"; do
        echo "  ${DOCKER_REGISTRY}/${DOCKER_NAMESPACE}/${IMAGE_NAME}:${tag}"
    done
}

# Execute main function with all arguments
main "$@"
