#!/usr/bin/env bash

set -euo pipefail

# Update API Gateway to point to the Proxy Service
# Usage:
#   PROJECT_ID=your-project API_ID=guidon-api GATEWAY_ID=guidon REGION=europe-west1 PROXY_SERVICE=discord-proxy ./update-gateway-proxy.sh

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${API_ID:=guidon-api}"
: "${GATEWAY_ID:=guidon}"
: "${PROXY_SERVICE:=discord-proxy}"
: "${REGION:=europe-west1}"

echo "Updating API Gateway to point to Proxy Service..."
echo "Project:        ${PROJECT_ID}"
echo "API ID:         ${API_ID}"
echo "Gateway ID:     ${GATEWAY_ID}"
echo "Proxy Service:  ${PROXY_SERVICE}"
echo "Region:         ${REGION}"

# Get Proxy Service URL
echo "\n[1/3] Getting Proxy Service URL..."
PROXY_URL=$(gcloud run services describe "${PROXY_SERVICE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")

if [ -z "${PROXY_URL}" ]; then
    echo "ERROR: Could not find Proxy Service '${PROXY_SERVICE}'"
    exit 1
fi

echo "Proxy Service URL: ${PROXY_URL}"

# Update OpenAPI spec with Proxy URL
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SPEC_FILE="${PROJECT_ROOT}/configs/openapi2-run.yaml"
TEMP_SPEC="${SPEC_FILE}.tmp"

echo "\n[2/3] Updating OpenAPI spec..."
# Extract domain from URL (remove https://)
PROXY_DOMAIN=$(echo "${PROXY_URL}" | sed 's|https://||')

# Update the address in the OpenAPI spec
sed "s|address: https://[^ ]*|address: ${PROXY_URL}|g" "${SPEC_FILE}" > "${TEMP_SPEC}"
mv "${TEMP_SPEC}" "${SPEC_FILE}"

echo "Updated OpenAPI spec with Proxy URL: ${PROXY_URL}"

# Deploy new API Gateway config
DATE_SUFFIX="$(date +%Y%m%d%H%M%S)"
CONFIG_ID="config-proxy-${DATE_SUFFIX}"

echo "\n[3/3] Deploying new API Gateway config..."
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

echo "\n✓ Done! API Gateway updated successfully"
echo "\nGateway URL: ${GATEWAY_URL}"
echo "Proxy Service: ${PROXY_URL}"
echo "\nArchitecture flow:"
echo "  Discord → ${GATEWAY_URL} → ${PROXY_URL} → Pub/Sub Topics → Processor Services"
echo "\nTest endpoints:"
echo "  # Health check"
echo "  curl -i ${GATEWAY_URL}/health"
echo ""
echo "  # Discord interaction (ping)"
echo "  curl -i -X POST ${GATEWAY_URL}/discord/interactions \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -H 'X-Signature-Ed25519: test' \\"
echo "    -H 'X-Signature-Timestamp: test' \\"
echo "    -d '{\"type\":1}'"
echo ""
echo "  # Web interaction (ping)"
echo "  curl -i -X POST ${GATEWAY_URL}/web/interactions \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"command\":\"ping\"}'"

