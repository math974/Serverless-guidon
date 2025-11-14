#!/usr/bin/env bash

set -euo pipefail

# Sync secrets from .env file to GCP Secret Manager
# Usage:
#   ./sync-secrets-from-env.sh

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${REGION:=europe-west1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

echo "=========================================="
echo "  Syncing Secrets from .env to GCP"
echo "=========================================="
echo "Project:        ${PROJECT_ID}"
echo "Region:         ${REGION}"
echo "Env file:       ${ENV_FILE}"
echo ""

# Check if .env file exists
if [ ! -f "${ENV_FILE}" ]; then
    echo "❌ Error: .env file not found at ${ENV_FILE}"
    echo ""
    echo "Create a .env file based on .env.example:"
    echo "  cp .env.example .env"
    echo "  # Then edit .env with your actual values"
    exit 1
fi

# Load .env file
set -a
source "${ENV_FILE}"
set +a

# Check required variables
check_var() {
    local var_name=$1
    local var_value="${!var_name:-}"
    if [ -z "${var_value}" ]; then
        echo "❌ Error: ${var_name} is not set in .env file"
        return 1
    fi
    return 0
}

echo "[1/4] Checking required variables in .env..."
if ! check_var "DISCORD_PUBLIC_KEY"; then exit 1; fi
if ! check_var "DISCORD_BOT_TOKEN"; then exit 1; fi
if ! check_var "DISCORD_APPLICATION_ID"; then exit 1; fi
echo "  ✓ All required variables found"

# Check if secret exists
check_secret() {
    local secret_name=$1
    if gcloud secrets describe "${secret_name}" --project="${PROJECT_ID}" &>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Create or update secret from environment variable
sync_secret() {
    local secret_name=$1
    local env_var=$2
    local description=$3
    local secret_value="${!env_var}"

    if check_secret "${secret_name}"; then
        echo "  Updating secret: ${secret_name}"
        echo -n "${secret_value}" | gcloud secrets versions add "${secret_name}" \
            --data-file=- \
            --project="${PROJECT_ID}" \
            >/dev/null 2>&1
        echo "    ✓ Secret ${secret_name} updated"
    else
        echo "  Creating secret: ${secret_name}"
        echo -n "${secret_value}" | gcloud secrets create "${secret_name}" \
            --data-file=- \
            --replication-policy="automatic" \
            --project="${PROJECT_ID}" \
            >/dev/null 2>&1
        echo "    ✓ Secret ${secret_name} created"
    fi
}

echo ""
echo "[2/4] Syncing secrets to GCP Secret Manager..."
sync_secret "discord-public-key" "DISCORD_PUBLIC_KEY" "Discord public key for signature verification"
sync_secret "discord-bot-token" "DISCORD_BOT_TOKEN" "Discord bot token"
sync_secret "discord-application-id" "DISCORD_APPLICATION_ID" "Discord application ID"

echo ""
echo "[3/4] Granting access to Cloud Run service account..."
SERVICE_ACCOUNT="$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')-compute@developer.gserviceaccount.com"

for secret_name in discord-public-key discord-bot-token discord-application-id; do
    gcloud secrets add-iam-policy-binding "${secret_name}" \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="roles/secretmanager.secretAccessor" \
        --project="${PROJECT_ID}" \
        >/dev/null 2>&1 || echo "    ✓ Access already granted for ${secret_name}"
done

echo ""
echo "[4/4] Updating Cloud Run services with secrets..."

# Update Proxy Service
echo "  Updating discord-proxy..."
gcloud run services update discord-proxy \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --update-secrets="DISCORD_PUBLIC_KEY=discord-public-key:latest,DISCORD_BOT_TOKEN=discord-bot-token:latest,DISCORD_APPLICATION_ID=discord-application-id:latest" \
    >/dev/null 2>&1 || echo "    ⚠ Service may not exist yet (deploy it first)"

# Update Registrar Service
echo "  Updating discord-registrar..."
gcloud run services update discord-registrar \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --update-secrets="DISCORD_BOT_TOKEN=discord-bot-token:latest,DISCORD_APPLICATION_ID=discord-application-id:latest" \
    >/dev/null 2>&1 || echo "    ⚠ Service may not exist yet (deploy it first)"

echo ""
echo "=========================================="
echo "  Secrets Sync Complete! ✓"
echo "=========================================="
echo ""
echo "Secrets synced to GCP Secret Manager:"
echo "  • discord-public-key"
echo "  • discord-bot-token"
echo "  • discord-application-id"
echo ""
echo "Note: Make sure to deploy services after syncing secrets:"
echo "  ./scripts/deploy-proxy.sh"
echo "  ./scripts/deploy-registrar.sh"

