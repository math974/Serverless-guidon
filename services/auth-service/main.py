"""
OAuth2 Discord Authentication Service using Functions Framework for Cloud Functions Gen2
"""
import os
import requests
import secrets
from datetime import datetime, timedelta, timezone
from google.cloud import firestore
from functions_framework import http
from flask import jsonify, Request, make_response, Response
from shared.correlation import with_correlation
from shared.observability import init_observability, traced_function
from urllib.parse import urlencode

logger, tracing = init_observability('discord-auth-service', app=None)

# --- Discord OAuth2 Configuration ---
DISCORD_CLIENT_ID = os.environ.get('DISCORD_CLIENT_ID', '').strip()
DISCORD_CLIENT_SECRET = os.environ.get('DISCORD_CLIENT_SECRET', '').strip()
DISCORD_REDIRECT_URI = os.environ.get('DISCORD_REDIRECT_URI', '').strip()
WEB_FRONTEND_URL = os.environ.get('WEB_FRONTEND_URL', '').strip()

# --- Discord OAuth2 Configuration ---
DISCORD_API_BASE_URL = "https://discord.com/api/v10"
DISCORD_OAUTH_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"

# --- Firestore / helpers ---
_db_client = None
FIRESTORE_DATABASE = os.environ.get("FIRESTORE_DATABASE", "guidon-db")

# --- Firestore client (singleton) ---
def get_db():
    """Get Firestore client singleton."""
    global _db_client
    if _db_client is None:
        _db_client = firestore.Client(database=FIRESTORE_DATABASE)
    return _db_client


