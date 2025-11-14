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
    entry_point = string
    source_dir  = string
    runtime     = optional(string)
    labels      = optional(map(string))
    secret_env = optional(list(object({
      key     = string
      secret  = string
      version = string
    })))
  }))
  default = {}
}





