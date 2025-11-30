# Configuration principale Terraform
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0, < 8.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 5.0, < 8.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
  }

  backend "gcs" {}
}

# Data source pour obtenir le project number
data "google_project" "project" {
  project_id = var.project_id
}

# Secrets pour les URLs des services - créés AVANT les fonctions avec des valeurs temporaires
# Cela évite la dépendance circulaire
resource "google_secret_manager_secret" "service_urls" {
  for_each = var.service_url_secrets

  project   = var.project_id
  secret_id = each.key

  replication {
    auto {}
  }

  labels = var.labels
}

# Valeurs temporaires initiales (pour le premier déploiement)
resource "google_secret_manager_secret_version" "initial_urls" {
  for_each = var.service_url_secrets

  secret      = google_secret_manager_secret.service_urls[each.key].id
  secret_data = "https://pending-deployment-${lower(each.key)}.example.com"

  lifecycle {
    ignore_changes = [secret_data] # Ne pas écraser les vraies valeurs après le premier apply
  }
}

# Service Accounts avec configuration depuis tfvars
module "service_accounts" {
  source   = "./modules/service-account"
  for_each = var.service_accounts

  project_id            = var.project_id
  account_id            = each.value.account_id
  display_name          = each.value.display_name
  description           = coalesce(each.value.description, "")
  project_roles         = coalesce(each.value.project_roles, [])
  cloud_run_permissions = coalesce(each.value.cloud_run_permissions, {})
  secret_permissions    = coalesce(each.value.secret_permissions, {})
}

# Permissions Cloud Run dynamiques basées sur authorized_invokers
# Pour chaque fonction, on crée les permissions pour les service accounts autorisés
locals {
  # Créer une map de permissions: {function_name-sa_name => {function_name, sa_name}}
  function_invoker_permissions = merge([
    for func_name, func_config in var.functions : {
      for sa_name in coalesce(func_config.authorized_invokers, []) :
      "${func_name}-${sa_name}" => {
        function_name = func_name
        sa_name       = sa_name
      }
    }
  ]...)
}

resource "google_cloud_run_service_iam_member" "function_invokers" {
  for_each = local.function_invoker_permissions

  project  = var.project_id
  location = var.region
  service  = module.functions[each.value.function_name].function_name
  role     = "roles/run.invoker"
  member   = each.value.sa_name == "allUsers" ? "allUsers" : module.service_accounts[each.value.sa_name].member

  depends_on = [module.functions, module.service_accounts]
}

resource "google_storage_bucket" "cf_src" {
  name                        = "${var.project_id}-cf2-src"
  project                     = var.project_id
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
  labels                      = var.labels
}

# Buckets GCS configurés dans les tfvars
module "gcs_buckets" {
  source   = "./modules/gcs-bucket"
  for_each = var.gcs_buckets

  project_id                  = var.project_id
  bucket_name                 = each.value.bucket_name
  location                    = coalesce(each.value.location, var.region)
  storage_class               = coalesce(each.value.storage_class, "STANDARD")
  public_read_access          = coalesce(each.value.public_read_access, false)
  force_destroy               = coalesce(each.value.force_destroy, false)
  uniform_bucket_level_access = coalesce(each.value.uniform_bucket_level_access, true)
  versioning_enabled          = coalesce(each.value.versioning_enabled, false)
  cors_enabled                = coalesce(each.value.cors_enabled, false)
  cors_origins                = coalesce(each.value.cors_origins, ["*"])
  cors_methods                = coalesce(each.value.cors_methods, ["GET", "HEAD"])
  cors_response_headers       = coalesce(each.value.cors_response_headers, ["Content-Type", "Access-Control-Allow-Origin"])
  cors_max_age_seconds        = coalesce(each.value.cors_max_age_seconds, 3600)
  lifecycle_rules             = coalesce(each.value.lifecycle_rules, [])
  iam_members                 = coalesce(each.value.iam_members, {})
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

  project_id            = var.project_id
  region                = var.region
  function_name         = each.key
  entry_point           = each.value.entry_point
  source_dir            = each.value.source_dir
  runtime               = try(each.value.runtime, "python311")
  labels                = merge(var.labels, coalesce(each.value.labels, {}))
  secret_env            = coalesce(each.value.secret_env, [])
  bucket_name           = google_storage_bucket.cf_src.name
  service_account_email = module.service_accounts["cloud-functions"].email

  # Configuration de l'accès : par défaut privé (pas d'accès public)
  # Les permissions IAM sont gérées dans la configuration des service accounts
  allow_public_access = false
  authorized_invokers = []

  depends_on = [
    module.service_accounts,
    google_secret_manager_secret_version.gcs_canvas_bucket_version,
    google_secret_manager_secret_version.oauth_login_url_initial,
    google_secret_manager_secret_version.discord_redirect_uri_initial,
    google_secret_manager_secret_version.gcp_project_id
  ]
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
  labels                = var.labels
  service_account_email = module.service_accounts["api-gateway"].email

