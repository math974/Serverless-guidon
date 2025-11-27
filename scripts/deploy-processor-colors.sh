#!/usr/bin/env bash

set -euo pipefail

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${SERVICE_NAME:=processor-colors}"
: "${REGION:=europe-west1}"
: "${SOURCE_DIR:=services/processor-colors}"
: "${TOPIC:=commands-colors}"
: "${MIN_INSTANCES:=1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Preparing service..."
"${SCRIPT_DIR}/prepare-services.sh"

ENV_VARS="GCP_PROJECT_ID=${PROJECT_ID},ENVIRONMENT=production"

echo "Deploying ${SERVICE_NAME}..."
gcloud functions deploy "${SERVICE_NAME}" \
  --gen2 \
  --runtime=python311 \
  --region="${REGION}" \
  --source="${PROJECT_ROOT}/${SOURCE_DIR}" \
  --entry-point=processor_colors_handler \
  --trigger-topic="${TOPIC}" \
  --no-allow-unauthenticated \
  --project="${PROJECT_ID}" \
  --set-env-vars="${ENV_VARS}" \
  --set-secrets="DISCORD_BOT_TOKEN=DISCORD_BOT_TOKEN:latest" \
  --timeout=540s \
  --min-instances="${MIN_INSTANCES}" \
  --memory=256MB \
  2>&1 | grep -v "No change" || true

echo "Deployed (triggered by Pub/Sub topic: ${TOPIC})"
