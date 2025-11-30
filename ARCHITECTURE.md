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
│                           DISCORD BOT INTERACTION                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY (GCP)                                  │
│  • Single entry point                                                       │
│  • URL: https://guidon-*.ew.gateway.dev                                     │
│  • Endpoints:                                                               │
│    - POST /discord/interactions (Discord bot)                               │
│    - POST /web/interactions (Web clients)                                   │
│    - GET /health                                                            │
│    - GET /auth/* (Auth service)                                             │
│    - GET /* (Web frontend)                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROXY SERVICE (Cloud Functions Gen2)                │
│  Service: proxy                                                             │
│  Authentication: Private (IAM - API Gateway only)                           │
│  Secrets: DISCORD_PUBLIC_KEY, DISCORD_BOT_TOKEN, DISCORD_APPLICATION_ID     │
│                                                                             │
│  Steps:                                                                     │
│  1. Verify Discord signature (DISCORD_PUBLIC_KEY)                           │
│  2. Parse interaction                                                       │
│  3. Handle simple commands directly (ping, hello)                           │
│  4. For complex commands → Publish to Pub/Sub                               │
│  5. Respond immediately to Discord (type 5 - deferred)                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
          ┌─────────▼─────────┐         ┌─────────▼──────────┐
          │  SIMPLE COMMANDS  │         │  COMPLEX COMMANDS  │
          │  (ping, hello)    │         │  (help, draw, etc) │
          │                   │         │                    │
          │  Direct response  │         │  Type 5 (deferred) │
          │  Type 4           │         │  + Pub/Sub         │
          └───────────────────┘         └────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PUB/SUB TOPICS (GCP)                                │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ interactions │  │commands-base │  │commands-draw │  │commands-     │     │
│  │              │  │              │  │              │  │ snapshot     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │commands-     │  │commands-stats│  │commands-     │  │commands-     │     │
│  │canvas-state  │  │              │  │colors        │  │pixel-info    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                                             │
│  All topics trigger Cloud Functions Gen2 via Eventarc                       │
└─────────────────────────────────────────────────────────────────────────────┘
            │                    │                    │
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│ PROCESSOR-BASE      │  │ PROCESSOR-DRAW      │  │ PROCESSOR-*         │
│ (Cloud Functions)   │  │ (Cloud Functions)   │  │ (Cloud Functions)   │
│                     │  │                     │  │                     │
│ Steps:              │  │ Steps:              │  │ Steps:              │
│ 1. Receive message  │  │ 1. Receive message  │  │ 1. Receive message  │
│ 2. Process command  │  │ 2. Check rate limit │  │ 2. Process command  │
│ 3. Send to Discord  │  │    (user-manager)   │  │ 3. Call canvas-     │
│    via webhook      │  │ 3. Draw pixel       │  │    service          │
│    (direct)         │  │    (canvas-service) │  │ 4. Send to Discord/ │
│                     │  │ 4. Increment usage  │  │    Web via webhook  │
│                     │  │    (user-manager)   │  │    (direct)         │
│                     │  │ 5. Send to Discord  │  │                     │
│                     │  │    via webhook      │  │                     │
│                     │  │    (direct)         │  │                     │
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
│                           WEB CLIENT (Browser)                              │
│  User authenticated via Discord OAuth2                                      │
│  Session ID stored in localStorage                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ POST /web/interactions
                                   │ Headers: X-Session-ID: <session_id>
                                   │ Body: { "command": "draw", "x": 10, ... }
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY (GCP)                                  │
│  Endpoint: POST /web/interactions                                           │
│  Routes to: proxy service                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ (IAM authenticated)
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROXY SERVICE (Cloud Functions Gen2)                │
│  Service: proxy                                                             │
│  Authentication: Private (IAM - API Gateway only)                           │
│                                                                             │
│  Steps:                                                                     │
│  1. Extract session ID from X-Session-ID header or Authorization Bearer     │
│  2. Call auth-service POST /auth/verify with session ID                     │
│  3. Receive verified Discord user info (user_id, username, avatar)          │
│  4. Inject user info into interaction payload                               │
│  5. Parse JSON request (command, options, webhook_url)                      │
│  6. Route to appropriate handler                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                   ┌───────────────┴───────────────┐
                   │                               │
         ┌─────────▼─────────┐         ┌─────────▼──────────┐
         │  SIMPLE COMMANDS  │         │  COMPLEX COMMANDS  │
         │  (ping, hello,    │         │  (draw, snapshot,  │
         │   help)           │         │   stats, etc)      │
         │                   │         │                    │
         │  Process directly │         │  Publish to Pub/Sub│
         │  Return JSON      │         │  Return 202        │
         │  (200 OK)         │         │  Accepted          │
         └───────────────────┘         └────────────────────┘
                                                   │
                                                   │ Pub/Sub message
                                                   │ { command, user, webhook_url }
                                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PUB/SUB TOPICS (GCP)                                │
│  Topic routing based on command:                                            │
│  • commands-draw → processor-draw                                           │
│  • commands-snapshot → processor-snapshot                                   │
│  • commands-stats → processor-stats                                         │
│  • commands-canvas-state → processor-canvas-state                           │
│  • commands-colors → processor-colors                                       │
│  • commands-pixel-info → processor-pixel-info                               │
│  • commands-base → processor-base                                           │
│                                                                             │
│  All topics trigger Cloud Functions Gen2 via Eventarc                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ Eventarc trigger
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PROCESSOR SERVICE (Cloud Functions Gen2)                 │
│  Example: processor-draw                                                    │
│                                                                             │
│  Steps:                                                                     │
│  1. Receive Pub/Sub message (via Eventarc)                                  │
│  2. Extract command, user info, webhook_url from message                    │
│  3. Check rate limit (user-manager via identity token)                      │
│  4. Execute command (e.g., draw pixel via canvas-service)                   │
│  5. Increment user usage (user-manager via identity token)                  │
│  6. Generate response payload                                               │
│  7. Send HTTP POST to webhook_url provided by client                        │
│     (webhook_url = https://web-frontend-url/webhook)                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ HTTP POST to webhook_url
                                   │ Body: { "token": "...", "status": "success", "data": {...} }
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         WEB FRONTEND (App Engine)                           │
│  POST /webhook: Receives webhook response from processor                   │
│  Stores response in memory with token as key                                │
│  GET /response/<token>: Returns stored response (polling endpoint)         │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ Client polls GET /response/<token>
                                   │ (every 500ms-1000ms, max 30 attempts)
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              WEB CLIENT                                     │
│  Polls GET /response/<token> until response is available                  │
│  Updates UI with response data when received                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Services Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA SERVICES                                       │
│                                                                             │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐           │
│  │  CANVAS-SERVICE             │  │  USER-MANAGER               │           │
│  │  (Cloud Functions Gen2)     │  │  (Cloud Functions Gen2)     │           │
│  │  Authentication: Private    │  │  Authentication: Private    │           │
│  │  (Identity Tokens)          │  │  (Identity Tokens)          │           │
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
│                                                                             │
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
│  │  • Firestore (sessions)     │                                            │
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
                              ├─► Extract X-Session-ID header or Authorization Bearer token
                              ├─► Call auth-service POST /auth/verify with session ID
                              ├─► Receive verified user info (user_id, username, avatar)
                              ├─► Inject user info into interaction payload
                              ├─► Parse JSON request (command, options, webhook_url)
                              ├─► Process command directly
                              └─► Return JSON response (200 OK)
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
                              ├─► Extract X-Session-ID header
                              ├─► Call auth-service POST /auth/verify
                              ├─► Receive verified user info
                              ├─► Inject user info into payload
                              ├─► Extract webhook_url from request
                              ├─► Publish to Pub/Sub with webhook_url
                              └─► Return 202 Accepted
                                     │
                                     ▼
                              Pub/Sub Topic (commands-draw)
                                     │
                                     ▼ (Eventarc trigger)
                              Processor-Draw (Cloud Functions Gen2)
                                     │
                              ├─► Check rate limit (user-manager)
                              ├─► Draw pixel (canvas-service)
                              ├─► Increment usage (user-manager)
                              ├─► Generate response payload
                              └─► POST to webhook_url provided by client
                                     │
                                     ▼
                              Web client receives response at webhook_url
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
  - `POST /web/interactions` → Proxy (Web clients, requires `X-Session-ID` header)
  - `GET /health` → Proxy
  - `GET /auth/*` → Auth Service
  - `GET /*` → Web Frontend
- **Authentication**: IAM - Only API Gateway service account can invoke proxy

### Proxy Service

- **Service**: `proxy`
- **Authentication**: Private (`--no-allow-unauthenticated` - IAM only)
- **IAM Access**: API Gateway service account only
- **Secrets**: `DISCORD_PUBLIC_KEY`, `DISCORD_BOT_TOKEN`, `DISCORD_APPLICATION_ID`
- **Responsibilities**:
  - Discord signature verification (for Discord interactions)
  - Web session authentication (calls auth-service /auth/verify)
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
- **Authentication**: Private (`--no-allow-unauthenticated` - IAM only)
- **IAM Access**: Eventarc service account (automatic via Pub/Sub trigger)
- **Secrets**: `DISCORD_BOT_TOKEN` (for Discord webhooks)
- **Responsibilities**:
  - Process base commands (ping, hello, help)
  - Send responses directly to Discord/web via webhooks

#### Processor-Draw

- **Service**: `processor-draw`
- **Topic**: `commands-draw`
- **Authentication**: Private (`--no-allow-unauthenticated` - IAM only)
- **IAM Access**: Eventarc service account (automatic via Pub/Sub trigger)
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
- **Authentication**: Private (`--no-allow-unauthenticated` - IAM only)
- **IAM Access**: Eventarc service account (automatic via Pub/Sub trigger)
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
- **Authentication**: Public (`--allow-unauthenticated`)
- **Secrets**: `DISCORD_BOT_TOKEN`
- **Dependencies**:
  - `canvas-service` (REST API via identity token)
- **Responsibilities**:
  - Get canvas state as JSON
  - Send responses directly to Discord/web via webhooks

#### Processor-Stats

- **Service**: `processor-stats`
- **Topic**: `commands-stats`
- **Authentication**: Private (`--no-allow-unauthenticated` - IAM only)
- **IAM Access**: Eventarc service account (automatic via Pub/Sub trigger)
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
- **Authentication**: Private (`--no-allow-unauthenticated` - IAM only)
- **IAM Access**: Eventarc service account (automatic via Pub/Sub trigger)
- **Secrets**: `DISCORD_BOT_TOKEN`
- **Dependencies**: None (stateless)
- **Responsibilities**:
  - List available colors
  - Send responses directly to Discord/web via webhooks

#### Processor-Pixel-Info

- **Service**: `processor-pixel-info`
- **Topic**: `commands-pixel-info`
- **Authentication**: Private (`--no-allow-unauthenticated` - IAM only)
- **IAM Access**: Eventarc service account (automatic via Pub/Sub trigger)
- **Secrets**: `DISCORD_BOT_TOKEN`
- **Dependencies**:
  - `canvas-service` (REST API via identity token)
- **Responsibilities**:
  - Get pixel information
  - Send responses directly to Discord/web via webhooks

### Data Services

#### Canvas Service

- **Service**: `canvas-service`
- **Authentication**: Private (`--no-allow-unauthenticated` - IAM only)
- **IAM Access**: Identity tokens (service-to-service)
- **Role**: Data layer for canvas operations
- **Storage**: Firestore (canvas state), GCS (snapshots)
- **Configuration**: `setting.json`
- **Environment Variables**:
  - `GCS_CANVAS_BUCKET` (from Secret Manager) - GCS bucket name for snapshots
  - `USER_MANAGER_URL` (from Secret Manager) - User manager service URL
  - `FIRESTORE_DATABASE` - Firestore database ID
  - `GCP_PROJECT_ID` - GCP project ID
  - `ENVIRONMENT` - Environment name (dev/stage/prod)

#### User Manager

- **Service**: `user-manager`
- **Authentication**: Private (`--no-allow-unauthenticated` - IAM only)
- **IAM Access**: Identity tokens (service-to-service)
- **Role**: User management, rate limiting, statistics
- **Storage**: Firestore (users collection)

#### Auth Service

- **Service**: `discord-auth-service`
- **Authentication**: Public (`--allow-unauthenticated`)
- **Role**: OAuth2 authentication for web clients
- **Storage**: Firestore (sessions collection)

### Frontend Services

#### Web Frontend

- **Service**: `web-frontend`
- **Authentication**: Public (`--allow-unauthenticated`)
- **Role**: Web interface for canvas
- **Pages**: Login, Canvas, Session (legacy)
- **Endpoints**:
  - `GET /` - Canvas page
  - `GET /login` - Login page
  - `POST /webhook` - Receives webhook responses from processors
  - `GET /response/<token>` - Returns stored response for polling
- **Response Handling**: Hybrid webhook + polling system
  - Processors send responses to `/webhook` endpoint
  - Frontend stores responses in memory with token as key
  - Client polls `/response/<token>` every 500ms-1000ms until response is available
- **Environment Variables**:
  - `GATEWAY_URL` - API Gateway URL
  - `AUTH_SERVICE_URL` - Auth service URL
  - `WEB_FRONTEND_URL` - Self URL (dynamically built if not set)

#### Discord Registrar

- **Service**: `discord-utils`
- **Authentication**: Public (`--allow-unauthenticated`)
- **Secrets**: `DISCORD_BOT_TOKEN`, `DISCORD_APPLICATION_ID`
- **Role**: Register Discord slash commands

## Authentication and Security

### Service Authentication

```
┌─────────────────────────────────────────────────────────┐
│                    AUTHENTICATION                       │
│                                                         │
│  Public Services (--allow-unauthenticated):             │
│  • web-frontend (public access)                         │
│  • auth-service (public access)                         │
│  • discord-registrar (public access)                    │
│  • processor-canvas-state (public access)               │
│                                                         │
│  Private Services (--no-allow-unauthenticated):         │
│  • proxy (IAM - API Gateway service account only)       │
│  • user-manager (IAM - identity tokens)                 │
│  • canvas-service (IAM - identity tokens)               │
│  • processor-base (IAM - Eventarc service account)      │
│  • processor-draw (IAM - Eventarc service account)      │
│  • processor-snapshot (IAM - Eventarc service account)  │
│  • processor-stats (IAM - Eventarc service account)     │
│  • processor-colors (IAM - Eventarc service account)    │
│  • processor-pixel-info (IAM - Eventarc service account)│
└─────────────────────────────────────────────────────────┘
```

### Service-to-Service Communication

- **Identity Tokens**: Services use Google Cloud identity tokens for authentication
- **Shared Clients**:
  - `shared/canvas_client.py` - Client for canvas-service (identity token auth)
  - `shared/user_client.py` - Client for user-manager (identity token auth)

### Eventarc and Pub/Sub Triggers

- **Eventarc**: Automatically creates Pub/Sub subscriptions for Cloud Functions Gen2
- **IAM Permissions**: Eventarc service account automatically receives `roles/run.invoker` permission
- **Private Processors**: Even though processors are private (`--no-allow-unauthenticated`), Eventarc can invoke them because:
  - Eventarc service account has `roles/run.invoker` on the function
  - This is automatically configured when deploying with `--trigger-topic`
- **No Manual Subscription Creation**: Cloud Functions Gen2 + Eventarc handles subscription creation automatically

### Web Client Authentication

- **OAuth2 Flow**: Web clients authenticate via Discord OAuth2 (auth-service)
- **Session Tokens**: Validated by proxy before processing web interactions
- **Session Storage**: Firestore (sessions collection)

## Secret Management

```
┌─────────────────────────────────────────────────────────┐
│              SECRET MANAGER (GCP)                       │
│                                                         │
│  ┌──────────────────┐  ┌──────────────────┐             │
│  │ DISCORD_PUBLIC_  │  │ DISCORD_BOT_     │             │
│  │ KEY              │  │ TOKEN            │             │
│  └──────────────────┘  └──────────────────┘             │
│                                                         │
│  ┌──────────────────┐  ┌──────────────────┐             │
│  │ DISCORD_         │  │ DISCORD_CLIENT_  │             │
│  │ APPLICATION_ID   │  │ ID/SECRET        │             │
│  └──────────────────┘  └──────────────────┘             │
│                                                         │
│  ┌──────────────────┐  ┌──────────────────┐             │
│  │ GCS_CANVAS_      │  │ USER_MANAGER_    │             │
│  │ BUCKET           │  │ URL              │             │
│  └──────────────────┘  └──────────────────┘             │
│                                                         │
│  ┌──────────────────┐  ┌──────────────────┐             │
│  │ CANVAS_SERVICE_  │  │ AUTH_SERVICE_    │             │
│  │ URL              │  │ URL              │             │
│  └──────────────────┘  └──────────────────┘             │
└─────────────────────────────────────────────────────────┘
            │                    │                    │
            │                    │                    │
            ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  PROXY           │  │  REGISTRAR       │  │  PROCESSORS      │
│  All secrets     │  │  BOT_TOKEN       │  │  BOT_TOKEN       │
│                  │  │  APP_ID          │  │  (webhooks)      │
└──────────────────┘  └──────────────────┘  └──────────────────┘
            │                    │                    │
            │                    │                    │
            ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  CANVAS-SERVICE  │  │  AUTH-SERVICE    │  │  WEB-FRONTEND    │
│  GCS_CANVAS_     │  │  CLIENT_ID/      │  │  GATEWAY_URL     │
│  BUCKET          │  │  SECRET          │  │  AUTH_SERVICE_  │
│  USER_MANAGER_   │  │  REDIRECT_URI    │  │  URL             │
│  URL             │  │  WEB_FRONTEND_   │  └──────────────────┘
└──────────────────┘  │  URL             │
                      └──────────────────┘
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
   make setup-pubsub
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
