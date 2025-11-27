#!/usr/bin/env bash

set -euo pipefail

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${SERVICE_NAME:=web-frontend}"
: "${SOURCE_DIR:=services/web-frontend}"
: "${MIN_INSTANCES:=1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

<<<<<<< HEAD
echo "Déploiement App Engine pour ${SERVICE_NAME}..."
=======
echo "Preparing service..."
"${SCRIPT_DIR}/prepare-services.sh"

echo "Deploying ${SERVICE_NAME}..."
>>>>>>> origin/main

cd "${PROJECT_ROOT}/${SOURCE_DIR}"

gcloud app deploy app.yaml \
  --project="${PROJECT_ID}" \
<<<<<<< HEAD
  --quiet
=======
  --timeout=120s \
  --min-instances="${MIN_INSTANCES}" \
  --memory=256MB \
  2>&1 | grep -v "No change" || true
>>>>>>> origin/main

APP_URL="https://${PROJECT_ID}.ew.r.appspot.com"
echo "Déployé sur : ${APP_URL}"
echo "Set WEB_FRONTEND_URL=${APP_URL} dans les variables d'environnement pour l'utiliser comme redirect."