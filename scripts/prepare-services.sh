#!/usr/bin/env bash

set -euo pipefail

# Copy shared modules to each service directory before deployment
# This allows Cloud Run to find the shared modules when deploying with --source

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SHARED_DIR="${PROJECT_ROOT}/services/shared"

echo "=========================================="
echo "  Preparing services for deployment"
echo "=========================================="
echo "Copying shared modules to each service..."
echo ""

# List of services that need shared modules
SERVICES=(
  "proxy"
  "processor-art"
  "processor-base"
  "discord-registrar"
)

# Copy shared modules to each service
for service in "${SERVICES[@]}"; do
  SERVICE_DIR="${PROJECT_ROOT}/services/${service}"
  
  if [ -d "${SERVICE_DIR}" ]; then
    echo "  → ${service}"
    
    # Remove existing shared directory if it exists
    rm -rf "${SERVICE_DIR}/shared"
    
    # Copy shared directory
    cp -r "${SHARED_DIR}" "${SERVICE_DIR}/"
    
    echo "    ✓ Shared modules copied"
  else
    echo "  ⚠ Warning: Service directory not found: ${service}"
  fi
done

echo ""
echo "=========================================="
echo "  ✓ All services prepared"
echo "=========================================="
echo ""
echo "Note: shared/ directories are gitignored in service folders"
echo "They are only used during deployment"

