"""Web frontend for Guidon - Canvas drawing interface."""
import os
import sys
import time
import threading
from flask import Flask, request as flask_request, make_response, jsonify, send_from_directory
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shared.observability import init_observability, traced_function
from shared.correlation import with_correlation

app = Flask(__name__)
logger, tracing = init_observability('web-frontend', app=None)

# In-memory storage for responses (token -> response_data)
# In a production environment with multiple instances, this should be Redis or Firestore
responses = {}
responses_lock = threading.Lock()

def cleanup_responses():
    """Cleanup old responses."""
    while True:
        time.sleep(60)
        with responses_lock:
            now = time.time()
            to_remove = [k for k, v in responses.items() if now - v['timestamp'] > 300]  # 5 minutes TTL
            for k in to_remove:
                del responses[k]

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_responses, daemon=True)
cleanup_thread.start()

OAUTH_LOGIN_URL = os.environ.get(
    "OAUTH_LOGIN_URL",
    "https://guidon-60g097ca.ew.gateway.dev/auth/login"
)
GATEWAY_URL = os.environ.get(
    "GATEWAY_URL",
    "https://guidon-60g097ca.ew.gateway.dev"
)
AUTH_SERVICE_URL = os.environ.get(
    "AUTH_SERVICE_URL",
    GATEWAY_URL
)
# URL of this service (web-frontend) to receive webhooks
# If not set, we try to guess or default to None (which will cause issues if not provided)
WEB_FRONTEND_URL = os.environ.get("WEB_FRONTEND_URL")
if not WEB_FRONTEND_URL:
    # Fallback for Cloud Run default URL pattern if needed, or warn
    logger.warning("WEB_FRONTEND_URL not set. Webhooks might not work correctly.")
    # Try to use a default if we know the project ID, but better to rely on env var
    # WEB_FRONTEND_URL = "https://web-frontend-..." 

WEBHOOK_URL = f"{WEB_FRONTEND_URL}/webhook" if WEB_FRONTEND_URL else None

@app.route('/webhook', methods=['POST'])
@traced_function("webhook_handler")
@with_correlation(logger)
def webhook_handler():
    """Receive webhook responses from processors."""
    correlation_id = getattr(flask_request, 'correlation_id', flask_request.headers.get('X-Correlation-ID'))
    try:
        data = flask_request.get_json(silent=True)
        if not data:
            logger.warning("Invalid JSON in webhook", correlation_id=correlation_id)
            return jsonify({'status': 'error', 'message': 'Invalid JSON'}), 400
        
        # Extract token from the response
        # The structure depends on what the processor sends.
        # Usually it sends the original interaction token or we need to find it.
        # Based on ARCHITECTURE.md, processors send response to webhook.
        # We assume the payload contains the 'token' or we can infer it.
        # If the processor sends the same structure as the response to Discord, it might not have the token.
        # But for 'web' interaction type, the proxy sends 'token' in the interaction object.
        # The processor should include this token in the response.
        
        token = data.get('token')
        if not token:
            # Try to find token in nested structures if needed
            token = data.get('interaction', {}).get('token')
            
        if not token:
            logger.warning("Missing token in webhook data", correlation_id=correlation_id)
            return jsonify({'status': 'error', 'message': 'Missing token'}), 400
            
        logger.info(f"Received webhook for token: {token}", correlation_id=correlation_id)
        
        with responses_lock:
            responses[token] = {
                'data': data,
                'timestamp': time.time()
            }
            
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logger.error("Error in webhook_handler", error=e, correlation_id=correlation_id)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@app.route('/response/<token>', methods=['GET'])
@traced_function("get_response")
@with_correlation(logger)
def get_response(token):
    """Get stored response for a token."""
    correlation_id = getattr(flask_request, 'correlation_id', flask_request.headers.get('X-Correlation-ID'))
    
    with responses_lock:
        response_entry = responses.get(token)
        
    if response_entry:
        logger.info(f"Returning response for token: {token}", correlation_id=correlation_id)
        return jsonify(response_entry['data']), 200
    else:
        # Return 202 Accepted to indicate it's still processing (or not found yet)
        # The client polls this endpoint.
        return jsonify({'status': 'pending'}), 202

@app.route('/', methods=['GET'])
@traced_function("web_app")
@with_correlation(logger)
def web_app():
    correlation_id = getattr(flask_request, 'correlation_id', flask_request.headers.get('X-Correlation-ID'))
    try:
        path = flask_request.path
        method = flask_request.method
        logger.info("Web request received", correlation_id=correlation_id, path=path, method=method)
        path_clean = path.rstrip('/')
        if path_clean == '/canvas' or path_clean == '':
            return canvas_page()
        return session_page()
    except Exception as e:
        logger.error("Error in web_app", error=e, correlation_id=correlation_id, path=flask_request.path)
        return make_response("Internal server error", 500)

