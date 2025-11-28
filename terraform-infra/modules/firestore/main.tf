terraform {
  required_version = ">= 1.3.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

# Enable Firestore API
resource "google_project_service" "firestore" {
  project = var.project_id
  service = "firestore.googleapis.com"
}

resource "google_project_service" "firebaserulesapi" {
  project = var.project_id
  service = "firebaserules.googleapis.com"
}

resource "google_project_service" "secretmanager" {
  project = var.project_id
  service = "secretmanager.googleapis.com"
}

# Create Firestore Database
# IMPORTANT: La database (default) ne peut être créée qu'une seule fois par projet GCP
# Si elle existe déjà, importer avec: terraform import module.firestore.google_firestore_database.database projects/PROJECT_ID/databases/(default)
resource "google_firestore_database" "database" {
  project     = var.project_id
  name        = var.database_id
  location_id = var.location_id
  type        = var.database_type

  # Use Datastore mode for DATASTORE_MODE, or default for FIRESTORE_NATIVE
  concurrency_mode                  = var.database_type == "FIRESTORE_NATIVE" ? "OPTIMISTIC" : null
  app_engine_integration_mode       = var.database_type == "FIRESTORE_NATIVE" ? "DISABLED" : null
  point_in_time_recovery_enablement = var.enable_pitr ? "POINT_IN_TIME_RECOVERY_ENABLED" : "POINT_IN_TIME_RECOVERY_DISABLED"

  # TOUJOURS activer la protection contre la suppression
  delete_protection_state = "DELETE_PROTECTION_ENABLED"

  # Empêcher Terraform de détruire la database
  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      # Ignorer les changements de type car on ne peut pas changer le type après création
      type,
      # Ignorer les changements de location car on ne peut pas déplacer la DB
      location_id,
    ]
  }

  depends_on = [
    google_project_service.firestore,
    google_project_service.firebaserulesapi
  ]
}

# IAM permissions pour les Cloud Functions
# Donne l'accès datastore.user aux service accounts des fonctions
resource "google_project_iam_member" "function_firestore_access" {
  for_each = toset(var.function_service_accounts)

  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${each.value}"

  depends_on = [google_firestore_database.database]
}

# Pour un accès plus restrictif, on peut aussi utiliser datastore.viewer pour la lecture seule
resource "google_project_iam_member" "function_firestore_viewer" {
  for_each = toset(var.function_service_accounts_readonly)

  project = var.project_id
  role    = "roles/datastore.viewer"
  member  = "serviceAccount:${each.value}"

  depends_on = [google_firestore_database.database]
}

# Secret Manager pour stocker le nom de la database
resource "google_secret_manager_secret" "firestore_database_name" {
  project   = var.project_id
  secret_id = "FIRESTORE_DATABASE"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "firestore_database_name_version" {
  secret      = google_secret_manager_secret.firestore_database_name.id
  secret_data = var.database_id
}

# Donner accès au secret aux Cloud Functions
resource "google_secret_manager_secret_iam_member" "function_secret_access" {
  for_each = toset(var.function_service_accounts)

  project   = var.project_id
  secret_id = google_secret_manager_secret.firestore_database_name.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${each.value}"
}