def auto_redirect_response(target_url: str, message: str) -> Response:
    """Return HTML that forces redirect (meta + JS) while keeping Location header."""
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <title>Redirecting...</title>
        <meta http-equiv="refresh" content="0;url={target_url}">
        <script>window.location.replace("{target_url}");</script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                background: #0f172a;
                color: #f8fafc;
            }}
            a {{ color: #60a5fa; }}
        </style>
    </head>
    <body>
        <div>
            <h2>{message}</h2>
            <p>If you are not redirected automatically, <a href="{target_url}">click here</a>.</p>
        </div>
    </body>
    </html>
    """
    response = make_response(html, 302)
    response.headers["Location"] = target_url
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response


class SessionManager:
    """Manages user sessions in Firestore."""

    @staticmethod
    def create_session(user_data: dict, discord_token: dict, correlation_id: str = None) -> str:
        """Create a new session for authenticated user."""
        db = get_db()
        session_id = secrets.token_urlsafe(32)
        user_id = user_data['id']
        username = f"{user_data['username']}#{user_data.get('discriminator', '0')}"

        logger.info(
            "Creating session",
            correlation_id=correlation_id,
            user_id=user_id,
            username=username,
            session_id=session_id[:10] + "..."
        )

        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'username': username,
            'avatar': user_data.get('avatar'),
            'discord_access_token': discord_token['access_token'],
            'discord_refresh_token': discord_token.get('refresh_token'),
            'discord_token_expires': datetime.now(timezone.utc) + timedelta(seconds=discord_token['expires_in']),
            'created_at': firestore.SERVER_TIMESTAMP,
            'last_activity': firestore.SERVER_TIMESTAMP,
            'expires_at': datetime.now(timezone.utc) + timedelta(days=30)
        }

        db.collection('sessions').document(session_id).set(session_data)

        # --- Update user record ---
        db.collection('users').document(user_id).set({
            'user_id': user_id,
            'username': username,
            'avatar': user_data.get('avatar'),
            'last_login': firestore.SERVER_TIMESTAMP
        }, merge=True)

        logger.info(
            "Session created successfully",
            correlation_id=correlation_id,
            user_id=user_id,
            session_id=session_id[:10] + "..."
        )

        return session_id

    @staticmethod
    def get_session(session_id: str, correlation_id: str = None) -> dict:
        """Get session data."""
        db = get_db()
        doc = db.collection('sessions').document(session_id).get()

        if doc.exists:
            session_data = doc.to_dict()

            # --- Check if expired ---
            if session_data.get('expires_at') and session_data['expires_at'] < datetime.now(timezone.utc):
                logger.info(
                    "Session expired",
                    correlation_id=correlation_id,
                    session_id=session_id[:10] + "...",
                    user_id=session_data.get('user_id')
                )
                SessionManager.delete_session(session_id, correlation_id)
                return None

            # --- Update last activity ---
            db.collection('sessions').document(session_id).update({
                'last_activity': firestore.SERVER_TIMESTAMP
            })

            logger.debug(
                "Session retrieved",
                correlation_id=correlation_id,
                session_id=session_id[:10] + "...",
                user_id=session_data.get('user_id')
            )

            return session_data

        logger.warning(
            "Session not found",
            correlation_id=correlation_id,
            session_id=session_id[:10] + "..." if session_id else None
        )
        return None

    @staticmethod
    def delete_session(session_id: str, correlation_id: str = None):
        """Delete a session."""
        logger.info(
            "Deleting session",
            correlation_id=correlation_id,
            session_id=session_id[:10] + "..." if session_id else None
        )
        db = get_db()
        db.collection('sessions').document(session_id).delete()
        logger.info(
            "Session deleted",
            correlation_id=correlation_id,
            session_id=session_id[:10] + "..." if session_id else None
        )

    @staticmethod
    def refresh_discord_token(session_id: str, correlation_id: str = None) -> bool:
        """Refresh Discord access token."""
        logger.info(
            "Refreshing Discord token",
            correlation_id=correlation_id,
            session_id=session_id[:10] + "..." if session_id else None
        )

        session_data = SessionManager.get_session(session_id, correlation_id)
        if not session_data or not session_data.get('discord_refresh_token'):
            logger.warning(
                "Cannot refresh token: session not found or no refresh token",
                correlation_id=correlation_id,
                session_id=session_id[:10] + "..." if session_id else None,
                has_session=bool(session_data),
                has_refresh_token=bool(session_data and session_data.get('discord_refresh_token'))
            )
            return False

        data = {
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': session_data['discord_refresh_token']
        }

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        try:
            response = requests.post(DISCORD_TOKEN_URL, data=data, headers=headers, timeout=10)
            if response.status_code == 200:
                token_data = response.json()

                db = get_db()
                db.collection('sessions').document(session_id).update({
                    'discord_access_token': token_data['access_token'],
                    'discord_refresh_token': token_data.get('refresh_token'),
                    'discord_token_expires': datetime.now(timezone.utc) + timedelta(seconds=token_data['expires_in'])
                })

                logger.info(
                    "Discord token refreshed successfully",
                    correlation_id=correlation_id,
                    session_id=session_id[:10] + "...",
                    user_id=session_data.get('user_id')
                )
                return True
            else:
                logger.error(
                    "Failed to refresh Discord token",
                    correlation_id=correlation_id,
                    session_id=session_id[:10] + "...",
                    status_code=response.status_code,
                    response_text=response.text[:200]
                )
        except Exception as e:
            logger.error(
                "Error refreshing Discord token",
                error=e,
                correlation_id=correlation_id,
                session_id=session_id[:10] + "..." if session_id else None
            )

        return False


def get_discord_user_info(access_token: str, correlation_id: str = None) -> dict:
    """Get Discord user information."""
    headers = {'Authorization': f'Bearer {access_token}'}

    logger.debug(
        "Fetching Discord user info",
        correlation_id=correlation_id
    )

    try:
        response = requests.get(f"{DISCORD_API_BASE_URL}/users/@me", headers=headers, timeout=10)
        if response.status_code == 200:
            user_data = response.json()
            logger.info(
                "Discord user info retrieved",
                correlation_id=correlation_id,
                user_id=user_data.get('id'),
                username=user_data.get('username')
            )
            return user_data
        else:
            logger.error(
                "Failed to get Discord user info",
                correlation_id=correlation_id,
                status_code=response.status_code,
                response_text=response.text[:200]
            )
    except Exception as e:
        logger.error(
            "Error getting Discord user info",
            error=e,
            correlation_id=correlation_id
        )

    return None


def add_cors_headers(response):
    """Add CORS headers to response."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Session-ID, X-Correlation-ID, Authorization'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response


@http
@with_correlation(logger)
@traced_function("auth_handler")
def auth_handler(request: Request):
    """
    Main HTTP handler for all auth endpoints.
    Routes based on path.
    """
    path = request.path
    method = request.method

    # Handle CORS preflight requests
    if method == 'OPTIONS':
        response = make_response('', 200)
        return add_cors_headers(response)

    if path == '/health' and method == 'GET':
        result = handle_health(request)
        response = result if isinstance(result, Response) else make_response(result[0], result[1]) if isinstance(result, tuple) else result
        return add_cors_headers(response)

    elif path == '/auth/login' and method == 'GET':
        return handle_login(request)

    elif path == '/auth/callback' and method == 'GET':
        return handle_callback(request)

    elif path == '/auth/logout' and method == 'POST':
        result = handle_logout(request)
        response = result if isinstance(result, Response) else make_response(result[0], result[1]) if isinstance(result, tuple) else result
        return add_cors_headers(response)

    elif path == '/auth/verify' and method == 'POST':
        result = handle_verify(request)
        response = result if isinstance(result, Response) else make_response(result[0], result[1]) if isinstance(result, tuple) else result
        return add_cors_headers(response)

    elif path == '/auth/user' and method == 'GET':
        result = handle_get_user(request)
        response = result if isinstance(result, Response) else make_response(result[0], result[1]) if isinstance(result, tuple) else result
        return add_cors_headers(response)

    elif path == '/auth/sessions/active' and method == 'GET':
        result = handle_active_sessions(request)
        response = result if isinstance(result, Response) else make_response(result[0], result[1]) if isinstance(result, tuple) else result
        return add_cors_headers(response)

    else:
        correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))
        logger.warning(
            "Unknown path requested",
            correlation_id=correlation_id,
            path=path,
            method=method
        )
        response = jsonify({
            'error': 'Not Found',
            'path': path,
            'method': method
        }), 404
        if isinstance(response, tuple):
            response = make_response(response[0], response[1])
        return add_cors_headers(response)


