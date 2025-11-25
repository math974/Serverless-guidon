.PHONY: help deploy-all deploy-proxy deploy-processor-base deploy-registrar deploy-auth deploy-user-manager deploy-canvas-service deploy-web-frontend deploy-processor-draw deploy-processor-snapshot deploy-processor-canvas-state deploy-processor-stats deploy-processor-colors deploy-processor-pixel-info setup-apis setup-pubsub setup-microservices-pubsub setup-firestore setup-gcs setup-all grant-eventarc-permissions register-commands update-gateway prepare-services test-health test-user-manager clean

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

setup-apis: ## Enable all required GCP APIs
	@echo "Enabling GCP APIs..."
	@jq -r '.apis[].name' configs/gcp-apis.json | while read api; do \
		echo "  Enabling $$api..."; \
		gcloud services enable "$$api" --project=$(PROJECT_ID) 2>&1 | grep -v "already enabled" || true; \
	done
	@echo "APIs enabled!"

setup-pubsub: ## Setup Pub/Sub topics and subscriptions
	@PROJECT_ID=$(PROJECT_ID) $(SCRIPTS_DIR)/setup-pubsub.sh

setup-microservices-pubsub: ## Setup microservices Pub/Sub topics and subscriptions
	@PROJECT_ID=$(PROJECT_ID) $(SCRIPTS_DIR)/setup-microservices-pubsub.sh

setup-firestore: ## Create Firestore database
	@echo "Creating Firestore database..."
	@DB_NAME=$$(jq -r '.database.name' configs/firestore-database.json); \
	gcloud firestore databases create \
		--database="$$DB_NAME" \
		--location=$(REGION) \
		--type=firestore-native \
		--project=$(PROJECT_ID) \
		2>&1 || echo "Database may already exist or creation in progress"

setup-gcs: ## Create GCS bucket for snapshots
	@echo "Creating GCS bucket..."
	@BUCKET_NAME=$$(jq -r '.bucket.name' configs/gcs-bucket.json); \
	gsutil mb -p $(PROJECT_ID) -l $(REGION) "gs://$$BUCKET_NAME" 2>&1 | grep -v "already exists" || echo "Bucket may already exist"; \
	echo "Bucket created: gs://$$BUCKET_NAME"

setup-all: ## Setup all GCP resources (APIs, Pub/Sub, Firestore, GCS)
	@$(MAKE) setup-apis
	@$(MAKE) setup-pubsub
	@$(MAKE) setup-firestore
	@$(MAKE) setup-gcs
	@echo ""
	@echo "✓ All GCP resources setup complete!"
	@echo "Next: Create secrets manually (see DEPLOYMENT_GUIDE.md)"

grant-eventarc-permissions: ## Grant Eventarc permissions to private services
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/grant-eventarc-permissions.sh

deploy-proxy: prepare-services ## Deploy proxy service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-proxy.sh

deploy-processor-base: prepare-services ## Deploy processor-base service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-processor-base.sh

deploy-registrar: prepare-services ## Deploy registrar service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-registrar.sh

deploy-auth: prepare-services ## Deploy auth service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-auth.sh

deploy-user-manager: prepare-services ## Deploy user-manager service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-user-manager.sh

deploy-canvas-service: prepare-services ## Deploy canvas-service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-canvas-service.sh

deploy-web-frontend: prepare-services ## Deploy web frontend service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-web-frontend.sh

deploy-processor-draw: prepare-services ## Deploy processor-draw service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-processor-draw.sh

deploy-processor-snapshot: prepare-services ## Deploy processor-snapshot service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-processor-snapshot.sh

deploy-processor-canvas-state: prepare-services ## Deploy processor-canvas-state service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-processor-canvas-state.sh

deploy-processor-stats: prepare-services ## Deploy processor-stats service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-processor-stats.sh

deploy-processor-colors: prepare-services ## Deploy processor-colors service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-processor-colors.sh

deploy-processor-pixel-info: prepare-services ## Deploy processor-pixel-info service
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/deploy-processor-pixel-info.sh

deploy-processors: ## Deploy all processor services
	@$(MAKE) deploy-processor-base
	@$(MAKE) deploy-processor-draw
	@$(MAKE) deploy-processor-snapshot
	@$(MAKE) deploy-processor-canvas-state
	@$(MAKE) deploy-processor-stats
	@$(MAKE) deploy-processor-colors
	@$(MAKE) deploy-processor-pixel-info

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
	@echo "Canvas Service:"
	@CANVAS_URL=$$(gcloud functions describe canvas-service --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null) && \
		echo "  $$CANVAS_URL/health" && curl -s $$CANVAS_URL/health | python3 -m json.tool || echo "  Not available"
	@echo "Web Frontend:"
	@WEB_URL=$$(gcloud functions describe web-frontend --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null) && \
		echo "  $$WEB_URL/health" && curl -s $$WEB_URL/health | python3 -m json.tool || echo "  Not available"

test-web: ## Test web endpoints
	@GATEWAY_URL=$$(gcloud api-gateway gateways describe $(GATEWAY_ID) --location=$(REGION) --project=$(PROJECT_ID) --format="value(defaultHostname)" 2>/dev/null) && \
		GATEWAY_URL="https://$$GATEWAY_URL" && \
		$(SCRIPTS_DIR)/test-web-interactions.sh || \
		echo "Gateway not available"

