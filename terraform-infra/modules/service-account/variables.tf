variable "project_id" {
  description = "ID du projet GCP"
  type        = string
}

variable "account_id" {
  description = "ID du service account (doit être unique dans le projet, 6-30 caractères)"
  type        = string

  validation {
    condition     = can(regex("^[a-z](?:[-a-z0-9]{4,28}[a-z0-9])$", var.account_id))
    error_message = "account_id doit avoir entre 6 et 30 caractères, commencer par une lettre minuscule et contenir uniquement des lettres minuscules, chiffres et tirets."
  }
}

variable "display_name" {
  description = "Nom d'affichage du service account"
  type        = string
}

variable "description" {
  description = "Description du service account"
  type        = string
  default     = ""
}

variable "project_roles" {
  description = "Liste des rôles IAM à attribuer au niveau du projet (ex: ['roles/datastore.user', 'roles/logging.logWriter'])"
  type        = list(string)
  default     = []
}

variable "cloud_run_permissions" {
  description = "Map des permissions IAM sur des services Cloud Run spécifiques {key => {service_name, region, role}}"
  type = map(object({
    service_name = string
    region       = string
    role         = string
  }))
  default = {}
}

variable "secret_permissions" {
  description = "Map des permissions IAM sur des secrets spécifiques {key => {secret_id, role}}"
  type = map(object({
    secret_id = string
    role      = string
  }))
  default = {}
}

