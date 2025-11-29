terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0, < 8.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
  }
}

# Activer l'API App Engine
resource "google_project_service" "appengine" {
  project = var.project_id
  service = "appengine.googleapis.com"

  disable_dependent_services = false
  disable_on_destroy         = false
}

# Créer l'application App Engine (une seule fois par projet)
resource "google_app_engine_application" "app" {
  project       = var.project_id
  location_id   = var.location_id
  database_type = "CLOUD_FIRESTORE"

  depends_on = [google_project_service.appengine]
}

# Bucket pour stocker le code source de l'application
resource "google_storage_bucket" "source" {
  project                     = var.project_id
  name                        = "${var.project_id}-appengine-source"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  labels = var.labels
}

# Générer le fichier app.yaml avec les variables
resource "local_file" "app_yaml" {
  content = templatefile(var.app_yaml_template_path, {
    GATEWAY_URL = var.env_variables["GATEWAY_URL"]
  })
  filename = "${var.source_dir}/app.yaml.generated"
}

# Créer une archive avec tout le code source
data "archive_file" "source" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.module}/.temp/${var.service_name}-source.zip"
  excludes = [
    ".git",
    ".gitignore",
    "__pycache__",
    "*.pyc",
    ".gcloudignore",
    "cert.pem",
    "key.pem"
  ]

  depends_on = [local_file.app_yaml]
}

# Uploader l'archive dans GCS
resource "google_storage_bucket_object" "source" {
  name   = "${var.service_name}-${data.archive_file.source.output_md5}.zip"
  bucket = google_storage_bucket.source.name
  source = data.archive_file.source.output_path

  depends_on = [data.archive_file.source]
}

# Déployer la version App Engine Standard
resource "google_app_engine_standard_app_version" "web_frontend" {
  project    = var.project_id
  version_id = "v-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  service    = var.service_name
  runtime    = var.runtime
  entrypoint {
    shell = var.entrypoint
  }

  deployment {
    zip {
      source_url = "https://storage.googleapis.com/${google_storage_bucket.source.name}/${google_storage_bucket_object.source.name}"
    }
  }

  env_variables = var.env_variables

  automatic_scaling {
    min_idle_instances = var.min_instances
    max_idle_instances = var.max_instances
    standard_scheduler_settings {
      min_instances = var.min_instances
      max_instances = var.max_instances
    }
  }

  delete_service_on_destroy = var.delete_service_on_destroy

  # Empêcher les redéploiements inutiles
  lifecycle {
    ignore_changes = [
      version_id,
      deployment[0].zip[0].source_url
    ]
  }

  depends_on = [
    google_app_engine_application.app,
    google_storage_bucket_object.source
  ]
}

# Note: Le fichier app.yaml.generated sera supprimé manuellement si nécessaire
# Un destroy provisioner ne peut pas référencer des variables externes

