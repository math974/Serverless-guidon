#!/usr/bin/env bash

set -euo pipefail

# Usage:
#   PROJECT_ID=your-project API_ID=guidon-api GATEWAY_ID=guidon-60g097ca REGION=europe-west1 \
#   ./deploy-gateway-no-key.sh

# Defaults (override via env)
: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${API_ID:=guidon-api}"
: "${GATEWAY_ID:=guidon}"
: "${SPEC:=/Users/jujumontpre/Documents/epitech/PGE5/modules/Serverless-guidon/openapi2-run.yaml}"

DATE_SUFFIX="$(date +%Y%m%d%H%M%S)"
CONFIG_ID="config-no-key-${DATE_SUFFIX}"

# Find gateway region if not specified
if [ -z "${REGION:-}" ]; then
  echo "Finding gateway region..."
  # Common GCP regions for API Gateway
  REGIONS=("europe-west1" "europe-west4" "us-central1" "us-east1" "asia-east1")
  REGION=""

  for r in "${REGIONS[@]}"; do
    if gcloud api-gateway gateways describe "${GATEWAY_ID}" \
      --location="${r}" \
      --project="${PROJECT_ID}" \
      --format="value(name)" >/dev/null 2>&1; then
      REGION="${r}"
      break
    fi
  done

  if [ -z "${REGION}" ]; then
    echo "ERROR: Gateway '${GATEWAY_ID}' not found. Listing all gateways..."
    echo ""
    echo "Available gateways:"
    for r in "${REGIONS[@]}"; do
      echo "Region ${r}:"
      gcloud api-gateway gateways list --location="${r}" --project="${PROJECT_ID}" --format="table(name,state)" 2>/dev/null || true
    done
    exit 1
  fi
fi

echo "Project:        ${PROJECT_ID}"
echo "API ID:         ${API_ID}"
echo "Gateway ID:     ${GATEWAY_ID}"
echo "Region:         ${REGION}"
echo "Spec:           ${SPEC}"
echo "New Config ID:  ${CONFIG_ID}"

echo "\n[1/2] Creating API config without API key..."
gcloud api-gateway api-configs create "${CONFIG_ID}" \
  --api="${API_ID}" \
  --openapi-spec="${SPEC}" \
  --project="${PROJECT_ID}"

echo "\n[2/2] Updating gateway to new config..."
gcloud api-gateway gateways update "${GATEWAY_ID}" \
  --api="${API_ID}" \
  --api-config="${CONFIG_ID}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}"

# Get actual gateway URL
GATEWAY_URL="https://$(gcloud api-gateway gateways describe "${GATEWAY_ID}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(defaultHostname)")"

echo "\nDone. Gateway now points to: ${GATEWAY_URL}"
echo "Test endpoints (optional):"
echo "  curl -i ${GATEWAY_URL}/health"
echo "  curl -i -X POST ${GATEWAY_URL}/discord/interactions -H 'Content-Type: application/json' -d '{"type":1}'"


