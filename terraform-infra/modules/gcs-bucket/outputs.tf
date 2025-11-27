output "bucket_name" {
  description = "Nom du bucket créé"
  value       = google_storage_bucket.bucket.name
}

output "bucket_url" {
  description = "URL du bucket"
  value       = google_storage_bucket.bucket.url
}

output "bucket_self_link" {
  description = "URI complet du bucket"
  value       = google_storage_bucket.bucket.self_link
}

output "public_url" {
  description = "URL publique pour accéder aux objets (si public_read_access activé)"
  value       = "https://storage.googleapis.com/${google_storage_bucket.bucket.name}"
}

