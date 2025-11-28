output "database_id" {
  description = "ID de la database Firestore"
  value       = google_firestore_database.database.id
}

output "database_name" {
  description = "Nom de la database Firestore"
  value       = google_firestore_database.database.name
}

output "database_location" {
  description = "Location de la database Firestore"
  value       = google_firestore_database.database.location_id
}

output "database_type" {
  description = "Type de la database Firestore"
  value       = google_firestore_database.database.type
}

output "secret_id" {
  description = "ID du secret contenant le nom de la database"
  value       = google_secret_manager_secret.firestore_database_name.secret_id
}

output "secret_name" {
  description = "Nom complet du secret (format: projects/*/secrets/*)"
  value       = google_secret_manager_secret.firestore_database_name.name
}

