#!/usr/bin/env bash

set -euo pipefail

# Setup Pub/Sub topics and subscriptions for Discord bot
# Usage:
#   PROJECT_ID=your-project ./setup-pubsub.sh

: "${PROJECT_ID:=serverless-ejguidon-dev}"

echo "Setting up Pub/Sub topics for Discord bot..."
echo "Project: ${PROJECT_ID}"

# Topics
TOPICS=(
    "discord-interactions"
    "discord-commands-base"
    "discord-commands-art"
)

# Create topics
for topic in "${TOPICS[@]}"; do
    echo "Creating topic: ${topic}"
    gcloud pubsub topics create "${topic}" \
        --project="${PROJECT_ID}" \
        2>&1 | grep -v "already exists" || echo "Topic ${topic} already exists"
done

echo ""
echo "Topics created successfully!"
echo ""
echo "To create push subscriptions for the processors:"
echo "  # Base commands processor"
echo "  gcloud pubsub subscriptions create discord-commands-base-sub \\"
echo "    --topic=discord-commands-base \\"
echo "    --push-endpoint=https://discord-processor-base-url.run.app/ \\"
echo "    --project=${PROJECT_ID}"
echo ""
echo "  # Art commands processor"
echo "  gcloud pubsub subscriptions create discord-commands-art-sub \\"
echo "    --topic=discord-commands-art \\"
echo "    --push-endpoint=https://discord-processor-art-url.run.app/ \\"
echo "    --project=${PROJECT_ID}"

