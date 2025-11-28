# Module pour créer et gérer des buckets Google Cloud Storage

terraform {
  required_version = ">= 1.3.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

# Création du bucket GCS
resource "google_storage_bucket" "bucket" {
  project       = var.project_id
  name          = var.bucket_name
  location      = var.location
  storage_class = var.storage_class
  labels        = var.labels

  # Forcer la destruction du bucket même s'il contient des objets (optionnel)
  force_destroy = var.force_destroy

  # Accès uniforme au niveau du bucket (IAM uniquement, pas d'ACL)
  uniform_bucket_level_access = var.uniform_bucket_level_access

  # Configuration CORS si activée
  dynamic "cors" {
    for_each = var.cors_enabled ? [1] : []
    content {
      origin          = var.cors_origins
      method          = var.cors_methods
      response_header = var.cors_response_headers
      max_age_seconds = var.cors_max_age_seconds
    }
  }

  # Règles de cycle de vie
  dynamic "lifecycle_rule" {
    for_each = var.lifecycle_rules
    content {
      action {
        type          = lifecycle_rule.value.action_type
        storage_class = try(lifecycle_rule.value.storage_class, null)
      }
      condition {
        age                        = try(lifecycle_rule.value.age, null)
        created_before             = try(lifecycle_rule.value.created_before, null)
        matches_prefix             = try(lifecycle_rule.value.matches_prefix, null)
        matches_suffix             = try(lifecycle_rule.value.matches_suffix, null)
        num_newer_versions         = try(lifecycle_rule.value.num_newer_versions, null)
        with_state                 = try(lifecycle_rule.value.with_state, null)
        days_since_custom_time     = try(lifecycle_rule.value.days_since_custom_time, null)
        days_since_noncurrent_time = try(lifecycle_rule.value.days_since_noncurrent_time, null)
      }
    }
  }

  # Versioning si activé
  dynamic "versioning" {
    for_each = var.versioning_enabled ? [1] : []
    content {
      enabled = true
    }
  }
}

# IAM : Accès public en lecture (allUsers) si activé
resource "google_storage_bucket_iam_member" "public_access" {
  count = var.public_read_access ? 1 : 0

  bucket = google_storage_bucket.bucket.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

# IAM : Permissions personnalisées sur le bucket
resource "google_storage_bucket_iam_member" "members" {
  for_each = var.iam_members

  bucket = google_storage_bucket.bucket.name
  role   = each.value.role
  member = each.value.member
}

