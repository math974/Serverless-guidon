#!/usr/bin/env bash

set -euo pipefail

# Update API Gateway to point to the Proxy Service
# Usage:
#   PROJECT_ID=your-project API_ID=guidon-api GATEWAY_ID=guidon REGION=europe-west1 PROXY_SERVICE=proxy ./update-gateway-proxy.sh

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${API_ID:=guidon-api}"
: "${GATEWAY_ID:=guidon}"
: "${PROXY_SERVICE:=proxy}"
: "${AUTH_SERVICE:=discord-auth-service}"
: "${REGION:=europe-west1}"

echo "Updating API Gateway..."

echo "[1/4] Getting proxy URL..."
PROXY_URL=$(gcloud functions describe "${PROXY_SERVICE}" \
  --gen2 \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(serviceConfig.uri)")

if [ -z "${PROXY_URL}" ]; then
    echo "Error: Proxy service not found"
    exit 1
fi

echo "[2/4] Getting auth-service URL..."
AUTH_URL=$(gcloud functions describe "${AUTH_SERVICE}" \
  --gen2 \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(serviceConfig.uri)" 2>/dev/null || echo "")

if [ -z "${AUTH_URL}" ]; then
    echo "Warning: Auth service not found (auth endpoints will not be updated)"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SPEC_FILE="${PROJECT_ROOT}/configs/openapi2-run.yaml"
TEMP_SPEC="${SPEC_FILE}.tmp"

echo "[3/4] Updating OpenAPI spec..."
if [ ! -f "${SPEC_FILE}" ]; then
    echo "Error: OpenAPI spec not found: ${SPEC_FILE}"
    exit 1
fi

export SPEC_FILE TEMP_SPEC PROXY_URL AUTH_URL
python3 << 'PYTHON_SCRIPT'
import yaml
import sys
import os

spec_file = os.environ['SPEC_FILE']
temp_spec = os.environ['TEMP_SPEC']
proxy_url = os.environ['PROXY_URL']
auth_url = os.environ.get('AUTH_URL', '')

try:
    # Read YAML file
    with open(spec_file, 'r') as f:
        spec = yaml.safe_load(f)

    if not spec or 'paths' not in spec:
        print("ERROR: Invalid OpenAPI spec structure", file=sys.stderr)
        sys.exit(1)

    # Update proxy endpoints
    proxy_endpoints = ['/discord/interactions', '/web/interactions', '/health']
    for endpoint in proxy_endpoints:
        if endpoint in spec['paths']:
            path_config = spec['paths'][endpoint]
            # Find the operation (post, get, etc.) and update its backend address
            for method in path_config:
                if isinstance(path_config[method], dict) and 'x-google-backend' in path_config[method]:
                    spec['paths'][endpoint][method]['x-google-backend']['address'] = proxy_url
                    print(f"  Updated {endpoint} ({method}) → {proxy_url}")

    # Update auth endpoints
    if auth_url:
        auth_endpoints = ['/auth/login', '/auth/callback', '/auth/logout', '/auth/verify', '/auth/user']
        for endpoint in auth_endpoints:
            if endpoint in spec['paths']:
                path_config = spec['paths'][endpoint]
                for method in path_config:
                    if isinstance(path_config[method], dict) and 'x-google-backend' in path_config[method]:
                        spec['paths'][endpoint][method]['x-google-backend']['address'] = auth_url
                        print(f"  Updated {endpoint} ({method}) → {auth_url}")

    # Write updated YAML (preserve formatting)
    with open(temp_spec, 'w') as f:
        yaml.dump(spec, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print("OpenAPI spec updated")
except ImportError:
    print("Error: PyYAML not installed. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error: Failed to update OpenAPI spec: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_SCRIPT

if [ $? -ne 0 ]; then
    echo "Warning: Python script failed, using sed fallback..."
    # Fallback to sed if Python/PyYAML is not available
    cp "${SPEC_FILE}" "${TEMP_SPEC}"

    if [ ! -z "${AUTH_URL}" ]; then
        sed -i.bak \
          -e "s|address: https://discord-auth-service[^ ]*|address: ${AUTH_URL}|g" \
          "${TEMP_SPEC}"
    fi

    sed -i.bak \
      -e "s|address: https://proxy[^ ]*|address: ${PROXY_URL}|g" \
      -e "s|address: https://[^-]*-gdu7lmfosq-ew\.a\.run\.app|address: ${PROXY_URL}|g" \
      "${TEMP_SPEC}"

    rm -f "${TEMP_SPEC}.bak" 2>/dev/null || true
fi

mv "${TEMP_SPEC}" "${SPEC_FILE}"

DATE_SUFFIX="$(date +%Y%m%d%H%M%S)"
CONFIG_ID="config-${DATE_SUFFIX}"

echo "[4/4] Deploying gateway config..."
gcloud api-gateway api-configs create "${CONFIG_ID}" \
  --api="${API_ID}" \
  --openapi-spec="${SPEC_FILE}" \
  --project="${PROJECT_ID}"

gcloud api-gateway gateways update "${GATEWAY_ID}" \
  --api="${API_ID}" \
  --api-config="${CONFIG_ID}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}"

# Get Gateway URL
GATEWAY_URL="https://$(gcloud api-gateway gateways describe "${GATEWAY_ID}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(defaultHostname)")"

echo "Gateway updated"
echo "Gateway URL: ${GATEWAY_URL}"
echo "Proxy: ${PROXY_URL}"
if [ ! -z "${AUTH_URL}" ]; then
    echo "Auth: ${AUTH_URL}"
fi

