variable "project_id" {
  description = "ID du projet GCP"
  type        = string
}

variable "region" {
  description = "Région GCP (ex: europe-west1)"
  type        = string
}

variable "api_id" {
  description = "Identifiant de l'API"
  type        = string
}

variable "gateway_id" {
  description = "Identifiant de la Gateway"
  type        = string
}

variable "api_config_id_prefix" {
  description = "Préfixe de l'identifiant de config (ex: v) pour générer un ID unique"
  type        = string
  default     = "v"
}

variable "openapi_spec_path" {
  description = "Chemin local vers le fichier OpenAPI"
  type        = string
}

variable "openapi_document_path" {
  description = "Chemin logique du document OpenAPI (nom de fichier)"
  type        = string
  default     = "openapi.yaml"
}

variable "labels" {
  description = "Labels pour les ressources"
  type        = map(string)
  default     = {}
}

variable "functions" {
  description = "Définition des fonctions serverless à déployer (map de fonctions)"
  type = map(object({
    entry_point         = string
    source_dir          = string
    runtime             = optional(string)
    labels              = optional(map(string))
    authorized_invokers = optional(list(string)) # Liste des service accounts autorisés (ex: ["api-gateway", "pubsub"])
    secret_env = optional(list(object({
      key     = string
      secret  = string
      version = string
    })))
  }))
  default = {}
}

variable "firestore_database_id" {
  description = "Nom de la database Firestore"
  type        = string
  default     = "guidon-db"
}

variable "service_accounts" {
  description = "Configuration des service accounts à créer avec leurs permissions IAM"
  type = map(object({
    account_id    = string
    display_name  = string
    description   = optional(string)
    project_roles = optional(list(string))
    cloud_run_permissions = optional(map(object({
      service_name = string
      region       = string
      role         = string
    })))
    secret_permissions = optional(map(object({
      secret_id = string
      role      = string
    })))
  }))
  default = {}
}

variable "gcs_buckets" {
  description = "Configuration des buckets Google Cloud Storage à créer"
  type = map(object({
    bucket_name                 = string
    location                    = optional(string)
    storage_class               = optional(string)
    public_read_access          = optional(bool)
    force_destroy               = optional(bool)
    uniform_bucket_level_access = optional(bool)
    versioning_enabled          = optional(bool)
    cors_enabled                = optional(bool)
    cors_origins                = optional(list(string))
    cors_methods                = optional(list(string))
    cors_response_headers       = optional(list(string))
    cors_max_age_seconds        = optional(number)
    lifecycle_rules = optional(list(object({
      action_type                = string
      storage_class              = optional(string)
      age                        = optional(number)
      created_before             = optional(string)
      matches_prefix             = optional(list(string))
      matches_suffix             = optional(list(string))
      num_newer_versions         = optional(number)
      with_state                 = optional(string)
      days_since_custom_time     = optional(number)
      days_since_noncurrent_time = optional(number)
    })))
    iam_members = optional(map(object({
      role   = string
      member = string
    })))
  }))
  default = {}
}

variable "service_url_secrets" {
  description = "Map des secrets pour les URLs des services {secret_name => function_name}"
  type        = map(string)
  default = {
    "USER_MANAGER_URL"   = "user-manager"
    "CANVAS_SERVICE_URL" = "canvas-service"
    "AUTH_SERVICE_URL"   = "auth-service"
  }
}

# ========================================
# Variables App Engine
# ========================================

variable "app_engine_location" {
  description = "Localisation de l'application App Engine (ex: europe-west)"
  type        = string
  default     = "europe-west"
}

variable "app_engine_service_name" {
  description = "Nom du service App Engine"
  type        = string
  default     = "default"
}

variable "app_engine_min_instances" {
  description = "Nombre minimum d'instances App Engine"
  type        = number
  default     = 0
}

variable "app_engine_max_instances" {
  description = "Nombre maximum d'instances App Engine"
  type        = number
  default     = 10
}
