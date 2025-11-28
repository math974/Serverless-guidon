# Discord Bot Serverless on GCP

A serverless Discord bot with web interface deployed on Google Cloud Platform using Cloud Functions Gen2, API Gateway, and a microservices architecture.

## Architecture Overview

```
Discord/Web → API Gateway → Proxy Service → Pub/Sub Topics → Processor Services → Webhooks (Discord/Web)
```

**Microservices Architecture**: Specialized services for each command type with separation of concerns.

See [ARCHITECTURE.md](ARCHITECTURE.md) for complete architecture documentation.

## Services

### Core Services

- **proxy**: Entry point for Discord and web interactions
- **user-manager**: User management, rate limiting, statistics
- **canvas-service**: Data layer for canvas operations
- **auth-service**: OAuth2 authentication for web clients
- **web-frontend**: Web interface for canvas

### Processor Services (Microservices)

- **processor-base**: Base commands (ping, hello, help)
- **processor-draw**: Draw pixels on canvas
- **processor-snapshot**: Create canvas snapshots
- **processor-canvas-state**: Get canvas state as JSON
- **processor-stats**: Canvas and user statistics
- **processor-colors**: List available colors
- **processor-pixel-info**: Get pixel information

### Utility Services

- **discord-utils**: Register Discord slash commands

## Prerequisites

1. Google Cloud Platform account with billing enabled
2. Discord Developer Account
3. gcloud CLI installed and configured
4. Python 3.11+
5. jq (for JSON processing)

## Quick Start

### 1. Configure Project

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
export REGION="europe-west1"
export API_ID="guidon-api"
export GATEWAY_ID="guidon"

# Or edit Makefile defaults
```

### 2. Setup GCP Resources

```bash
# Setup all base resources (APIs, Pub/Sub, Firestore, GCS)
make setup-all
```

### 3. Create Secrets

Create all required secrets in GCP Secret Manager. See `configs/gcp-secrets.json` for complete list:

```bash
# Required secrets:
# - DISCORD_PUBLIC_KEY
# - DISCORD_BOT_TOKEN
# - DISCORD_APPLICATION_ID
# - DISCORD_CLIENT_ID (for OAuth2)
# - DISCORD_CLIENT_SECRET (for OAuth2)
# - DISCORD_REDIRECT_URI (for OAuth2)
# - WEB_FRONTEND_URL (for OAuth2)

# Example:
echo -n "your_discord_public_key" | gcloud secrets create DISCORD_PUBLIC_KEY \
  --data-file=- --project=$PROJECT_ID
```

### 4. Deploy Services

```bash
# Deploy all services in correct order
make deploy-all

# Or deploy individually:
make deploy-user-manager
make deploy-canvas-service
make deploy-proxy
make deploy-web-frontend
make deploy-auth
make deploy-registrar
make deploy-processors
```

### 5. Configure API Gateway

```bash
# Update API Gateway configuration
make update-gateway
```

### 6. Register Discord Commands

```bash
# Register all commands
make register-commands

# Or register specific command
make register-command CMD=draw
```

### 7. Configure Discord

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application
3. Go to "General Information" > "Interactions Endpoint URL"
4. Set: `https://guidon-*.ew.gateway.dev/discord/interactions`
   (Replace `*` with your actual gateway ID)

## Available Make Commands

### Setup Commands

- `make setup-all` - Setup all GCP resources (APIs, Pub/Sub, Firestore, GCS)
- `make setup-apis` - Enable all required GCP APIs
- `make setup-pubsub` - Create Pub/Sub topics
- `make setup-firestore` - Create Firestore database
- `make setup-gcs` - Create GCS bucket

### Deployment Commands

- `make deploy-all` - Deploy all services
- `make deploy-proxy` - Deploy proxy service
- `make deploy-user-manager` - Deploy user-manager service
- `make deploy-canvas-service` - Deploy canvas-service
- `make deploy-web-frontend` - Deploy web frontend
- `make deploy-auth` - Deploy auth service
- `make deploy-registrar` - Deploy Discord command registrar
- `make deploy-processors` - Deploy all processor services
- `make deploy-processor-draw` - Deploy processor-draw service
- `make deploy-processor-snapshot` - Deploy processor-snapshot service
- `make deploy-processor-canvas-state` - Deploy processor-canvas-state service
- `make deploy-processor-stats` - Deploy processor-stats service
- `make deploy-processor-colors` - Deploy processor-colors service
- `make deploy-processor-pixel-info` - Deploy processor-pixel-info service
- `make deploy-processor-base` - Deploy processor-base service

### Configuration Commands

- `make update-gateway` - Update API Gateway configuration
- `make register-commands` - Register all Discord commands
- `make register-command CMD=draw` - Register specific command

