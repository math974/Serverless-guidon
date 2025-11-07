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

variable "api_config_id" {
  description = "Identifiant de la config de l'API (ex: v1)"
  type        = string
  default     = "v1"
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





