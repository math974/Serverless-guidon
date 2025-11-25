terraform {
  required_version = ">= 1.3.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.4.0"
    }
  }
}

locals {}

resource "google_project_service" "apis" {
  for_each = toset([
    "cloudfunctions.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
  ])
  project = var.project_id
  service = each.key
}

# Note: Source code is deployed via gcloud CLI in GitHub Actions pipeline
# Terraform creates the function with a minimal source, then gcloud CLI updates it
# We use a static minimal-template directory for initial deployment
data "archive_file" "minimal_source_zip" {
  type        = "zip"
  source_dir  = "${path.module}/minimal-template"
  output_path = "${path.module}/.minimal-${var.function_name}.zip"
}

resource "google_storage_bucket_object" "minimal_archive" {
  name   = "${var.function_name}/minimal.zip"
  bucket = var.bucket_name
  source = data.archive_file.minimal_source_zip.output_path
}

resource "google_cloudfunctions2_function" "function" {
  provider = google-beta
  name     = var.function_name
  project  = var.project_id
  location = var.region

  labels = var.labels

  build_config {
    runtime     = var.runtime
    entry_point = var.entry_point
    source {
      storage_source {
        bucket = var.bucket_name
        object = google_storage_bucket_object.minimal_archive.name
      }
    }
  }

  service_config {
    ingress_settings               = "ALLOW_ALL"
    all_traffic_on_latest_revision = true

    dynamic "secret_environment_variables" {
      for_each = var.secret_env
      content {
        key        = secret_environment_variables.value.key
        project_id = var.project_id
        secret     = secret_environment_variables.value.secret
        version    = secret_environment_variables.value.version
      }
    }
  }

  depends_on = [google_project_service.apis, google_storage_bucket_object.minimal_archive]

  lifecycle {
    ignore_changes = [build_config[0].source]
  }
}

resource "google_cloudfunctions2_function_iam_member" "invoker_public" {
  project        = var.project_id
  location       = var.region
  cloud_function = google_cloudfunctions2_function.function.name
  role           = "roles/cloudfunctions.invoker"
  member         = "allUsers"
}



