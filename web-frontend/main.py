"""Web frontend for Guidon - Canvas drawing interface."""
import os
import sys
import time
import threading
import json
from flask import Flask, request as flask_request, make_response, jsonify, send_from_directory
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shared.observability import init_observability, traced_function
from shared.correlation import with_correlation

app = Flask(__name__)
logger, tracing = init_observability('web-frontend', app=None)

responses = {}
responses_lock = threading.Lock()

def cleanup_responses():
    """Cleanup old responses."""
    while True:
        time.sleep(60)
        with responses_lock:
            now = time.time()
            to_remove = [k for k, v in responses.items() if now - v['timestamp'] > 300]
            for k in to_remove:
                del responses[k]

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

WEB_FRONTEND_URL = os.environ.get("WEB_FRONTEND_URL")
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

        token = data.get('token') or data.get('interaction', {}).get('token')
        if not token:
            logger.warning("Missing token in webhook data", correlation_id=correlation_id)
            return jsonify({'status': 'error', 'message': 'Missing token'}), 400

        status = data.get('status')
        if status == 'processing':
            logger.info(
                "Ignoring processing status webhook",
                correlation_id=correlation_id,
                token=token
            )
            return jsonify({'status': 'ignored'}), 200

        data_type = data.get('type')
        has_data = bool(data.get('data'))
        has_embeds = bool(data.get('data', {}).get('embeds'))
        has_token = bool(data.get('token'))

        logger.info(
            f"Received webhook for token: {token}",
            correlation_id=correlation_id,
            token=token,
            has_status=bool(status),
            status=status,
            data_type=data_type,
            has_data=has_data,
            has_embeds=has_embeds,
            has_token=has_token,
            data_keys=list(data.keys())[:10]
        )

        # Store response for polling
        with responses_lock:
            responses[token] = {
                'data': data,
                'timestamp': time.time()
            }
            logger.info(
                "Stored webhook response",
                correlation_id=correlation_id,
                token=token,
                total_responses=len(responses),
                response_type=data_type,
                has_embeds=has_embeds
            )

        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logger.error("Error in webhook_handler", error=e, correlation_id=correlation_id)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@app.route('/response/<token>', methods=['GET'])
@traced_function("get_response")
@with_correlation(logger)
def get_response(token):
    """Return stored webhook response for a token."""
    correlation_id = getattr(flask_request, 'correlation_id', flask_request.headers.get('X-Correlation-ID'))

    logger.info(
        "GET /response/<token> called",
        correlation_id=correlation_id,
        token=token
    )

    with responses_lock:
        entry = responses.get(token)
        available_tokens = list(responses.keys())[:10]  # Log first 10 tokens for debugging

    if entry:
        entry_data = entry.get('data', {})
        entry_status = entry_data.get('status')
        entry_type = entry_data.get('type')
        has_embeds = bool(entry_data.get('data', {}).get('embeds'))

        if entry_status == 'processing':
            logger.info(
                "Stored response has processing status, ignoring",
                correlation_id=correlation_id,
                token=token
            )
            return jsonify({'status': 'pending'}), 202

        logger.info(
            "Returning stored response",
            correlation_id=correlation_id,
            token=token,
            has_data=bool(entry_data),
            status=entry_status,
            type=entry_type,
            has_embeds=has_embeds,
            data_keys=list(entry_data.keys())[:10]
        )
        return jsonify(entry_data), 200

    logger.warning(
        "Response still pending",
        correlation_id=correlation_id,
        token=token,
        available_tokens=available_tokens,
        total_responses=len(responses)
    )
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

def get_canvas_size():
    """Get canvas size from canvas-service or use default."""
    try:
        canvas_service_url = os.environ.get('CANVAS_SERVICE_URL', GATEWAY_URL)
        response = requests.get(
            f"{canvas_service_url}/canvas/size",
            timeout=0.5
        )
        if response.status_code == 200:
            data = response.json()
            canvas_size = data.get('size')
            if canvas_size:
                return canvas_size
    except (requests.exceptions.RequestException, Exception) as e:
        error_msg = str(e) if e else "Unknown error"
        logger.debug("Could not fetch canvas size from API", error=error_msg)

    return 100

@app.route('/login', methods=['GET'])
@traced_function("login_page")
@with_correlation(logger)
def login_page():
    correlation_id = getattr(flask_request, 'correlation_id', flask_request.headers.get('X-Correlation-ID'))
    logger.info("Login page accessed", correlation_id=correlation_id)
    template_path = os.path.join(os.path.dirname(__file__), 'template', 'login.html')

    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html = f.read()

        canvas_size = get_canvas_size()

        html = html.replace('{{OAUTH_LOGIN_URL}}', OAUTH_LOGIN_URL)
        html = html.replace('{{CANVAS_SIZE}}', str(canvas_size))

        response = make_response(html)
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except FileNotFoundError:
        logger.error("Login template not found", template_path=template_path)
        return make_response("Error: Login template not found", 500)
    except Exception as e:
        logger.error("Error generating login page HTML", error=e, correlation_id=correlation_id)
        return make_response("Error loading login page", 500)

@app.route('/canvas', methods=['GET'])
def canvas_page():
    correlation_id = getattr(flask_request, 'correlation_id', flask_request.headers.get('X-Correlation-ID'))
    session_id = flask_request.args.get("session")
    logger.info("Canvas page accessed", correlation_id=correlation_id, has_session=bool(session_id))
    template_path = os.path.join(os.path.dirname(__file__), 'template', 'canvas.html')

    try:
        current_webhook_url = WEBHOOK_URL or _build_webhook_url(flask_request)
        logger.info(
            "Using webhook URL for frontend client",
            correlation_id=correlation_id,
            webhook_url=current_webhook_url,
            source="env" if WEBHOOK_URL else "dynamic"
        )

        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                html = f.read()

            config_script = f'''<script>
window.SESSION_ID = {repr(session_id) if session_id else 'null'};
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
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        logger.error("Error generating canvas page HTML", error=e, correlation_id=correlation_id)
        return make_response("Error loading canvas page", 500)


def _build_webhook_url(request):
    scheme = request.headers.get('X-Forwarded-Proto', request.scheme)
    host = request.headers.get('Host', request.host)
    url = f"{scheme}://{host}/webhook"
    logger.info("Constructed dynamic webhook URL", scheme=scheme, host=host, url=url)
    return url

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
    clean_filename = filename.split('?')[0]
    response = send_from_directory(js_dir, clean_filename)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/css/<path:filename>')
def serve_css(filename):
    css_dir = os.path.join(os.path.dirname(__file__), 'css')
    return send_from_directory(css_dir, filename)

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
    return send_from_directory(assets_dir, filename)

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
    app.run(host='0.0.0.0', port=8080, debug=False)