@traced_function("handle_health")
def handle_health(request: Request):
    """Health check endpoint."""
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))
    logger.info("Health check called", correlation_id=correlation_id)
    return jsonify({
        'status': 'healthy',
        'service': 'auth-service',
        'configured': bool(DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET),
        'framework': 'functions_framework'
    }), 200


@traced_function("handle_login")
def handle_login(request: Request):
    """Initiate Discord OAuth2 login."""
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))

    if not DISCORD_CLIENT_ID or not DISCORD_REDIRECT_URI:
        logger.error(
            "OAuth2 not configured",
            correlation_id=correlation_id,
            has_client_id=bool(DISCORD_CLIENT_ID),
            has_redirect_uri=bool(DISCORD_REDIRECT_URI)
        )
        return jsonify({'error': 'OAuth2 not configured'}), 500

    # --- Generate state for CSRF protection ---
    state = secrets.token_urlsafe(32)

    logger.info(
        "Initiating Discord OAuth2 login",
        correlation_id=correlation_id,
        state=state[:10] + "..."
    )

    # --- Store state in query param (stateless approach) ---
    # --- In production, you might want to use signed cookies or cache ---

    params = {
        'client_id': DISCORD_CLIENT_ID,
        'redirect_uri': DISCORD_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'identify email',
        'state': state
    }

    oauth_url = f"{DISCORD_OAUTH_URL}?{urlencode(params)}"

    logger.info(
        "Redirecting to Discord OAuth2",
        correlation_id=correlation_id,
        state=state[:10] + "...",
        redirect_uri=DISCORD_REDIRECT_URI
    )

    return auto_redirect_response(oauth_url, "Redirecting to Discord OAuth2...")


