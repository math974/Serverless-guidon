output "function_urls" {
  description = "URLs publiques par fonction"
  value       = { for name, mod in module.functions : name => mod.function_url }
}


