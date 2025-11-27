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

echo "Deploying all services"
echo "Project: ${PROJECT_ID}, Region: ${REGION}"

echo "[1/15] Verifying secrets..."

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

# Optional: Check OAuth2 secrets (for auth-service)
OAUTH2_SECRETS=()
if ! check_secret "DISCORD_CLIENT_ID"; then
    OAUTH2_SECRETS+=("DISCORD_CLIENT_ID")
fi
if ! check_secret "DISCORD_CLIENT_SECRET"; then
    OAUTH2_SECRETS+=("DISCORD_CLIENT_SECRET")
fi
if ! check_secret "DISCORD_REDIRECT_URI"; then
    OAUTH2_SECRETS+=("DISCORD_REDIRECT_URI")
fi
if ! check_secret "WEB_FRONTEND_URL"; then
    OAUTH2_SECRETS+=("WEB_FRONTEND_URL")
fi

if [ ${#MISSING_SECRETS[@]} -gt 0 ]; then
    echo "Error: Missing required secrets:"
    for secret in "${MISSING_SECRETS[@]}"; do
        echo "  - ${secret}"
    done
    exit 1
fi

if [ ${#OAUTH2_SECRETS[@]} -gt 0 ]; then
    echo "Warning: Missing OAuth2 secrets (auth-service will be skipped)"
fi

echo "Secrets verified"

echo "[2/15] Creating Pub/Sub topics..."
"${SCRIPT_DIR}/setup-pubsub.sh"

echo "[3/15] Deploying user-manager..."
"${SCRIPT_DIR}/deploy-user-manager.sh"
USER_MANAGER_URL=$(gcloud functions describe user-manager --gen2 --region="${REGION}" --project="${PROJECT_ID}" --format="value(serviceConfig.uri)")

echo "[4/15] Deploying canvas-service..."
"${SCRIPT_DIR}/deploy-canvas-service.sh"
CANVAS_SERVICE_URL=$(gcloud functions describe canvas-service --gen2 --region="${REGION}" --project="${PROJECT_ID}" --format="value(serviceConfig.uri)")

echo "[5/15] Deploying proxy..."
"${SCRIPT_DIR}/deploy-proxy.sh"
PROXY_URL=$(gcloud functions describe proxy --gen2 --region="${REGION}" --project="${PROJECT_ID}" --format="value(serviceConfig.uri)")

echo "[6/15] Deploying web-frontend..."
"${SCRIPT_DIR}/deploy-web-frontend.sh"
WEB_FRONTEND_URL=$(gcloud functions describe web-frontend --gen2 --region="${REGION}" --project="${PROJECT_ID}" --format="value(serviceConfig.uri)")

echo "[7/15] Deploying auth-service..."
if [ ${#OAUTH2_SECRETS[@]} -eq 0 ]; then
    "${SCRIPT_DIR}/deploy-auth.sh"
    AUTH_URL=$(gcloud functions describe discord-auth-service --gen2 --region="${REGION}" --project="${PROJECT_ID}" --format="value(serviceConfig.uri)" 2>/dev/null || echo "")
else
    echo "Skipped (missing OAuth2 secrets)"
    AUTH_URL=""
fi

echo "[8/15] Deploying registrar..."
"${SCRIPT_DIR}/deploy-registrar.sh"
REGISTRAR_URL=$(gcloud functions describe discord-utils --gen2 --region="${REGION}" --project="${PROJECT_ID}" --format="value(serviceConfig.uri)")

echo "[9/15] Deploying processor-base..."
"${SCRIPT_DIR}/deploy-processor-base.sh"

echo "[10/15] Deploying processor-draw..."
"${SCRIPT_DIR}/deploy-processor-draw.sh"

echo "[11/15] Deploying processor-snapshot..."
"${SCRIPT_DIR}/deploy-processor-snapshot.sh"

echo "[12/15] Deploying processor-canvas-state..."
"${SCRIPT_DIR}/deploy-processor-canvas-state.sh"

echo "[13/15] Deploying processor-stats..."
"${SCRIPT_DIR}/deploy-processor-stats.sh"

echo "[14/15] Deploying processor-colors..."
"${SCRIPT_DIR}/deploy-processor-colors.sh"

echo "[15/15] Deploying processor-pixel-info..."
"${SCRIPT_DIR}/deploy-processor-pixel-info.sh"

GATEWAY_URL="https://$(gcloud api-gateway gateways describe "${GATEWAY_ID}" --location="${REGION}" --project="${PROJECT_ID}" --format="value(defaultHostname)" 2>/dev/null || echo "")"

echo ""
echo "Deployment complete"
echo ""
echo "Services:"
echo "  user-manager: ${USER_MANAGER_URL}"
echo "  canvas-service: ${CANVAS_SERVICE_URL}"
echo "  proxy: ${PROXY_URL}"
echo "  web-frontend: ${WEB_FRONTEND_URL}"
if [ ! -z "$AUTH_URL" ]; then
    echo "  auth-service: ${AUTH_URL}"
fi
echo "  registrar: ${REGISTRAR_URL}"
echo "  processor-base: deployed"
echo "  processor-draw: deployed"
echo "  processor-snapshot: deployed"
echo "  processor-canvas-state: deployed"
echo "  processor-stats: deployed"
echo "  processor-colors: deployed"
echo "  processor-pixel-info: deployed"
if [ ! -z "$GATEWAY_URL" ]; then
    echo "  gateway: ${GATEWAY_URL}"
fi
echo ""
echo "Next steps:"
echo "  1. Update gateway: make update-gateway"
echo "  2. Register commands: curl -X POST ${REGISTRAR_URL}/register"
if [ ! -z "$GATEWAY_URL" ]; then
    echo "  3. Discord webhook: ${GATEWAY_URL}/discord/interactions"
    echo "  4. Web frontend: ${GATEWAY_URL}"
fi
