variable "project_id" {
  description = "ID du projet GCP"
  type        = string
}

variable "region" {
  description = "Région (ex: europe-west1)"
  type        = string
}

variable "function_name" {
  description = "Nom de la Cloud Function (Gen2)"
  type        = string
}

variable "entry_point" {
  description = "Nom de la fonction Python (handler) ex: hello_http"
  type        = string
}

variable "runtime" {
  description = "Runtime Cloud Functions Gen2"
  type        = string
  default     = "python311"
}

variable "source_dir" {
  description = "Chemin local du répertoire contenant le code source de la fonction (utilisé pour référence, déploiement via gcloud CLI)"
  type        = string
}

variable "bucket_name" {
  description = "Nom du bucket GCS pour stocker l'archive source minimale (obligatoire)"
  type        = string

  validation {
    condition     = length(var.bucket_name) > 0
    error_message = "bucket_name doit être renseigné et non vide."
  }
}

variable "labels" {
  description = "Labels à appliquer"
  type        = map(string)
  default     = {}
}

variable "secret_env" {
  description = "Secrets à injecter en variables d'environnement (liste d'objets: key, secret, version)"
  type = list(object({
    key     = string
    secret  = string
    version = string
  }))
  default = []
}



