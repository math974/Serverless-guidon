terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }

  # Remote state backend (GCS).
  # Bucket and prefix are provided by the deploy/destroy scripts using -backend-config
  # for each environment/workspace (see configs/dev.config and configs/prd.config).
  backend "gcs" {}
}

# API Storage nécessaire
resource "google_project_service" "storage_api" {
  service = "storage.googleapis.com"
}

# Bucket simple pour les IAM
resource "google_storage_bucket" "iam_bucket" {
  name          = "${var.project_id}-sample-iam"
  location      = var.region
  force_destroy = true
  uniform_bucket_level_access = true

  depends_on = [google_project_service.storage_api]
}
