terraform {
  required_version = ">= 1.3.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

# Enable Pub/Sub API
resource "google_project_service" "pubsub" {
  project = var.project_id
  service = "pubsub.googleapis.com"
}

# Pub/Sub Topics
resource "google_pubsub_topic" "topics" {
  for_each = { for topic in var.topics : topic.name => topic }

  name    = each.value.name
  project = var.project_id
  labels  = var.labels

  depends_on = [google_project_service.pubsub]
}

# Pub/Sub Push Subscriptions for Cloud Functions
resource "google_pubsub_subscription" "push_subscriptions" {
  for_each = var.push_subscriptions

  name    = each.value.name
  project = var.project_id
  topic   = google_pubsub_topic.topics[each.value.topic_name].name

  push_config {
    push_endpoint = each.value.push_endpoint

    oidc_token {
      service_account_email = each.value.service_account_email
    }
  }

  ack_deadline_seconds       = try(each.value.ack_deadline_seconds, 60)
  message_retention_duration = try(each.value.message_retention_duration, "604800s")
  retain_acked_messages      = try(each.value.retain_acked_messages, false)

  labels = var.labels
}

# IAM permissions pour permettre à Pub/Sub d'invoquer les Cloud Functions
resource "google_cloud_run_service_iam_member" "pubsub_invoker" {
  for_each = var.push_subscriptions

  project  = var.project_id
  location = each.value.function_region
  service  = each.value.function_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${each.value.service_account_email}"
}

