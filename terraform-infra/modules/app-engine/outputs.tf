output "app_id" {
  description = "ID de l'application App Engine"
  value       = google_app_engine_application.app.app_id
}

output "default_hostname" {
  description = "Hostname par défaut de l'application"
  value       = google_app_engine_application.app.default_hostname
}

output "default_bucket" {
  description = "Bucket GCS par défaut de l'application"
  value       = google_app_engine_application.app.default_bucket
}

output "app_url" {
  description = "URL complète de l'application"
  value       = "https://${google_app_engine_application.app.default_hostname}"
}

output "service_name" {
  description = "Nom du service déployé"
  value       = google_app_engine_standard_app_version.web_frontend.service
}

output "version_id" {
  description = "ID de la version déployée"
  value       = google_app_engine_standard_app_version.web_frontend.version_id
}

output "source_bucket" {
  description = "Nom du bucket contenant le code source"
  value       = google_storage_bucket.source.name
}

