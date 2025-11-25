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
    external = {
      source  = "hashicorp/external"
      version = ">= 2.3.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.4.0"
    }
  }
}

locals {
  # Build directory where we copy source + shared folder
  build_dir       = "${path.module}/.build-${var.function_name}"
  shared_src_path = "${path.root}/../services/shared"
  
  # Calculate hash of source files for triggering rebuild
  source_hash = sha256(join("", [
    for f in fileset(var.source_dir, "**") :
    filesha256("${var.source_dir}/${f}")
  ]))
  shared_hash = sha256(join("", [
    for f in fileset(local.shared_src_path, "**") :
    filesha256("${local.shared_src_path}/${f}")
  ]))
}

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

# Prepare source code: copy service source + shared folder to build directory
# This runs during plan phase via external data source
data "external" "prepare_source" {
  program = ["bash", "${path.module}/prepare-source.sh", local.build_dir, var.source_dir, local.shared_src_path]
  
  query = {
    source_hash = local.source_hash
    shared_hash = local.shared_hash
  }
}

# Create zip archive from build directory
data "archive_file" "source_zip" {
  depends_on  = [data.external.prepare_source]
  type        = "zip"
  source_dir  = local.build_dir
  output_path = "${path.module}/.archive-${var.function_name}.zip"
}

# Upload zip to Cloud Storage
resource "google_storage_bucket_object" "source_archive" {
  name   = "${var.function_name}/source-${data.archive_file.source_zip.output_md5}.zip"
  bucket = var.bucket_name
  source = data.archive_file.source_zip.output_path
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
        object = google_storage_bucket_object.source_archive.name
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

  depends_on = [google_project_service.apis, google_storage_bucket_object.source_archive]
}

resource "google_cloudfunctions2_function_iam_member" "invoker_public" {
  project        = var.project_id
  location       = var.region
  cloud_function = google_cloudfunctions2_function.function.name
  role           = "roles/cloudfunctions.invoker"
  member         = "allUsers"
}



