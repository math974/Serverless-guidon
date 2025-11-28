output "function_url" {
  description = "URL publique HTTP de la fonction"
  value       = google_cloudfunctions2_function.function.url
}

output "function_name" {
  description = "Nom de la Cloud Function créée"
  value       = google_cloudfunctions2_function.function.name
}

output "service_config" {
  description = "Configuration du service Cloud Run"
  value       = google_cloudfunctions2_function.function.service_config
}



