#!/usr/bin/env bash

set -euo pipefail

# Deploy the processor-base service to Cloud Functions
# Usage:
#   PROJECT_ID=your-project REGION=europe-west1 ./deploy-processor-base.sh

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${SERVICE_NAME:=processor-base}"
: "${REGION:=europe-west1}"
: "${SOURCE_DIR:=services/processor-base}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Preparing service..."
"${SCRIPT_DIR}/prepare-services.sh"

# Get user-manager URL if available
USER_MANAGER_URL=$(gcloud functions describe user-manager --gen2 --region="${REGION}" --project="${PROJECT_ID}" --format="value(serviceConfig.uri)" 2>/dev/null || echo "")

ENV_VARS="GCP_PROJECT_ID=${PROJECT_ID},ENVIRONMENT=production"
if [ ! -z "${USER_MANAGER_URL}" ]; then
    ENV_VARS="${ENV_VARS},USER_MANAGER_URL=${USER_MANAGER_URL}"
fi

echo "Deploying processor-base..."
gcloud functions deploy "${SERVICE_NAME}" \
  --gen2 \
  --runtime=python311 \
  --region="${REGION}" \
  --source="${PROJECT_ROOT}/${SOURCE_DIR}" \
  --entry-point=processor_base_handler \
  --trigger-topic=commands-base \
  --no-allow-unauthenticated \
  --project="${PROJECT_ID}" \
  --set-env-vars="${ENV_VARS}" \
  --timeout=540s \
  --memory=512MB \
  2>&1 | grep -v "No change" || true

echo "Deployed (triggered by Pub/Sub topic: commands-base)"

# Grant permissions to invoke user-manager
if [ ! -z "${USER_MANAGER_URL:-}" ]; then
  echo "Granting permission to invoke user-manager..."
  "${SCRIPT_DIR}/grant-service-invoker.sh" "${SERVICE_NAME}" "user-manager" "${PROJECT_ID}" "${REGION}" || true
fi
