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

# Note: Functions are deployed via gcloud CLI in GitHub Actions
# Terraform creates the function infrastructure with minimal source, then gcloud CLI updates it
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
  bucket_name   = google_storage_bucket.cf_src.name
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

  # Utiliser le template OpenAPI paramétré avec les URLs backend des fonctions
  openapi_template_path = "specs/openapi-template.yaml"
  openapi_variables = {
    PROXY_URL = module.functions["proxy"].function_url
    AUTH_URL  = module.functions["auth-service"].function_url
  }
}

module "pubsub" {
  source = "./modules/pubsub"

  project_id = var.project_id
  labels     = var.labels

  topics = [
    {
      name        = "interactions"
      description = "Topic for all Discord and Web interactions"
    },
    {
      name        = "commands-base"
      description = "Topic for base commands (ping, hello, help)"
    },
    {
      name        = "commands-draw"
      description = "Topic for draw command processing"
    },
    {
      name        = "commands-snapshot"
      description = "Topic for snapshot command processing"
    },
    {
      name        = "commands-canvas-state"
      description = "Topic for canvas_state command processing"
    },
    {
      name        = "commands-stats"
      description = "Topic for stats command processing"
    },
    {
      name        = "commands-colors"
      description = "Topic for colors command processing"
    },
    {
      name        = "commands-pixel-info"
      description = "Topic for pixel_info/getpixel command processing"
    }
  ]

  push_subscriptions = {
    processor_base = {
      name                  = "processor-base-sub"
      topic_name            = "commands-base"
      push_endpoint         = module.functions["processor-base"].function_url
      service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
      function_name         = "processor-base"
      function_region       = var.region
    }
    processor_draw = {
      name                  = "processor-draw-sub"
      topic_name            = "commands-draw"
      push_endpoint         = module.functions["processor-draw"].function_url
      service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
      function_name         = "processor-draw"
      function_region       = var.region
    }
    processor_snapshot = {
      name                  = "processor-snapshot-sub"
      topic_name            = "commands-snapshot"
      push_endpoint         = module.functions["processor-snapshot"].function_url
      service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
      function_name         = "processor-snapshot"
      function_region       = var.region
    }
    processor_canvas_state = {
      name                  = "processor-canvas-state-sub"
      topic_name            = "commands-canvas-state"
      push_endpoint         = module.functions["processor-canvas-state"].function_url
      service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
      function_name         = "processor-canvas-state"
      function_region       = var.region
    }
    processor_stats = {
      name                  = "processor-stats-sub"
      topic_name            = "commands-stats"
      push_endpoint         = module.functions["processor-stats"].function_url
      service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
      function_name         = "processor-stats"
      function_region       = var.region
    }
    processor_colors = {
      name                  = "processor-colors-sub"
      topic_name            = "commands-colors"
      push_endpoint         = module.functions["processor-colors"].function_url
      service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
      function_name         = "processor-colors"
      function_region       = var.region
    }
    processor_pixel_info = {
      name                  = "processor-pixel-info-sub"
      topic_name            = "commands-pixel-info"
      push_endpoint         = module.functions["processor-pixel-info"].function_url
      service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
      function_name         = "processor-pixel-info"
      function_region       = var.region
    }
  }

  depends_on = [module.functions]
}