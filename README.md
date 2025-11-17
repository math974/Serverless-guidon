# Discord Bot Serverless on GCP

A serverless Discord bot deployed on Google Cloud Platform using Cloud Functions and API Gateway.

## Prerequisites

1. Google Cloud Platform account with billing enabled
2. Discord Developer Account
3. gcloud CLI installed and configured

## Setup

### 1. GCP Configuration

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable apigateway.googleapis.com
gcloud services enable servicecontrol.googleapis.com
gcloud services enable servicemanagement.googleapis.com
```

### 2. Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the Public Key from "General Information"
5. Go to "OAuth2" > "URL Generator" and select:
   - Scope: `applications.commands`
   - Bot Permissions: `Send Messages`

### 3. Environment Configuration

```bash
# Copy environment template
cp helloworld/.env.example helloworld/.env

# Edit .env with your Discord public key
DISCORD_PUBLIC_KEY=your_actual_discord_public_key
```

## Deployment

### Option 1: Cloud Functions Only

```bash
# Make deploy script executable
chmod +x deploy.sh

# Edit deploy.sh with your configuration
# Then deploy
./deploy.sh
```

### Option 2: With API Gateway

```bash
# First deploy the function
./deploy.sh

# Update openapi2-run.yaml with your function URL
# Then deploy API Gateway
chmod +x deploy-gateway.sh
./deploy-gateway.sh
```

## Discord Slash Commands Registration

After deployment, register your slash commands:

```bash
# Install discord.py for command registration
pip install discord.py

# Run command registration script
python register_commands.py
```

## Testing

1. Invite your bot to a Discord server using the OAuth2 URL
2. Use `/hello` or `/ping` commands to test
3. Check GCP Console for logs and monitoring

## Monitoring

- **Logs**: `gcloud functions logs read discord-bot --region=europe-west1`
- **Metrics**: GCP Console > Cloud Functions > discord-bot

## Costs

- Cloud Functions: ~$0.40 per million requests
- API Gateway: ~$3.00 per million API calls
- Typical small bot: <$1/month

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check Discord public key in environment variables
2. **Function timeout**: Increase timeout in deploy.sh
3. **Discord verification failed**: Ensure webhook URL is correct

### Debug Commands

```bash
# Check function status
gcloud functions describe discord-bot --region=europe-west1

# View recent logs
gcloud functions logs read discord-bot --region=europe-west1 --limit=50

# Test function locally
functions-framework --target=discord_bot --debug
```
