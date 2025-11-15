# Complete Architecture - Processing Flow

## Main Flow Diagram

### Discord Bot Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DISCORD BOT INTERACTION                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY (GCP)                                   │
│  • Single entry point                                                        │
│  • URL: https://guidon-*.ew.gateway.dev                                     │
│  • Endpoints:                                                                │
│    - POST /discord/interactions (Discord bot)                                │
│    - POST /web/interactions (Web clients)                                    │
│    - GET /health                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROXY SERVICE (Cloud Run)                            │
│  Service: discord-proxy                                                      │
│  Secrets: DISCORD_PUBLIC_KEY, DISCORD_BOT_TOKEN, DISCORD_APPLICATION_ID     │
│                                                                              │
│  Steps:                                                                      │
│  1. ✅ Verify Discord signature (DISCORD_PUBLIC_KEY)                       │
│  2. ✅ Parse interaction                                                     │
│  3. ✅ Handle simple commands directly (ping, hello)                        │
│  4. ✅ For complex commands → Publish to Pub/Sub                            │
│  5. ✅ Respond immediately to Discord (type 5 - deferred)                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
          ┌─────────▼─────────┐         ┌─────────▼─────────┐
          │  SIMPLE COMMANDS   │         │  COMPLEX COMMANDS │
          │  (ping, hello)     │         │  (help, draw, etc)│
          │                   │         │                    │
          │  Direct response  │         │  Type 5 (deferred) │
          │  Type 4           │         │  + Pub/Sub         │
          └───────────────────┘         └────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PUB/SUB TOPICS (GCP)                                │
│                                                                              │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐          │
│  │ discord-commands-base       │  │ discord-commands-art        │          │
│  │ • hello                     │  │ • draw                      │          │
│  │ • ping                      │  │ • snapshot                 │          │
│  │ • help                      │  │                            │          │
│  └─────────────────────────────┘  └─────────────────────────────┘          │
│            │                                    │                           │
│            │                                    │                           │
│            ▼                                    ▼                           │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐          │
│  │ discord-commands-base-sub   │  │ discord-commands-art-sub    │          │
│  │ (Push Subscription)         │  │ (Push Subscription)         │          │
│  └─────────────────────────────┘  └─────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
            │                                    │
            │                                    │
            ▼                                    ▼
┌─────────────────────────────┐  ┌─────────────────────────────┐
│  PROCESSOR-BASE (Cloud Run)  │  │  PROCESSOR-ART (Cloud Run)  │
│  Service: discord-processor- │  │  Service: discord-processor- │
│            base              │  │            art               │
│  Secrets: NONE              │  │  Secrets: NONE              │
│                              │  │                              │
│  Steps:                      │  │  Steps:                      │
│  1. Receive Pub/Sub message   │  │  1. Receive Pub/Sub message   │
│  2. Decode interaction       │  │  2. Decode interaction       │
│  3. Process command          │  │  3. Process command          │
│     via CommandHandler       │  │     via CommandHandler       │
│  4. Send response to Proxy   │  │  4. Send response to Proxy   │
│     (POST /discord/response) │  │     (POST /discord/response) │
└─────────────────────────────┘  └─────────────────────────────┘
            │                                    │
            │                                    │
            └──────────────┬─────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROXY SERVICE (return)                               │
