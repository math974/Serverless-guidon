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

variable "service_account_email" {
  description = "Email du service account à utiliser pour la Cloud Function"
  type        = string
  default     = null
}

variable "allow_public_access" {
  description = "Autoriser l'accès public (allUsers) à la fonction. Si false, seuls les service accounts autorisés peuvent l'invoquer."
  type        = bool
  default     = false
}

variable "authorized_invokers" {
  description = "Liste des membres autorisés à invoquer la fonction (ex: ['serviceAccount:xxx@yyy.iam.gserviceaccount.com']). Ignoré si allow_public_access = true."
  type        = list(string)
  default     = []
}



