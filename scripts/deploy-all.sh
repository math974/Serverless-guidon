#!/usr/bin/env bash

set -euo pipefail

# Deploy all services to GCP
# Usage:
#   PROJECT_ID=your-project REGION=europe-west1 API_ID=guidon-api GATEWAY_ID=guidon ./deploy-all.sh

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${REGION:=europe-west1}"
: "${API_ID:=guidon-api}"
: "${GATEWAY_ID:=guidon}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=========================================="
echo "  Discord Bot - Full Deployment"
echo "=========================================="
echo "Project:        ${PROJECT_ID}"
echo "Region:         ${REGION}"
echo "API ID:         ${API_ID}"
echo "Gateway ID:     ${GATEWAY_ID}"
echo ""

# Step 0: Verify secrets exist in GCP Secret Manager
echo "=========================================="
echo "[0/7] Verifying secrets in GCP Secret Manager..."
echo "=========================================="

check_secret() {
    local secret_name=$1
    if gcloud secrets describe "${secret_name}" --project="${PROJECT_ID}" &>/dev/null; then
        return 0
    else
        return 1
    fi
}

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
    echo "  ❌ Missing secrets in GCP Secret Manager:"
    for secret in "${MISSING_SECRETS[@]}"; do
        echo "    • ${secret}"
    done
    echo ""
    echo "  Create these secrets in GCP Secret Manager:"
    echo "    gcloud secrets create DISCORD_PUBLIC_KEY --data-file=- --project=${PROJECT_ID}"
    echo "    gcloud secrets create DISCORD_BOT_TOKEN --data-file=- --project=${PROJECT_ID}"
    echo "    gcloud secrets create DISCORD_APPLICATION_ID --data-file=- --project=${PROJECT_ID}"
    exit 1
fi

echo "  ✓ All required secrets found in GCP Secret Manager"

# Step 1: Create Pub/Sub topics
echo ""
echo "=========================================="
echo "[1/7] Creating Pub/Sub topics..."
echo "=========================================="
./setup-pubsub.sh

# Step 2: Deploy Proxy Service
echo ""
echo "=========================================="
echo "[2/7] Deploying Proxy Service..."
echo "=========================================="
./deploy-proxy.sh
PROXY_URL=$(gcloud run services describe discord-proxy \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")
echo "✓ Proxy Service deployed: ${PROXY_URL}"

# Step 3: Deploy Processor-Base Service
echo ""
echo "=========================================="
echo "[3/7] Deploying Processor-Base Service..."
echo "=========================================="
./deploy-processor-base.sh
PROCESSOR_BASE_URL=$(gcloud run services describe discord-processor-base \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")
echo "✓ Processor-Base deployed: ${PROCESSOR_BASE_URL}"

# Step 4: Deploy Processor-Art Service
echo ""
echo "=========================================="
echo "[4/7] Deploying Processor-Art Service..."
echo "=========================================="
./deploy-processor-art.sh
PROCESSOR_ART_URL=$(gcloud run services describe discord-processor-art \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")
echo "✓ Processor-Art deployed: ${PROCESSOR_ART_URL}"

# Step 5: Deploy Registrar Service
echo ""
echo "=========================================="
echo "[5/7] Deploying Registrar Service..."
echo "=========================================="
./deploy-registrar.sh
REGISTRAR_URL=$(gcloud run services describe discord-registrar \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")
echo "✓ Registrar Service deployed: ${REGISTRAR_URL}"

# Step 6: Create Pub/Sub subscriptions
echo ""
echo "=========================================="
echo "[6/7] Creating Pub/Sub subscriptions..."
echo "=========================================="

# Base commands subscription
echo "Creating subscription: discord-commands-base-sub"
gcloud pubsub subscriptions create discord-commands-base-sub \
  --topic=discord-commands-base \
  --push-endpoint="${PROCESSOR_BASE_URL}/" \
  --project="${PROJECT_ID}" \
  2>&1 | grep -v "already exists" || echo "  ✓ Subscription already exists"
echo "  → ${PROCESSOR_BASE_URL}/"

# Art commands subscription
echo "Creating subscription: discord-commands-art-sub"
gcloud pubsub subscriptions create discord-commands-art-sub \
  --topic=discord-commands-art \
  --push-endpoint="${PROCESSOR_ART_URL}/" \
  --project="${PROJECT_ID}" \
  2>&1 | grep -v "already exists" || echo "  ✓ Subscription already exists"
echo "  → ${PROCESSOR_ART_URL}/"
echo "✓ Subscriptions created"

# Step 7: Update API Gateway
echo ""
echo "=========================================="
echo "[7/7] Updating API Gateway..."
echo "=========================================="
./update-gateway-proxy.sh
GATEWAY_URL="https://$(gcloud api-gateway gateways describe "${GATEWAY_ID}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(defaultHostname)")"
echo "✓ API Gateway updated"

# Summary
echo ""
echo "=========================================="
echo "  Deployment Complete! 🎉"
echo "=========================================="
echo ""
echo "Services deployed:"
echo "  • Proxy Service:        ${PROXY_URL}"
echo "  • Processor-Base:       ${PROCESSOR_BASE_URL}"
echo "  • Processor-Art:         ${PROCESSOR_ART_URL}"
echo "  • Registrar Service:    ${REGISTRAR_URL}"
echo "  • API Gateway:          ${GATEWAY_URL}"
echo ""
echo "Pub/Sub Topics:"
echo "  • discord-interactions"
echo "  • discord-commands-base"
echo "  • discord-commands-art"
echo ""
echo "Pub/Sub Subscriptions:"
echo "  • discord-commands-base-sub → ${PROCESSOR_BASE_URL}/"
echo "  • discord-commands-art-sub → ${PROCESSOR_ART_URL}/"
echo ""
echo "Next steps:"
echo "  1. Register Discord commands:"
echo "     curl -X POST ${REGISTRAR_URL}/register"
echo ""
echo "  2. Configure Discord webhook URL:"
echo "     ${GATEWAY_URL}/discord/interactions"
echo ""
echo "Test endpoints:"
echo "  curl -i ${GATEWAY_URL}/health"
echo "  curl -i ${PROXY_URL}/health"
echo "  curl -i ${PROCESSOR_BASE_URL}/health"
echo "  curl -i ${PROCESSOR_ART_URL}/health"
echo "  curl -i ${REGISTRAR_URL}/health"
echo ""
