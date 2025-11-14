#!/usr/bin/env bash

set -euo pipefail

# Deploy the processor-base service to Cloud Run
# Usage:
#   PROJECT_ID=your-project REGION=europe-west1 ./deploy-processor-base.sh

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${SERVICE_NAME:=discord-processor-base}"
: "${REGION:=europe-west1}"
: "${SOURCE_DIR:=services/processor-base}"

echo "Project:        ${PROJECT_ID}"
echo "Service Name:   ${SERVICE_NAME}"
echo "Region:         ${REGION}"
echo "Source Dir:     ${SOURCE_DIR}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "\n[1/2] Deploying processor-base service to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --source="${PROJECT_ROOT}/${SOURCE_DIR}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --allow-unauthenticated \
  --platform=managed

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")

echo "\n[2/2] Deployment complete!"
echo "\nDone. Processor-base service URL: ${SERVICE_URL}"
echo "Create a Pub/Sub push subscription pointing to: ${SERVICE_URL}/"

