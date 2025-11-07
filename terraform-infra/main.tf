# Configuration principale Terraform
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 5.0"
    }
  }

  backend "gcs" {}
}

module "api_gateway" {
  source = "./modules/api-gateway"

  providers = {
    google      = google
    google-beta = google-beta
  }

  project_id            = var.project_id
  region                = var.region
  api_id                = var.api_id
  gateway_id            = var.gateway_id
  api_config_id         = var.api_config_id
  openapi_spec_path     = var.openapi_spec_path
  openapi_document_path = var.openapi_document_path
  labels                = var.labels
}





