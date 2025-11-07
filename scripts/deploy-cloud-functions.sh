#!/usr/bin/env bash

set -euo pipefail

# Usage:
#   PROJECT_ID=your-project REGION=europe-west1 \
#   ./deploy-cloud-functions.sh

# Defaults (override via env)
: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${REGION:=europe-west1}"
: "${SOURCE_DIR:=./picasso-bot}"

echo "Project:        ${PROJECT_ID}"
echo "Region:         ${REGION}"
echo "Source Dir:     ${SOURCE_DIR}"

# Function for Discord interactions
FUNCTION_NAME_DISCORD="discord-interactions"
ENTRY_POINT_DISCORD="discord_interactions"

# Function for health check
FUNCTION_NAME_HEALTH="discord-health"
ENTRY_POINT_HEALTH="health_check"

# Function for command registration
FUNCTION_NAME_REGISTER="discord-register-commands"
ENTRY_POINT_REGISTER="register_commands"

echo "\n[1/3] Deploying Discord interactions function..."
gcloud functions deploy "${FUNCTION_NAME_DISCORD}" \
  --gen2 \
  --runtime=python311 \
  --region="${REGION}" \
  --source="${SOURCE_DIR}" \
  --entry-point="${ENTRY_POINT_DISCORD}" \
  --trigger-http \
  --allow-unauthenticated \
  --project="${PROJECT_ID}" \
  --memory=256MB \
  --timeout=60s

echo "\n[2/3] Deploying health check function..."
gcloud functions deploy "${FUNCTION_NAME_HEALTH}" \
  --gen2 \
  --runtime=python311 \
  --region="${REGION}" \
  --source="${SOURCE_DIR}" \
  --entry-point="${ENTRY_POINT_HEALTH}" \
  --trigger-http \
  --allow-unauthenticated \
  --project="${PROJECT_ID}" \
  --memory=256MB \
  --timeout=30s

echo "\n[3/3] Deploying register commands function..."
gcloud functions deploy "${FUNCTION_NAME_REGISTER}" \
  --gen2 \
  --runtime=python311 \
  --region="${REGION}" \
  --source="${SOURCE_DIR}" \
  --entry-point="${ENTRY_POINT_REGISTER}" \
  --trigger-http \
  --allow-unauthenticated \
  --project="${PROJECT_ID}" \
  --memory=256MB \
  --timeout=60s

# Get function URLs
DISCORD_URL=$(gcloud functions describe "${FUNCTION_NAME_DISCORD}" \
  --gen2 \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(serviceConfig.uri)")

HEALTH_URL=$(gcloud functions describe "${FUNCTION_NAME_HEALTH}" \
  --gen2 \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(serviceConfig.uri)")

REGISTER_URL=$(gcloud functions describe "${FUNCTION_NAME_REGISTER}" \
  --gen2 \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(serviceConfig.uri)")

echo "\nDone. Function URLs:"
echo "  Discord Interactions: ${DISCORD_URL}"
echo "  Health Check:         ${HEALTH_URL}"
echo "  Register Commands:    ${REGISTER_URL}"
echo "\nTest endpoints (optional):"
echo "  curl -i ${HEALTH_URL}"
echo "  curl -i -X POST ${DISCORD_URL} -H 'Content-Type: application/json' -d '{\"type\":1}'"

