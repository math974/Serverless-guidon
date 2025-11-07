variable "project_id" {
  description = "ID du projet GCP où déployer l'API Gateway"
  type        = string
}

variable "region" {
  description = "Région GCP pour la gateway (ex: europe-west1)"
  type        = string
}

variable "api_id" {
  description = "Identifiant de l'API (google_api_gateway_api.api_id)"
  type        = string
}

variable "gateway_id" {
  description = "Identifiant de la Gateway (google_api_gateway_gateway.gateway_id)"
  type        = string
}

variable "api_config_id_prefix" {
  description = "Préfixe de l'identifiant de la config (ex: v). Un suffixe unique sera généré."
  type        = string
  default     = "v"
}

variable "openapi_spec_path" {
  description = "Chemin local vers le fichier OpenAPI (YAML/JSON)"
  type        = string
}

variable "openapi_document_path" {
  description = "Chemin logique du document dans la config (nom du fichier)"
  type        = string
  default     = "openapi.yaml"
}

variable "labels" {
  description = "Labels à appliquer aux ressources"
  type        = map(string)
  default     = {}
}





