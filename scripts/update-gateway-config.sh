#!/usr/bin/env bash

set -euo pipefail

# Usage:
#   PROJECT_ID=your-project REGION=europe-west1 \
#   ./update-gateway-config.sh

# Defaults (override via env)
: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${REGION:=europe-west1}"
: "${OPENAPI_SPEC:=./configs/openapi2-run.yaml}"

echo "Project:        ${PROJECT_ID}"
echo "Region:         ${REGION}"
echo "OpenAPI Spec:   ${OPENAPI_SPEC}"

# Function names
FUNCTION_NAME_DISCORD="discord-interactions"
FUNCTION_NAME_HEALTH="discord-health"
FUNCTION_NAME_REGISTER="discord-register-commands"

# Get function URLs
echo "\n[1/3] Getting Discord interactions function URL..."
DISCORD_URL=$(gcloud functions describe "${FUNCTION_NAME_DISCORD}" \
  --gen2 \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(serviceConfig.uri)" 2>/dev/null || echo "")

echo "\n[2/3] Getting health check function URL..."
HEALTH_URL=$(gcloud functions describe "${FUNCTION_NAME_HEALTH}" \
  --gen2 \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(serviceConfig.uri)" 2>/dev/null || echo "")

echo "\n[3/3] Getting register commands function URL..."
REGISTER_URL=$(gcloud functions describe "${FUNCTION_NAME_REGISTER}" \
  --gen2 \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(serviceConfig.uri)" 2>/dev/null || echo "")

if [ -z "${DISCORD_URL}" ] || [ -z "${HEALTH_URL}" ] || [ -z "${REGISTER_URL}" ]; then
  echo "ERROR: One or more functions not found. Please deploy functions first."
  echo "  Discord: ${DISCORD_URL:-NOT FOUND}"
  echo "  Health:  ${HEALTH_URL:-NOT FOUND}"
  echo "  Register: ${REGISTER_URL:-NOT FOUND}"
  exit 1
fi

echo "\nFunction URLs:"
echo "  Discord Interactions: ${DISCORD_URL}"
echo "  Health Check:         ${HEALTH_URL}"
echo "  Register Commands:    ${REGISTER_URL}"

# Create backup
BACKUP_FILE="${OPENAPI_SPEC}.backup.$(date +%Y%m%d%H%M%S)"
cp "${OPENAPI_SPEC}" "${BACKUP_FILE}"
echo "\nBackup created: ${BACKUP_FILE}"

# Update OpenAPI spec with actual URLs
# Remove protocol and path for address field
DISCORD_ADDRESS=$(echo "${DISCORD_URL}" | sed 's|https://||')
HEALTH_ADDRESS=$(echo "${HEALTH_URL}" | sed 's|https://||')
REGISTER_ADDRESS=$(echo "${REGISTER_URL}" | sed 's|https://||')

# Update the YAML file
# For Discord interactions
sed -i.bak "s|address: https://discord-interactions-.*|address: https://${DISCORD_ADDRESS}|" "${OPENAPI_SPEC}"

# For health check
sed -i.bak "s|address: https://discord-health-.*|address: https://${HEALTH_ADDRESS}|" "${OPENAPI_SPEC}"

# For register commands
sed -i.bak "s|address: https://discord-register-commands-.*|address: https://${REGISTER_ADDRESS}|" "${OPENAPI_SPEC}"

# Remove backup files created by sed
rm -f "${OPENAPI_SPEC}.bak"

echo "\nOpenAPI spec updated successfully!"
echo "You can now deploy the gateway with:"
echo "  ./scripts/deploy-gateway-no-key.sh"