### Utility Commands

- `make prepare-services` - Prepare services (copy shared/)
- `make test-health` - Test health endpoints for all services
- `make test-user-manager` - Test user-manager service
- `make test-web` - Test web endpoints
- `make urls` - Display URLs for all services
- `make clean` - Clean temporary files

### Logging Commands

- `make logs-proxy` - Show proxy service logs
- `make logs-user-manager` - Show user-manager logs
- `make logs-canvas-service` - Show canvas-service logs
- `make logs-processor-draw` - Show processor-draw logs
- `make logs-all` - Show logs for all services

See `make help` for complete list.

## Project Structure

```
.
├── services/
│   ├── proxy/              # Proxy service (entry point)
│   ├── user-manager/       # User management service
│   ├── canvas-service/     # Canvas data layer
│   ├── auth-service/       # OAuth2 authentication
│   ├── discord-registrar/  # Command registrar
│   ├── processor-base/     # Base commands processor
│   ├── processor-draw/     # Draw command processor
│   ├── processor-snapshot/ # Snapshot command processor
│   ├── processor-canvas-state/ # Canvas state processor
│   ├── processor-stats/    # Stats command processor
│   ├── processor-colors/   # Colors command processor
│   ├── processor-pixel-info/ # Pixel info processor
│   └── shared/             # Shared code (clients, utils)
├── web-frontend/           # Web interface (App Engine)
│   ├── main.py             # Main application
│   ├── app.yaml            # App Engine configuration
│   ├── template/           # HTML templates
│   ├── js/                 # JavaScript files
│   ├── css/                # CSS files
│   └── shared/             # Shared code
├── scripts/                # Deployment scripts
├── configs/                # Configuration files (JSON)
│   ├── gcp-apis.json       # GCP APIs to enable
│   ├── gcp-secrets.json    # Secrets configuration
│   ├── pubsub-topics.json  # Pub/Sub topics
│   ├── services-config.json # Services configuration
│   └── openapi2-run.yaml   # API Gateway configuration
├── Makefile                # Main deployment commands
├── ARCHITECTURE.md         # Complete architecture documentation
└── README.md              # This file
```

## Configuration Files

All GCP resources are defined in JSON configuration files:

- `configs/gcp-apis.json` - GCP APIs to enable
- `configs/gcp-secrets.json` - Secrets configuration
- `configs/pubsub-topics.json` - Pub/Sub topics
- `configs/firestore-database.json` - Firestore database
- `configs/gcs-bucket.json` - GCS bucket configuration
- `configs/services-config.json` - Services configuration
- `configs/iam-permissions.json` - IAM permissions documentation

## Testing

### Test Health Endpoints

```bash
make test-health
```

### Test User Manager

```bash
make test-user-manager
```

### Test Web Endpoints

```bash
make test-web
```

### View Service URLs

```bash
make urls
```

## Monitoring

### View Logs

```bash
# View logs for specific service
make logs-proxy
make logs-processor-draw

# View all logs
make logs-all
```

### GCP Console

- **Cloud Functions**: Monitor function invocations, errors, latency
- **API Gateway**: Monitor API requests, errors, latency
- **Pub/Sub**: Monitor message throughput, subscriptions
- **Firestore**: Monitor database operations
- **Cloud Storage**: Monitor bucket usage

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check Discord public key in secrets
2. **403 Forbidden**: Check IAM permissions for private services
3. **Function timeout**: Increase timeout in deployment script
4. **ModuleNotFoundError**: Ensure `shared/` directory is copied (run `make prepare-services`)
5. **Eventarc trigger not working**: Check Eventarc permissions (`make grant-eventarc-permissions`)

### Debug Commands

```bash
# Check service status
gcloud functions describe proxy --gen2 --region=europe-west1 --project=$PROJECT_ID

# View recent logs
gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=proxy" \
  --project=$PROJECT_ID --limit=50

# Check API Gateway
gcloud api-gateway gateways describe guidon --location=europe-west1 --project=$PROJECT_ID

# Check Pub/Sub topics
gcloud pubsub topics list --project=$PROJECT_ID
```

## Architecture Benefits

1. **Complete Isolation**: Each service can crash without affecting others
2. **Scalability**: Each service scales independently
3. **Maintenance**: Update one service without affecting others
4. **Security**: API Gateway as single entry point, private services with IAM
5. **Reliability**: Pub/Sub guarantees message delivery
6. **Monitoring**: Each service can be monitored separately
7. **Specialized Microservices**: Each command has its own service
8. **Dedicated Data Layer**: Canvas-service as single source of truth

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Complete architecture documentation
- [configs/](configs/) - Configuration files with documentation