│  Endpoint: POST /discord/response                                            │
│                                                                              │
│  Steps:                                                                      │
│  1. Receive response from processor                                          │
│  2. Send response to Discord via webhook                                    │
│     (uses DISCORD_BOT_TOKEN)                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DISCORD                                        │
│  User receives bot response                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Web Client Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           WEB CLIENT INTERACTION                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY (GCP)                                   │
│  Endpoint: POST /web/interactions                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROXY SERVICE (Cloud Run)                            │
│  Service: discord-proxy                                                      │
│                                                                              │
│  Steps:                                                                      │
│  1. ✅ Parse JSON request (no signature verification)                       │
│  2. ✅ Handle simple commands directly (ping, hello, help)                  │
│  3. ✅ For complex commands → Publish to Pub/Sub                            │
│  4. ✅ Return JSON response (immediate or 202 Accepted)                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
          ┌─────────▼─────────┐         ┌─────────▼─────────┐
          │  SIMPLE COMMANDS   │         │  COMPLEX COMMANDS │
          │  (ping, hello,     │         │  (draw, snapshot) │
          │   help)            │         │                    │
          │                   │         │                    │
          │  Direct JSON      │         │  202 Accepted      │
          │  response (200)   │         │  + Pub/Sub         │
          └───────────────────┘         └────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PUB/SUB TOPICS (GCP)                                │
│  Same topics as Discord flow                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PROCESSOR SERVICES (Cloud Run)                            │
│  Same processors as Discord flow                                            │
│                                                                              │
│  Steps:                                                                      │
│  1. Receive Pub/Sub message                                                  │
│  2. Process command                                                          │
│  3. Send response to Proxy                                                   │
│     (POST /web/response for web interactions)                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROXY SERVICE (return)                               │
│  Endpoint: POST /web/response                                               │
│                                                                              │
│  Steps:                                                                      │
│  1. Receive response from processor                                          │
│  2. Convert to web format (JSON)                                             │
│  3. Return JSON response                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              WEB CLIENT                                      │
│  Receives JSON response                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Detailed Flow by Command Type

### 1. Simple Command (ping, hello, help) - < 1 second

#### Discord Flow

```
Discord → API Gateway → Proxy
                          │
                          ├─► Verify signature
                          ├─► Process directly
                          └─► Respond to Discord (Type 4)
```

#### Web Flow

```
Web Client → API Gateway → Proxy
                              │
                              ├─► Parse JSON
                              ├─► Process directly
                              └─► Return JSON (200 OK)
```

**Total time: < 1 second**

### 2. Complex Command (draw, snapshot) - < 3 seconds

#### Discord Flow

```
Discord → API Gateway → Proxy
                          │
                          ├─► Verify signature
                          ├─► Publish to Pub/Sub
                          └─► Respond to Discord (Type 5 - deferred)
                                 │
                                 ▼
                          Pub/Sub Topic
                                 │
                                 ▼
                          Processor Service
                                 │
                          ├─► Process command
                          └─► POST /discord/response → Proxy
                                 │
                                 ▼
                          Proxy → Discord (webhook)
```

#### Web Flow

```
Web Client → API Gateway → Proxy
                              │
                              ├─► Parse JSON
                              ├─► Publish to Pub/Sub
                              └─► Return 202 Accepted
                                     │
                                     ▼
                              Pub/Sub Topic
                                     │
                                     ▼
                              Processor Service
                                     │
                              ├─► Process command
                              └─► POST /web/response → Proxy
                                     │
                                     ▼
                              Proxy → Return JSON to client
```

**Total time:**

- **Discord**: Initial response < 3 seconds (Type 5), Final response up to 15 minutes (via webhook)
- **Web**: Initial response < 3 seconds (202 Accepted), Final response via async callback

## Components and Responsibilities

### API Gateway

- **Role**: Single entry point, traffic management
- **URL**: `https://guidon-*.ew.gateway.dev`
- **Endpoints**:
  - `POST /discord/interactions` → Proxy (Discord bot)
  - `POST /web/interactions` → Proxy (Web clients)
  - `GET /health` → Proxy

### Proxy Service

- **Service**: `discord-proxy`
- **Secrets**: `DISCORD_PUBLIC_KEY`, `DISCORD_BOT_TOKEN`, `DISCORD_APPLICATION_ID`
- **Responsibilities**:
  - ✅ Discord signature verification (for Discord interactions)
  - ✅ Simple command handling (ping, hello, help) - both Discord and Web
  - ✅ Publishing to Pub/Sub for complex commands
  - ✅ Receiving processor responses (Discord and Web)
  - ✅ Sending all responses to Discord (webhook)
  - ✅ Returning JSON responses to Web clients

