#!/bin/bash

# Setup Google Cloud authentication for Terraform
echo "Setting up Google Cloud authentication..."

# Install gcloud if not present
if ! command -v gcloud &> /dev/null; then
    echo "Please install Google Cloud SDK first: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Login to Google Cloud
echo "Please login to Google Cloud..."
gcloud auth login

# Set application default credentials
echo "Setting application default credentials..."
gcloud auth application-default login

# Set project (replace with your actual project ID)
read -p "Enter your Google Cloud Project ID: " PROJECT_ID
gcloud config set project $PROJECT_ID

echo "Authentication setup complete!"
echo "You can now run: terraform init"
