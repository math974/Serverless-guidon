#!/usr/bin/env bash

set -euo pipefail

# Setup Pub/Sub topics and subscriptions for Discord bot
# Usage:
#   PROJECT_ID=your-project ./setup-pubsub.sh

: "${PROJECT_ID:=serverless-ejguidon-dev}"

echo "Setting up Pub/Sub topics for Discord bot..."
echo "Project: ${PROJECT_ID}"

# Topics - Base topics and microservices topics
TOPICS=(
    "interactions"
    "commands-base"
    "commands-draw"
    "commands-snapshot"
    "commands-canvas-state"
    "commands-stats"
    "commands-colors"
    "commands-pixel-info"
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
echo "Note: With Cloud Functions Gen2, subscriptions are created AUTOMATICALLY"
echo "   when you deploy functions with --trigger-topic."
echo ""
echo "   The following functions will auto-subscribe:"
echo "   • processor-base → subscribes to: commands-base"
echo "   • processor-draw → subscribes to: commands-draw"
echo "   • processor-snapshot → subscribes to: commands-snapshot"
echo "   • processor-canvas-state → subscribes to: commands-canvas-state"
echo "   • processor-stats → subscribes to: commands-stats"
echo "   • processor-colors → subscribes to: commands-colors"
echo "   • processor-pixel-info → subscribes to: commands-pixel-info"
echo ""
echo "   No manual subscription creation needed!"

