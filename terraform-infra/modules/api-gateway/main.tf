terraform {
  required_version = ">= 1.3.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.50.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 4.50.0"
    }
  }
}

// Lecture du fichier OpenAPI directement via filebase64()

resource "google_project_service" "apigateway" {
  project = var.project_id
  service = "apigateway.googleapis.com"
}

resource "google_api_gateway_api" "api" {
  provider = google-beta
  project  = var.project_id
  api_id   = var.api_id
  labels   = var.labels

  depends_on = [google_project_service.apigateway]
}

resource "google_api_gateway_api_config" "config" {
  provider      = google-beta
  project       = var.project_id
  api           = google_api_gateway_api.api.api_id
  api_config_id_prefix = var.api_config_id_prefix

  openapi_documents {
    document {
      path     = var.openapi_document_path
      contents = filebase64(var.openapi_spec_path)
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_api_gateway_gateway" "gateway" {
  provider   = google-beta
  project    = var.project_id
  region     = var.region
  gateway_id = var.gateway_id
  api_config = google_api_gateway_api_config.config.name
  labels     = var.labels
}

