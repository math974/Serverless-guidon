#!/usr/bin/env bash

set -euo pipefail

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${SERVICE_NAME:=web-frontend}"
: "${SOURCE_DIR:=services/web-frontend}"
: "${MIN_INSTANCES:=1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Déploiement App Engine pour ${SERVICE_NAME}..."

cd "${PROJECT_ROOT}/${SOURCE_DIR}"

gcloud app deploy app.yaml \
  --project="${PROJECT_ID}" \
  --quiet

APP_URL="https://${PROJECT_ID}.ew.r.appspot.com"
echo "Déployé sur : ${APP_URL}"
echo "Set WEB_FRONTEND_URL=${APP_URL} dans les variables d'environnement pour l'utiliser comme redirect."