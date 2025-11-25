#!/usr/bin/env bash

set -euo pipefail

# Grant Eventarc service account permissions to invoke private Cloud Functions
# Usage:
#   PROJECT_ID=your-project REGION=europe-west1 ./grant-eventarc-permissions.sh

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${REGION:=europe-west1}"

echo "Granting Eventarc permissions to private services..."
echo "Project: ${PROJECT_ID}, Region: ${REGION}"
echo ""

# Get Eventarc service account
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
EVENTARC_SA="service-${PROJECT_NUMBER}@gcp-sa-eventarc.iam.gserviceaccount.com"

echo "Eventarc Service Account: ${EVENTARC_SA}"
echo ""

# Private services that need Eventarc permissions (Pub/Sub triggered)
PRIVATE_SERVICES=(
    "processor-base"
    "processor-draw"
    "processor-snapshot"
    "processor-canvas-state"
    "processor-stats"
    "processor-colors"
    "processor-pixel-info"
)

# Services that are private but HTTP-triggered (don't need Eventarc, but need service account permissions)
HTTP_PRIVATE_SERVICES=(
    "user-manager"
    "canvas-service"
)

echo "[1/2] Granting Eventarc permissions to Pub/Sub-triggered services..."
for service in "${PRIVATE_SERVICES[@]}"; do
    echo "  Granting invoker permission to ${service}..."
    gcloud functions add-invoker-policy-binding "${service}" \
        --gen2 \
        --region="${REGION}" \
        --member="serviceAccount:${EVENTARC_SA}" \
        --project="${PROJECT_ID}" \
        2>&1 | grep -v "already has role" || echo "    ✓ ${service} already has permission"
done

echo ""
echo "[2/2] Granting service account permissions to HTTP-triggered private services..."
echo "  Note: These services need permissions for service-to-service calls"
echo ""

# For HTTP-triggered services, we need to grant permissions to the Cloud Functions service account
# so other services can call them
CF_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for service in "${HTTP_PRIVATE_SERVICES[@]}"; do
    echo "  Granting invoker permission to ${service} for Cloud Functions SA..."
    gcloud functions add-invoker-policy-binding "${service}" \
        --gen2 \
        --region="${REGION}" \
        --member="serviceAccount:${CF_SA}" \
        --project="${PROJECT_ID}" \
        2>&1 | grep -v "already has role" || echo "    ✓ ${service} already has permission"
done

echo ""
echo "=========================================="
echo "Permissions granted successfully!"
echo "=========================================="
echo ""
echo "Eventarc can now invoke:"
for service in "${PRIVATE_SERVICES[@]}"; do
    echo "  ✓ ${service}"
done
echo ""
echo "Cloud Functions can now invoke:"
for service in "${HTTP_PRIVATE_SERVICES[@]}"; do
    echo "  ✓ ${service}"
done

