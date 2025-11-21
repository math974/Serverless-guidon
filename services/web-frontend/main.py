"""Web frontend for Guidon - Canvas drawing interface."""
import os
import sys
from flask import Flask, request, make_response, jsonify, send_from_directory, Request
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shared.observability import init_observability, traced_function
from shared.correlation import with_correlation

app = Flask(__name__)
logger, tracing = init_observability('web-frontend', app=None)

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

@app.route('/', methods=['GET'])
@with_correlation(logger)
@traced_function("web_app")
def web_app(request: Request):
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))
    try:
        path = request.path
        method = request.method
        logger.info("Web request received", correlation_id=correlation_id, path=path, method=method)
        path_clean = path.rstrip('/')
        if path_clean == '/canvas' or path_clean == '':
            return canvas_page()
        return session_page()
    except Exception as e:
        logger.error("Error in web_app", error=e, correlation_id=correlation_id, path=request.path)
        return make_response("Internal server error", 500)

@app.route('/canvas', methods=['GET'])
def canvas_page():
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))
    session_id = request.args.get("session")
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
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                html = f.read()
            html = html.replace(
                '<script>',
                f'''<script>\n    const SESSION_ID = {repr(session_id)};\n    const GATEWAY_URL = {repr(GATEWAY_URL)};\n    if (SESSION_ID) {{\n        localStorage.setItem('guidon_session', SESSION_ID);\n    }}'''
            )
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
    session_id = request.args.get("session")
    username = request.args.get("user", "Visitor")
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
    app.run(host='0.0.0.0', port=8080)