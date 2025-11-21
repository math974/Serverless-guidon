#!/usr/bin/env bash

set -euo pipefail

# Prepare services by copying shared/ directory to each service
# This script should be run before deployment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SHARED_DIR="${PROJECT_ROOT}/services/shared"

SERVICES=(
    "services/proxy"
    "services/processor-base"
    "services/processor-art"
    "services/discord-registrar"
    "services/auth-service"
    "services/user-manager"
    "services/web-frontend"
)

for service_dir in "${SERVICES[@]}"; do
    service_path="${PROJECT_ROOT}/${service_dir}"
    target_shared="${service_path}/shared"

    if [ ! -d "${service_path}" ]; then
        continue
    fi

    rm -rf "${target_shared}" 2>/dev/null || true
    cp -r "${SHARED_DIR}" "${target_shared}"
done
