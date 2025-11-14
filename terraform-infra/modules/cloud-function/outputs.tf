output "function_url" {
  description = "URL publique HTTP de la fonction"
  value       = try(google_cloudfunctions2_function.function.url, google_cloudfunctions2_function.function.service_config[0].uri)
}



