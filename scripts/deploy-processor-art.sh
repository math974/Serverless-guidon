#!/usr/bin/env bash

set -euo pipefail

# Deploy the processor-art service to Cloud Run
# Usage:
#   PROJECT_ID=your-project REGION=europe-west1 ./deploy-processor-art.sh

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${SERVICE_NAME:=discord-processor-art}"
: "${REGION:=europe-west1}"
: "${SOURCE_DIR:=services/processor-art}"

echo "Project:        ${PROJECT_ID}"
echo "Service Name:   ${SERVICE_NAME}"
echo "Region:         ${REGION}"
echo "Source Dir:     ${SOURCE_DIR}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "\n[0/2] Preparing service (copying shared modules)..."
"${SCRIPT_DIR}/prepare-services.sh"

echo "\n[1/2] Deploying processor-art service to Cloud Run..."
# OpenTelemetry: Configure GCP_PROJECT_ID for Cloud Trace and ENVIRONMENT for observability
gcloud run deploy "${SERVICE_NAME}" \
  --source="${PROJECT_ROOT}/${SOURCE_DIR}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --allow-unauthenticated \
  --platform=managed \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},ENVIRONMENT=production"  # OpenTelemetry: GCP_PROJECT_ID for Cloud Trace, ENVIRONMENT for observability config

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")

echo "\n[2/2] Deployment complete!"
echo "\nDone. Processor-art service URL: ${SERVICE_URL}"
echo "Create a Pub/Sub push subscription pointing to: ${SERVICE_URL}/"

