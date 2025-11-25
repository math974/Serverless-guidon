#!/usr/bin/env bash

# Helper function to grant invoker permissions between services
# Usage: grant_service_invoker CALLING_SERVICE RECEIVING_SERVICE PROJECT_ID REGION

set -euo pipefail

CALLING_SERVICE=$1
RECEIVING_SERVICE=$2
PROJECT_ID=${3:-serverless-ejguidon-dev}
REGION=${4:-europe-west1}

echo "Granting ${CALLING_SERVICE} permission to invoke ${RECEIVING_SERVICE}..."

# Get the service account of the calling service
CALLING_SERVICE_ACCOUNT=$(gcloud functions describe "${CALLING_SERVICE}" \
  --gen2 \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(serviceConfig.serviceAccountEmail)" 2>/dev/null || echo "")

if [ -z "${CALLING_SERVICE_ACCOUNT}" ]; then
  echo "Warning: Could not get service account for ${CALLING_SERVICE}, skipping permission grant"
  exit 0
fi

# Grant invoker permission using gcloud functions add-invoker-policy-binding
gcloud functions add-invoker-policy-binding "${RECEIVING_SERVICE}" \
  --gen2 \
  --region="${REGION}" \
  --member="serviceAccount:${CALLING_SERVICE_ACCOUNT}" \
  --project="${PROJECT_ID}" \
  2>&1 | grep -v "already has role" || echo "  ✓ ${CALLING_SERVICE} already has permission to invoke ${RECEIVING_SERVICE}"

echo "  ✓ Granted ${CALLING_SERVICE} permission to invoke ${RECEIVING_SERVICE}"

