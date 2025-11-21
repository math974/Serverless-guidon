#!/usr/bin/env bash

set -euo pipefail

# Deploy the canvas-service to Cloud Run
# Usage:
#   PROJECT_ID=your-project REGION=europe-west1 ./deploy-canvas-service.sh

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${SERVICE_NAME:=canvas-service}"
: "${REGION:=europe-west1}"
: "${SOURCE_DIR:=services/canvas-service}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Preparing service..."
"${SCRIPT_DIR}/prepare-services.sh"

ENV_VARS="GCP_PROJECT_ID=${PROJECT_ID},ENVIRONMENT=production,FIRESTORE_DATABASE=guidon-db"
if [ ! -z "${GCS_CANVAS_BUCKET:-}" ]; then
  ENV_VARS="${ENV_VARS},GCS_CANVAS_BUCKET=${GCS_CANVAS_BUCKET}"
fi

echo "Deploying canvas-service..."
gcloud functions deploy "${SERVICE_NAME}" \
  --gen2 \
  --runtime=python311 \
  --region="${REGION}" \
  --source="${PROJECT_ROOT}/${SOURCE_DIR}" \
  --entry-point=canvas_service \
  --trigger-http \
  --allow-unauthenticated \
  --project="${PROJECT_ID}" \
  --set-env-vars="${ENV_VARS}" \
  --timeout=540s \
  --memory=512MB \
  2>&1 | grep -v "No change" || true

SERVICE_URL=$(gcloud functions describe "${SERVICE_NAME}" --gen2 --region="${REGION}" --project="${PROJECT_ID}" --format="value(serviceConfig.uri)")

echo "Deployed: ${SERVICE_URL}"

# Note: Service is public (--allow-unauthenticated) for now
# TODO: Switch to private and grant Cloud Functions service account permissions

echo ""
echo "Available endpoints:"
echo "  GET  ${SERVICE_URL}/health"
echo "  POST ${SERVICE_URL}/canvas/draw"
echo "  GET  ${SERVICE_URL}/canvas/state"
echo "  POST ${SERVICE_URL}/canvas/snapshot"
echo "  GET  ${SERVICE_URL}/canvas/stats"
echo "  GET  ${SERVICE_URL}/canvas/pixel/{x}/{y}"

