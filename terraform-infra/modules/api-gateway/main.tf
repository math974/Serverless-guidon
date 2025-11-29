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

// Lecture du fichier OpenAPI (templatefile si fourni, sinon file)
locals {
  openapi_raw = var.openapi_template_path != null ? templatefile(var.openapi_template_path, var.openapi_variables) : file(var.openapi_spec_path)
}

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
  provider             = google-beta
  project              = var.project_id
  api                  = google_api_gateway_api.api.api_id
  api_config_id_prefix = var.api_config_id_prefix

  gateway_config {
    backend_config {
      google_service_account = var.service_account_email
    }
  }

  openapi_documents {
    document {
      path     = var.openapi_document_path
      contents = base64encode(local.openapi_raw)
    }
  }

  # Labels pour forcer le redéploiement quand le contenu OpenAPI change
  labels = var.openapi_content_hash != null ? merge(
    var.labels,
    {
      "openapi-hash" = substr(var.openapi_content_hash, 0, 63)
    }
  ) : var.labels

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

