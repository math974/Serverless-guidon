output "email" {
  description = "Email du service account créé"
  value       = google_service_account.sa.email
}

output "name" {
  description = "Nom complet du service account créé"
  value       = google_service_account.sa.name
}

output "unique_id" {
  description = "ID unique du service account"
  value       = google_service_account.sa.unique_id
}

output "account_id" {
  description = "ID du service account"
  value       = google_service_account.sa.account_id
}

output "member" {
  description = "Membre IAM formaté (serviceAccount:email)"
  value       = "serviceAccount:${google_service_account.sa.email}"
}

