# Serverless Discord Bot - GCP Architecture

A modular, serverless Discord bot built on Google Cloud Platform using API Gateway, Cloud Run, and Pub/Sub.

## Architecture Overview

```
Discord → API Gateway → Proxy Service → Pub/Sub Topics → Processor Services → Proxy → Discord
```

**Key Features:**

- Centralized Discord API interaction in proxy service
- Event-driven architecture with Pub/Sub
- Separate processors for different command categories
- Secrets managed directly in GCP Secret Manager

## Quick Start

### 1. Setup Secrets in GCP Secret Manager

Create the required secrets in GCP Secret Manager:

```bash
# Discord Public Key
echo -n "your-discord-public-key" | gcloud secrets create DISCORD_PUBLIC_KEY \
  --data-file=- \
  --replication-policy="automatic" \
  --project=YOUR_PROJECT_ID

# Discord Bot Token
echo -n "your-discord-bot-token" | gcloud secrets create DISCORD_BOT_TOKEN \
  --data-file=- \
  --replication-policy="automatic" \
  --project=YOUR_PROJECT_ID

# Discord Application ID
echo -n "your-discord-application-id" | gcloud secrets create DISCORD_APPLICATION_ID \
  --data-file=- \
  --replication-policy="automatic" \
  --project=YOUR_PROJECT_ID
```

