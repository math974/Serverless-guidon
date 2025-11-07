output "api_name" {
  description = "Nom complet de l'API (projects/.../locations/global/apis/...)"
  value       = google_api_gateway_api.api.name
}

output "api_config_name" {
  description = "Nom complet de la config d'API"
  value       = google_api_gateway_api_config.config.name
}

output "gateway_id" {
  description = "Identifiant de la gateway"
  value       = google_api_gateway_gateway.gateway.gateway_id
}

output "gateway_default_hostname" {
  description = "Hostname par défaut de la gateway (gateway.dev)"
  value       = google_api_gateway_gateway.gateway.default_hostname
}





