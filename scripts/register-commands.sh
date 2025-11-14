#!/usr/bin/env bash

set -euo pipefail

# Register Discord commands via the registrar service
# Usage:
#   ./register-commands.sh [all|command_name]
#   PROJECT_ID=your-project REGION=europe-west1 ./register-commands.sh

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${REGION:=europe-west1}"
: "${SERVICE_NAME:=discord-registrar}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Registering Discord commands..."
echo "Project:        ${PROJECT_ID}"
echo "Region:         ${REGION}"
echo "Service:        ${SERVICE_NAME}"
echo ""

# Get registrar service URL
echo "[1/2] Getting registrar service URL..."
REGISTRAR_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)" 2>/dev/null)

if [ -z "${REGISTRAR_URL}" ]; then
    echo "❌ Error: Registrar service '${SERVICE_NAME}' not found"
    echo ""
    echo "Deploy the registrar service first:"
    echo "  ./scripts/deploy-registrar.sh"
    exit 1
fi

echo "  ✓ Registrar URL: ${REGISTRAR_URL}"
echo ""

# Register commands
COMMAND="${1:-all}"

if [ "${COMMAND}" = "all" ]; then
    echo "[2/2] Registering all commands..."
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${REGISTRAR_URL}/register")
    HTTP_CODE=$(echo "${RESPONSE}" | tail -n1)
    BODY=$(echo "${RESPONSE}" | sed '$d')

    if [ "${HTTP_CODE}" = "200" ]; then
        echo "  ✓ All commands registered successfully"
        echo ""
        echo "Response:"
        echo "${BODY}" | jq '.' 2>/dev/null || echo "${BODY}"
    else
        echo "  ❌ Error registering commands (HTTP ${HTTP_CODE})"
        echo ""
        echo "Response:"
        echo "${BODY}"
        exit 1
    fi
else
    echo "[2/2] Registering command: ${COMMAND}..."
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${REGISTRAR_URL}/register/${COMMAND}")
    HTTP_CODE=$(echo "${RESPONSE}" | tail -n1)
    BODY=$(echo "${RESPONSE}" | sed '$d')

    if [ "${HTTP_CODE}" = "200" ]; then
        echo "  ✓ Command '${COMMAND}' registered successfully"
        echo ""
        echo "Response:"
        echo "${BODY}" | jq '.' 2>/dev/null || echo "${BODY}"
    else
        echo "  ❌ Error registering command (HTTP ${HTTP_CODE})"
        echo ""
        echo "Response:"
        echo "${BODY}"
        exit 1
    fi
fi

echo ""
echo "Done! Commands should now be available in Discord."
echo ""
echo "To list all registered commands:"
echo "  curl ${REGISTRAR_URL}/commands"

