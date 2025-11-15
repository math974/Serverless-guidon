# Complete Architecture - Discord Bot with API Gateway

## Overview

```
Discord → API Gateway → Proxy Service → Pub/Sub Topics → Processor Services → Proxy → Discord
```

**Note**: Proxy handles all Discord requests (centralized secrets).

## Components

### 1. **API Gateway** (GCP API Gateway)

- **Role**: Single entry point, traffic management, security
- **URL**: `https://guidon-*.ew.gateway.dev`
- **Endpoints**:
  - `POST /discord/interactions` → Proxy Service
  - `GET /health` → Proxy Service
- **Benefits**:
  - Single stable entry point
  - Traffic management and rate limiting
  - Centralized monitoring
  - No need to expose Cloud Run services directly

### 2. **Proxy Service** (`proxy/`)

- **Role**: Central point for all Discord interactions
- **Cloud Run Service**: `discord-proxy`
- **Secrets**: `DISCORD_PUBLIC_KEY`, `DISCORD_BOT_TOKEN`, `DISCORD_APPLICATION_ID`
- **Functions**:
  - ✅ Verifies Discord signatures (security)
  - ✅ Handles simple commands directly (ping, hello)
  - ✅ Routes complex commands to Pub/Sub
  - ✅ Receives processor responses (`POST /discord/response`)
  - ✅ Sends all responses to Discord (centralized)
- **Pub/Sub Topics used**:
  - `discord-commands-base`: for `/hello`, `/ping`, `/help`
  - `discord-commands-art`: for `/draw`, `/snapshot`
  - `discord-interactions`: for other interactions

### 3. **Pub/Sub Topics** (GCP Pub/Sub)

- **Role**: Asynchronous message queue, service decoupling
- **Topics**:
  - `discord-commands-base` → Processor-Base
  - `discord-commands-art` → Processor-Art
  - `discord-interactions` → (optional, for monitoring)
- **Benefits**:
  - Complete decoupling between Proxy and Processors
  - Automatic scalability
  - Message delivery guarantee
  - Isolation: if one processor crashes, others continue

### 4. **Processor Services** (Cloud Run)

- **Processor-Base** (`processor-base/`)

  - Processes: `/hello`, `/ping`, `/help`
  - Service: `discord-processor-base`
  - Subscription: `discord-commands-base-sub`
  - Secrets: None (proxy handles Discord)
  - Sends responses to proxy via `POST /discord/response`

- **Processor-Art** (`processor-art/`)
  - Processes: `/draw`, `/snapshot`
  - Service: `discord-processor-art`
  - Subscription: `discord-commands-art-sub`
  - Secrets: None (proxy handles Discord)
  - Sends responses to proxy via `POST /discord/response`

## Complete Flow

### Example: `/ping` Command

```
1. Discord user types `/ping`
   ↓
2. Discord sends interaction to API Gateway
   https://guidon-*.ew.gateway.dev/discord/interactions
   ↓
3. API Gateway routes to Proxy Service
   https://discord-proxy-*.run.app/discord/interactions
   ↓
4. Proxy Service :
   - Verifies Discord signature ✓
   - Detects `/ping` (simple command)
   - Responds directly to Discord (Type 4)
   ↓
5. Discord displays response to user
```

### Example: `/help` Command (Complex)

```
1. Discord user types `/help`
   ↓
2. Discord → API Gateway → Proxy Service
   ↓
3. Proxy Service :
   - Verifies signature ✓
   - Detects `/help` (base command)
   - Publishes to topic `discord-commands-base`
   - Responds to Discord (Type 5 - deferred)
   ↓
4. Pub/Sub sends message to Processor-Base
   via subscription `discord-commands-base-sub`
   ↓
5. Processor-Base :
   - Processes `/help` command
   - Generates response
   - Sends response to Proxy (POST /discord/response)
   ↓
6. Proxy receives response and sends to Discord via webhook
   ↓
7. Discord displays response to user
```

### Example: `/draw` Command

```
1. Discord user types `/draw x:10 y:20 color:#FF0000`
   ↓
2. Discord → API Gateway → Proxy Service
   ↓
3. Proxy Service :
   - Verifies signature ✓
   - Detects `/draw` (art command)
   - Publishes to topic `discord-commands-art`
   - Responds to Discord (Type 5 - deferred)
   ↓
4. Pub/Sub sends to Processor-Art
   ↓
5. Processor-Art :
   - Processes `/draw` command
   - (Drawing logic here)
   - Sends response to Proxy (POST /discord/response)
   ↓
6. Proxy receives response and sends to Discord via webhook
   ↓
7. Discord displays response
```

## Isolation and Resilience

### If Processor-Art crashes:

- ✅ Processor-Base continues to work
- ✅ Commands `/ping`, `/hello`, `/help` still work
- ✅ Only `/draw` and `/snapshot` commands are affected

### If Processor-Base crashes:

- ✅ Processor-Art continues to work
- ✅ Commands `/draw` and `/snapshot` still work
- ✅ Only base commands are affected

### If Proxy Service crashes:

- ❌ No commands work (single entry point)
- ✅ But messages in Pub/Sub are preserved
- ✅ Once Proxy restarts, messages are processed

## Deployment

### Recommended order:

1. **Create Pub/Sub topics**

   ```bash
   ./scripts/setup-pubsub.sh
   ```

2. **Deploy Proxy Service**

   ```bash
   ./scripts/deploy-proxy.sh
   ```

3. **Deploy Processor Services**

   ```bash
   ./scripts/deploy-processor-base.sh
   ./scripts/deploy-processor-art.sh
   ```

4. **Create Pub/Sub subscriptions**

   ```bash
   # After retrieving processor URLs
   gcloud pubsub subscriptions create discord-commands-base-sub \
     --topic=discord-commands-base \
     --push-endpoint=<PROCESSOR_BASE_URL>/ \
     --project=$PROJECT_ID

   gcloud pubsub subscriptions create discord-commands-art-sub \
     --topic=discord-commands-art \
     --push-endpoint=<PROCESSOR_ART_URL>/ \
     --project=$PROJECT_ID
   ```

5. **Configure API Gateway**

   ```bash
   ./scripts/update-gateway-proxy.sh
   ```

6. **Configure Discord**
   - Set API Gateway URL in Discord settings
   - `https://guidon-*.ew.gateway.dev/discord/interactions`

## Architecture Benefits

1. **Complete Isolation**: Each service can crash without affecting others
2. **Scalability**: Each service scales independently
3. **Maintenance**: Update one service without affecting others
4. **Security**: API Gateway as single entry point
5. **Reliability**: Pub/Sub guarantees message delivery
6. **Monitoring**: Each service can be monitored separately
7. **Secret Centralization**: All Discord secrets in proxy service
