#!/usr/bin/env bash

set -euo pipefail

# Deploy the web frontend Cloud Function (HTML landing page)

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${SERVICE_NAME:=web-frontend}"
: "${REGION:=europe-west1}"
: "${SOURCE_DIR:=services/web-frontend}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Preparing service..."
"${SCRIPT_DIR}/prepare-services.sh"

echo "Deploying ${SERVICE_NAME}..."

gcloud functions deploy "${SERVICE_NAME}" \
  --gen2 \
  --runtime=python311 \
  --region="${REGION}" \
  --source="${PROJECT_ROOT}/${SOURCE_DIR}" \
  --entry-point=web_app \
  --trigger-http \
  --allow-unauthenticated \
  --project="${PROJECT_ID}" \
  --timeout=120s \
  --memory=256MB \
  2>&1 | grep -v "No change" || true

SERVICE_URL=$(gcloud functions describe "${SERVICE_NAME}" --gen2 --region="${REGION}" --project="${PROJECT_ID}" --format="value(serviceConfig.uri)")

echo "Deployed: ${SERVICE_URL}"
echo "Set WEB_FRONTEND_URL=${SERVICE_URL} in auth-service secrets/env vars to use it as redirect."
