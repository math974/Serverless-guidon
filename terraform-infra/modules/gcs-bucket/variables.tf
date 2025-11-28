variable "project_id" {
  description = "ID du projet GCP"
  type        = string
}

variable "bucket_name" {
  description = "Nom unique du bucket GCS (doit être globalement unique)"
  type        = string
}

variable "location" {
  description = "Localisation du bucket (ex: europe-west1, EU, US)"
  type        = string
  default     = "europe-west1"
}

variable "storage_class" {
  description = "Classe de stockage (STANDARD, NEARLINE, COLDLINE, ARCHIVE)"
  type        = string
  default     = "STANDARD"
}

variable "labels" {
  description = "Labels à appliquer au bucket"
  type        = map(string)
  default     = {}
}

variable "force_destroy" {
  description = "Autoriser la destruction du bucket même s'il contient des objets"
  type        = bool
  default     = false
}

variable "uniform_bucket_level_access" {
  description = "Activer l'accès uniforme au niveau bucket (IAM uniquement, recommandé)"
  type        = bool
  default     = true
}

variable "public_read_access" {
  description = "Rendre le bucket accessible publiquement en lecture (allUsers)"
  type        = bool
  default     = false
}

variable "versioning_enabled" {
  description = "Activer le versioning des objets"
  type        = bool
  default     = false
}

# CORS Configuration
variable "cors_enabled" {
  description = "Activer la configuration CORS"
  type        = bool
  default     = false
}

variable "cors_origins" {
  description = "Origines autorisées pour CORS"
  type        = list(string)
  default     = ["*"]
}

variable "cors_methods" {
  description = "Méthodes HTTP autorisées pour CORS"
  type        = list(string)
  default     = ["GET", "HEAD"]
}

variable "cors_response_headers" {
  description = "Headers de réponse autorisés pour CORS"
  type        = list(string)
  default     = ["Content-Type", "Access-Control-Allow-Origin"]
}

variable "cors_max_age_seconds" {
  description = "Durée de cache pour la réponse CORS preflight"
  type        = number
  default     = 3600
}

# Lifecycle Rules
variable "lifecycle_rules" {
  description = "Règles de cycle de vie pour la gestion automatique des objets"
  type = list(object({
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
  }))
  default = []
}

# IAM Members
variable "iam_members" {
  description = "Permissions IAM personnalisées sur le bucket {key => {role, member}}"
  type = map(object({
    role   = string
    member = string
  }))
  default = {}
}

