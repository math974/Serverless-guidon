#!/usr/bin/env bash

set -euo pipefail

# Deploy the auth service to Cloud Functions
# Usage:
#   PROJECT_ID=your-project REGION=europe-west1 ./deploy-auth.sh

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${SERVICE_NAME:=discord-auth-service}"
: "${REGION:=europe-west1}"
: "${SOURCE_DIR:=services/auth-service}"

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

# Check required secrets for auth-service
MISSING_SECRETS=()
if ! check_secret "DISCORD_CLIENT_ID"; then
    MISSING_SECRETS+=("DISCORD_CLIENT_ID")
fi
if ! check_secret "DISCORD_CLIENT_SECRET"; then
    MISSING_SECRETS+=("DISCORD_CLIENT_SECRET")
fi
if ! check_secret "DISCORD_REDIRECT_URI"; then
    MISSING_SECRETS+=("DISCORD_REDIRECT_URI")
fi
if ! check_secret "WEB_FRONTEND_URL"; then
    MISSING_SECRETS+=("WEB_FRONTEND_URL")
fi

if [ ${#MISSING_SECRETS[@]} -gt 0 ]; then
    echo "Error: Missing secrets:"
    for secret in "${MISSING_SECRETS[@]}"; do
        echo "  - ${secret}"
    done
    exit 1
fi

echo "Deploying auth-service..."
gcloud functions deploy "${SERVICE_NAME}" \
  --gen2 \
  --runtime=python311 \
  --region="${REGION}" \
  --source="${PROJECT_ROOT}/${SOURCE_DIR}" \
  --entry-point=auth_handler \
  --trigger-http \
  --project="${PROJECT_ID}" \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},ENVIRONMENT=production,FIRESTORE_DATABASE=guidon-db" \
  --set-secrets="DISCORD_CLIENT_ID=DISCORD_CLIENT_ID:latest,DISCORD_CLIENT_SECRET=DISCORD_CLIENT_SECRET:latest,DISCORD_REDIRECT_URI=DISCORD_REDIRECT_URI:latest,WEB_FRONTEND_URL=WEB_FRONTEND_URL:latest" \
  --timeout=300s \
  --memory=512MB \
  2>&1 | grep -v "No change" || true

SERVICE_URL=$(gcloud functions describe "${SERVICE_NAME}" --gen2 --region="${REGION}" --project="${PROJECT_ID}" --format="value(serviceConfig.uri)")

echo "Deployed: ${SERVICE_URL}"
echo "Note: OAuth2 accessible via Gateway. Run: make update-gateway"