@app.route('/canvas', methods=['GET'])
def canvas_page():
    correlation_id = getattr(flask_request, 'correlation_id', flask_request.headers.get('X-Correlation-ID'))
    session_id = flask_request.args.get("session")
    try:
        if not session_id:
            logger.warning("Canvas page accessed without session", correlation_id=correlation_id)
            if OAUTH_LOGIN_URL:
                login_template_path = os.path.join(os.path.dirname(__file__), 'template', 'login.html')
                try:
                    with open(login_template_path, 'r', encoding='utf-8') as f:
                        login_html = f.read()
                    login_html = login_html.replace('{{OAUTH_LOGIN_URL}}', OAUTH_LOGIN_URL)
                except FileNotFoundError:
                    logger.warning("Login template not found", template_path=login_template_path)
                    login_html = f"<html><body><h1>Error: Template not found</h1></body></html>"
                response = make_response(login_html)
                response.headers["Content-Type"] = "text/html; charset=utf-8"
                return response
        logger.info("Canvas page accessed", correlation_id=correlation_id, has_session=bool(session_id))
        template_path = os.path.join(os.path.dirname(__file__), 'template', 'canvas.html')
        
        # Determine Webhook URL dynamically if not set
        current_webhook_url = WEBHOOK_URL
        if not current_webhook_url:
            # Construct from request
            scheme = flask_request.headers.get('X-Forwarded-Proto', flask_request.scheme)
            host = flask_request.headers.get('Host', flask_request.host)
            current_webhook_url = f"{scheme}://{host}/webhook"
            logger.info(f"Constructed dynamic webhook URL: {current_webhook_url}", correlation_id=correlation_id)

        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                html = f.read()
            
            # Prepare config script
            config_script = f'''<script>
    window.SESSION_ID = {repr(session_id)};
    window.GATEWAY_URL = {repr(GATEWAY_URL)};
    window.WEBHOOK_URL = {repr(current_webhook_url)};
    if (window.SESSION_ID) {{
        localStorage.setItem('guidon_session', window.SESSION_ID);
    }}
</script>'''
            
            # Inject config script
            if '<!-- CONFIG_PLACEHOLDER -->' in html:
                html = html.replace('<!-- CONFIG_PLACEHOLDER -->', config_script)
            else:
                # Fallback: inject before </head>
                html = html.replace('</head>', f'{config_script}\n</head>')
                
        except FileNotFoundError:
            logger.error("Canvas template not found", template_path=template_path)
            html = "<html><body><h1>Error: Canvas template not found</h1></body></html>"
        response = make_response(html)
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        return response
    except Exception as e:
        logger.error("Error generating canvas page HTML", error=e, correlation_id=correlation_id)
        return make_response("Error loading canvas page", 500)

@app.route('/session', methods=['GET'])
def session_page():
    session_id = flask_request.args.get("session")
    username = flask_request.args.get("user", "Visitor")
    has_session = bool(session_id)
    session_display = session_id or "unknown"
    template_path = os.path.join(os.path.dirname(__file__), 'template', 'session.html')
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html = f.read()
        if has_session:
            content = f"""
            <h1>Welcome, {username}!</h1>
            <p>Authentication succeeded. Here is your session:</p>
            <div class='session'>{session_display}</div>
            <p>Copy it to use with the API or paste it in Postman.</p>
            <a class='btn' href='/canvas?session={session_id}'>Go to Canvas</a>
            """
        else:
            content = f"""
            <h1>Welcome to Guidon</h1>
            <p>Connect with Discord to start drawing on the shared canvas.</p>
            <a class='btn' href='{OAUTH_LOGIN_URL or "#"}'>Connect with Discord</a>
            <p class='muted'>Click the button above to authenticate with Discord.</p>
            """
        html = html.replace('{{CONTENT}}', content)
    except FileNotFoundError:
        logger.warning("Session template not found", template_path=template_path)
        html = f"<html><body><h1>Error: Template not found</h1></body></html>"
    response = make_response(html)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response

@app.route('/js/<path:filename>')
def serve_js(filename):
    js_dir = os.path.join(os.path.dirname(__file__), 'js')
    return send_from_directory(js_dir, filename)

# Ajoute ici d'autres routes si besoin

def verify_session(session_id: str) -> dict:
    try:
        if not AUTH_SERVICE_URL:
            return None
        response = requests.post(
            f"{AUTH_SERVICE_URL}/auth/verify",
            json={'session_id': session_id},
            timeout=2
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('valid'):
                return data.get('user')
    except Exception as e:
        logger.warning("Session verification error", error=e)
    return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, ssl_context=('cert.pem', 'key.pem'))