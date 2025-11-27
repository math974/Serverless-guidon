variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "labels" {
  description = "Labels à appliquer aux ressources"
  type        = map(string)
  default     = {}
}

variable "topics" {
  description = "Liste des topics Pub/Sub à créer"
  type = list(object({
    name        = string
    description = string
  }))
}

variable "push_subscriptions" {
  description = "Map des subscriptions push vers les Cloud Functions"
  type = map(object({
    name                  = string
    topic_name            = string
    push_endpoint         = string
    service_account_email = string
    function_name         = string
    function_region       = string
    ack_deadline_seconds  = optional(number, 60)
  }))
  default = {}
}

