#!/usr/bin/env bash

set -euo pipefail

# Deploy the Discord command registrar service to Cloud Run
# Usage:
#   PROJECT_ID=your-project REGION=europe-west1 ./deploy-registrar.sh

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${SERVICE_NAME:=discord-registrar}"
: "${REGION:=europe-west1}"
: "${SOURCE_DIR:=services/discord-registrar}"

echo "Project:        ${PROJECT_ID}"
echo "Service Name:   ${SERVICE_NAME}"
echo "Region:         ${REGION}"
echo "Source Dir:     ${SOURCE_DIR}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Check if secrets exist
check_secret() {
    local secret_name=$1
    if gcloud secrets describe "${secret_name}" --project="${PROJECT_ID}" &>/dev/null; then
        return 0
    else
        return 1
    fi
}

echo "\n[0/2] Checking required secrets in GCP Secret Manager..."
MISSING_SECRETS=()
if ! check_secret "DISCORD_BOT_TOKEN"; then
    MISSING_SECRETS+=("DISCORD_BOT_TOKEN")
fi
if ! check_secret "DISCORD_APPLICATION_ID"; then
    MISSING_SECRETS+=("DISCORD_APPLICATION_ID")
fi

if [ ${#MISSING_SECRETS[@]} -gt 0 ]; then
    echo "  ❌ Error: Missing secrets in GCP Secret Manager:"
    for secret in "${MISSING_SECRETS[@]}"; do
        echo "    • ${secret}"
    done
    echo ""
    echo "  Create these secrets in GCP Secret Manager:"
    echo "    gcloud secrets create <secret-name> --data-file=- --project=${PROJECT_ID}"
    echo ""
    echo "  Or use the GCP Console: https://console.cloud.google.com/security/secret-manager"
    exit 1
fi

echo "  ✓ All required secrets found"
echo "\n[1/2] Deploying registrar service to Cloud Run..."
# OpenTelemetry: Configure GCP_PROJECT_ID for Cloud Trace and ENVIRONMENT for observability
gcloud run deploy "${SERVICE_NAME}" \
  --source="${PROJECT_ROOT}/${SOURCE_DIR}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --allow-unauthenticated \
  --platform=managed \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},ENVIRONMENT=production" \  # OpenTelemetry: GCP_PROJECT_ID for Cloud Trace, ENVIRONMENT for observability config
  --update-secrets="DISCORD_BOT_TOKEN=DISCORD_BOT_TOKEN:latest,DISCORD_APPLICATION_ID=DISCORD_APPLICATION_ID:latest" \
  2>&1 | grep -v "No change" || true

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")

echo "\n[2/2] Service deployed successfully!"
echo "\nDone. Registrar service URL: ${SERVICE_URL}"
echo ""
echo "To register commands, call:"
echo "  curl -X POST ${SERVICE_URL}/register"
echo ""
echo "Or use Cloud Scheduler to register commands automatically."
echo ""
echo "Note: Secrets are loaded from GCP Secret Manager:"
echo "  • DISCORD_BOT_TOKEN:latest"
echo "  • DISCORD_APPLICATION_ID:latest"

