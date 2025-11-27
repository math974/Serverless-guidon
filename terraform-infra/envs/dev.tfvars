project_id            = "serverless-ejguidon-dev"
region                = "europe-west1"
api_id                = "picasso-api"
gateway_id            = "picasso-gw-dev"
api_config_id_prefix  = "v"
openapi_spec_path     = "specs/openapi.yaml"
firestore_database_id = "guidon-db"

labels = {
  environment = "dev"
  app         = "picasso"
}

functions = {
  "proxy" = {
    entry_point         = "proxy_handler"
    source_dir          = "../services/proxy"
    runtime             = "python311"
    authorized_invokers = ["api-gateway"]
  }
  "auth-service" = {
    entry_point         = "auth_handler"
    source_dir          = "../services/auth-service"
    runtime             = "python311"
    authorized_invokers = ["api-gateway"]
    secret_env = [
      {
        key     = "FIRESTORE_DATABASE"
        secret  = "FIRESTORE_DATABASE"
        version = "latest"
      }
    ]
  }
  "user-manager" = {
    entry_point         = "user_management_handler"
    source_dir          = "../services/user-manager"
    runtime             = "python311"
    authorized_invokers = ["api-gateway"]
    secret_env = [
      {
        key     = "FIRESTORE_DATABASE"
        secret  = "FIRESTORE_DATABASE"
        version = "latest"
      }
    ]
  }
  "discord-registrar" = {
    entry_point = "registrar_handler"
    source_dir  = "../services/discord-registrar"
    runtime     = "python311"
  }
  "canvas-service" = {
    entry_point         = "canvas_service"
    source_dir          = "../services/canvas-service"
    runtime             = "python311"
    authorized_invokers = []
    secret_env = [
      {
        key     = "FIRESTORE_DATABASE"
        secret  = "FIRESTORE_DATABASE"
        version = "latest"
      }
    ]
  }
  "processor-base" = {
    entry_point         = "processor_base_handler"
    source_dir          = "../services/processor-base"
    runtime             = "python311"
    authorized_invokers = ["pubsub"]
  }
  "processor-stats" = {
    entry_point         = "processor_stats_handler"
    source_dir          = "../services/processor-stats"
    runtime             = "python311"
    authorized_invokers = ["pubsub"]
  }
  "processor-colors" = {
    entry_point         = "processor_colors_handler"
    source_dir          = "../services/processor-colors"
    runtime             = "python311"
    authorized_invokers = ["pubsub"]
  }
  "processor-draw" = {
    entry_point         = "processor_draw_handler"
    source_dir          = "../services/processor-draw"
    runtime             = "python311"
    authorized_invokers = ["pubsub"]
  }
  "processor-pixel-info" = {
    entry_point         = "processor_pixel_info_handler"
    source_dir          = "../services/processor-pixel-info"
    runtime             = "python311"
    authorized_invokers = ["pubsub"]
  }
  "processor-snapshot" = {
    entry_point         = "processor_snapshot_handler"
    source_dir          = "../services/processor-snapshot"
    runtime             = "python311"
    authorized_invokers = ["pubsub"]
  }
  "processor-canvas-state" = {
    entry_point         = "processor_canvas_state_handler"
    source_dir          = "../services/processor-canvas-state"
    runtime             = "python311"
    authorized_invokers = ["pubsub"]
  }
}

service_accounts = {
  "cloud-functions" = {
    account_id   = "cloud-functions-sa"
    display_name = "Cloud Functions Service Account"
    description  = "Service account pour exécuter les Cloud Functions avec permissions minimales"
    project_roles = [
      "roles/datastore.user",              # Firestore lecture/écriture
      "roles/pubsub.publisher",            # Publier sur Pub/Sub topics
      "roles/logging.logWriter",           # Écrire les logs
      "roles/cloudtrace.agent",            # Traçage distribué
      "roles/monitoring.metricWriter",     # Métriques
      "roles/secretmanager.secretAccessor" # Lire les secrets
    ]
  }
  "api-gateway" = {
    account_id   = "api-gateway-sa"
    display_name = "API Gateway Service Account"
    description  = "Service account pour l'API Gateway - permissions gérées dynamiquement"
  }
  "pubsub" = {
    account_id   = "pubsub-invoker-sa"
    display_name = "Pub/Sub Invoker Service Account"
    description  = "Service account pour Pub/Sub push subscriptions - permissions gérées dynamiquement"
  }
}

gcs_buckets = {
  "canvas-snapshots" = {
    bucket_name        = "discord-canvas-snapshots-dev"
    location           = "europe-west1"
    storage_class      = "STANDARD"
    public_read_access = true # Les snapshots doivent être accessibles publiquement
    force_destroy      = true # Dev: autoriser destruction facile
    cors_enabled       = true
    cors_origins       = ["*"]
    cors_methods       = ["GET", "HEAD"]
    cors_response_headers = [
      "Content-Type",
      "Access-Control-Allow-Origin"
    ]
    cors_max_age_seconds = 3600
    lifecycle_rules = [
      {
        action_type    = "Delete"
        age            = 30 # Dev: nettoyer plus rapidement (30 jours)
        matches_prefix = ["snapshots/"]
      }
    ]
  }
}





