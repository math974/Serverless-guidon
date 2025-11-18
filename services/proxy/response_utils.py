"""Response utilities."""
import os

def get_proxy_url(request=None) -> str:
    """Get proxy URL for Cloud Functions Gen2, ensuring HTTPS.
    Args:
        request: Functions Framework request object (optional)

    Returns:
        Proxy URL with HTTPS (base URL without path)
    """
    proxy_url = os.environ.get('PROXY_SERVICE_URL')

    if not proxy_url and request:
        host = request.headers.get('Host')
        scheme = request.headers.get('X-Forwarded-Proto', 'https')

        if host:
            if 'cloudfunctions.net' in host:
                proxy_url = f"{scheme}://{host}"
            else:
                proxy_url = f"{scheme}://{host}"

    if not proxy_url:
        project_id = os.environ.get('GCP_PROJECT_ID', os.environ.get('GOOGLE_CLOUD_PROJECT', 'serverless-ejguidon-dev'))
        region = os.environ.get('FUNCTION_REGION', 'europe-west1')
        function_name = os.environ.get('FUNCTION_TARGET', 'proxy')
        proxy_url = f"https://{region}-{project_id}.cloudfunctions.net/{function_name}"

    # Ensure HTTPS
    if proxy_url.startswith('http://'):
        proxy_url = proxy_url.replace('http://', 'https://', 1)

    proxy_url = proxy_url.rstrip('/')

    if 'cloudfunctions.net' in proxy_url and proxy_url.count('/') == 2:
        function_name = os.environ.get('FUNCTION_TARGET', 'proxy')
        proxy_url = f"{proxy_url}/{function_name}"

    return proxy_url


def get_error_response(interaction_type: str, error_type: str = 'unavailable') -> tuple:
    """Get error response formatted for interaction type.

    Args:
        interaction_type: 'discord' or 'web'
        error_type: 'unavailable' or 'internal'

    Returns:
        Tuple of (response_dict, status_code)
    """
    if interaction_type == 'discord':
        if error_type == 'unavailable':
            return {
                'type': 4,
                'data': {
                    'embeds': [{
                        'title': 'Service Temporarily Unavailable',
                        'description': 'The message queue is temporarily unavailable. Please try again in a moment.',
                        'color': 0xFF0000,
                        'footer': {'text': 'Service continues running - error logged'}
                    }]
                }
            }, 200
        else:
            return {
                'type': 4,
                'data': {
                    'embeds': [{
                        'title': 'Internal Error',
                        'description': 'An unexpected error occurred. The service is still running.',
                        'color': 0xFF0000,
                        'footer': {'text': 'Error logged - service continues running'}
                    }]
                }
            }, 200
    else:
        if error_type == 'unavailable':
            return {
                'status': 'error',
                'message': 'Service temporarily unavailable. Please try again in a moment.'
            }, 503
        else:
            return {
                'status': 'error',
                'message': 'An unexpected error occurred.'
            }, 500