### Pub/Sub Topics

- **discord-commands-base**: Base commands (hello, ping, help)
- **discord-commands-art**: Art commands (draw, snapshot)

### Processor-Base

- **Service**: `discord-processor-base`
- **Secrets**: None
- **Responsibilities**:
  - Process base commands
  - Send responses to proxy

### Processor-Art

- **Service**: `discord-processor-art`
- **Secrets**: None
- **Responsibilities**:
  - Process art commands
  - Send responses to proxy

### Discord-Registrar

- **Service**: `discord-registrar`
- **Secrets**: `DISCORD_BOT_TOKEN`, `DISCORD_APPLICATION_ID`
- **Responsibilities**:
  - Register Discord commands
  - Can be called manually or via Cloud Scheduler

## Timeline Sequence

### Simple Command (ping)

```
T+0ms    : Discord sends interaction
T+50ms   : API Gateway receives
T+100ms  : Proxy verifies signature
T+150ms  : Proxy processes ping
T+200ms  : Proxy responds to Discord (Type 4)
T+250ms  : Discord displays response
```

### Complex Command (help)

```
T+0ms    : Discord sends interaction
T+50ms   : API Gateway receives
T+100ms  : Proxy verifies signature
T+150ms  : Proxy publishes to Pub/Sub
T+200ms  : Proxy responds to Discord (Type 5 - deferred)
T+250ms  : Discord displays "Bot is thinking..."
T+500ms  : Pub/Sub pushes to Processor
T+600ms  : Processor processes command
T+800ms  : Processor sends response to Proxy
T+900ms  : Proxy sends to Discord (webhook)
T+1000ms : Discord displays final response
```

## Secret Management

```
┌─────────────────────────────────────────────────────────┐
│              SECRET MANAGER (GCP)                       │
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │ discord-public-  │  │ discord-bot-     │            │
│  │ key              │  │ token            │            │
│  └──────────────────┘  └──────────────────┘            │
│                                                          │
│  ┌──────────────────┐                                   │
│  │ discord-         │                                   │
│  │ application-id   │                                   │
│  └──────────────────┘                                   │
└─────────────────────────────────────────────────────────┘
            │                    │                    │
            │                    │                    │
            ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  PROXY           │  │  REGISTRAR       │  │  PROCESSORS      │
│  ✅ All secrets  │  │  ✅ BOT_TOKEN    │  │  ❌ No Discord   │
│                  │  │  ✅ APP_ID       │  │     secrets      │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

## Available Endpoints

### API Gateway

- `POST /discord/interactions` - Discord bot interactions
- `POST /web/interactions` - Web client interactions
- `GET /health` - Health check

### Proxy Service

- `POST /discord/interactions` - Receives Discord interactions (with signature verification)
- `POST /web/interactions` - Receives web client interactions (no signature verification)
- `POST /discord/response` - Receives processor responses for Discord
- `POST /web/response` - Receives processor responses for web clients
- `GET /health` - Health check

### Processor Services

- `POST /` - Receives Pub/Sub messages (push subscription)
- `GET /health` - Health check

### Registrar Service

- `POST /register` - Register all commands
- `POST /register/<command_name>` - Register specific command
- `GET /commands` - List all defined commands
- `GET /health` - Health check

## Architecture Benefits

1. **Secret Centralization**: All Discord secrets in proxy
2. **Separation of Concerns**: Each service has a clear role
3. **Scalability**: Processors can scale independently
4. **Decoupling**: Pub/Sub enables service isolation
5. **Security**: Signature verification at entry point (Discord only)
6. **Performance**: Simple commands respond in < 1 second
7. **Unified Interface**: Same command processing for Discord and Web clients
8. **Flexibility**: Web clients can use same commands without Discord-specific requirements
