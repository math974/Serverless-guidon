output "function_urls" {
  description = "URLs publiques par fonction"
  value       = { for name, mod in module.functions : name => mod.function_url }
}

output "pubsub_topics" {
  description = "Pub/Sub topics créés"
  value       = module.pubsub.topic_names
}

output "pubsub_subscriptions" {
  description = "Pub/Sub subscriptions créées"
  value       = module.pubsub.subscription_names
}