Or use the [GCP Console](https://console.cloud.google.com/security/secret-manager).

**Required secrets:**

- `DISCORD_PUBLIC_KEY` - Discord public key for signature verification
- `DISCORD_BOT_TOKEN` - Discord bot token
- `DISCORD_APPLICATION_ID` - Discord application ID

### 2. Grant Access to Cloud Run

Grant the Cloud Run service account access to the secrets:

```bash
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for secret in DISCORD_PUBLIC_KEY DISCORD_BOT_TOKEN DISCORD_APPLICATION_ID; do
  gcloud secrets add-iam-policy-binding "${secret}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --project=YOUR_PROJECT_ID
done
```

### 3. Deploy Services

Deploy all services in order:

```bash
# Create Pub/Sub topics
./scripts/setup-pubsub.sh

# Deploy proxy service
./scripts/deploy-proxy.sh

# Deploy processor services
./scripts/deploy-processor-base.sh
./scripts/deploy-processor-art.sh

# Deploy registrar service
./scripts/deploy-registrar.sh
```

Or use the all-in-one script:

```bash
./scripts/deploy-all.sh
```

### 4. Register Discord Commands

After deploying the registrar service:

```bash
# Register all commands (recommended)
./scripts/register-commands.sh

# Or register a specific command
./scripts/register-commands.sh hello

# Or manually using curl
REGISTRAR_URL=$(gcloud run services describe discord-registrar \
  --region=europe-west1 \
  --format="value(status.url)")
curl -X POST ${REGISTRAR_URL}/register
```

### 5. Configure API Gateway

Update the API Gateway to point to your proxy service:

```bash
./scripts/update-gateway-proxy.sh
```

### 6. Configure Discord

Set the API Gateway URL in your Discord application settings:

- Interaction URL: `https://guidon-*.ew.gateway.dev/discord/interactions`

## Project Structure

```
.
├── .env                    # Local secrets (not in git)
├── .env.example            # Template for .env
├── services/               # All Cloud Run services
│   ├── proxy/              # Proxy service (handles all Discord requests)
│   │   ├── main.py         # Flask routes
│   │   ├── config.py       # Configuration
│   │   ├── discord_utils.py
│   │   ├── command_handler.py
│   │   ├── interaction_handler.py
│   │   ├── pubsub_utils.py
│   │   └── response_utils.py
│   ├── processor-base/     # Base commands processor (ping, hello, help)
│   ├── processor-art/      # Art commands processor (draw, snapshot)
│   └── discord-registrar/  # Command registration service
├── scripts/                # Deployment and setup scripts
│   ├── sync-secrets-from-env.sh  # Sync .env to GCP Secret Manager
│   ├── deploy-proxy.sh
│   ├── deploy-processor-base.sh
│   ├── deploy-processor-art.sh
│   ├── deploy-registrar.sh
│   ├── register-commands.sh      # Register Discord commands
│   └── deploy-all.sh
└── configs/
    └── openapi2-run.yaml   # API Gateway configuration
```

## Services

### Proxy Service (`discord-proxy`)

- **Role**: Central point for all Discord interactions
- **Secrets**: All Discord secrets (PUBLIC_KEY, BOT_TOKEN, APPLICATION_ID)
- **Responsibilities**:
  - Discord signature verification
  - Simple command handling (ping, hello)
  - Routing complex commands to Pub/Sub
  - Receiving processor responses
  - Sending all responses to Discord

### Processor-Base (`discord-processor-base`)

- **Role**: Process base commands
- **Commands**: `/hello`, `/ping`, `/help`
- **Secrets**: None (proxy handles Discord)

### Processor-Art (`discord-processor-art`)

- **Role**: Process art-related commands
- **Commands**: `/draw`, `/snapshot`
- **Secrets**: None (proxy handles Discord)

### Discord-Registrar (`discord-registrar`)

- **Role**: Register Discord slash commands
- **Secrets**: DISCORD_BOT_TOKEN, DISCORD_APPLICATION_ID
- **Endpoints**:
  - `POST /register` - Register all commands
  - `POST /register/<command>` - Register specific command
  - `GET /commands` - List all commands

## Registering Commands

### Using the CLI Script (Recommended)

```bash
# Register all commands
./scripts/register-commands.sh

# Register a specific command
./scripts/register-commands.sh hello
./scripts/register-commands.sh ping
./scripts/register-commands.sh draw
```

### Using curl Directly

```bash
# Get registrar URL
REGISTRAR_URL=$(gcloud run services describe discord-registrar \
  --region=europe-west1 \
  --format="value(status.url)")

# Register all commands
curl -X POST ${REGISTRAR_URL}/register

# Register a specific command
curl -X POST ${REGISTRAR_URL}/register/hello

# List all defined commands
curl ${REGISTRAR_URL}/commands
```

### Available Commands

**Base Commands:**

- `/hello` - RATP service greeting
- `/ping` - Test bot latency
- `/help` - Show available commands

**Art Commands:**

- `/draw` - Draw a pixel on the canvas (requires: x, y, color)
- `/snapshot` - Take a snapshot of the current canvas

## Secret Management

### Using .env File (Recommended)

1. Create `.env` from template:

   ```bash
   cp .env.example .env
   ```

2. Fill in your Discord secrets in `.env`

3. Sync to GCP:
   ```bash
   ./scripts/sync-secrets-from-env.sh
   ```

### Manual Secret Creation

Alternatively, use the interactive script:

```bash
./scripts/setup-secrets.sh
```

## Environment Variables

### Local Development

- Use `.env` file (not committed to git)

### Cloud Run Services

- Secrets are loaded from GCP Secret Manager
- Automatically injected as environment variables

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Complete architecture documentation
- [ARCHITECTURE_FLOW.md](ARCHITECTURE_FLOW.md) - Detailed flow diagrams

## Deployment Workflow

1. **Ensure secrets exist in GCP Secret Manager**:

   ```bash
   # Verify secrets exist
   gcloud secrets list --project=YOUR_PROJECT_ID
   ```

2. **Deploy services**:

   ```bash
   ./scripts/deploy-all.sh
   ```

3. **Register commands**:

   ```bash
   ./scripts/register-commands.sh
   ```

4. **Update API Gateway**:
   ```bash
   ./scripts/update-gateway-proxy.sh
   ```

## Troubleshooting

### Secrets not found

- Ensure all required secrets exist in GCP Secret Manager
- Verify secrets are accessible by the Cloud Run service account
- Check IAM permissions: `gcloud secrets get-iam-policy SECRET_NAME --project=YOUR_PROJECT_ID`

### Service deployment fails

- Check that secrets exist in GCP Secret Manager
- Verify PROJECT_ID and REGION are correct

### Commands not working

- Verify commands are registered: `curl <REGISTRAR_URL>/commands`
- Check API Gateway URL is set in Discord settings
- Verify proxy service is deployed and accessible
