#!/usr/bin/env bash

set -euo pipefail

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${SERVICE_NAME:=processor-snapshot}"
: "${REGION:=europe-west1}"
: "${SOURCE_DIR:=services/processor-snapshot}"
: "${TOPIC:=commands-snapshot}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Preparing service..."
"${SCRIPT_DIR}/prepare-services.sh"

USER_MANAGER_URL=${USER_MANAGER_URL:-$(gcloud functions describe user-manager --gen2 --region="${REGION}" --project="${PROJECT_ID}" --format="value(serviceConfig.uri)" 2>/dev/null || echo "")}
CANVAS_SERVICE_URL=${CANVAS_SERVICE_URL:-$(gcloud functions describe canvas-service --gen2 --region="${REGION}" --project="${PROJECT_ID}" --format="value(serviceConfig.uri)" 2>/dev/null || echo "")}

ENV_VARS="GCP_PROJECT_ID=${PROJECT_ID},ENVIRONMENT=production"
if [ ! -z "${USER_MANAGER_URL}" ]; then
  ENV_VARS="${ENV_VARS},USER_MANAGER_URL=${USER_MANAGER_URL}"
fi
if [ ! -z "${CANVAS_SERVICE_URL}" ]; then
  ENV_VARS="${ENV_VARS},CANVAS_SERVICE_URL=${CANVAS_SERVICE_URL}"
fi

echo "Deploying ${SERVICE_NAME}..."
gcloud functions deploy "${SERVICE_NAME}" \
  --gen2 \
  --runtime=python311 \
  --region="${REGION}" \
  --source="${PROJECT_ROOT}/${SOURCE_DIR}" \
  --entry-point=processor_snapshot_handler \
  --trigger-topic="${TOPIC}" \
  --allow-unauthenticated \
  --project="${PROJECT_ID}" \
  --set-env-vars="${ENV_VARS}" \
  --set-secrets="DISCORD_BOT_TOKEN=DISCORD_BOT_TOKEN:latest" \
  --timeout=540s \
  --memory=512MB \
  2>&1 | grep -v "No change" || true

echo "Deployed (triggered by Pub/Sub topic: ${TOPIC})"

# Note: Service is public (--allow-unauthenticated) for now
# TODO: Switch to private and grant Eventarc permissions

