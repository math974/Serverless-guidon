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





