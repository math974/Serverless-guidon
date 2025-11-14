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

resource "google_storage_bucket" "cf_src" {
  name                        = "${var.project_id}-cf2-src"
  project                     = var.project_id
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
  labels                      = var.labels
}

module "functions" {
  source   = "./modules/cloud-function"
  for_each = var.functions

  providers = {
    google      = google
    google-beta = google-beta
  }

  project_id    = var.project_id
  region        = var.region
  function_name = each.key
  entry_point   = each.value.entry_point
  source_dir    = each.value.source_dir
  runtime       = try(each.value.runtime, "python311")
  labels        = merge(var.labels, coalesce(each.value.labels, {}))
  secret_env    = coalesce(each.value.secret_env, [])

  bucket_name = google_storage_bucket.cf_src.name
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
  api_config_id_prefix  = var.api_config_id_prefix
  openapi_spec_path     = var.openapi_spec_path
  openapi_document_path = var.openapi_document_path
  labels                = var.labels

  # Utiliser le template OpenAPI paramétré avec l'URL backend de la fonction
  openapi_template_path = "specs/openapi-template.yaml"
  openapi_variables = {
    HELLO_URL = module.functions["hello-http"].function_url
    PING_URL  = module.functions["ping-http"].function_url
  }
}





