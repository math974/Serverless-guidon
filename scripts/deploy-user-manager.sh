#!/usr/bin/env bash

set -euo pipefail

# Deploy the user-manager service to Cloud Functions
# Usage:
#   PROJECT_ID=your-project REGION=europe-west1 ./deploy-user-manager.sh

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${SERVICE_NAME:=user-manager}"
: "${REGION:=europe-west1}"
: "${SOURCE_DIR:=services/user-manager}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Preparing service..."
"${SCRIPT_DIR}/prepare-services.sh"

echo "Deploying user-manager..."
RATE_LIMITS_JSON=${RATE_LIMITS_JSON:-}

ENV_VARS="GCP_PROJECT_ID=${PROJECT_ID},ENVIRONMENT=production,FIRESTORE_DATABASE=guidon-db"
if [ ! -z "${RATE_LIMITS_JSON}" ]; then
  ENV_VARS="${ENV_VARS},RATE_LIMITS_JSON=$(python3 -c 'import json,os;print(json.dumps(json.loads(os.environ["RATE_LIMITS_JSON"])))')"
fi

gcloud functions deploy "${SERVICE_NAME}" \
  --gen2 \
  --runtime=python311 \
  --region="${REGION}" \
  --source="${PROJECT_ROOT}/${SOURCE_DIR}" \
  --entry-point=user_management_handler \
  --trigger-http \
  --allow-unauthenticated \
  --project="${PROJECT_ID}" \
  --set-env-vars="${ENV_VARS}" \
  --timeout=300s \
  --memory=512MB \
  2>&1 | grep -v "No change" || true

SERVICE_URL=$(gcloud functions describe "${SERVICE_NAME}" --gen2 --region="${REGION}" --project="${PROJECT_ID}" --format="value(serviceConfig.uri)")

echo "Deployed: ${SERVICE_URL}"

# Note: Service is public (--allow-unauthenticated) for now
# TODO: Switch to private and grant Cloud Functions service account permissions

