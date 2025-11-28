variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "database_id" {
  description = "ID de la database Firestore (par défaut '(default)' pour la database principale)"
  type        = string
  default     = "(default)"
}

variable "location_id" {
  description = "Location de la database Firestore (ex: europe-west1)"
  type        = string
}

variable "database_type" {
  description = "Type de database: FIRESTORE_NATIVE ou DATASTORE_MODE"
  type        = string
  default     = "FIRESTORE_NATIVE"
  validation {
    condition     = contains(["FIRESTORE_NATIVE", "DATASTORE_MODE"], var.database_type)
    error_message = "Le type de database doit être FIRESTORE_NATIVE ou DATASTORE_MODE."
  }
}

variable "enable_pitr" {
  description = "Activer Point-in-Time Recovery"
  type        = bool
  default     = false
}

# Note: delete_protection est TOUJOURS activée via delete_protection_state = "DELETE_PROTECTION_ENABLED"
# et lifecycle { prevent_destroy = true } dans main.tf

variable "function_service_accounts" {
  description = "Liste des service accounts des Cloud Functions qui ont besoin d'accéder à Firestore (lecture/écriture)"
  type        = list(string)
  default     = []
}

variable "function_service_accounts_readonly" {
  description = "Liste des service accounts des Cloud Functions qui ont besoin d'un accès lecture seule à Firestore"
  type        = list(string)
  default     = []
}

