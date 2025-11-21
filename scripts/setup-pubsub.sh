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
echo "Note: With Cloud Functions Gen2, subscriptions are created AUTOMATICALLY"
echo "   when you deploy functions with --trigger-topic."
echo ""
echo "   The following functions will auto-subscribe:"
echo "   • processor-base → subscribes to: discord-commands-base"
echo "   • processor-art → subscribes to: discord-commands-art"
echo ""
echo "   No manual subscription creation needed!"

