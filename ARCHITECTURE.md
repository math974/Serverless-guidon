# Complete Architecture - Discord Bot with API Gateway

## Overview

```
Discord/Web → API Gateway → Proxy Service → Pub/Sub Topics → Processor Services → Webhooks (Discord/Web)
```

**Note**: Microservices architecture with separation of concerns and specialized services.

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
│    - GET /auth/* (Auth service)                                              │
│    - GET /* (Web frontend)                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROXY SERVICE (Cloud Functions Gen2)                │
│  Service: proxy                                                              │
│  Authentication: Private (IAM - API Gateway only)                            │
│  Secrets: DISCORD_PUBLIC_KEY, DISCORD_BOT_TOKEN, DISCORD_APPLICATION_ID     │
│                                                                              │
│  Steps:                                                                      │
│  1. Verify Discord signature (DISCORD_PUBLIC_KEY)                         │
│  2. Parse interaction                                                     │
│  3. Handle simple commands directly (ping, hello)                        │
│  4. For complex commands → Publish to Pub/Sub                            │
│  5. Respond immediately to Discord (type 5 - deferred)                   │
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
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ interactions │  │commands-base│  │commands-draw  │  │commands-     │    │
│  │              │  │             │  │              │  │ snapshot     │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │commands-     │  │commands-stats│  │commands-     │  │commands-     │    │
│  │canvas-state  │  │              │  │colors        │  │pixel-info    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                              │
│  All topics trigger Cloud Functions Gen2 via Eventarc                       │
└─────────────────────────────────────────────────────────────────────────────┘
            │                    │                    │
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│  PROCESSOR-BASE      │  │  PROCESSOR-DRAW     │  │  PROCESSOR-*        │
│  (Cloud Functions)   │  │  (Cloud Functions)  │  │  (Cloud Functions)  │
│                      │  │                      │  │                      │
│  Steps:              │  │  Steps:              │  │  Steps:              │
│  1. Receive message   │  │  1. Receive message   │  │  1. Receive message   │
│  2. Process command   │  │  2. Check rate limit  │  │  2. Process command   │
│  3. Send to Discord   │  │     (user-manager)    │  │  3. Call canvas-      │
│     via webhook       │  │  3. Draw pixel         │  │     service           │
│     (direct)          │  │     (canvas-service)   │  │  4. Send to Discord/  │
│                      │  │  4. Increment usage    │  │     Web via webhook   │
│                      │  │     (user-manager)     │  │     (direct)          │
│                      │  │  5. Send to Discord    │  │                      │
│                      │  │     via webhook        │  │                      │
│                      │  │     (direct)           │  │                      │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
            │                    │                    │
            │                    │                    │
            └────────────────────┴────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DISCORD                                        │
│  User receives bot response (via webhook)                                   │
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
│  Headers: Authorization: Bearer <session_token>                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROXY SERVICE (Cloud Functions Gen2)                │
│  Service: proxy                                                              │
│                                                                              │
│  Steps:                                                                      │
│  1. Verify session (auth-service)                                        │
│  2. Parse JSON request                                                   │
│  3. Handle simple commands directly (ping, hello, help)                  │
│  4. For complex commands → Publish to Pub/Sub                            │
│  5. Return JSON response (immediate or 202 Accepted)                    │
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
│  All topics trigger Cloud Functions Gen2 via Eventarc                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PROCESSOR SERVICES (Cloud Functions Gen2)                │
│  Same processors as Discord flow                                            │
│                                                                              │
│  Steps:                                                                      │
│  1. Receive Pub/Sub message (via Eventarc)                                   │
│  2. Process command                                                          │
│  3. Send response to provided webhook URL (direct)                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              WEB CLIENT                                      │
│  Receives JSON response (via webhook callback)                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Services Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA SERVICES                                        │
│                                                                              │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐           │
│  │  CANVAS-SERVICE             │  │  USER-MANAGER               │           │
│  │  (Cloud Functions Gen2)     │  │  (Cloud Functions Gen2)    │           │
│  │  Authentication: Private     │  │  Authentication: Private    │           │
│  │  (Identity Tokens)          │  │  (Identity Tokens)         │           │
│  │                             │  │                             │           │
│  │  REST API:                  │  │  REST API:                  │           │
│  │  • POST /canvas/draw        │  │  • GET /api/users/{id}      │           │
│  │  • GET /canvas/state        │  │  • POST /api/users/{id}/    │           │
│  │  • POST /canvas/snapshot    │  │    increment                │           │
│  │  • GET /canvas/stats        │  │  • POST /api/rate-limit/    │           │
│  │  • GET /canvas/pixel/{x}/{y}│  │    check                    │           │
│  │                             │  │  • GET /api/stats/          │           │
│  │  Storage:                   │  │    leaderboard              │           │
│  │  • Firestore (canvas state) │  │                             │           │
│  │  • GCS (snapshots)          │  │  Storage:                   │           │
│  │                             │  │  • Firestore (users)        │           │
│  └─────────────────────────────┘  └─────────────────────────────┘           │
│                                                                              │
│  ┌─────────────────────────────┐                                            │
│  │  AUTH-SERVICE               │                                            │
│  │  (Cloud Functions Gen2)     │                                            │
│  │  Authentication: Public     │                                            │
│  │                             │                                            │
│  │  REST API:                  │                                            │
│  │  • GET /auth/login          │                                            │
│  │  • GET /auth/callback       │                                            │
│  │  • POST /auth/verify        │                                            │
│  │  • GET /auth/user           │                                            │
│  │  • POST /auth/logout        │                                            │
│  │                             │                                            │
│  │  Storage:                   │                                            │
│  │  • Firestore (sessions)      │                                            │
│  └─────────────────────────────┘                                            │
└─────────────────────────────────────────────────────────────────────────────┘
            ▲                    ▲                    ▲
            │                    │                    │
            │                    │                    │
            └────────────────────┴────────────────────┘
                           │
                           │ (Identity Token Auth)
                           │
            ┌───────────────┴───────────────┐
            │                               │
    ┌───────▼────────┐            ┌─────────▼────────┐
    │  PROCESSORS    │            │  PROXY           │
    │  (via shared   │            │  (for web        │
    │   clients)     │            │   auth)          │
    └────────────────┘            └──────────────────┘
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
                              ├─► Verify session (auth-service)
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
                          Pub/Sub Topic (commands-draw)
                                 │
                                 ▼ (Eventarc trigger)
                          Processor-Draw (Cloud Functions Gen2)
                                 │
                          ├─► Check rate limit (user-manager via identity token)
                          ├─► Draw pixel (canvas-service via identity token)
                          ├─► Increment usage (user-manager via identity token)
                          ├─► Generate response
                          └─► Send directly to Discord via webhook
                                 │
                                 ▼
                          Discord displays response
```

#### Web Flow

```
Web Client → API Gateway → Proxy
                              │
                              ├─► Verify session (auth-service)
                              ├─► Publish to Pub/Sub
                              └─► Return 202 Accepted
                                     │
                                     ▼
                              Pub/Sub Topic (commands-draw)
                                     │
                                     ▼ (Eventarc trigger)
                              Processor-Draw (Cloud Functions Gen2)
                                     │
                              ├─► Process command (same logic as Discord)
                              └─► Send response to provided webhook URL
                                     │
                                     ▼
                              Web client receives response
```

**Total time:**

- **Discord**: Initial response < 3 seconds (Type 5), Final response up to 15 minutes (via webhook)
- **Web**: Initial response < 3 seconds (202 Accepted), Final response via webhook callback

## Components and Responsibilities

### API Gateway

- **Role**: Single entry point, traffic management
- **URL**: `https://guidon-*.ew.gateway.dev`
- **Endpoints**:
  - `POST /discord/interactions` → Proxy (Discord bot)
  - `POST /web/interactions` → Proxy (Web clients)
  - `GET /health` → Proxy
  - `GET /auth/*` → Auth Service
  - `GET /*` → Web Frontend
- **Authentication**: IAM - Only API Gateway service account can invoke proxy

### Proxy Service

- **Service**: `proxy`
- **Authentication**: Private (IAM - API Gateway only)
- **Secrets**: `DISCORD_PUBLIC_KEY`, `DISCORD_BOT_TOKEN`, `DISCORD_APPLICATION_ID`
- **Responsibilities**:
  - Discord signature verification (for Discord interactions)
  - Web session authentication (for web interactions via auth-service)
  - Simple command handling (ping, hello, help) - both Discord and Web
  - Publishing to Pub/Sub for complex commands
  - No longer handles processor responses (processors send directly via webhooks)

### Pub/Sub Topics

- **interactions**: General interactions
- **commands-base**: Base commands (hello, ping, help)
- **commands-draw**: Draw command
- **commands-snapshot**: Snapshot command
- **commands-canvas-state**: Canvas state command
- **commands-stats**: Stats command
- **commands-colors**: Colors command
- **commands-pixel-info**: Pixel info command

### Processor Services

All processors are Cloud Functions Gen2 triggered by Pub/Sub via Eventarc.

#### Processor-Base

- **Service**: `processor-base`
- **Topic**: `commands-base`
- **Secrets**: `DISCORD_BOT_TOKEN` (for Discord webhooks)
- **Responsibilities**:
  - Process base commands (ping, hello, help)
  - Send responses directly to Discord/web via webhooks

#### Processor-Draw

- **Service**: `processor-draw`
- **Topic**: `commands-draw`
- **Secrets**: `DISCORD_BOT_TOKEN`
- **Dependencies**:
  - `canvas-service` (REST API via identity token)
  - `user-manager` (REST API via identity token)
- **Responsibilities**:
  - Check rate limits
  - Draw pixels on canvas
  - Increment user usage
  - Send responses directly to Discord/web via webhooks

#### Processor-Snapshot

- **Service**: `processor-snapshot`
- **Topic**: `commands-snapshot`
- **Secrets**: `DISCORD_BOT_TOKEN`
- **Dependencies**:
  - `canvas-service` (REST API via identity token)
  - `user-manager` (REST API via identity token)
- **Responsibilities**:
  - Create canvas snapshots
  - Send responses directly to Discord/web via webhooks

#### Processor-Canvas-State

- **Service**: `processor-canvas-state`
- **Topic**: `commands-canvas-state`
- **Secrets**: `DISCORD_BOT_TOKEN`
- **Dependencies**:
  - `canvas-service` (REST API via identity token)
- **Responsibilities**:
  - Get canvas state as JSON
  - Send responses directly to Discord/web via webhooks

#### Processor-Stats

- **Service**: `processor-stats`
- **Topic**: `commands-stats`
- **Secrets**: `DISCORD_BOT_TOKEN`
- **Dependencies**:
  - `canvas-service` (REST API via identity token)
  - `user-manager` (REST API via identity token)
- **Responsibilities**:
  - Get canvas and user statistics
  - Send responses directly to Discord/web via webhooks

#### Processor-Colors

- **Service**: `processor-colors`
- **Topic**: `commands-colors`
- **Secrets**: `DISCORD_BOT_TOKEN`
- **Dependencies**: None (stateless)
- **Responsibilities**:
  - List available colors
  - Send responses directly to Discord/web via webhooks

#### Processor-Pixel-Info

- **Service**: `processor-pixel-info`
- **Topic**: `commands-pixel-info`
- **Secrets**: `DISCORD_BOT_TOKEN`
- **Dependencies**:
  - `canvas-service` (REST API via identity token)
- **Responsibilities**:
  - Get pixel information
  - Send responses directly to Discord/web via webhooks

### Data Services

#### Canvas Service

- **Service**: `canvas-service`
- **Authentication**: Private (identity tokens)
- **Role**: Data layer for canvas operations
- **Storage**: Firestore (canvas state), GCS (snapshots)
- **Configuration**: `setting.json`

#### User Manager

- **Service**: `user-manager`
- **Authentication**: Private (identity tokens)
- **Role**: User management, rate limiting, statistics
- **Storage**: Firestore (users collection)

#### Auth Service

- **Service**: `discord-auth-service`
- **Authentication**: Public
- **Role**: OAuth2 authentication for web clients
- **Storage**: Firestore (sessions collection)

### Frontend Services

#### Web Frontend

- **Service**: `web-frontend`
- **Authentication**: Public
- **Role**: Web interface for canvas
- **Pages**: Login, Canvas, Session (legacy)

#### Discord Registrar

- **Service**: `discord-utils`
- **Authentication**: Public
- **Secrets**: `DISCORD_BOT_TOKEN`, `DISCORD_APPLICATION_ID`
- **Role**: Register Discord slash commands

## Authentication and Security

### Service Authentication

```
┌─────────────────────────────────────────────────────────┐
│                    AUTHENTICATION                        │
│                                                          │
│  Public Services:                                        │
│  • web-frontend (public access)                         │
│  • auth-service (public access)                          │
│  • discord-registrar (public access)                     │
│                                                          │
│  Private Services (IAM):                                 │
│  • proxy (API Gateway service account only)              │
│  • user-manager (identity tokens)                        │
│  • canvas-service (identity tokens)                     │
│  • processor-* (Eventarc service account only)           │
└─────────────────────────────────────────────────────────┘
```

### Service-to-Service Communication

- **Identity Tokens**: Services use Google Cloud identity tokens for authentication
- **Shared Clients**:
  - `shared/canvas_client.py` - Client for canvas-service (identity token auth)
  - `shared/user_client.py` - Client for user-manager (identity token auth)

### Web Client Authentication

- **OAuth2 Flow**: Web clients authenticate via Discord OAuth2 (auth-service)
- **Session Tokens**: Validated by proxy before processing web interactions
- **Session Storage**: Firestore (sessions collection)

## Secret Management

```
┌─────────────────────────────────────────────────────────┐
│              SECRET MANAGER (GCP)                       │
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐              │
│  │ DISCORD_PUBLIC_  │  │ DISCORD_BOT_     │              │
│  │ KEY              │  │ TOKEN            │              │
│  └──────────────────┘  └──────────────────┘              │
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐              │
│  │ DISCORD_         │  │ DISCORD_CLIENT_  │              │
│  │ APPLICATION_ID   │  │ ID/SECRET        │              │
│  └──────────────────┘  └──────────────────┘              │
└─────────────────────────────────────────────────────────┘
            │                    │                    │
            │                    │                    │
            ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  PROXY           │  │  REGISTRAR       │  │  PROCESSORS      │
│  ✅ All secrets  │  │  ✅ BOT_TOKEN    │  │  ✅ BOT_TOKEN    │
│                  │  │  ✅ APP_ID       │  │     (webhooks)   │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

## Available Endpoints

### API Gateway

- `POST /discord/interactions` - Discord bot interactions
- `POST /web/interactions` - Web client interactions
- `GET /health` - Health check
- `GET /auth/*` - Auth service endpoints
- `GET /*` - Web frontend pages

### Proxy Service

- `POST /discord/interactions` - Receives Discord interactions (with signature verification)
- `POST /web/interactions` - Receives web client interactions (with session verification)
- `GET /health` - Health check

### Data Services

#### Canvas Service

- `POST /canvas/draw` - Draw a pixel
- `GET /canvas/state` - Get canvas state (JSON)
- `POST /canvas/snapshot` - Create a snapshot
- `GET /canvas/stats` - Canvas statistics
- `GET /canvas/pixel/{x}/{y}` - Pixel information
- `GET /health` - Health check

#### User Manager

- `GET /api/users/{user_id}` - Get a user
- `POST /api/users` - Create/update a user
- `POST /api/users/{user_id}/increment` - Increment usage
- `POST /api/rate-limit/check` - Check rate limit
- `GET /api/rate-limit/{user_id}` - Rate limit information
- `GET /api/stats/leaderboard` - Leaderboard
- `GET /health` - Health check

#### Auth Service

- `GET /auth/login` - Start OAuth2 flow
- `GET /auth/callback` - OAuth2 callback
- `POST /auth/verify` - Verify a session
- `GET /auth/user` - Get current user
- `POST /auth/logout` - Logout
- `GET /health` - Health check

### Processor Services

- `POST /` - Receives Pub/Sub messages (via Eventarc trigger)
- `GET /health` - Health check (if implemented)

### Registrar Service

- `POST /register` - Register all commands
- `POST /register/{command_name}` - Register specific command
- `GET /commands` - List all defined commands
- `GET /health` - Health check

## Deployment

### Recommended order:

1. **Create base GCP resources**

   ```bash
   make setup-all
   ```

2. **Create secrets**

   ```bash
   # See configs/gcp-secrets.json for complete list
   ```

3. **Create Pub/Sub topics**

   ```bash
   make setup-microservices-pubsub
   ```

4. **Deploy data services**

   ```bash
   make deploy-user-manager
   make deploy-canvas-service
   ```

5. **Deploy Proxy**

   ```bash
   make deploy-proxy
   ```

6. **Deploy frontend services**

   ```bash
   make deploy-web-frontend
   make deploy-auth
   make deploy-registrar
   ```

7. **Deploy Processors**

   ```bash
   make deploy-processors
   ```

8. **Configure API Gateway**

   ```bash
   make update-gateway
   ```

9. **Configure Discord**
   - Set API Gateway URL in Discord settings
   - `https://guidon-*.ew.gateway.dev/discord/interactions`

## Architecture Benefits

1. **Complete Isolation**: Each service can crash without affecting others
2. **Scalability**: Each service scales independently
3. **Maintenance**: Update one service without affecting others
4. **Security**: API Gateway as single entry point, private services with IAM
5. **Reliability**: Pub/Sub guarantees message delivery
6. **Monitoring**: Each service can be monitored separately
7. **Secret Centralization**: All Discord secrets in proxy
8. **Separation of Concerns**: Each service has a clear role
9. **Specialized Microservices**: Each command has its own service
10. **Dedicated Data Layer**: Canvas-service as single source of truth
11. **Direct Webhooks**: Processors send responses directly, reducing latency
12. **Identity Token Authentication**: Secure service-to-service communication