  # Utiliser le template OpenAPI paramétré avec les URLs backend des fonctions
  openapi_spec_path     = var.openapi_spec_path
  openapi_template_path = var.openapi_spec_path
  openapi_variables = {
    PROXY_URL = module.functions["proxy"].function_url
    AUTH_URL  = module.functions["auth-service"].function_url
  }

  # Hash du fichier OpenAPI pour forcer le redéploiement quand le contenu change
  openapi_content_hash = filesha256(var.openapi_spec_path)

  depends_on = [module.service_accounts]
}

# ============================================================================
# PHASE 2 : Mise à jour des secrets avec les vraies URLs de l'API Gateway
# ============================================================================

# Mise à jour avec la vraie URL OAuth Login
resource "google_secret_manager_secret_version" "oauth_login_url_real" {
  secret      = google_secret_manager_secret.oauth_login_url.id
  secret_data = "${module.api_gateway.gateway_url}/auth/login"

  depends_on = [
    google_secret_manager_secret_version.oauth_login_url_initial,
    module.api_gateway
  ]
}

# Mise à jour avec la vraie URL Discord Redirect
resource "google_secret_manager_secret_version" "discord_redirect_uri_real" {
  secret      = google_secret_manager_secret.discord_redirect_uri.id
  secret_data = "${module.api_gateway.gateway_url}/auth/callback"

  depends_on = [
    google_secret_manager_secret_version.discord_redirect_uri_initial,
    module.api_gateway
  ]
}

module "firestore" {
  source = "./modules/firestore"

  project_id    = var.project_id
  database_id   = var.firestore_database_id
  location_id   = var.region
  database_type = "FIRESTORE_NATIVE"
  enable_pitr   = false

  # Les permissions IAM sont gérées dans le module service-accounts
  # On ne passe plus de service accounts ici
  function_service_accounts = []
}

# ============================================================================
# Web Frontend - App Engine
# ============================================================================

module "app_engine" {
  source = "./modules/app-engine"

  project_id                = var.project_id
  location_id               = var.app_engine_location
  region                    = var.region
  service_name              = var.app_engine_service_name
  runtime                   = "python310"
  entrypoint                = "gunicorn -b :$PORT --timeout 60 --workers 2 main:app"
  source_dir                = "${path.root}/../web-frontend"
  app_yaml_template_path    = "${path.root}/../web-frontend/app.yaml.tpl"
  min_instances             = var.app_engine_min_instances
  max_instances             = var.app_engine_max_instances
  delete_service_on_destroy = false

  env_variables = {
    GATEWAY_URL = module.api_gateway.gateway_url
  }

  labels = var.labels

  depends_on = [
    module.api_gateway,
    module.firestore
  ]
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
      service_account_email = module.service_accounts["pubsub"].email
      function_name         = "processor-base"
      function_region       = var.region
    }
    processor_draw = {
      name                  = "processor-draw-sub"
      topic_name            = "commands-draw"
      push_endpoint         = module.functions["processor-draw"].function_url
      service_account_email = module.service_accounts["pubsub"].email
      function_name         = "processor-draw"
      function_region       = var.region
    }
    processor_snapshot = {
      name                  = "processor-snapshot-sub"
      topic_name            = "commands-snapshot"
      push_endpoint         = module.functions["processor-snapshot"].function_url
      service_account_email = module.service_accounts["pubsub"].email
      function_name         = "processor-snapshot"
      function_region       = var.region
    }
    processor_canvas_state = {
      name                  = "processor-canvas-state-sub"
      topic_name            = "commands-canvas-state"
      push_endpoint         = module.functions["processor-canvas-state"].function_url
      service_account_email = module.service_accounts["pubsub"].email
      function_name         = "processor-canvas-state"
      function_region       = var.region
    }
    processor_stats = {
      name                  = "processor-stats-sub"
      topic_name            = "commands-stats"
      push_endpoint         = module.functions["processor-stats"].function_url
      service_account_email = module.service_accounts["pubsub"].email
      function_name         = "processor-stats"
      function_region       = var.region
    }
    processor_colors = {
      name                  = "processor-colors-sub"
      topic_name            = "commands-colors"
      push_endpoint         = module.functions["processor-colors"].function_url
      service_account_email = module.service_accounts["pubsub"].email
      function_name         = "processor-colors"
      function_region       = var.region
    }
    processor_pixel_info = {
      name                  = "processor-pixel-info-sub"
      topic_name            = "commands-pixel-info"
      push_endpoint         = module.functions["processor-pixel-info"].function_url
      service_account_email = module.service_accounts["pubsub"].email
      function_name         = "processor-pixel-info"
      function_region       = var.region
    }
  }

  depends_on = [module.functions]
}

# Mise à jour des secrets avec les vraies URLs après le déploiement des fonctions
resource "google_secret_manager_secret_version" "real_urls" {
  for_each = var.service_url_secrets

  secret      = google_secret_manager_secret.service_urls[each.key].id
  secret_data = module.functions[each.value].cloud_run_url

  depends_on = [
    google_secret_manager_secret_version.initial_urls,
    module.functions
  ]
}

# Donner accès aux secrets des URLs aux service accounts des Cloud Functions
resource "google_secret_manager_secret_iam_member" "url_secrets_access" {
  for_each = google_secret_manager_secret.service_urls

  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = module.service_accounts["cloud-functions"].member

  depends_on = [module.service_accounts]
}

