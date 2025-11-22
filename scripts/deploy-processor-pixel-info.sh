#!/usr/bin/env bash

set -euo pipefail

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${SERVICE_NAME:=processor-pixel-info}"
: "${REGION:=europe-west1}"
: "${SOURCE_DIR:=services/processor-pixel-info}"
: "${TOPIC:=commands-pixel-info}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Preparing service..."
"${SCRIPT_DIR}/prepare-services.sh"

CANVAS_SERVICE_URL=${CANVAS_SERVICE_URL:-$(gcloud functions describe canvas-service --gen2 --region="${REGION}" --project="${PROJECT_ID}" --format="value(serviceConfig.uri)" 2>/dev/null || echo "")}

ENV_VARS="GCP_PROJECT_ID=${PROJECT_ID},ENVIRONMENT=production"
if [ ! -z "${CANVAS_SERVICE_URL}" ]; then
  ENV_VARS="${ENV_VARS},CANVAS_SERVICE_URL=${CANVAS_SERVICE_URL}"
fi

echo "Deploying ${SERVICE_NAME}..."
gcloud functions deploy "${SERVICE_NAME}" \
  --gen2 \
  --runtime=python311 \
  --region="${REGION}" \
  --source="${PROJECT_ROOT}/${SOURCE_DIR}" \
  --entry-point=processor_pixel_info_handler \
  --trigger-topic="${TOPIC}" \
  --no-allow-unauthenticated \
  --project="${PROJECT_ID}" \
  --set-env-vars="${ENV_VARS}" \
  --set-secrets="DISCORD_BOT_TOKEN=DISCORD_BOT_TOKEN:latest" \
  --timeout=540s \
  --memory=256MB \
  2>&1 | grep -v "No change" || true

echo "Deployed (triggered by Pub/Sub topic: ${TOPIC})"

# Grant permissions to invoke canvas-service
if [ ! -z "${CANVAS_SERVICE_URL:-}" ]; then
  echo "Granting permission to invoke canvas-service..."
  "${SCRIPT_DIR}/grant-service-invoker.sh" "${SERVICE_NAME}" "canvas-service" "${PROJECT_ID}" "${REGION}" || true
fi

