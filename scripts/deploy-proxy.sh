#!/usr/bin/env bash

set -euo pipefail

# Deploy the proxy service to Cloud Functions
# Usage:
#   PROJECT_ID=your-project REGION=europe-west1 ./deploy-proxy.sh

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${SERVICE_NAME:=proxy}"
: "${REGION:=europe-west1}"
: "${SOURCE_DIR:=services/proxy}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Preparing service..."
"${SCRIPT_DIR}/prepare-services.sh"

echo "Verifying secrets..."

# Check if secrets exist
check_secret() {
    local secret_name=$1
    if gcloud secrets describe "${secret_name}" --project="${PROJECT_ID}" &>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Check required secrets
MISSING_SECRETS=()
if ! check_secret "DISCORD_PUBLIC_KEY"; then
    MISSING_SECRETS+=("DISCORD_PUBLIC_KEY")
fi
if ! check_secret "DISCORD_BOT_TOKEN"; then
    MISSING_SECRETS+=("DISCORD_BOT_TOKEN")
fi
if ! check_secret "DISCORD_APPLICATION_ID"; then
    MISSING_SECRETS+=("DISCORD_APPLICATION_ID")
fi

if [ ${#MISSING_SECRETS[@]} -gt 0 ]; then
    echo "Error: Missing secrets:"
    for secret in "${MISSING_SECRETS[@]}"; do
        echo "  - ${secret}"
    done
    exit 1
fi

# Fetch user-manager URL if not provided
if [ -z "${USER_MANAGER_URL:-}" ]; then
    USER_MANAGER_URL=$(gcloud functions describe user-manager --gen2 --region="${REGION}" --project="${PROJECT_ID}" --format="value(serviceConfig.uri)" 2>/dev/null || echo "")
fi

ENV_VARS="GCP_PROJECT_ID=${PROJECT_ID},ENVIRONMENT=production"
if [ ! -z "${USER_MANAGER_URL}" ]; then
    ENV_VARS="${ENV_VARS},USER_MANAGER_URL=${USER_MANAGER_URL}"
fi

echo "Deploying proxy..."
gcloud functions deploy "${SERVICE_NAME}" \
  --gen2 \
  --runtime=python311 \
  --region="${REGION}" \
  --source="${PROJECT_ROOT}/${SOURCE_DIR}" \
  --entry-point=proxy_handler \
  --trigger-http \
  --no-allow-unauthenticated \
  --project="${PROJECT_ID}" \
  --set-env-vars="${ENV_VARS}" \
  --set-secrets="DISCORD_PUBLIC_KEY=DISCORD_PUBLIC_KEY:latest,DISCORD_BOT_TOKEN=DISCORD_BOT_TOKEN:latest,DISCORD_APPLICATION_ID=DISCORD_APPLICATION_ID:latest" \
  --timeout=300s \
  --memory=512MB \
  2>&1 | grep -v "No change" || true

SERVICE_URL=$(gcloud functions describe "${SERVICE_NAME}" --gen2 --region="${REGION}" --project="${PROJECT_ID}" --format="value(serviceConfig.uri)")

echo "Deployed: ${SERVICE_URL}"

# Grant permissions to invoke user-manager
if [ ! -z "${USER_MANAGER_URL:-}" ]; then
  echo "Granting permission to invoke user-manager..."
  "${SCRIPT_DIR}/grant-service-invoker.sh" "${SERVICE_NAME}" "user-manager" "${PROJECT_ID}" "${REGION}" || true
fi

# Grant API Gateway permission to invoke proxy
echo "Granting API Gateway permission to invoke proxy..."
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)" 2>/dev/null || echo "")
if [ ! -z "${PROJECT_NUMBER}" ]; then
  # API Gateway uses the Cloud Services service account by default
  GATEWAY_SA="${PROJECT_NUMBER}@cloudservices.gserviceaccount.com"
  echo "  Using service account: ${GATEWAY_SA}"
  gcloud functions add-invoker-policy-binding "${SERVICE_NAME}" \
    --gen2 \
    --region="${REGION}" \
    --member="serviceAccount:${GATEWAY_SA}" \
    --project="${PROJECT_ID}" \
    2>&1 | grep -v "already has role" || echo "  ✓ API Gateway already has permission"
  echo "  ✓ Granted API Gateway permission to invoke proxy"
  echo ""
  echo "Note: If you use a custom service account for API Gateway, update this script"
  echo "      to use that service account instead."
fi

