#!/usr/bin/env bash

set -euo pipefail

# Create Pub/Sub topics and subscriptions for microservices
# Usage:
#   PROJECT_ID=your-project REGION=europe-west1 ./setup-microservices-pubsub.sh

: "${PROJECT_ID:=serverless-ejguidon-dev}"
: "${REGION:=europe-west1}"

echo "Creating Pub/Sub topics for microservices..."

topics=(
    "commands-draw"
    "commands-snapshot"
    "commands-canvas-state"
    "commands-stats"
    "commands-colors"
    "commands-pixel-info"
)

for topic in "${topics[@]}"; do
    echo "Creating topic: ${topic}"
    gcloud pubsub topics create "${topic}" \
        --project="${PROJECT_ID}" \
        2>&1 | grep -v "already exists" || true
done

echo ""
echo "Creating Pub/Sub subscriptions..."

# Get service URLs (will be set after deployment)
SERVICE_DRAW_URL="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/processor-draw"
SERVICE_SNAPSHOT_URL="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/processor-snapshot"
SERVICE_CANVAS_STATE_URL="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/processor-canvas-state"
SERVICE_STATS_URL="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/processor-stats"
SERVICE_COLORS_URL="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/processor-colors"
SERVICE_PIXEL_INFO_URL="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/processor-pixel-info"

subscriptions=(
    "commands-draw-sub:commands-draw:${SERVICE_DRAW_URL}"
    "commands-snapshot-sub:commands-snapshot:${SERVICE_SNAPSHOT_URL}"
    "commands-canvas-state-sub:commands-canvas-state:${SERVICE_CANVAS_STATE_URL}"
    "commands-stats-sub:commands-stats:${SERVICE_STATS_URL}"
    "commands-colors-sub:commands-colors:${SERVICE_COLORS_URL}"
    "commands-pixel-info-sub:commands-pixel-info:${SERVICE_PIXEL_INFO_URL}"
)

for sub_config in "${subscriptions[@]}"; do
    IFS=':' read -r sub_name topic_name service_url <<< "${sub_config}"
    echo "Creating subscription: ${sub_name} for topic: ${topic_name}"
    gcloud pubsub subscriptions create "${sub_name}" \
        --topic="${topic_name}" \
        --push-endpoint="${service_url}" \
        --project="${PROJECT_ID}" \
        2>&1 | grep -v "already exists" || true
done

echo ""
echo "Pub/Sub topics and subscriptions created!"
echo ""
echo "Note: Update subscription push endpoints after deploying services:"
echo "  gcloud pubsub subscriptions update <sub-name> --push-endpoint=<service-url>"

