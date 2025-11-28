# Module générique pour créer un service account avec ses permissions IAM
# Réutilisable pour n'importe quel service (Cloud Functions, API Gateway, Pub/Sub, etc.)

terraform {
  required_version = ">= 1.3.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

# Création du Service Account
resource "google_service_account" "sa" {
  project      = var.project_id
  account_id   = var.account_id
  display_name = var.display_name
  description  = var.description
}

# Attribution des rôles IAM au niveau projet
resource "google_project_iam_member" "project_roles" {
  for_each = toset(var.project_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.sa.email}"
}

# Attribution des permissions IAM sur des ressources spécifiques (Cloud Run services)
resource "google_cloud_run_service_iam_member" "service_permissions" {
  for_each = var.cloud_run_permissions

  project  = var.project_id
  location = each.value.region
  service  = each.value.service_name
  role     = each.value.role
  member   = "serviceAccount:${google_service_account.sa.email}"
}

# Attribution des permissions IAM sur des secrets spécifiques
resource "google_secret_manager_secret_iam_member" "secret_permissions" {
  for_each = var.secret_permissions

  project   = var.project_id
  secret_id = each.value.secret_id
  role      = each.value.role
  member    = "serviceAccount:${google_service_account.sa.email}"
}

