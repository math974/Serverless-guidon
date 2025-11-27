output "topic_ids" {
  description = "IDs des topics Pub/Sub créés"
  value       = { for name, topic in google_pubsub_topic.topics : name => topic.id }
}

output "topic_names" {
  description = "Noms des topics Pub/Sub créés"
  value       = { for name, topic in google_pubsub_topic.topics : name => topic.name }
}

output "subscription_ids" {
  description = "IDs des subscriptions Pub/Sub créées"
  value       = { for name, sub in google_pubsub_subscription.push_subscriptions : name => sub.id }
}

output "subscription_names" {
  description = "Noms des subscriptions Pub/Sub créées"
  value       = { for name, sub in google_pubsub_subscription.push_subscriptions : name => sub.name }
}

