.PHONY: help deploy-all deploy-proxy deploy-processor-base deploy-processor-art deploy-registrar deploy-auth deploy-user-manager setup-pubsub register-commands update-gateway prepare-services test-health clean

# Default variables
PROJECT_ID ?= serverless-ejguidon-dev
REGION ?= europe-west1
API_ID ?= guidon-api
GATEWAY_ID ?= guidon
SCRIPT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
SCRIPTS_DIR := $(SCRIPT_DIR)/scripts

help: ## Display help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-30s %s\n", $$1, $$2}'

prepare-services: ## Prepare services (copy shared/)
	@$(SCRIPTS_DIR)/prepare-services.sh

setup-pubsub: ## Setup Pub/Sub topics and subscriptions
	@PROJECT_ID=$(PROJECT_ID) $(SCRIPTS_DIR)/setup-pubsub.sh

deploy-proxy: prepare-services ## Deploy proxy service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-proxy.sh

deploy-processor-base: prepare-services ## Deploy processor-base service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-processor-base.sh

deploy-processor-art: prepare-services ## Deploy processor-art service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-processor-art.sh

deploy-registrar: prepare-services ## Deploy registrar service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-registrar.sh

deploy-auth: prepare-services ## Deploy auth service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-auth.sh

deploy-user-manager: prepare-services ## Deploy user-manager service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-user-manager.sh

deploy-all: ## Deploy all services
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) API_ID=$(API_ID) GATEWAY_ID=$(GATEWAY_ID) $(SCRIPTS_DIR)/deploy-all.sh

register-commands: ## Register Discord commands
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/register-commands.sh

register-command: ## Register a specific command (usage: make register-command CMD=draw)
	@if [ -z "$(CMD)" ]; then \
		echo "Error: Specify a command with CMD=command_name"; \
		exit 1; \
	fi
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/register-commands.sh $(CMD)

update-gateway: ## Update API Gateway
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) API_ID=$(API_ID) GATEWAY_ID=$(GATEWAY_ID) $(SCRIPTS_DIR)/update-gateway-proxy.sh

test-health: ## Test health endpoints for all services
	@echo "Proxy:"
	@PROXY_URL=$$(gcloud functions describe proxy --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null) && \
		echo "  $$PROXY_URL/health" && curl -s $$PROXY_URL/health | python3 -m json.tool || echo "  Not available"
	@echo "Registrar:"
	@REGISTRAR_URL=$$(gcloud functions describe discord-utils --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null) && \
		echo "  $$REGISTRAR_URL/health" && curl -s $$REGISTRAR_URL/health | python3 -m json.tool || echo "  Not available"
	@echo "User-Manager:"
	@USER_MANAGER_URL=$$(gcloud functions describe user-manager --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null) && \
		echo "  $$USER_MANAGER_URL/health" && curl -s $$USER_MANAGER_URL/health | python3 -m json.tool || echo "  Not available"
	@echo "Auth Service:"
	@AUTH_URL=$$(gcloud functions describe discord-auth-service --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null) && \
		echo "  $$AUTH_URL/health" && curl -s $$AUTH_URL/health | python3 -m json.tool || echo "  Not available"

test-web: ## Test web endpoints
	@GATEWAY_URL=$$(gcloud api-gateway gateways describe $(GATEWAY_ID) --location=$(REGION) --project=$(PROJECT_ID) --format="value(defaultHostname)" 2>/dev/null) && \
		GATEWAY_URL="https://$$GATEWAY_URL" && \
		$(SCRIPTS_DIR)/test-web-interactions.sh || \
		echo "Gateway not available"

logs-proxy: ## Show proxy service logs
	@gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=proxy" \
		--project=$(PROJECT_ID) --limit=50 --format="table(timestamp,severity,jsonPayload.message)" --order=desc

logs-processor-base: ## Show processor-base service logs
	@gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=processor-base" \
		--project=$(PROJECT_ID) --limit=50 --format="table(timestamp,severity,jsonPayload.message)" --order=desc

logs-processor-art: ## Show processor-art service logs
	@gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=processor-art" \
		--project=$(PROJECT_ID) --limit=50 --format="table(timestamp,severity,jsonPayload.message)" --order=desc

logs-registrar: ## Show registrar service logs
	@gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=discord-utils" \
		--project=$(PROJECT_ID) --limit=50 --format="table(timestamp,severity,jsonPayload.message)" --order=desc

logs-user-manager: ## Show user-manager service logs
	@gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=user-manager" \
		--project=$(PROJECT_ID) --limit=50 --format="table(timestamp,severity,jsonPayload.message)" --order=desc

logs-auth: ## Show auth service logs (OAuth2)
	@gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=discord-auth-service" \
		--project=$(PROJECT_ID) --limit=50 --format="table(timestamp,severity,jsonPayload.message)" --order=desc

logs-all: ## Show logs for all services
	@echo "Proxy:"
	@$(MAKE) logs-proxy
	@echo "Processor-Base:"
	@$(MAKE) logs-processor-base
	@echo "Processor-Art:"
	@$(MAKE) logs-processor-art
	@echo "Registrar:"
	@$(MAKE) logs-registrar
	@echo "User-Manager:"
	@$(MAKE) logs-user-manager
	@echo "Auth Service:"
	@$(MAKE) logs-auth || echo "  Not deployed"

urls: ## Display URLs for all services
	@echo "Proxy:"
	@gcloud functions describe proxy --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null || echo "  Not deployed"
	@echo "Registrar:"
	@gcloud functions describe discord-utils --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null || echo "  Not deployed"
	@echo "User-Manager:"
	@gcloud functions describe user-manager --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null || echo "  Not deployed"
	@echo "Auth Service:"
	@gcloud functions describe discord-auth-service --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null || echo "  Not deployed"
	@echo "API Gateway:"
	@gcloud api-gateway gateways describe $(GATEWAY_ID) --location=$(REGION) --project=$(PROJECT_ID) --format="value(defaultHostname)" 2>/dev/null | sed 's/^/  https:\/\//' || echo "  Not deployed"
	@GATEWAY_URL=$$(gcloud api-gateway gateways describe $(GATEWAY_ID) --location=$(REGION) --project=$(PROJECT_ID) --format="value(defaultHostname)" 2>/dev/null) && \
		if [ ! -z "$$GATEWAY_URL" ]; then \
			echo "OAuth2 endpoints:"; \
			echo "  https://$$GATEWAY_URL/auth/login"; \
			echo "  https://$$GATEWAY_URL/auth/callback"; \
			echo "  https://$$GATEWAY_URL/auth/logout"; \
			echo "  https://$$GATEWAY_URL/auth/verify"; \
		fi

clean: ## Clean temporary files
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name ".DS_Store" -delete 2>/dev/null || true

.DEFAULT_GOAL := help

