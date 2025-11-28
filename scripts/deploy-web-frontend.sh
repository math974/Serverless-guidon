#!/usr/bin/env bash

set -euo pipefail

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${SERVICE_NAME:=web-frontend}"
: "${SOURCE_DIR:=web-frontend}"
: "${MIN_INSTANCES:=1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Deploying App Engine service ${SERVICE_NAME}..."

cd "${PROJECT_ROOT}/${SOURCE_DIR}"

gcloud app deploy app.yaml \
  --project="${PROJECT_ID}" \
  --quiet

APP_HOST=$(gcloud app describe --project="${PROJECT_ID}" --format="value(defaultHostname)" 2>/dev/null || echo "")
if [ -z "${APP_HOST}" ]; then
  echo "Unable to get App Engine hostname. Initialize App Engine and try again."
  exit 1
fi

APP_URL="https://${APP_HOST}"
echo "Deployed at: ${APP_URL}"
echo "Set WEB_FRONTEND_URL=${APP_URL} for services that redirect to the frontend (auth-service, processors, etc.)."