test-user-manager: ## Test user-manager service and stats
	@PROJECT_ID=$(PROJECT_ID) REGION=$(REGION) $(SCRIPTS_DIR)/test-user-manager.sh

logs-proxy: ## Show proxy service logs
	@gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=proxy" \
		--project=$(PROJECT_ID) --limit=50 --format="table(timestamp,severity,jsonPayload.message)" --order=desc

logs-processor-base: ## Show processor-base service logs
	@gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=processor-base" \
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

logs-canvas-service: ## Show canvas-service logs
	@gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=canvas-service" \
		--project=$(PROJECT_ID) --limit=50 --format="table(timestamp,severity,jsonPayload.message)" --order=desc

logs-web-frontend: ## Show web-frontend logs
	@gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=web-frontend" \
		--project=$(PROJECT_ID) --limit=50 --format="table(timestamp,severity,jsonPayload.message)" --order=desc

logs-processor-draw: ## Show processor-draw logs
	@gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=processor-draw" \
		--project=$(PROJECT_ID) --limit=50 --format="table(timestamp,severity,jsonPayload.message)" --order=desc

logs-processor-snapshot: ## Show processor-snapshot logs
	@gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=processor-snapshot" \
		--project=$(PROJECT_ID) --limit=50 --format="table(timestamp,severity,jsonPayload.message)" --order=desc

logs-processor-canvas-state: ## Show processor-canvas-state logs
	@gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=processor-canvas-state" \
		--project=$(PROJECT_ID) --limit=50 --format="table(timestamp,severity,jsonPayload.message)" --order=desc

logs-processor-stats: ## Show processor-stats logs
	@gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=processor-stats" \
		--project=$(PROJECT_ID) --limit=50 --format="table(timestamp,severity,jsonPayload.message)" --order=desc

logs-processor-colors: ## Show processor-colors logs
	@gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=processor-colors" \
		--project=$(PROJECT_ID) --limit=50 --format="table(timestamp,severity,jsonPayload.message)" --order=desc

logs-processor-pixel-info: ## Show processor-pixel-info logs
	@gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=processor-pixel-info" \
		--project=$(PROJECT_ID) --limit=50 --format="table(timestamp,severity,jsonPayload.message)" --order=desc

logs-all: ## Show logs for all services
	@echo "Proxy:"
	@$(MAKE) logs-proxy
	@echo "Processor-Base:"
	@$(MAKE) logs-processor-base
	@echo "Registrar:"
	@$(MAKE) logs-registrar
	@echo "User-Manager:"
	@$(MAKE) logs-user-manager
	@echo "Auth Service:"
	@$(MAKE) logs-auth || echo "  Not deployed"
	@echo "Canvas Service:"
	@$(MAKE) logs-canvas-service || echo "  Not deployed"
	@echo "Web Frontend:"
	@$(MAKE) logs-web-frontend || echo "  Not deployed"
	@echo "Processor-Draw:"
	@$(MAKE) logs-processor-draw || echo "  Not deployed"
	@echo "Processor-Snapshot:"
	@$(MAKE) logs-processor-snapshot || echo "  Not deployed"
	@echo "Processor-Canvas-State:"
	@$(MAKE) logs-processor-canvas-state || echo "  Not deployed"
	@echo "Processor-Stats:"
	@$(MAKE) logs-processor-stats || echo "  Not deployed"
	@echo "Processor-Colors:"
	@$(MAKE) logs-processor-colors || echo "  Not deployed"
	@echo "Processor-Pixel-Info:"
	@$(MAKE) logs-processor-pixel-info || echo "  Not deployed"

urls: ## Display URLs for all services
	@echo "Proxy:"
	@gcloud functions describe proxy --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null || echo "  Not deployed"
	@echo "Registrar:"
	@gcloud functions describe discord-utils --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null || echo "  Not deployed"
	@echo "User-Manager:"
	@gcloud functions describe user-manager --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null || echo "  Not deployed"
	@echo "Auth Service:"
	@gcloud functions describe discord-auth-service --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null || echo "  Not deployed"
	@echo "Canvas Service:"
	@gcloud functions describe canvas-service --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null || echo "  Not deployed"
	@echo "Web Frontend:"
	@gcloud functions describe web-frontend --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null || echo "  Not deployed"
	@echo "Processor-Base:"
	@gcloud functions describe processor-base --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null || echo "  Not deployed"
	@echo "Processor-Draw:"
	@gcloud functions describe processor-draw --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null || echo "  Not deployed"
	@echo "Processor-Snapshot:"
	@gcloud functions describe processor-snapshot --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null || echo "  Not deployed"
	@echo "Processor-Canvas-State:"
	@gcloud functions describe processor-canvas-state --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null || echo "  Not deployed"
	@echo "Processor-Stats:"
	@gcloud functions describe processor-stats --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null || echo "  Not deployed"
	@echo "Processor-Colors:"
	@gcloud functions describe processor-colors --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null || echo "  Not deployed"
	@echo "Processor-Pixel-Info:"
	@gcloud functions describe processor-pixel-info --gen2 --region=$(REGION) --project=$(PROJECT_ID) --format="value(serviceConfig.uri)" 2>/dev/null || echo "  Not deployed"
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

