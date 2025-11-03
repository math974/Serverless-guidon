#!/usr/bin/env bash

set -euo pipefail

# Usage:
#   PROJECT_ID=your-project SERVICE_NAME=sunbot REGION=europe-west1 \
#   ./deploy-cloud-run.sh

# Defaults (override via env)
: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${SERVICE_NAME:=sunbot}"
: "${REGION:=europe-west1}"
: "${SOURCE_DIR:=./picasso-bot}"

echo "Project:        ${PROJECT_ID}"
echo "Service Name:   ${SERVICE_NAME}"
echo "Region:         ${REGION}"
echo "Source Dir:     ${SOURCE_DIR}"

echo "\n[1/1] Deploying Cloud Run service..."
gcloud run deploy "${SERVICE_NAME}" \
  --source="${SOURCE_DIR}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --allow-unauthenticated \
  --platform=managed

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")

echo "\nDone. Service URL: ${SERVICE_URL}"
echo "Test endpoints (optional):"
echo "  curl -i ${SERVICE_URL}/health"
echo "  curl -i -X POST ${SERVICE_URL}/discord/interactions -H 'Content-Type: application/json' -d '{\"type\":1}'"

