output "project_id" {
  description = "L'ID du projet Google Cloud"
  value       = var.project_id
}

output "region" {
  description = "La région utilisée"
  value       = var.region
}

output "iam_bucket_name" {
  description = "Le nom du bucket IAM"
  value       = google_storage_bucket.iam_bucket.name
}

output "iam_bucket_url" {
  description = "L'URL du bucket IAM"
  value       = google_storage_bucket.iam_bucket.url
}
