variable "project_id" {
  description = "ID du projet GCP"
  type        = string
}

variable "location_id" {
  description = "Localisation de l'application App Engine (ex: europe-west)"
  type        = string
}

variable "region" {
  description = "Région pour le bucket de stockage (ex: europe-west1)"
  type        = string
}

variable "service_name" {
  description = "Nom du service App Engine"
  type        = string
  default     = "default"
}

variable "runtime" {
  description = "Runtime de l'application (ex: python310)"
  type        = string
  default     = "python310"
}

variable "entrypoint" {
  description = "Commande d'entrée de l'application"
  type        = string
  default     = "gunicorn -b :$PORT --timeout 60 --workers 2 main:app"
}

variable "source_dir" {
  description = "Chemin vers le répertoire source de l'application"
  type        = string
}

variable "app_yaml_template_path" {
  description = "Chemin vers le template app.yaml.tpl"
  type        = string
}

variable "env_variables" {
  description = "Variables d'environnement pour l'application"
  type        = map(string)
  default     = {}
}

variable "min_instances" {
  description = "Nombre minimum d'instances"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Nombre maximum d'instances"
  type        = number
  default     = 10
}

variable "delete_service_on_destroy" {
  description = "Supprimer le service lors de la destruction"
  type        = bool
  default     = false
}

variable "labels" {
  description = "Labels à appliquer aux ressources"
  type        = map(string)
  default     = {}
}