@traced_function("handle_callback")
def handle_callback(request: Request):
    """Handle Discord OAuth2 callback."""
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))
    code = request.args.get('code')
    state = request.args.get('state')

    logger.info(
        "OAuth2 callback received",
        correlation_id=correlation_id,
        has_code=bool(code),
        state=state[:10] + "..." if state else None
    )

    if not code:
        logger.warning(
            "OAuth2 callback missing authorization code",
            correlation_id=correlation_id,
            state=state[:10] + "..." if state else None
        )
        return jsonify({'error': 'No authorization code provided'}), 400

    # --- In production, verify state for CSRF protection ---
    # --- For now, we'll skip this since we're stateless ---

    # --- Exchange code for token ---
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI
    }

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    try:
        logger.info(
            "Exchanging authorization code for token",
            correlation_id=correlation_id
        )
        token_response = requests.post(DISCORD_TOKEN_URL, data=data, headers=headers, timeout=10)

        if token_response.status_code != 200:
            logger.error(
                "Token exchange failed",
                correlation_id=correlation_id,
                status_code=token_response.status_code,
                response_text=token_response.text[:200]
            )
            return jsonify({
                'error': 'Failed to exchange code for token',
                'details': token_response.text
            }), 400

        token_data = token_response.json()
        access_token = token_data['access_token']

        logger.info(
            "Token exchange successful",
            correlation_id=correlation_id
        )

        # --- Get user information ---
        user_data = get_discord_user_info(access_token, correlation_id)
        if not user_data:
            logger.error(
                "Failed to get user information after token exchange",
                correlation_id=correlation_id
            )
            return jsonify({'error': 'Failed to get user information'}), 400

        # --- Create session ---
        session_id = SessionManager.create_session(user_data, token_data, correlation_id)

        # --- Redirect to web frontend with session ---
        frontend_url = WEB_FRONTEND_URL or 'https://web-frontend.example.com'
        redirect_url = f"{frontend_url.rstrip('/')}/canvas?session={session_id}"

        logger.info(
            "OAuth2 authentication successful, redirecting to frontend",
            correlation_id=correlation_id,
            user_id=user_data.get('id'),
            session_id=session_id[:10] + "..."
        )

        return auto_redirect_response(
            redirect_url,
            "Authentication succeeded. Redirecting to the frontend..."
        )

    except Exception as e:
        logger.error(
            "OAuth2 callback error",
            error=e,
            correlation_id=correlation_id
        )
        return jsonify({
            'error': 'Authentication failed',
            'details': str(e)
        }), 500


@traced_function("handle_logout")
def handle_logout(request: Request):
    """Logout user and invalidate session."""
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))

    try:
        data = request.get_json(silent=True)
        if not data:
            logger.warning(
                "Logout request with invalid JSON",
                correlation_id=correlation_id
            )
            return jsonify({'error': 'Invalid JSON'}), 400

        session_id = data.get('session_id')

        if session_id:
            logger.info(
                "Logging out user",
                correlation_id=correlation_id,
                session_id=session_id[:10] + "..."
            )
            SessionManager.delete_session(session_id, correlation_id)
            logger.info(
                "User logged out successfully",
                correlation_id=correlation_id,
                session_id=session_id[:10] + "..."
            )
        else:
            logger.warning(
                "Logout request without session_id",
                correlation_id=correlation_id
            )

        return jsonify({'status': 'logged_out'}), 200

    except Exception as e:
        logger.error(
            "Logout error",
            error=e,
            correlation_id=correlation_id
        )
        return jsonify({'error': 'Logout failed'}), 500