# Secret pour le nom du bucket GCS canvas snapshots
resource "google_secret_manager_secret" "gcs_canvas_bucket" {
  project   = var.project_id
  secret_id = "GCS_CANVAS_BUCKET"

  replication {
    auto {}
  }

  labels = var.labels
}

resource "google_secret_manager_secret_version" "gcs_canvas_bucket_version" {
  secret      = google_secret_manager_secret.gcs_canvas_bucket.id
  secret_data = module.gcs_buckets["canvas-snapshots"].bucket_name

  depends_on = [module.gcs_buckets]
}

# Accès au secret GCS_CANVAS_BUCKET pour les Cloud Functions
resource "google_secret_manager_secret_iam_member" "gcs_bucket_access" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.gcs_canvas_bucket.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = module.service_accounts["cloud-functions"].member

  depends_on = [module.service_accounts]
}

# ============================================================================
# PHASE 1 : Secrets basés sur l'API Gateway (valeurs temporaires)
# ============================================================================

# Secret pour l'URL de login OAuth
resource "google_secret_manager_secret" "oauth_login_url" {
  project   = var.project_id
  secret_id = "OAUTH_LOGIN_URL"

  replication {
    auto {}
  }

  labels = var.labels
}

# Valeur temporaire initiale pour OAUTH_LOGIN_URL (pour le premier déploiement)
resource "google_secret_manager_secret_version" "oauth_login_url_initial" {
  secret      = google_secret_manager_secret.oauth_login_url.id
  secret_data = "https://pending-api-gateway-deployment.example.com/auth/login"

  lifecycle {
    ignore_changes = [secret_data] # Ne pas écraser la vraie valeur après le premier apply
  }
}

# Secret pour l'URI de redirection Discord OAuth
resource "google_secret_manager_secret" "discord_redirect_uri" {
  project   = var.project_id
  secret_id = "DISCORD_REDIRECT_URI"

  replication {
    auto {}
  }

  labels = var.labels
}

# Valeur temporaire initiale pour DISCORD_REDIRECT_URI (pour le premier déploiement)
resource "google_secret_manager_secret_version" "discord_redirect_uri_initial" {
  secret      = google_secret_manager_secret.discord_redirect_uri.id
  secret_data = "https://pending-api-gateway-deployment.example.com/auth/callback"

  lifecycle {
    ignore_changes = [secret_data] # Ne pas écraser la vraie valeur après le premier apply
  }
}

# Accès au secret OAUTH_LOGIN_URL pour les Cloud Functions
resource "google_secret_manager_secret_iam_member" "oauth_login_url_access" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.oauth_login_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = module.service_accounts["cloud-functions"].member

  depends_on = [module.service_accounts]
}

# Accès au secret DISCORD_REDIRECT_URI pour les Cloud Functions
resource "google_secret_manager_secret_iam_member" "discord_redirect_uri_access" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.discord_redirect_uri.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = module.service_accounts["cloud-functions"].member

  depends_on = [module.service_accounts]
}

# ========================================
# Secret pour l'URL du Web Frontend
# ========================================

resource "google_secret_manager_secret" "web_frontend_url" {
  project   = var.project_id
  secret_id = "WEB_FRONTEND_URL"

  replication {
    auto {}
  }

  labels = var.labels
}

# Valeur temporaire initiale pour WEB_FRONTEND_URL (pour le premier déploiement)
resource "google_secret_manager_secret_version" "web_frontend_url_initial" {
  secret      = google_secret_manager_secret.web_frontend_url.id
  secret_data = "https://pending-web-frontend-deployment.example.com"

  lifecycle {
    ignore_changes = [secret_data] # Ne pas écraser la vraie valeur après le premier apply
  }
}

# Accès au secret WEB_FRONTEND_URL pour les Cloud Functions
resource "google_secret_manager_secret_iam_member" "web_frontend_url_access" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.web_frontend_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = module.service_accounts["cloud-functions"].member

  depends_on = [module.service_accounts]
}

# Mise à jour avec la vraie URL du Web Frontend après le déploiement
resource "google_secret_manager_secret_version" "web_frontend_url_real" {
  secret      = google_secret_manager_secret.web_frontend_url.id
  secret_data = module.app_engine.app_url

  depends_on = [
    google_secret_manager_secret_version.web_frontend_url_initial,
    module.app_engine
  ]
}

# Secret GCP_PROJECT_ID pour toutes les fonctions
resource "google_secret_manager_secret" "gcp_project_id" {
  project   = var.project_id
  secret_id = "GCP_PROJECT_ID"

  replication {
    auto {}
  }

  labels = var.labels
}

resource "google_secret_manager_secret_version" "gcp_project_id" {
  secret      = google_secret_manager_secret.gcp_project_id.id
  secret_data = var.project_id
}

# Accès au secret GCP_PROJECT_ID pour les Cloud Functions
resource "google_secret_manager_secret_iam_member" "gcp_project_id_access" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.gcp_project_id.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = module.service_accounts["cloud-functions"].member

  depends_on = [module.service_accounts]
}