@traced_function("handle_verify")
def handle_verify(request: Request):
    """Verify a session token."""
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))

    try:
        data = request.get_json(silent=True)
        if not data:
            logger.warning(
                "Verify request with invalid JSON",
                correlation_id=correlation_id
            )
            return jsonify({'error': 'Invalid JSON'}), 400

        session_id = data.get('session_id')

        if not session_id:
            logger.warning(
                "Verify request without session_id",
                correlation_id=correlation_id
            )
            return jsonify({
                'valid': False,
                'error': 'No session ID provided'
            }), 400

        logger.info(
            "Verifying session",
            correlation_id=correlation_id,
            session_id=session_id[:10] + "..."
        )

        session_data = SessionManager.get_session(session_id, correlation_id)

        if not session_data:
            logger.warning(
                "Session verification failed: invalid or expired",
                correlation_id=correlation_id,
                session_id=session_id[:10] + "..."
            )
            return jsonify({
                'valid': False,
                'error': 'Invalid or expired session'
            }), 401

        logger.info(
            "Session verified successfully",
            correlation_id=correlation_id,
            session_id=session_id[:10] + "...",
            user_id=session_data.get('user_id')
        )

        return jsonify({
            'valid': True,
            'user': {
                'id': session_data['user_id'],
                'username': session_data['username'],
                'avatar': session_data.get('avatar')
            }
        }), 200

    except Exception as e:
        logger.error(
            "Session verification error",
            error=e,
            correlation_id=correlation_id
        )
        return jsonify({
            'valid': False,
            'error': 'Verification failed'
        }), 500


@traced_function("handle_get_user")
def handle_get_user(request: Request):
    """Get current user information from session."""
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))
    session_id = request.headers.get('X-Session-ID')

    if not session_id:
        logger.warning(
            "Get user request without session_id",
            correlation_id=correlation_id
        )
        return jsonify({'error': 'No session ID provided'}), 401

    logger.info(
        "Getting user information",
        correlation_id=correlation_id,
        session_id=session_id[:10] + "..."
    )

    session_data = SessionManager.get_session(session_id, correlation_id)

    if not session_data:
        logger.warning(
            "Get user failed: invalid or expired session",
            correlation_id=correlation_id,
            session_id=session_id[:10] + "..."
        )
        return jsonify({'error': 'Invalid or expired session'}), 401

    # --- Check if Discord token needs refresh ---
    if session_data.get('discord_token_expires') and \
       session_data['discord_token_expires'] < datetime.now(timezone.utc):
        logger.info(
            "Discord token expired, refreshing",
            correlation_id=correlation_id,
            session_id=session_id[:10] + "...",
            user_id=session_data.get('user_id')
        )
        if not SessionManager.refresh_discord_token(session_id, correlation_id):
            logger.error(
                "Token refresh failed",
                correlation_id=correlation_id,
                session_id=session_id[:10] + "..."
            )
            return jsonify({'error': 'Token refresh failed'}), 401
        session_data = SessionManager.get_session(session_id, correlation_id)

    logger.info(
        "User information retrieved",
        correlation_id=correlation_id,
        session_id=session_id[:10] + "...",
        user_id=session_data.get('user_id')
    )

    return jsonify({
        'user_id': session_data['user_id'],
        'username': session_data['username'],
        'avatar': session_data.get('avatar')
    }), 200


@traced_function("handle_active_sessions")
def handle_active_sessions(request: Request):
    """Get count of active sessions."""
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))

    try:
        logger.info(
            "Getting active sessions count",
            correlation_id=correlation_id
        )

        db = get_db()

        # --- Count non-expired sessions ---
        now = datetime.now(timezone.utc)
        query = db.collection('sessions').where('expires_at', '>', now)
        count = len(list(query.stream()))

        logger.info(
            "Active sessions count retrieved",
            correlation_id=correlation_id,
            active_sessions=count
        )

        return jsonify({
            'active_sessions': count,
            'timestamp': now.isoformat()
        }), 200

    except Exception as e:
        logger.error(
            "Active sessions error",
            error=e,
            correlation_id=correlation_id
        )
        return jsonify({'error': str(e)}), 500
